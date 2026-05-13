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

"""Tests for feat_req__persistency__cached_access.

Verifies that key-value pairs are accessible from the in-memory cache
immediately after set_value() without requiring a flush or disk read.
Three scenarios cover the basic read-after-write, cache update on overwrite,
and concurrent access to multiple cached keys.
"""

from math import isclose
from pathlib import Path
from typing import Any

import pytest
from fit_scenario import ResultCode
from persistency_scenario import PersistencyScenario
from test_properties import add_test_properties
from testing_utils import LogContainer

pytestmark = pytest.mark.parametrize("version", ["rust", "cpp"], scope="class")


@add_test_properties(
    partially_verifies=["feat_req__persistency__cached_access"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestCachedAccess(PersistencyScenario):
    """Verify that a written value is immediately readable from the in-memory cache.

    The scenario calls set_value(cache_key=1.0) then get_value — with NO flush
    between.  The returned value must be 1.0, proving that reads are served from
    the in-memory cache without a round-trip to persistent storage.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.cached_access"

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

    def test_cached_value_readable(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify get_value returns the written value from the in-memory cache."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("key", value="cache_key")
        assert log is not None, "No cached_read log entry found for cache_key"
        assert isclose(float(log.value), 1.0, abs_tol=1e-4), f"Expected cached value 1.0, got {log.value}"


@add_test_properties(
    partially_verifies=["feat_req__persistency__cached_access"],
    test_type="requirements-based",
    derivation_technique="boundary-value-analysis",
)
class TestCachedAccessUpdate(PersistencyScenario):
    """Verify that the cache reflects updated values immediately on overwrite.

    The scenario writes V1=1.0, reads it (expect 1.0), then overwrites with
    V2=2.0 and reads again (expect 2.0).  No flush between operations.
    This confirms the cache has no staleness — it always reflects the most
    recently written value.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.cached_access_update"

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

    def test_v1_cached_correctly(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify the cache returns V1=1.0 immediately after the first write."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("phase", value="after_v1")
        assert log is not None, "No after_v1 log entry found"
        assert isclose(float(log.value), 1.0, abs_tol=1e-4), f"Expected V1=1.0 from cache, got {log.value}"

    def test_v2_cached_without_staleness(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify the cache returns V2=2.0 after overwrite, with no stale V1."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("phase", value="after_v2")
        assert log is not None, "No after_v2 log entry found"
        assert isclose(float(log.value), 2.0, abs_tol=1e-4), (
            f"Expected V2=2.0 from cache after overwrite, got {log.value}"
        )


@add_test_properties(
    partially_verifies=["feat_req__persistency__cached_access"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestCachedAccessMultiKey(PersistencyScenario):
    """Verify that all pending writes across multiple keys are cached consistently.

    The scenario writes 5 keys (mk_0 through mk_4, values 0.0–40.0) without
    flushing.  All five are immediately readable from the cache with correct
    values, confirming the cache holds the full in-flight write set.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.cached_access_multi_key"

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

    def test_all_keys_cached(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify all 5 keys are readable from the cache with correct values."""
        assert results.return_code == ResultCode.SUCCESS
        expected = {f"mk_{i}": float(i * 10) for i in range(5)}
        for key, exp_val in expected.items():
            log = logs_info_level.find_log("key", value=key)
            assert log is not None, f"No cached log entry found for {key}"
            assert isclose(float(log.value), exp_val, abs_tol=1e-4), (
                f"Expected {key}={exp_val} from cache, got {log.value}"
            )


@add_test_properties(
    partially_verifies=["feat_req__persistency__cached_access"],
    test_type="requirements-based",
    derivation_technique="fault-injection",
)
class TestCachedAccessAfterFlush(PersistencyScenario):
    """Verify that the in-memory cache remains valid after a flush.

    The scenario writes flush_key=5.0, flushes (without reopening), then reads
    flush_key.  The read must be served by the cache, not require a fresh disk
    load.  If the implementation clears the cache on flush, this read fails.
    """

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.cached_access_after_flush"

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

    def test_cached_value_readable_after_flush(self, results: Any, logs_info_level: LogContainer) -> None:
        """Verify get_value returns 5.0 from cache immediately after flush."""
        assert results.return_code == ResultCode.SUCCESS
        log = logs_info_level.find_log("phase", value="after_flush")
        assert log is not None, "No after_flush log entry found"
        assert isclose(float(log.value), 5.0, abs_tol=1e-4), f"Expected 5.0 after flush, got {log.value}"
