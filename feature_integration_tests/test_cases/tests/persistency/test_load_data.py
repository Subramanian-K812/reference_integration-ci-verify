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

"""Tests for feat_req__persistency__load_data.

Verifies that key-value pairs written and flushed in one KVS session are
correctly loaded in a subsequent session.  Three scenarios exercise different
aspects of the load guarantee: basic single-key round-trip, most-recent-wins
semantics after multiple flushes, and cross-instance isolation during load.
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
    partially_verifies=["feat_req__persistency__load_data"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestLoadData(PersistencyScenario):
    """Verify that a value written and flushed is loadable from persistent storage.

    The scenario:
    1. Opens KVS, writes data_key=42.0, flushes, drops the handle.
    2. Reopens KVS (forces reload from disk snapshot), reads data_key.

    Both the snapshot file on disk and the value logged after reload are
    verified to contain 42.0.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.load_data"

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

    def test_snapshot_contains_written_value(self, results: Any, temp_dir: Path) -> None:
        """Verify the snapshot file contains data_key=42.0 after flush."""
        assert results.return_code == ResultCode.SUCCESS
        verify_kvs_snapshot_hash(temp_dir, instance_id=1, snapshot_id=0)
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        assert "data_key" in snapshot, "data_key missing from snapshot"
        assert isclose(float(snapshot["data_key"]["v"]), 42.0, abs_tol=1e-4)

    def test_value_readable_after_reload(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify the reload phase log confirms data_key=42.0 was loaded from disk."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("key", value="data_key")
        assert log is not None, "No reload log entry found for data_key"
        assert isclose(float(log.value), 42.0, abs_tol=1e-4), f"Expected 42.0 after reload, got {log.value}"


@add_test_properties(
    partially_verifies=["feat_req__persistency__load_data"],
    test_type="requirements-based",
    derivation_technique="boundary-value-analysis",
)
class TestLoadDataAfterMultipleFlushes(PersistencyScenario):
    """Verify that KVS loads the most recent snapshot after multiple successive flushes.

    The scenario writes V1=10.0, V2=20.0, V3=30.0 each with a separate flush,
    then reopens.  The loaded value must be 30.0 (V3), proving the most-recent-
    wins semantics required by feat_req__persistency__load_data.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.load_data_after_multiple_flushes"

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

    def test_latest_value_loaded(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify the reload log shows 30.0 (V3), not an older value."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("phase", value="reload_latest")
        assert log is not None, "No reload_latest log entry found"
        assert isclose(float(log.value), 30.0, abs_tol=1e-4), f"Expected most-recent value 30.0, got {log.value}"

    def test_current_snapshot_has_latest_value(self, results: Any, temp_dir: Path) -> None:
        """Verify the newest snapshot holds V3=30.0.

        The KVS uses a ring-buffer rotation scheme where snapshot_id=0 always
        refers to the current (newest) slot.  With snapshot_max_count=3 and 3
        flushes, kvs_1_0.json contains the latest state (V3=30.0).
        """
        assert results.return_code == ResultCode.SUCCESS
        verify_kvs_snapshot_hash(temp_dir, instance_id=1, snapshot_id=0)
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        assert "data_key" in snapshot, "data_key missing from newest snapshot"
        assert isclose(float(snapshot["data_key"]["v"]), 30.0, abs_tol=1e-4)


@add_test_properties(
    partially_verifies=[
        "feat_req__persistency__load_data",
        "feat_req__persistency__store_data",
    ],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestLoadDataMultiInstance(PersistencyScenario):
    """Verify that two KVS instances in the same directory each load only their own data.

    Instance 1 writes key_a=10.0; instance 2 writes key_b=20.0.  After flush
    and reload, instance 1 must return key_a and must NOT expose key_b, and
    vice versa.  This is the multi-instance isolation property of
    feat_req__persistency__load_data.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.load_data_multi_instance"

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

    def test_instance_1_loaded_own_key(self, results: Any, logs_info_level: LogContainer) -> None:
        """Instance 1 reload log must contain key_a=10.0."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("instance", value="1")
        assert log is not None, "No reload log found for instance 1"
        assert log.key == "key_a", f"Expected key='key_a' in instance 1 log, got '{log.key}'"
        assert isclose(float(log.value), 10.0, abs_tol=1e-4)

    def test_instance_2_loaded_own_key(self, results: Any, logs_info_level: LogContainer) -> None:
        """Instance 2 reload log must contain key_b=20.0."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("instance", value="2")
        assert log is not None, "No reload log found for instance 2"
        assert log.key == "key_b", f"Expected key='key_b' in instance 2 log, got '{log.key}'"
        assert isclose(float(log.value), 20.0, abs_tol=1e-4)

    def test_snapshot_isolation_instance_1(self, results: Any, temp_dir: Path) -> None:
        """Snapshot 1 must contain key_a and must NOT contain key_b."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot1 = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        assert "key_a" in snapshot1, "key_a missing from instance 1 snapshot"
        assert "key_b" not in snapshot1, "key_b leaked into instance 1 snapshot"

    def test_snapshot_isolation_instance_2(self, results: Any, temp_dir: Path) -> None:
        """Snapshot 2 must contain key_b and must NOT contain key_a."""
        assert results.return_code == ResultCode.SUCCESS
        snapshot2 = read_kvs_snapshot(temp_dir, instance_id=2, snapshot_id=0)
        assert "key_b" in snapshot2, "key_b missing from instance 2 snapshot"
        assert "key_a" not in snapshot2, "key_a leaked into instance 2 snapshot"


@add_test_properties(
    partially_verifies=["feat_req__persistency__load_data"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestLoadDataMultipleKeys(PersistencyScenario):
    """Verify that all keys written in one session are loadable in the next.

    The scenario writes 5 distinct keys (mk_key_0..mk_key_4) with a single
    flush, then reopens and reads each key back.  A serializer that silently
    drops all but the first key would pass the single-key scenario but fail
    here.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.load_data_multiple_keys"

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

    def test_all_keys_present_in_log(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify the reload log contains an entry for every written key."""
        assert results.return_code == ResultCode.SUCCESS
        expected = {f"mk_key_{i}": float(i * 10) for i in range(5)}
        for key, exp_val in expected.items():
            log = logs_info_level.find_log("key", value=key)
            assert log is not None, f"No reload log entry for {key}"
            assert isclose(float(log.value), exp_val, abs_tol=1e-4), f"Expected {key}={exp_val}, got {log.value}"

    def test_all_keys_in_snapshot(self, results: Any, temp_dir: Path) -> None:
        """Verify all 5 keys are persisted in the snapshot file."""
        assert results.return_code == ResultCode.SUCCESS
        verify_kvs_snapshot_hash(temp_dir, instance_id=1, snapshot_id=0)
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        for i in range(5):
            key = f"mk_key_{i}"
            assert key in snapshot, f"{key} missing from snapshot"
            assert isclose(float(snapshot[key]["v"]), float(i * 10), abs_tol=1e-4), (
                f"Expected {key}={i * 10}, got {snapshot[key]}"
            )
