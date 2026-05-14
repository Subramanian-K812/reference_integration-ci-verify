# PR Review — FIT Scenarios: load_data, cached_access, direct_access, write_amplification

**Reviewer persona**: PiotrKorkus  
**Date**: 2026-05-12  
**Files reviewed**: 12 files  
- `feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/load_data.rs`
- `feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/cached_access.rs`
- `feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/direct_access.rs`
- `feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/write_amplification.rs`
- `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/load_data.cpp`
- `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/cached_access.cpp`
- `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/direct_access.cpp`
- `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/write_amplification.cpp`
- `feature_integration_tests/test_cases/tests/persistency/test_load_data.py`
- `feature_integration_tests/test_cases/tests/persistency/test_cached_access.py`
- `feature_integration_tests/test_cases/tests/persistency/test_direct_access.py`
- `feature_integration_tests/test_cases/tests/persistency/test_write_amplification.py`

---

## Summary

The PR adds FIT coverage for four previously untested persistency requirements
(`load_data`, `cached_access`, `direct_access`, `write_amplification`).  Structure
is consistent with the existing codebase: Rust and C++ scenario binaries, Python
orchestrator tests inheriting `PersistencyScenario`, full `@add_test_properties`
traceability, `pytestmark` parametrize over `["rust", "cpp"]`.  Three findings
must be fixed before merge: one vacuous C++ log assertion, two missing key-field
assertions in the multi-instance load test.  The rest are style and consistency
issues.

---

## Positives

- All 13 new scenarios are fully registered in both `mod.rs` and `mod.cpp`, and both
  binaries build clean — the two-phase write-then-reopen pattern is implemented
  correctly and consistently across Rust and C++.
- Every test class carries `@add_test_properties` with specific requirement IDs and
  multi-instance isolation is covered for all four requirements — this directly
  addresses the gap flagged in earlier reviews.
- Docstrings on every scenario class explain the precise observable behaviour being
  tested, not just what the scenario does.

---

## Findings

---

### [Major] C++ `snapshot_count` is hardcoded — `test_snapshot_count_logged_as_one` is vacuous for the cpp path

**File**: `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/write_amplification.cpp`, lines 61–65  
**Evidence**:
```cpp
// Log snapshot_count = 1 so Python can assert single-file write.
kvs_build_helpers::log_info(
    "\"snapshot_count\":1,\"phase\":\"after_single_flush\"",
    "cpp_test_scenarios::scenarios::persistency::write_amplification");
```

**Problem**: The C++ wrapper does not expose `snapshot_count()` so the value is
hardcoded.  The Python assertion `assert int(log.snapshot_count) == 1` always
passes for C++ regardless of how many files the KVS actually created.  Only the
file-glob tests (`test_single_snapshot_file_created`) provide real signal on the
cpp path.  
**Fix**: Either add a comment documenting this limitation explicitly and drop the
`test_snapshot_count_logged_as_one` assertion for the cpp path (gate it with
`if version == "rust"`), or count actual JSON files via Python and log that
count from C++ instead.  
**Test idea**: A test that verifies the file count after 10 writes is already
present — it is the authoritative check.  Remove or guard the redundant
`snapshot_count` log assertion for cpp.

---

### [Major] Missing `log.key` assertion in `TestLoadDataMultiInstance`

**File**: `feature_integration_tests/test_cases/tests/persistency/test_load_data.py`, lines 149–154 and 157–162  
**Evidence**:
```python
def test_instance_1_loaded_own_key(self, results: Any, logs_info_level: LogContainer) -> None:
    assert results.return_code == ResultCode.SUCCESS
    log = logs_info_level.find_log("instance", value="1")
    assert log is not None, "No reload log found for instance 1"
    assert isclose(float(log.value), 10.0, abs_tol=1e-4)   # ← no key assertion
```

**Problem**: `find_log("instance", value="1")` returns the first log entry where
`instance="1"` — but only `log.value` is checked, not `log.key`.  If the scenario
logged the wrong key with the right value the test would still pass.  The canonical
pattern from `test_multiple_kvs_per_app.py` always asserts both fields:
```python
assert log1.key == kvs_key
assert log1.value == kvs_value_1
```
**Fix**: Add `assert log.key == "key_a"` (instance 1) and `assert log.key == "key_b"` (instance 2).

---

### [Major] Fuzzy boolean check for `exists` field — should use `is True` / `is False`

**File**: `feature_integration_tests/test_cases/tests/persistency/test_direct_access.py`, lines 138–141, 148–151, 168–170, 178–180, 188–190, 198–200  
**Evidence**:
```python
assert log.exists in (True, "true"), ...
assert log.exists in (False, "false"), ...
```

**Problem**: The `exists` field is emitted as a JSON boolean (`"exists":true`) in
both C++ (`std::string(a_in_1 ? "true" : "false")` inside a raw JSON string, which
produces an unquoted boolean value) and Rust (`info!(exists = a_in_1)`).
`LogContainer` parses this as Python `True`/`False`.  The `"true"` / `"false"`
string alternatives are dead code that masks a wrong value if the parser ever
changes behaviour.  Per project convention, boolean assertions must be explicit:
```python
assert log.exists is True
assert log.exists is False
```

---

### [Minor] `from math import isclose` inside a test method body

**File**: `feature_integration_tests/test_cases/tests/persistency/test_direct_access.py`, line 60  
**Evidence**:
```python
def test_target_key_readable(self, results: Any, logs_info_level: LogContainer) -> None:
    ...
    from math import isclose          # ← import inside method
    assert isclose(float(log.value), 30.0, abs_tol=1e-4), ...
```

**Problem**: `isclose` is not in the module-level imports (unlike all three sibling
test files).  An import inside a test method works but is inconsistent with the
rest of the module and hides a missing top-level import.  
**Fix**: Add `from math import isclose` to the module-level import block and remove
the inline import.

---

### [Minor] `get_logs` positional-field call — inconsistent with canonical pattern

**File**: `feature_integration_tests/test_cases/tests/persistency/test_direct_access.py`, lines 168, 178, 188, 198  
**Evidence**:
```python
logs = [l for l in logs_info_level.get_logs("key", value="key_a")
        if getattr(l, "instance", None) == "1"]
```

**Problem**: All other usages in the codebase pass `field` as a keyword argument
(`logs.get_logs(field="level", value="INFO")`).  The positional call is an
inconsistency.  More importantly, the canonical pattern for multi-instance log
filtering is to chain two `get_logs` / `find_log` calls rather than a list
comprehension with `getattr`:
```python
instance_1_logs = logs_info_level.get_logs(field="instance", value="1")
log = instance_1_logs.find_log(field="key", value="key_a")
assert log is not None, "..."
assert log.exists is True
```
This removes the dependency on `getattr` fallback and aligns with how
`test_multiple_kvs_per_app.py` handles multi-value log lookup.

---

### [Minor] `snapshot_id=0` assumption undocumented in `TestLoadDataAfterMultipleFlushes`

**File**: `feature_integration_tests/test_cases/tests/persistency/test_load_data.py`, lines 121–125  
**Evidence**:
```python
def test_current_snapshot_has_latest_value(self, results: Any, temp_dir: Path) -> None:
    snapshot = read_kvs_snapshot(temp_dir, instance_id=1, snapshot_id=0)
    assert isclose(float(snapshot["data_key"]["v"]), 30.0, abs_tol=1e-4)
```

**Problem**: With `snapshot_max_count=3` and 3 flushes the KVS holds 3 files.
`read_kvs_snapshot(..., snapshot_id=0)` reads `kvs_1_0.json`.  The test silently
assumes `snapshot_id=0` is the *newest* snapshot, which depends on the rotation
scheme.  If the rotation evicts the lowest ID and `0` is the oldest, this
assertion would check V1=10.0, not V3=30.0, and the test would fail spuriously.  
**Fix**: Add a comment explaining why `snapshot_id=0` is the newest slot, or use
the log-based check (`test_latest_value_loaded`) as the primary assertion and drop
the file check, which is already covered by the log assertion.

---

### [Minor] Duplicate `parse_params` helper copy-pasted across 4 Rust modules

**Files**: `load_data.rs` line 21, `cached_access.rs` line 21, `direct_access.rs` line 21, `write_amplification.rs` line 21  
**Evidence**:
```rust
fn parse_params(input: &str) -> Result<KvsParameters, String> {
    let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
    KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())
}
```

**Problem**: The exact same 3-line function is copy-pasted into all four modules.
If the `kvs_parameters_1` key name or error handling changes, all four files must
be updated.  
**Fix**: Move to `crate::internals::persistency::kvs_parameters` (or a new
`test_helpers.rs` in the persistency scenario directory) and import it in each
module.

---

### [Nit] C++ `DirectAccessKeyExists` uses `get_value_f64().has_value()` as proxy for `key_exists()` — not stated clearly in the test docstring

**File**: `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/direct_access.cpp`, lines 118–122  
**Evidence**:
```cpp
// Phase 2: reload and check via get_value (proxy for key_exists).
const bool exists_present = kvs->get_value_f64("present_key").has_value();
```

**Problem**: The Python test docstring and assertion wording says "key_exists()"
but the C++ scenario uses a typed-get proxy.  A key could theoretically be present
with a non-f64 type and `get_value_f64` would return empty while `key_exists`
would return true.  This is a known C++ wrapper limitation, but the test method
docstrings in the Python test (`test_present_key_exists`, `test_absent_key_not_exists`)
don't mention the proxy.  
**Fix**: Add a comment in the Python docstrings: "Note: C++ path uses `get_value_f64().has_value()` as a proxy for `key_exists()` — the test key is always written as f64."

---

### [Nit] No hash integrity check in any new test

**Files**: `test_load_data.py`, `test_direct_access.py`, `test_write_amplification.py`  
**Problem**: The existing tests (`test_reset_to_default.py`, `test_combined_requirements.py`)
call `verify_kvs_snapshot_hash(temp_dir, instance_id, snapshot_id)` after reading
the snapshot.  All new tests that read the snapshot file skip this check.  
**Fix**: Add `verify_kvs_snapshot_hash(temp_dir, instance_id=1, snapshot_id=0)` to
at least one test method per class that reads a snapshot, consistent with existing
practice.

---

## Suggested Next Steps

1. Fix the three **Major** findings: guard or remove the vacuous C++ `snapshot_count`
   log assertion; add `log.key ==` assertions in `TestLoadDataMultiInstance`; replace
   fuzzy `exists in (True, "true")` with `exists is True`.
2. Fix the **Minor** `isclose` missing top-level import in `test_direct_access.py`.
3. Replace list-comprehension multi-instance log filtering with the canonical
   chained `get_logs(...).find_log(...)` pattern.
4. Add `verify_kvs_snapshot_hash` calls to snapshot-reading tests (nit, but
   ensures new tests are on par with existing ones).

---

## Requirements Traceability Check

| Test Class | `partially_verifies` IDs | Status |
|---|---|---|
| `TestLoadData` | `feat_req__persistency__load_data` | OK |
| `TestLoadDataAfterMultipleFlushes` | `feat_req__persistency__load_data` | OK |
| `TestLoadDataMultiInstance` | `feat_req__persistency__load_data`, `feat_req__persistency__store_data` | OK |
| `TestCachedAccess` | `feat_req__persistency__cached_access` | OK |
| `TestCachedAccessUpdate` | `feat_req__persistency__cached_access` | OK |
| `TestCachedAccessMultiKey` | `feat_req__persistency__cached_access` | OK |
| `TestDirectAccess` | `feat_req__persistency__direct_access` | OK |
| `TestDirectAccessAbsentKey` | `feat_req__persistency__direct_access` | OK |
| `TestDirectAccessKeyExists` | `feat_req__persistency__direct_access` | OK |
| `TestDirectAccessMultiInstance` | `feat_req__persistency__direct_access` | OK |
| `TestWriteAmplification` | `feat_req__persistency__write_amplification` | OK |
| `TestWriteAmplificationSingleFlushCoversAllKeys` | `feat_req__persistency__write_amplification` | OK |
| `TestWriteAmplificationMultiInstance` | `feat_req__persistency__write_amplification` | OK |
