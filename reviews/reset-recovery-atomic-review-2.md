# Local Changes Review — reset_resistant / recovery_from_reset / atomic_store (pass 2)

**Reviewer persona**: PiotrKorkus  
**Date**: 2026-05-06  
**Scope**: All files modified against HEAD on branch
`Subramanian-K812_add_fit_persistency_reset_resistant_recovery_atomic`  
**Files reviewed**: 42 changed files (27 new, 15 modified)

---

## Summary

The functional code is in good shape: previous review findings were addressed,
all three new scenarios (reset-resistant, recovery-from-reset, atomic-store) have
correct Rust and C++ implementations with full `PersistencyScenario` inheritance
and `@add_test_properties` traceability. Four issues block a clean PR: the
unwired patch file (carried over), three new committed artifacts, and a
`from typing import Generator` regression in `fit_scenario.py`. Two minor
log-emission gaps remain.

---

## Positives

- All three new test classes correctly inherit from `PersistencyScenario` — no
  duplicated `temp_dir` fixtures in the reset-resistant, recovery, or atomic
  test files.
- `TestOptionalModeWithoutDefaults.test_optional_mode_succeeds` is now present,
  closing the zero-test-methods finding from the previous follow-up review.
- `SelectiveReset` and `FullReset` both emit post-reset default values and have
  matching `test_reset_key_returns_default` / `test_full_reset_key_returns_default`
  log assertions — the lifecycle gap flagged in the follow-up review is closed.
- `snapshot_count` was quietly removed from the `reset_resistant` log line —
  previous finding addressed without noise.

---

## Findings

---

### [Critical] `patches/baselibs/004-add-missing-ecu-vector-vajson-package.patch` still unresolved

**File**: `patches/baselibs/004-add-missing-ecu-vector-vajson-package.patch` (still present)  
**Evidence**: No reference to this file exists in `known_good.json` or
`bazel_common/score_modules_target_sw.MODULE.bazel`. The file itself contains
the same diff block duplicated twice (copy-paste artifact).  
**Problem**: Committed but never applied; silently does nothing. Already flagged as
Critical in `reviews/9-review.md`. Still unresolved.  
**Fix**: Wire it up in `score_modules_target_sw.MODULE.bazel` alongside patch `003`,
or remove it entirely.

---

### [Major] Three new artifact files committed: `reviews/reset-recovery-atomic-review.md`, `docs/pr_description_persistency_fit.md`, `docs/pr_description_persistency_fit.txt`

**Files**:
- `reviews/reset-recovery-atomic-review.md` (new, 235 lines)
- `docs/pr_description_persistency_fit.md` (new, 77 lines)
- `docs/pr_description_persistency_fit.txt` (new, 93 lines)

**Evidence**: Each appears as `new file mode 100644` in the diff.  
**Problem**: These are development-time artifacts — one is a code-review log, two
are PR-drafting documents. Committing them extends the pattern already flagged as
Major in `reviews/9-review.md` ("remove all seven `docs/` working-note files from
this PR").  
**Fix**: Remove all three from the PR. The accumulated `reviews/` and `docs/`
artifacts (`9-review.md`, `9-review-followup.md`, the six analysis docs) should be
addressed in the same cleanup pass.

---

### [Major] `reviews/9-review.md` and `reviews/9-review-followup.md` still present

**Files**: `reviews/9-review.md` (243 lines), `reviews/9-review-followup.md` (129 lines)  
**Evidence**: Both still appear in the diff as newly committed. `9-review.md` itself
states "Remove from this PR" and "Keep locally or in a wiki."  
**Problem**: The instruction to remove these was in the review, but the removal was
not done. The PR now carries three committed review artifacts.  
**Fix**: Remove both files.

---

### [Major] `fit_scenario.py` — `from typing import Generator` regression

**File**: `feature_integration_tests/test_cases/fit_scenario.py`, line 14  
**Evidence** (diff):
```diff
-from collections.abc import Generator
+from typing import Generator
```
**Problem**: `typing.Generator` is a deprecated alias since Python 3.9; the
canonical import is `collections.abc.Generator`. The original code was correct.
This change was unnecessary and moves in the wrong direction.  
**Fix**: Revert to `from collections.abc import Generator`.

---

### [Minor] C++ `AtomicStoreNoPartialWrite` Phase 2 emits `found_key` log that no Python test asserts on

**File**: `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/atomic_store.cpp`, lines 153–160  
**Evidence**:
```cpp
kvs_build_helpers::log_info(
    "\"key\":\"key_d\",\"found_key\":" + std::string(found ? "true" : "false"),
    "cpp_test_scenarios::scenarios::persistency::atomic_store_no_partial_write");
```
**Problem**: The Python test `TestAtomicStoreNoPartialWrite.test_no_snapshot_file_created`
only checks the file does not exist — it never calls `find_log("key", value="key_d")`.
The `found_key` field is a structured log observable that is produced but never
validated. The Rust scenario has no Phase 2 at all, so the C++ and Rust flows are
also asymmetric.  
**Fix (option A)**: Add a Python test method that asserts `found_key == false` from
the log, making the log emission meaningful.  
**Fix (option B)**: Remove Phase 2 from C++ to match Rust and eliminate the
unverified observable.

---

### [Minor] C++ `RecoveryFromReset` Phase 3 emits `found_key` and `value` logs that no Python test asserts on

**File**: `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/recovery_from_reset.cpp`, lines 89–95  
**Evidence**:
```cpp
kvs_build_helpers::log_info(
    "\"key\":\"data_key\",\"found_key\":" + std::string(found ? "true" : "false")
    + ",\"value\":" + kvs_build_helpers::format_double_python(val),
    "cpp_test_scenarios::scenarios::persistency::recovery_from_reset");
```
**Problem**: The Python test `test_disk_snapshot_contains_last_flushed_value` reads
`kvs_1_0.json` directly and never calls `find_log(...)`. The `found_key` and `value`
fields are observable outputs that are never tested. The Rust scenario has no
equivalent Phase 3, creating further C++/Rust asymmetry.  
**Fix**: Either add a Python assertion
`log = logs_info_level.find_log("key", value="data_key"); assert isclose(float(log.value), 50.0)`
or remove Phase 3 from C++ to align with Rust.

---

### [Minor] `TestMultiInstanceDefaultIsolation` still inherits `FitScenario` and duplicates `temp_dir`

**File**: `feature_integration_tests/test_cases/tests/persistency/test_default_values.py`, lines 584–589  
**Evidence**:
```python
class TestMultiInstanceDefaultIsolation(FitScenario):
    ...
    @pytest.fixture(scope="class")
    def temp_dir(self, tmp_path_factory, version):
        yield from temp_dir_common(tmp_path_factory, self.__class__.__name__, version)
```
**Problem**: `PersistencyScenario` provides exactly this fixture. Unlike
`DefaultValuesParityScenario` (which needs the extra `defaults` parameter in the
path), this class has no such constraint. It should inherit from `PersistencyScenario`
and remove the duplicate fixture.  
**Fix**:
```python
class TestMultiInstanceDefaultIsolation(PersistencyScenario):
    # no temp_dir fixture needed
```

---

### [Nit] `logs_info_level` annotated as `Any` in several test methods; should be `LogContainer`

**Files**: `test_reset_to_default.py`, `test_combined_requirements.py`, `test_default_values.py` — test methods using `logs_info_level: Any`  
**Evidence** (example):
```python
def test_default_value_reported_after_reset(self, results: ScenarioResult, logs_info_level: Any) -> None:
```
**Problem**: `LogContainer` is the correct type for `logs_info_level`. Using `Any`
hides type errors and reduces IDE support.  
**Fix**: Replace `Any` with `LogContainer` and ensure `from testing_utils import LogContainer`
is present in each affected file.

---

## Suggested Next Steps

1. Remove `patches/baselibs/004-add-missing-ecu-vector-vajson-package.patch` or wire
   it up — it is still the only Critical blocker.
2. Remove all committed artifacts in one pass:
   `reviews/9-review.md`, `reviews/9-review-followup.md`,
   `reviews/reset-recovery-atomic-review.md`,
   `docs/pr_description_persistency_fit.md`, `docs/pr_description_persistency_fit.txt`.
3. Revert `fit_scenario.py` line 14 to `from collections.abc import Generator`.
4. Decide on the C++ Phase 2/3 log emissions — either add Python assertions or remove
   the phases to align with Rust.
5. Change `TestMultiInstanceDefaultIsolation` base class to `PersistencyScenario`.

---

## Requirements Traceability Check

| Test Class | `partially_verifies` / `fully_verifies` IDs | Status |
|---|---|---|
| `TestResetResistant` | `feat_req__persistency__reset_resistant` | OK |
| `TestResetResistantMultiInstance` | `feat_req__persistency__reset_resistant` | OK |
| `TestRecoveryFromReset` | `feat_req__persistency__recovery_from_reset` | OK |
| `TestAtomicStore` | `feat_req__persistency__atomic_store` | OK |
| `TestAtomicStoreNoPartialWrite` | `feat_req__persistency__atomic_store` | OK (file check) |
| `TestAllValueTypes` | `support_datatype_value`, `support_datatype_keys`, `store_data` | OK |
| `TestAllTypesWithUtf8Keys` | `support_datatype_keys`, `support_datatype_value`, `store_data` | OK |
| `TestDefaultValuesIgnored` | `default_values`, `default_value_get` | OK |
| `TestDefaultValuesChecksum` | `default_values` | OK |
| `TestDefaultValuesMissingDefaultsFile` | `default_values`, `default_value_file` | OK |
| `TestDefaultValuesMalformedDefaultsFile` | `default_values`, `default_value_file` | OK |
| `TestOptionalModeWithoutDefaults` | `default_values`, `default_value_file`, `store_data` | OK — `test_optional_mode_succeeds` now present |
| `TestGetDefaultValue` | `fully: default_value_get`; `partial: default_values`, `default_value_file` | OK |
| `TestSelectiveReset` | `reset_to_default`, `default_values`, `default_value_file`, `store_data` | OK |
| `TestFullReset` | `reset_to_default`, `default_values`, `default_value_file`, `store_data` | OK |
| `TestResetToDefault` | `feat_req__persistency__reset_to_default` | OK |
| `TestMultiInstanceDefaultIsolation` | `default_values`, `multiple_kvs` | OK |
| `TestPartialOverrideSnapshot` | `default_values`, `default_value_file`, `store_data` | OK |
| `TestUtf8KeysWithDefaults` | `support_datatype_keys`, `default_values`, `default_value_file` | OK |
| `TestUtf8DefaultValueGet` | `fully: default_value_get`; `partial: support_datatype_keys` | OK |
