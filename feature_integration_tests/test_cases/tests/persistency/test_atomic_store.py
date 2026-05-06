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

"""Tests for feat_req__persistency__atomic_store.

Verifies that a single flush() call atomically persists all pending in-memory
writes.  No partial-write state is observable: either all keys are present in
the snapshot, or none are.
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
    partially_verifies=["feat_req__persistency__atomic_store"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestAtomicStore(PersistencyScenario):
    """Verify that flush() persists all pending writes as a single atomic operation.

    The scenario:

    1. Creates a KVS instance and writes three keys (key_a=10.0, key_b=20.0,
       key_c=30.0) to the in-memory store without flushing between writes.
    2. Flushes once — all three keys must be persisted together.
    3. Re-opens the KVS (forces a load from the snapshot) and reads all three
       keys.  All must be present with their written values.

    The Python test inspects both the log entries and the snapshot file to
    confirm atomic store semantics.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.atomic_store"

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

    def test_all_keys_persisted_in_snapshot(self, results: Any, temp_dir: Path) -> None:
        """Verify the snapshot file contains all three keys after a single flush.

        If any key is missing from the snapshot it indicates a non-atomic write:
        some keys were written while others were not, violating the requirement.
        """
        assert results.return_code == ResultCode.SUCCESS
        snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)

        assert "key_a" in snapshot, "key_a missing from snapshot — non-atomic write detected"
        assert isclose(float(snapshot["key_a"]["v"]), 10.0, abs_tol=1e-4)

        assert "key_b" in snapshot, "key_b missing from snapshot — non-atomic write detected"
        assert isclose(float(snapshot["key_b"]["v"]), 20.0, abs_tol=1e-4)

        assert "key_c" in snapshot, "key_c missing from snapshot — non-atomic write detected"
        assert isclose(float(snapshot["key_c"]["v"]), 30.0, abs_tol=1e-4)

    def test_all_keys_readable_after_reload(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify log entries confirm all keys are readable after KVS reload.

        The scenario emits one log line per key from the re-opened KVS
        instance.  Finding all three in the logs proves the reload (from the
        persisted snapshot) delivered all keys to the application layer.
        """
        assert results.return_code == ResultCode.SUCCESS

        log_a = logs_info_level.find_log("key", value="key_a")
        assert log_a is not None, "No log entry found for key_a after reload"
        assert isclose(float(log_a.value), 10.0, abs_tol=1e-4)

        log_b = logs_info_level.find_log("key", value="key_b")
        assert log_b is not None, "No log entry found for key_b after reload"
        assert isclose(float(log_b.value), 20.0, abs_tol=1e-4)

        log_c = logs_info_level.find_log("key", value="key_c")
        assert log_c is not None, "No log entry found for key_c after reload"
        assert isclose(float(log_c.value), 30.0, abs_tol=1e-4)

    def test_snapshot_hash_file_exists(self, results: Any, temp_dir: Path) -> None:
        """Verify that an integrity hash file was created alongside the snapshot."""
        assert results.return_code == ResultCode.SUCCESS
        assert (temp_dir / "kvs_1_0.hash").exists(), (
            "Hash file kvs_1_0.hash is missing — snapshot may not have been written"
        )


@add_test_properties(
    partially_verifies=["feat_req__persistency__atomic_store"],
    test_type="requirements-based",
    derivation_technique="boundary-value-analysis",
)
class TestAtomicStoreNoPartialWrite(PersistencyScenario):
    """Verify the 'or nothing' side of atomic store semantics.

    The scenario:

    1. Writes key_d=999.0 to the in-memory KVS store.
    2. Drops the KVS instance WITHOUT flushing (simulates hard reset mid-write).

    Because no flush ever occurred, no snapshot file is created on disk.  The
    Python test asserts kvs_1_0.json does not exist, proving that the un-flushed
    write never reached persistent storage (the "or nothing" guarantee).
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.atomic_store_no_partial_write"

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

    def test_no_snapshot_file_created(self, results: Any, temp_dir: Path) -> None:
        """Verify no snapshot file was created when no flush was ever called."""
        assert results.return_code == ResultCode.SUCCESS
        assert not (temp_dir / "kvs_1_0.json").exists(), (
            "Snapshot file kvs_1_0.json exists even though flush() was never called. "
            "The un-flushed write may have been persisted incorrectly."
        )
