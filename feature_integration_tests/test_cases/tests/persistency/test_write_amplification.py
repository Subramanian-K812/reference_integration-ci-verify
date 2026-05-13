# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

"""Tests for feat_req__persistency__write_amplification.

Verifies that flush() minimises write amplification: multiple pending writes
are batched into a single storage operation, producing one snapshot file
regardless of how many keys were written.  Three scenarios cover the file-count
invariant, the all-keys-in-one-file guarantee, and cross-instance file isolation.
"""

from math import isclose
from pathlib import Path
from typing import Any

import pytest
from fit_scenario import ResultCode
from persistency_scenario import PersistencyScenario, read_kvs_snapshot, verify_kvs_snapshot_hash
from test_properties import add_test_properties
from testing_utils import LogContainer

pytestmark = pytest.mark.parametrize("version", ["rust", "cpp"], scope="class")


@add_test_properties(
    partially_verifies=["feat_req__persistency__write_amplification"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestWriteAmplification(PersistencyScenario):
    """Verify that writing 10 keys and flushing once creates exactly 1 snapshot file.

    Write amplification is the ratio of bytes written to storage vs bytes of
    user data.  The strongest observable form at FIT level is that N key writes
    followed by a single flush() produce exactly 1 snapshot file — not N files.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.write_amplification"

    @pytest.fixture(scope="class")
    def test_config(self, temp_dir: Path) -> dict[str, Any]:
        return {
            "kvs_parameters_1": {
                "kvs_parameters": {
                    "instance_id": 1,
                    "dir": str(temp_dir),
                },
            },
        }

    def test_single_snapshot_file_created(self, results: Any, temp_dir: Path) -> None:
        """Verify exactly one snapshot JSON file exists after 10 writes and one flush."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot_files = list(temp_dir.glob("kvs_1_*.json"))
        assert len(snapshot_files) == 1, (
            f"Expected 1 snapshot file after single flush, found {len(snapshot_files)}: {snapshot_files}"
        )

    def test_single_hash_file_created(self, results: Any, temp_dir: Path) -> None:
        """Verify exactly one hash file accompanies the snapshot."""
        assert results.return_code == ResultCode.SUCCESS
        hash_files = list(temp_dir.glob("kvs_1_*.hash"))
        assert len(hash_files) == 1, f"Expected 1 hash file after single flush, found {len(hash_files)}: {hash_files}"

    def test_snapshot_count_logged_as_one(self, version: str, results: Any, logs_info_level: LogContainer) -> None:
        """Verify the scenario logs snapshot_count=1 after the single flush.

        Note: This assertion is only meaningful for the Rust path.  The C++
        wrapper does not expose snapshot_count() so the C++ scenario hardcodes
        the value 1 in its log output.  The authoritative single-file check for
        C++ is test_single_snapshot_file_created, which counts actual files.
        """
        assert results.return_code == ResultCode.SUCCESS
        if version == "cpp":
            return  # C++ hardcodes snapshot_count=1; file-glob test is authoritative.
        log = logs_info_level.find_log("phase", value="after_single_flush")
        assert log is not None, "No after_single_flush log entry"
        assert int(log.snapshot_count) == 1, f"Expected snapshot_count=1, got {log.snapshot_count}"


@add_test_properties(
    partially_verifies=["feat_req__persistency__write_amplification"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestWriteAmplificationSingleFlushCoversAllKeys(PersistencyScenario):
    """Verify that a single flush captures the complete key set in one snapshot.

    Writing keys A, B, C and flushing once must produce a single snapshot
    containing all three keys.  This confirms the batched-write property:
    the entire in-memory state is transferred to disk in one storage write.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.write_amplification_single_flush_covers_all_keys"

    @pytest.fixture(scope="class")
    def test_config(self, temp_dir: Path) -> dict[str, Any]:
        return {
            "kvs_parameters_1": {
                "kvs_parameters": {
                    "instance_id": 1,
                    "dir": str(temp_dir),
                },
            },
        }

    def test_all_keys_in_single_snapshot(self, results: Any, temp_dir: Path) -> None:
        """Verify the single snapshot file contains all three written keys."""
        assert results.return_code == ResultCode.SUCCESS
        verify_kvs_snapshot_hash(temp_dir, instance_id=1, snapshot_id=0)
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        for key in ("wa_key_a", "wa_key_b", "wa_key_c"):
            assert key in snapshot, f"{key} missing from the single snapshot — incomplete batch write"

    def test_only_one_snapshot_created(self, results: Any, temp_dir: Path) -> None:
        """Verify one flush produced exactly one snapshot file."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot_files = list(temp_dir.glob("kvs_1_*.json"))
        assert len(snapshot_files) == 1, f"Expected 1 snapshot file, found {len(snapshot_files)}: {snapshot_files}"


@add_test_properties(
    partially_verifies=["feat_req__persistency__write_amplification"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestWriteAmplificationMultiInstance(PersistencyScenario):
    """Verify that each instance's flush writes only to its own snapshot file.

    Instance 1 writes wa_key_a and flushes; instance 2 writes wa_key_b and
    flushes.  The snapshots must be fully disjoint: kvs_1_0.json contains ONLY
    wa_key_a and kvs_2_0.json contains ONLY wa_key_b.  Cross-contamination
    would indicate a write amplification bug where one instance's flush touches
    another instance's storage file.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.write_amplification_multi_instance"

    @pytest.fixture(scope="class")
    def test_config(self, temp_dir: Path) -> dict[str, Any]:
        return {
            "kvs_parameters_1": {
                "kvs_parameters": {"instance_id": 1, "dir": str(temp_dir)},
            },
            "kvs_parameters_2": {
                "kvs_parameters": {"instance_id": 2, "dir": str(temp_dir)},
            },
        }

    def test_instance_1_snapshot_has_only_key_a(self, results: Any, temp_dir: Path) -> None:
        """Instance 1 snapshot must contain wa_key_a and must NOT contain wa_key_b."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot1 = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        assert "wa_key_a" in snapshot1, "wa_key_a missing from instance 1 snapshot"
        assert "wa_key_b" not in snapshot1, (
            "wa_key_b leaked into instance 1 snapshot — cross-instance write amplification"
        )

    def test_instance_2_snapshot_has_only_key_b(self, results: Any, temp_dir: Path) -> None:
        """Instance 2 snapshot must contain wa_key_b and must NOT contain wa_key_a."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot2 = read_kvs_snapshot(temp_dir, instance_id=2, snapshot_id=0)
        assert "wa_key_b" in snapshot2, "wa_key_b missing from instance 2 snapshot"
        assert "wa_key_a" not in snapshot2, (
            "wa_key_a leaked into instance 2 snapshot — cross-instance write amplification"
        )

    def test_two_snapshot_files_total(self, results: Any, temp_dir: Path) -> None:
        """Verify exactly one snapshot per instance — two files total."""
        assert results.return_code == ResultCode.SUCCESS
        assert (temp_dir / "kvs_1_0.json").exists(), "kvs_1_0.json missing"
        assert (temp_dir / "kvs_2_0.json").exists(), "kvs_2_0.json missing"
        # No extra snapshot files should exist.
        all_snapshots = list(temp_dir.glob("kvs_*.json"))
        # Exclude default files (kvs_N_default.json).
        data_snapshots = [f for f in all_snapshots if "_default" not in f.name]
        assert len(data_snapshots) == 2, (
            f"Expected exactly 2 snapshot files (one per instance), found {len(data_snapshots)}: {data_snapshots}"
        )


@add_test_properties(
    partially_verifies=["feat_req__persistency__write_amplification"],
    test_type="requirements-based",
    derivation_technique="boundary-value-analysis",
)
class TestWriteAmplificationOverwriteSameKey(PersistencyScenario):
    """Verify that overwriting the same key N times and flushing once produces a single entry.

    The scenario writes ow_key=V1, then V2, then V3 — all in the cache without
    flushing — then flushes once.  The snapshot must contain ow_key exactly
    once with value V3=3.0.  If the serializer emits one entry per set_value
    call (3 entries), that is write amplification.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.write_amplification_overwrite_same_key"

    @pytest.fixture(scope="class")
    def test_config(self, temp_dir: Path) -> dict[str, Any]:
        return {
            "kvs_parameters_1": {
                "kvs_parameters": {
                    "instance_id": 1,
                    "dir": str(temp_dir),
                },
            },
        }

    def test_single_snapshot_file(self, results: Any, temp_dir: Path) -> None:
        """Verify 3 overwrites + 1 flush = exactly 1 snapshot file."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot_files = list(temp_dir.glob("kvs_1_*.json"))
        assert len(snapshot_files) == 1, f"Expected 1 snapshot file, found {len(snapshot_files)}: {snapshot_files}"

    def test_snapshot_contains_latest_value(self, results: Any, temp_dir: Path) -> None:
        """Verify the snapshot holds ow_key=3.0 (V3), not V1 or V2."""
        assert results.return_code == ResultCode.SUCCESS
        verify_kvs_snapshot_hash(temp_dir, instance_id=1, snapshot_id=0)
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        assert "ow_key" in snapshot, "ow_key missing from snapshot"
        assert isclose(float(snapshot["ow_key"]["v"]), 3.0, abs_tol=1e-4), (
            f"Expected ow_key=3.0 (V3) in snapshot, got {snapshot['ow_key']}"
        )

    def test_logged_value_is_latest(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify the scenario logs ow_key=3.0 (V3) from the in-memory cache."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("phase", value="after_overwrite_flush")
        assert log is not None, "No after_overwrite_flush log entry"
        assert isclose(float(log.value), 3.0, abs_tol=1e-4), f"Expected ow_key=3.0, got {log.value}"


@add_test_properties(
    partially_verifies=["feat_req__persistency__write_amplification"],
    test_type="requirements-based",
    derivation_technique="boundary-value-analysis",
)
class TestWriteAmplificationMultipleFlushes(PersistencyScenario):
    """Verify that each flush creates exactly one new snapshot file (bounded growth).

    The scenario performs two write+flush cycles with snapshot_max_count=2.
    After flush 1: exactly 1 snapshot file.  After flush 2: exactly 2 snapshot
    files.  This confirms one-flush-one-snapshot semantics, ruling out
    amplification from repeated flushing.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.write_amplification_multiple_flushes"

    @pytest.fixture(scope="class")
    def test_config(self, temp_dir: Path) -> dict[str, Any]:
        return {
            "kvs_parameters_1": {
                "kvs_parameters": {
                    "instance_id": 1,
                    "dir": str(temp_dir),
                    "snapshot_max_count": 3,  # C++ KVS wrapper requires minimum 3.
                },
            },
        }

    def test_two_snapshot_files_after_two_flushes(self, results: Any, temp_dir: Path) -> None:
        """Verify exactly 2 snapshot files exist after 2 flush cycles."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot_files = [f for f in temp_dir.glob("kvs_1_*.json") if "_default" not in f.name]
        assert len(snapshot_files) == 2, (
            f"Expected 2 snapshot files after 2 flushes, found {len(snapshot_files)}: {snapshot_files}"
        )

    def test_snapshot_count_increments(self, version: str, results: Any, logs_info_level: LogContainer) -> None:
        """Verify snapshot_count is 1 after flush 1 and 2 after flush 2.

        Note: This assertion is only meaningful for the Rust path.  The C++
        wrapper does not expose snapshot_count() so the C++ scenario hardcodes
        the values 1 and 2 in its log output.  The authoritative bounded-growth
        check for C++ is test_two_snapshot_files_after_two_flushes.
        """
        assert results.return_code == ResultCode.SUCCESS
        if version == "cpp":
            return  # C++ hardcodes snapshot_count values; file-count test is authoritative.
        log1 = logs_info_level.find_log("phase", value="after_flush_1")
        assert log1 is not None, "No after_flush_1 log entry"
        assert int(log1.snapshot_count) == 1, f"Expected snapshot_count=1 after flush 1, got {log1.snapshot_count}"

        log2 = logs_info_level.find_log("phase", value="after_flush_2")
        assert log2 is not None, "No after_flush_2 log entry"
        assert int(log2.snapshot_count) == 2, f"Expected snapshot_count=2 after flush 2, got {log2.snapshot_count}"
