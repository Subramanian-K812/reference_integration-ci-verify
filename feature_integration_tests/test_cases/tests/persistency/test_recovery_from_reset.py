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
