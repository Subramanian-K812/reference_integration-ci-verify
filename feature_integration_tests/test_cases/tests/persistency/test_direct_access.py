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

"""Tests for feat_req__persistency__direct_access.

Verifies that individual key-value pairs can be retrieved by name from a loaded
KVS without requiring iteration over the full storage.  Four scenarios cover:
targeted key read after reload, absent key error semantics, key_exists
correctness, and cross-instance isolation of key visibility.
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
    partially_verifies=["feat_req__persistency__direct_access"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestDirectAccess(PersistencyScenario):
    """Verify that a specific key can be read directly after KVS reload.

    The scenario writes da_key_0 through da_key_4, flushes, then reopens and
    accesses da_key_3 by name.  The correct value (30.0) is returned, proving
    direct key lookup works on a loaded store.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.direct_access"

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

    def test_target_key_readable(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify da_key_3 is readable with value 30.0 after reload."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("key", value="da_key_3")
        assert log is not None, "No direct_access log entry for da_key_3"
        assert isclose(float(log.value), 30.0, abs_tol=1e-4), f"Expected da_key_3=30.0, got {log.value}"

    def test_all_keys_in_snapshot(self, results: Any, temp_dir: Path) -> None:
        """Verify all 5 keys are present in the snapshot file after flush."""
        assert results.return_code == ResultCode.SUCCESS
        verify_kvs_snapshot_hash(temp_dir, instance_id=1, snapshot_id=0)
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
        for i in range(5):
            key = f"da_key_{i}"
            assert key in snapshot, f"{key} missing from snapshot"


@add_test_properties(
    partially_verifies=["feat_req__persistency__direct_access"],
    test_type="requirements-based",
    derivation_technique="fault-injection",
)
class TestDirectAccessAbsentKey(PersistencyScenario):
    """Verify that accessing a never-written key returns a KeyNotFound error.

    The scenario does not write any key.  A get_value call for nonexistent_key
    must fail gracefully.  The scenario logs the key_not_found result and exits
    with SUCCESS — confirming error semantics, not a crash.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.direct_access_absent_key"

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

    def test_absent_key_returns_error(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify the scenario completes successfully and logs key_not_found."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("key", value="nonexistent_key")
        assert log is not None, "Expected log entry for nonexistent_key absent-key check"
        assert log.result == "key_not_found", f"Expected result='key_not_found', got '{log.result}'"


@add_test_properties(
    partially_verifies=["feat_req__persistency__direct_access"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestDirectAccessKeyExists(PersistencyScenario):
    """Verify key_exists() semantics: true for a written key, false for an absent one.

    The scenario writes present_key=7.0, flushes, reopens, and checks both
    present_key (expect exists=true) and absent_key (expect exists=false).
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.direct_access_key_exists"

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

    def test_present_key_exists(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify key_exists returns true for a key that was written and flushed.

        Note: The C++ path uses get_value_f64().has_value() as a proxy for
        key_exists() — the KVS C++ wrapper does not expose key_exists() directly.
        The test key is always written as f64 so the proxy is exact.
        """
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("key", value="present_key")
        assert log is not None, "No key_exists log for present_key"
        assert log.exists is True, f"Expected exists=True for present_key, got {log.exists!r}"

    def test_absent_key_not_exists(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify key_exists returns false for a key that was never written.

        Note: The C++ path uses get_value_f64().has_value() as a proxy for
        key_exists() — the KVS C++ wrapper does not expose key_exists() directly.
        """
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("key", value="absent_key")
        assert log is not None, "No key_exists log for absent_key"
        assert log.exists is False, f"Expected exists=False for absent_key, got {log.exists!r}"


@add_test_properties(
    partially_verifies=["feat_req__persistency__direct_access"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestDirectAccessMultiInstance(PersistencyScenario):
    """Verify that direct key access is isolated per KVS instance.

    Instance 1 has key_a; instance 2 has key_b.  After flush and reload, each
    instance's key_exists check must confirm its own key present (true) and
    the other instance's key absent (false).
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.direct_access_multi_instance"

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

    def test_instance_1_key_a_present(self, results: Any, logs_info_level: LogContainer) -> None:
        """Instance 1 must see key_a as present."""
        assert results.return_code == ResultCode.SUCCESS
        instance_1_logs = logs_info_level.get_logs(field="instance", value="1")
        log = instance_1_logs.find_log(field="key", value="key_a")
        assert log is not None, "No key_a log for instance 1"
        assert log.exists is True, f"Expected key_a exists=True in instance 1, got {log.exists!r}"

    def test_instance_1_key_b_absent(self, results: Any, logs_info_level: LogContainer) -> None:
        """Instance 1 must NOT see key_b (belongs to instance 2)."""
        assert results.return_code == ResultCode.SUCCESS
        instance_1_logs = logs_info_level.get_logs(field="instance", value="1")
        log = instance_1_logs.find_log(field="key", value="key_b")
        assert log is not None, "No key_b isolation log for instance 1"
        assert log.exists is False, f"Expected key_b exists=False in instance 1, got {log.exists!r}"

    def test_instance_2_key_b_present(self, results: Any, logs_info_level: LogContainer) -> None:
        """Instance 2 must see key_b as present."""
        assert results.return_code == ResultCode.SUCCESS
        instance_2_logs = logs_info_level.get_logs(field="instance", value="2")
        log = instance_2_logs.find_log(field="key", value="key_b")
        assert log is not None, "No key_b log for instance 2"
        assert log.exists is True, f"Expected key_b exists=True in instance 2, got {log.exists!r}"

    def test_instance_2_key_a_absent(self, results: Any, logs_info_level: LogContainer) -> None:
        """Instance 2 must NOT see key_a (belongs to instance 1)."""
        assert results.return_code == ResultCode.SUCCESS
        instance_2_logs = logs_info_level.get_logs(field="instance", value="2")
        log = instance_2_logs.find_log(field="key", value="key_a")
        assert log is not None, "No key_a isolation log for instance 2"
        assert log.exists is False, f"Expected key_a exists=False in instance 2, got {log.exists!r}"


@add_test_properties(
    partially_verifies=["feat_req__persistency__direct_access"],
    test_type="requirements-based",
    derivation_technique="fault-injection",
)
class TestDirectAccessKeyExistsUnflushed(PersistencyScenario):
    """Verify key_exists() works correctly on keys that are only in the cache.

    The scenario writes unflushed_key=3.0 without flushing, then calls
    key_exists().  An implementation that only checks the on-disk snapshot
    would return false here — a correctness bug.  An absent key must return
    false regardless.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.direct_access_key_exists_unflushed"

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

    def test_unflushed_key_exists(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify key_exists returns true for a key in the cache but not yet flushed.

        Note: The C++ path uses get_value_f64().has_value() as a proxy for
        key_exists() — the KVS C++ wrapper does not expose key_exists() directly.
        The test key is always written as f64 so the proxy is exact.
        """
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("key", value="unflushed_key")
        assert log is not None, "No unflushed_key log entry found"
        assert log.exists is True, f"Expected exists=True for unflushed_key, got {log.exists!r}"

    def test_absent_key_not_exists_unflushed(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify key_exists returns false for a key that was never written.

        Note: The C++ path uses get_value_f64().has_value() as a proxy for
        key_exists() — the KVS C++ wrapper does not expose key_exists() directly.
        """
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("key", value="never_written_key")
        assert log is not None, "No never_written_key log entry found"
        assert log.exists is False, f"Expected exists=False for never_written_key, got {log.exists!r}"
