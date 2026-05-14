# FIT Review — feat_req__persistency__{reset_resistant, recovery_from_reset, atomic_store}

**Reviewer persona**: PiotrKorkus  
**Date**: 2026-05-05  
**Branch**: `Subramanian-K812_add_fit_persistency_reset_resistant_recovery_atomic`  
**Files reviewed**: 10 files (3 Rust scenarios, 3 C++ scenarios, 3 Python test cases, 1 C++ KvsInstance extension)

---

## Summary

The PR adds FIT coverage for three persistency requirements using the correct two-phase
(write-and-reload) scenario pattern. Requirement traceability is in place, the Rust scenarios
are clean, and the tests pass end-to-end for both backends. However the C++ scenarios bypass the
shared `kvs_build_helpers.h` infrastructure that the rest of the C++ test scenarios use,
re-implementing `unix_seconds_string()` locally in all three files and hand-crafting JSON
instead of calling `kvs_build_helpers::log_info()`. There are also test hygiene issues: one
logged field is never asserted, one test method is redundant, and all three test classes
re-implement a `temp_dir` fixture that `PersistencyScenario` already provides.

---

## Positives

- Rust scenario design is clean and idiomatic: `tracing::info!` with structured fields,
  two-phase open/close pattern, correct use of `SnapshotId`.
- All three `@add_test_properties` decorators are present with valid requirement IDs and
  correct `test_type` / `derivation_technique` values.
- `pytestmark` has `scope="class"` in all three test files — well done.
- The `snapshot_max_count: 3` discovery (Rust defaults to 1) was correctly fixed so rotation
  tests actually produce two snapshots.
- C++ scenarios guard every fallible call with a `throw std::runtime_error(...)`, consistent
  with the codebase convention.

---

## Findings

---

### [Major] C++ scenarios bypass `kvs_build_helpers::log_info()` — each re-implements `unix_seconds_string()` and hand-crafts JSON

**Files**: 
- `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/reset_resistant.cpp`, lines 25–38  
- `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/recovery_from_reset.cpp`, lines 25–38  
- `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/atomic_store.cpp`, lines 25–38  

**Evidence**:
```cpp
// In each of the three new files — anonymous namespace:
std::string unix_seconds_string() {
    const auto now = std::chrono::system_clock::now();
    ...
}
// Then used as:
std::cout << "{\"timestamp\":\"" << timestamp
          << "\",\"level\":\"INFO\",\"fields\":{\"key\":\"data_key\",\"value\":"
          << current_val.value() << ...
```

**Problem**: `kvs_build_helpers.h` (already included by all other C++ scenarios from the same
branch: `reset_to_default.cpp`, `default_values.cpp`, etc.) provides `unix_seconds_string()`
and `log_info()` exactly for this purpose. The three new files do not include this header and
instead duplicate the logic, diverging from the established convention and making future
maintenance harder. The hand-crafted JSON is also more fragile than the shared `log_info()`
call.

**Fix**: Include `kvs_build_helpers.h`, remove the local `unix_seconds_string()` definition, and replace `std::cout <<` blocks with `kvs_build_helpers::log_info(fields, target)`. For example in `reset_resistant.cpp`:
```cpp
#include "../../internals/persistency/kvs_build_helpers.h"
// ...
kvs_build_helpers::log_info(
    "\"key\":\"data_key\",\"value\":" + std::to_string(current_val.value()) +
    ",\"snapshot_count\":" + std::to_string(kvs->snapshot_count()),
    "cpp_test_scenarios::scenarios::persistency::reset_resistant");
```

**Test idea**: Build the binary with a clang `--whole-archive` link and confirm no duplicate `unix_seconds_string` symbol warnings appear.

---

### [Major] `snapshot_count` is logged by both Rust and C++ `reset_resistant` but never asserted in any Python test method

**File**: `feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/reset_resistant.rs`, line 72  
**File**: `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/reset_resistant.cpp`, lines 107–113  
**File**: `feature_integration_tests/test_cases/tests/persistency/test_reset_resistant.py`

**Evidence**:
```rust
// Rust — reset_resistant.rs
info!(key = "data_key", value = current_val, snapshot_count = snapshot_count);
```
```python
# Python — no test asserts on snapshot_count field at all
# test_reset_resistant.py reads snapshot files directly instead
```

**Problem**: `snapshot_count` is emitted as a structured log field but the Python tests never
call `logs_info_level.find_log("snapshot_count", ...)`. The logged field goes unvalidated.
Either add an assertion (the count should be 2 after two flushes with `snapshot_max_count=3`)
or remove the field from the log line to avoid misleading future readers into thinking it is
tested.

**Fix (option A — assert it)**:
```python
def test_snapshot_count_after_rotation(self, results: Any, logs_info_level: LogContainer) -> None:
    assert results.return_code == ResultCode.SUCCESS
    log = logs_info_level.find_log("key", value="data_key")
    assert log is not None
    assert int(log.snapshot_count) == 2
```

**Fix (option B — remove from log)**: Drop `snapshot_count` from `info!(...)` and the
`std::cout` block since it adds noise without being verified.

---

### [Minor] All three test classes re-implement `temp_dir` instead of inheriting from `PersistencyScenario`

**Files**:
- `test_reset_resistant.py`, lines 55–60  
- `test_recovery_from_reset.py`, lines 57–62  
- `test_atomic_store.py`, lines 60–65  

**Evidence** (identical block in all three):
```python
@pytest.fixture(scope="class")
def temp_dir(
    self,
    tmp_path_factory: pytest.TempPathFactory,
    version: str,
):
    yield from temp_dir_common(tmp_path_factory, self.__class__.__name__, version)
```

**Problem**: `PersistencyScenario` (in `persistency_scenario.py`, which is already on the
module path for both `fit_rust` and `fit_cpp` targets) provides exactly this fixture. All
three classes extend `FitScenario` and duplicate the code instead of inheriting from
`PersistencyScenario`. Any future change to the temp-dir lifecycle must be applied in four
places.

**Fix**: Change base class from `FitScenario` to `PersistencyScenario` and remove the
duplicated `temp_dir` fixture from each class:
```python
from persistency_scenario import PersistencyScenario, read_kvs_snapshot

class TestResetResistant(PersistencyScenario):
    # no temp_dir fixture needed
```

---

### [Minor] `test_scenario_completes_without_error` in `TestRecoveryFromReset` is redundant

**File**: `feature_integration_tests/test_cases/tests/persistency/test_recovery_from_reset.py`, lines 90–93  

**Evidence**:
```python
def test_scenario_completes_without_error(self, results: Any) -> None:
    """Verify the scenario exits without panic or signal."""
    assert results.return_code == ResultCode.SUCCESS
```

**Problem**: `test_restored_value_equals_pre_reset_state` (the preceding method) already
asserts `results.return_code == ResultCode.SUCCESS` as its first line. The second method adds
no additional observable behaviour and runs the scenario a second time at class scope (it does
not, since `results` is `scope="class"`, but it still clutters the test output with a
redundant case).

**Fix**: Remove `test_scenario_completes_without_error`. The exit-code check belongs in the
substantive test method, where it already is.

---

### [Minor] `temp_dir` fixture return type annotation is missing in all three test files

**Files**: `test_reset_resistant.py` line 56, `test_recovery_from_reset.py` line 58,
`test_atomic_store.py` line 61  

**Evidence**:
```python
def temp_dir(
    self,
    tmp_path_factory: pytest.TempPathFactory,
    version: str,
):  # <— no return type annotation
    yield from temp_dir_common(...)
```

**Problem**: The existing `PersistencyScenario.temp_dir` and
`TestMultipleInstanceIds.temp_dir` both carry `-> Generator[Path, None, None]`. The new
fixtures are missing it, inconsistent with the codebase style.

**Fix**: Add `-> Generator[Path, None, None]` return annotation and import
`from collections.abc import Generator` (already imported in two of the three files but
unused once `PersistencyScenario` inheritance is adopted).

---

### [Nit] `from testing_utils import LogContainer` is unused in `test_reset_resistant.py`

**File**: `feature_integration_tests/test_cases/tests/persistency/test_reset_resistant.py`, line 28

**Evidence**:
```python
from testing_utils import LogContainer  # imported but no test method uses it
```

**Problem**: None of the three test methods in `TestResetResistant` use `LogContainer` — all
assertions are on snapshot files. The import is dead code.

**Fix**: Remove the `LogContainer` import from `test_reset_resistant.py`.

---

## Suggested Next Steps

1. Include `kvs_build_helpers.h` in all three new C++ scenarios and switch to
   `kvs_build_helpers::log_info()` — this is the primary correctness risk.
2. Either assert on `snapshot_count` in the Python test, or remove it from the log emission
   to avoid untested observable outputs.
3. Change test class base to `PersistencyScenario` to eliminate the duplicated `temp_dir`
   fixture.
4. Remove `test_scenario_completes_without_error` from `TestRecoveryFromReset`.
5. Add missing return type annotations on `temp_dir` fixtures.

---

## Requirements Traceability Check

| Test Class | `partially_verifies` IDs | Status |
|---|---|---|
| `TestResetResistant` | `feat_req__persistency__reset_resistant` | OK |
| `TestRecoveryFromReset` | `feat_req__persistency__recovery_from_reset` | OK |
| `TestAtomicStore` | `feat_req__persistency__atomic_store` | OK |
