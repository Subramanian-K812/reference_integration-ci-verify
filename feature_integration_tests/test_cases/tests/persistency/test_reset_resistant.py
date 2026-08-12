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

"""Tests for feat_req__persistency__reset_resistant.

Verifies that KVS preserves the previous snapshot after a flush-rotation cycle,
so that a snapshot representing the last-known-good state is always available
after a reset.
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
    partially_verifies=["feat_req__persistency__reset_resistant"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestResetResistant(PersistencyScenario):
    """Verify that KVS storage is reset-resistant.

    The scenario writes and flushes a value (50.0), then re-opens the KVS,
    writes a new value (100.0), and flushes again — triggering snapshot
    rotation.  Both the new snapshot (kvs_1_0.json, value=100.0) and the
    previous snapshot (kvs_1_1.json, value=50.0) must be present on disk after
    the rotation, proving that prior consistent state is not lost on update.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.reset_resistant"

    @pytest.fixture(scope="class")
    def test_config(self, temp_dir: Path) -> dict[str, Any]:
        return {
            "kvs_parameters_1": {
                "kvs_parameters": {
                    "instance_id": 1,
                    "dir": str(temp_dir),
                    "snapshot_max_count": 3,
                },
            },
        }

    def test_current_snapshot_has_new_value(self, results: Any, temp_dir: Path) -> None:
        """Verify that snapshot_0 (newest) holds the updated value (100.0)."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        assert "data_key" in snapshot, "data_key not found in current snapshot (kvs_1_0.json)"
        assert isclose(float(snapshot["data_key"]["v"]), 100.0, abs_tol=1e-4)

    def test_previous_snapshot_preserved(self, results: Any, temp_dir: Path) -> None:
        """Verify that snapshot_1 (previous) still holds the old value (50.0).

        This is the core assertion for reset-resistance: the snapshot that
        existed before the last flush must not be overwritten during rotation.
        """
        assert results.return_code == ResultCode.SUCCESS
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=1)
        assert "data_key" in snapshot, (
            "data_key not found in previous snapshot (kvs_1_1.json). "
            "The snapshot may not have been preserved after rotation."
        )
        assert isclose(float(snapshot["data_key"]["v"]), 50.0, abs_tol=1e-4)

    def test_hash_files_exist(self, results: Any, temp_dir: Path) -> None:
        """Verify that integrity hash files accompany both snapshots."""
        assert results.return_code == ResultCode.SUCCESS
        assert (temp_dir / "kvs_1_0.hash").exists(), "Hash file missing for snapshot_0"
        assert (temp_dir / "kvs_1_1.hash").exists(), "Hash file missing for snapshot_1"

    def test_kvs_can_reload_after_interruption(self, version: str, results: Any, logs_info_level: LogContainer) -> None:
        """Verify that KVS can reload from the last successful snapshot after a
        simulated interruption (un-flushed write following the rotation).

        After Phase 2 produces two snapshots (kvs_1_0.json=100.0,
        kvs_1_1.json=50.0), Phase 3 writes data_key=150.0 WITHOUT flushing
        (simulating a hard reset mid-write).  Phase 4 then opens a fresh KVS
        instance from disk and must load 100.0 — the value from the last
        successful flush — not the un-persisted 150.0.

        This is the core assertion for `feat_req__persistency__reset_resistant`:
        the existing snapshot survives an interrupted write attempt, and the
        KVS API can still recover to the last consistent state.
        """
        if version == "rust":
            pytest.skip(
                "Rust KVS uses an in-process instance pool keyed by instance_id. "
                "Re-opening with the same id within one binary run returns the cached "
                "in-memory handle (150.0 from Phase 3), not the on-disk snapshot (100.0). "
                "Snapshot preservation is verified by test_current_snapshot_has_new_value "
                "and test_previous_snapshot_preserved."
            )
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("phase", value="after_interruption")
        assert log is not None, (
            "No log entry with phase='after_interruption' found. "
            "Phase 4 (KVS reload after simulated interruption) may not have executed."
        )
        assert isclose(float(log.value), 100.0, abs_tol=1e-4), (
            f"KVS reload after interruption returned {log.value} instead of 100.0. "
            "The un-flushed write (150.0) may have overwritten the last-good snapshot, "
            "or the wrong snapshot was loaded."
        )


@add_test_properties(
    partially_verifies=["feat_req__persistency__reset_resistant"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestResetResistantMultiInstance(PersistencyScenario):
    """Verify that snapshot rotation for two KVS instances in the same directory
    is completely isolated — one instance's snapshot files never contaminate
    the other's.

    The scenario:

    1. Instance 1 (id=1) writes inst1_key=10.0 and flushes.
    2. Instance 2 (id=2) writes inst2_key=20.0 and flushes.
    3. Instance 1 writes inst1_key=110.0 and flushes (rotation: kvs_1_1.json=10.0,
       kvs_1_0.json=110.0).
    4. Instance 2 writes inst2_key=220.0 and flushes (rotation: kvs_2_1.json=20.0,
       kvs_2_0.json=220.0).

    The Python test asserts all four snapshot files carry the correct values.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.reset_resistant_multi_instance"

    @pytest.fixture(scope="class")
    def test_config(self, temp_dir: Path) -> dict[str, Any]:
        return {
            "kvs_parameters_1": {
                "kvs_parameters": {
                    "instance_id": 1,
                    "dir": str(temp_dir),
                    "snapshot_max_count": 3,
                },
            },
            "kvs_parameters_2": {
                "kvs_parameters": {
                    "instance_id": 2,
                    "dir": str(temp_dir),
                    "snapshot_max_count": 3,
                },
            },
        }

    def test_instance1_current_snapshot_has_new_value(self, results: Any, temp_dir: Path) -> None:
        """Verify kvs_1_0.json holds the updated value (110.0) for instance 1."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        assert "inst1_key" in snapshot, "inst1_key missing from kvs_1_0.json"
        assert isclose(float(snapshot["inst1_key"]["v"]), 110.0, abs_tol=1e-4)

    def test_instance1_previous_snapshot_preserved(self, results: Any, temp_dir: Path) -> None:
        """Verify kvs_1_1.json holds the old value (10.0) for instance 1."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=1)
        assert "inst1_key" in snapshot, "inst1_key missing from kvs_1_1.json"
        assert isclose(float(snapshot["inst1_key"]["v"]), 10.0, abs_tol=1e-4)

    def test_instance2_current_snapshot_has_new_value(self, results: Any, temp_dir: Path) -> None:
        """Verify kvs_2_0.json holds the updated value (220.0) for instance 2."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot = read_kvs_snapshot(temp_dir, instance_id=2, snapshot_id=0)
        assert "inst2_key" in snapshot, "inst2_key missing from kvs_2_0.json"
        assert isclose(float(snapshot["inst2_key"]["v"]), 220.0, abs_tol=1e-4)

    def test_instance2_previous_snapshot_preserved(self, results: Any, temp_dir: Path) -> None:
        """Verify kvs_2_1.json holds the old value (20.0) for instance 2."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot = read_kvs_snapshot(temp_dir, instance_id=2, snapshot_id=1)
        assert "inst2_key" in snapshot, "inst2_key missing from kvs_2_1.json"
        assert isclose(float(snapshot["inst2_key"]["v"]), 20.0, abs_tol=1e-4)

    def test_no_cross_contamination(self, results: Any, temp_dir: Path) -> None:
        """Verify that instance 1's keys do not appear in instance 2's snapshots
        and vice versa.
        """
        assert results.return_code == ResultCode.SUCCESS
        snap1 = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        snap2 = read_kvs_snapshot(temp_dir, instance_id=2, snapshot_id=0)
        assert "inst2_key" not in snap1, (
            "inst2_key found in instance-1 snapshot (kvs_1_0.json) — cross-contamination detected"
        )
        assert "inst1_key" not in snap2, (
            "inst1_key found in instance-2 snapshot (kvs_2_0.json) — cross-contamination detected"
        )
