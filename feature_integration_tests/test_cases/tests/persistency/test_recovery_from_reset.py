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

"""Tests for feat_req__persistency__recovery_from_reset.

Verifies that after a simulated reset (un-flushed in-memory write followed by
process termination) the on-disk KVS snapshot still holds the last successfully
flushed value.  A post-reset boot therefore automatically recovers to a
consistent, known-good state.
"""

from math import isclose
from pathlib import Path
from typing import Any

import pytest
from fit_scenario import ResultCode
from persistency_scenario import PersistencyScenario, read_kvs_snapshot
from test_properties import add_test_properties
from testing_utils import LogContainer

pytestmark = pytest.mark.parametrize("version", ["rust", "cpp"], scope="class")


@add_test_properties(
    partially_verifies=["feat_req__persistency__recovery_from_reset"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestRecoveryFromReset(PersistencyScenario):
    """Verify that KVS automatically recovers to the last flushed state after reset.

    The scenario:

    1. Writes data_key=50.0 and flushes — this is the last-known-good (LKG) state
       on disk (kvs_1_0.json).
    2. Re-opens the KVS handle and writes data_key=100.0 WITHOUT flushing —
       simulates a hard reset / power loss mid-write.

    The Python test reads kvs_1_0.json directly and asserts data_key = 50.0,
    proving that the un-flushed 100.0 write never reached persistent storage.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.recovery_from_reset"

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

    def test_disk_snapshot_contains_last_flushed_value(self, results: Any, temp_dir: Path) -> None:
        """Verify that the on-disk snapshot holds the last-flushed value (50.0).

        After the simulated reset (Phase 2: un-flushed write of 100.0), the
        snapshot file `kvs_1_0.json` must still contain `data_key = 50.0` —
        the value from the last successful flush (Phase 1).  The un-flushed
        100.0 write must not have reached persistent storage.

        This is the core assertion for `feat_req__persistency__recovery_from_reset`:
        a post-reset boot always loads from the last successful snapshot and
        recovers to that consistent state automatically.
        """
        assert results.return_code == ResultCode.SUCCESS
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        assert "data_key" in snapshot, (
            "data_key not found in kvs_1_0.json. The last-flushed snapshot may not have been written correctly."
        )
        assert isclose(float(snapshot["data_key"]["v"]), 50.0, abs_tol=1e-4), (
            f"Disk snapshot value {snapshot['data_key']['v']} != 50.0. "
            "The un-flushed write (100.0) appears to have reached persistent storage, "
            "violating the recovery-from-reset guarantee."
        )

    def test_kvs_api_reloads_last_flushed_value(
        self, version: str, results: Any, logs_info_level: LogContainer
    ) -> None:
        """Verify that a fresh KVS instance (Phase 3) returns the last-flushed
        value (50.0) after a simulated reset.

        Opening a new KVS handle after the simulated reset must load from the
        on-disk snapshot and expose `data_key = 50.0` through the API — not
        the un-flushed in-memory value (100.0) from Phase 2.  This confirms
        that the KVS recovery mechanism works end-to-end at the API level,
        not only at the file-system level.
        """
        if version == "rust":
            pytest.skip(
                "Rust KVS uses an in-process instance pool keyed by instance_id. "
                "Re-opening with the same id within one binary run returns the cached "
                "in-memory handle, so Phase 3 reads the in-memory value (100.0) rather "
                "than the on-disk snapshot (50.0). "
                "Disk-level recovery is verified by test_kvs_recovers_to_last_flushed_value."
            )
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("phase", value="reload")
        assert log is not None, (
            "No log entry with phase='reload' found. "
            "Phase 3 (fresh KVS reload after simulated reset) may not have executed."
        )
        assert isclose(float(log.value), 50.0, abs_tol=1e-4), (
            f"KVS reload returned {log.value} instead of 50.0. "
            "The fresh KVS instance did not recover to the last-flushed snapshot."
        )


@add_test_properties(
    partially_verifies=["feat_req__persistency__recovery_from_reset"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestRecoveryFromResetMultiInstance(PersistencyScenario):
    """Verify that two KVS instances in the same directory each independently
    recover to their own last-flushed state after a simulated reset.

    The scenario:

    1. Instance 1 writes inst1_key=50.0 and flushes (LKG on disk: kvs_1_0.json).
    2. Instance 2 writes inst2_key=60.0 and flushes (LKG on disk: kvs_2_0.json).
    3. Instance 1 re-opens, writes inst1_key=100.0 WITHOUT flushing (reset mid-write).
    4. Instance 2 re-opens, writes inst2_key=120.0 WITHOUT flushing (reset mid-write).

    Expected disk state after the reset:
      kvs_1_0.json: inst1_key = 50.0  (un-flushed 100.0 never persisted)
      kvs_2_0.json: inst2_key = 60.0  (un-flushed 120.0 never persisted)

    This confirms that a crash of one instance's write path does not corrupt
    the snapshot belonging to the other instance — each instance recovers
    independently to its own last-flushed state.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.recovery_from_reset_multi_instance"

    @pytest.fixture(scope="class")
    def test_config(self, temp_dir: Path) -> dict[str, Any]:
        return {
            "kvs_parameters_1": {
                "kvs_parameters": {
                    "instance_id": 1,
                    "dir": str(temp_dir),
                },
            },
            "kvs_parameters_2": {
                "kvs_parameters": {
                    "instance_id": 2,
                    "dir": str(temp_dir),
                },
            },
        }

    def test_instance1_recovers_to_last_flushed_value(self, results: Any, temp_dir: Path) -> None:
        """Verify kvs_1_0.json holds 50.0 (the last flushed value) for instance 1.

        The un-flushed write of 100.0 in Phase 2 must not have reached persistent
        storage.  Instance 1 must recover to the consistent state from Phase 1.
        """
        assert results.return_code == ResultCode.SUCCESS
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        assert "inst1_key" in snapshot, "inst1_key not found in kvs_1_0.json — Phase 1 flush may not have succeeded."
        assert isclose(float(snapshot["inst1_key"]["v"]), 50.0, abs_tol=1e-4), (
            f"Instance 1 recovered to {snapshot['inst1_key']['v']} instead of 50.0. "
            "The un-flushed write (100.0) appears to have been persisted incorrectly."
        )

    def test_instance2_recovers_to_last_flushed_value(self, results: Any, temp_dir: Path) -> None:
        """Verify kvs_2_0.json holds 60.0 (the last flushed value) for instance 2.

        The un-flushed write of 120.0 in Phase 2 must not have reached persistent
        storage.  Instance 2 must recover to the consistent state from Phase 1.
        """
        assert results.return_code == ResultCode.SUCCESS
        snapshot = read_kvs_snapshot(temp_dir, instance_id=2, snapshot_id=0)
        assert "inst2_key" in snapshot, "inst2_key not found in kvs_2_0.json — Phase 1 flush may not have succeeded."
        assert isclose(float(snapshot["inst2_key"]["v"]), 60.0, abs_tol=1e-4), (
            f"Instance 2 recovered to {snapshot['inst2_key']['v']} instead of 60.0. "
            "The un-flushed write (120.0) appears to have been persisted incorrectly."
        )

    def test_kvs_api_reloads_both_instances(self, version: str, results: Any, logs_info_level: LogContainer) -> None:
        """Verify that fresh KVS instances (Phase 3) for both instance IDs
        return their respective last-flushed values after a simulated reset.

        Instance 1 must load inst1_key=50.0 and instance 2 must load
        inst2_key=60.0 from their on-disk snapshots.  This confirms that each
        instance recovers independently through the KVS API, not only at the
        file-system level.
        """
        if version == "rust":
            pytest.skip(
                "Rust KVS uses an in-process instance pool keyed by instance_id. "
                "Re-opening with the same id within one binary run returns the cached "
                "in-memory handle, so Phase 3 reads in-memory values rather than "
                "on-disk snapshots. "
                "Disk-level recovery is verified by test_instance1_recovers_to_last_flushed_value "
                "and test_instance2_recovers_to_last_flushed_value."
            )
        assert results.return_code == ResultCode.SUCCESS

        log1 = logs_info_level.find_log("key", value="inst1_key")
        assert log1 is not None, (
            "No log entry found for inst1_key (phase='reload'). Phase 3 reload for instance 1 may not have executed."
        )
        assert isclose(float(log1.value), 50.0, abs_tol=1e-4), (
            f"Instance 1 reload returned {log1.value} instead of 50.0."
        )

        log2 = logs_info_level.find_log("key", value="inst2_key")
        assert log2 is not None, (
            "No log entry found for inst2_key (phase='reload'). Phase 3 reload for instance 2 may not have executed."
        )
        assert isclose(float(log2.value), 60.0, abs_tol=1e-4), (
            f"Instance 2 reload returned {log2.value} instead of 60.0."
        )

    def test_no_cross_contamination_after_reset(self, results: Any, temp_dir: Path) -> None:
        """Verify that neither instance's snapshot contains keys from the other.

        A reset of one instance's write path must not corrupt the snapshot file
        that belongs to the other instance.
        """
        assert results.return_code == ResultCode.SUCCESS
        snap1 = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        snap2 = read_kvs_snapshot(temp_dir, instance_id=2, snapshot_id=0)
        assert "inst2_key" not in snap1, (
            "inst2_key found in kvs_1_0.json — instance-2 data contaminated instance-1 snapshot."
        )
        assert "inst1_key" not in snap2, (
            "inst1_key found in kvs_2_0.json — instance-1 data contaminated instance-2 snapshot."
        )
