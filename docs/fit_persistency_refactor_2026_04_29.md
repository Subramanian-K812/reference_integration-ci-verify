# FIT Persistency Refactor — April 29 2026

## Overview

The FIT (Feature Integration Test) persistency layer was refactored to eliminate scenarios that were
exact duplicates of CIT (Component Integration Test) cases.  Ten one-type-per-scenario tests and four
one-operation-per-scenario tests were replaced with two creative multi-requirement combinations that
exercise interactions CIT cannot observe:

- **`AllValueTypes`** — all nine KVS value types in a single atomic flush  
- **`SelectiveReset`** — six keys, even-indexed keys reset to default, odd-indexed retain overrides

Both scenarios are implemented in Rust **and** C++ so the Python test orchestrator validates both
language implementations.

---

## Files Changed

### Rust Scenarios

#### `feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/supported_datatypes.rs`

**Removed**
- `SupportedDatatypesKeys` struct + `Scenario` impl (set 3 UTF-8 key names with null values)
- `SupportedDatatypesValues` struct + `Scenario` impl (parametrised by a `KvsValue`)
- 9 factory functions: `value_types_i32()`, `value_types_u32()`, `value_types_i64()`,
  `value_types_u64()`, `value_types_f64()`, `value_types_bool()`, `value_types_string()`,
  `value_types_array()`, `value_types_object()`
- `value_types_group()` sub-group function

**Added**
- `AllValueTypes` struct + `Scenario` impl: writes all 9 types (`i32_key`, `u32_key`, `i64_key`,
  `u64_key`, `f64_key`, `bool_key`, `str_key`, `arr_key`, `obj_key`) in one flush using a shared
  nested object and array payload

**Updated**
- `supported_datatypes_group()` — now returns `[AllValueTypes, AllTypesUtf8]` with no sub-groups

---

#### `feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/default_values.rs`

**Removed**
- `DefaultValues` struct (set one override key, flush once)
- `RemoveKey` struct (set key, flush, remove_key, flush)
- `ResetAllKeys` struct (set 5 keys, flush, `reset()`, flush)
- `ResetSingleKey` struct (set 5 keys, flush, `reset_key` on index 2, flush)

**Added**
- `SelectiveReset` struct: opens KVS with optional defaults for `sel_key_0`..`sel_key_5`,
  overrides all 6, flushes, calls `reset_key` on even-indexed (0, 2, 4) via `step_by(2)`, flushes
  again — leaving even keys absent and odd keys at their override values

**Updated**
- `default_values_group()` — now returns `[Checksum, PartialOverride, GetDefaultValue, SelectiveReset]`

---

### C++ Scenarios

#### `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/supported_datatypes.cpp`

**Removed**
- `SupportedDatatypesKeys` class (UTF-8 null-value keys)
- `SupportedDatatypesValues` class with all static factory methods (`supported_datatypes_i32()` …
  `supported_datatypes_object()`) and `value_types_group()` sub-group

**Added**
- `AllValueTypes` class: identical logic to the Rust scenario — writes all 9 typed values using the
  same key names, array payload, and nested object; calls
  `KvsInstance::normalize_snapshot_file_to_rust_envelope(params)` to convert C++ native format to
  the Rust envelope so Python assertions are format-agnostic

**Updated**
- `supported_datatypes_group()` — now returns `{AllValueTypes, AllTypesUtf8}` with an empty
  sub-groups vector

---

#### `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/default_values.cpp`

**Removed**
- `DefaultValues` class
- `RemoveKey` class
- `ResetAllKeys` class
- `ResetSingleKey` class

**Added**
- `SelectiveReset` class: same logic as the Rust counterpart using `create_kvs()` (which supports
  optional defaults and `reset_key`); calls
  `KvsInstance::normalize_snapshot_file_to_rust_envelope(params)` at end of `run()`

**Updated**
- `default_values_group()` — now returns
  `{Checksum, PartialOverride, GetDefaultValue, SelectiveReset}`

---

### Python Test Cases

#### `feature_integration_tests/test_cases/tests/persistency/test_datatype_support.py`

**Removed**
- `TestSupportedDatatypesKeys` class (checked 3 UTF-8 key names in snapshot)
- `TestSupportedDatatypesValues` abstract base class
- 9 concrete subclasses: `TestSupportedDatatypesValues_I32`, `_U32`, `_I64`, `_U64`, `_F64`,
  `_Bool`, `_String`, `_Array`, `_Object`
- Unused `from abc import abstractmethod` import

**Added**
- `_EXPECTED_ALL_TYPES` dict — ground-truth type-tagged values for all 9 keys including nested
  array and object structure
- `TestAllValueTypes(SupportedDatatypesScenario)` — single test method
  `test_all_types_in_snapshot` that verifies every key in `_EXPECTED_ALL_TYPES` is present in the
  KVS snapshot with the correct `t`/`v` tags; uses `assert_tagged_value` helper for nested
  structure comparison

**Requirement traceability**:
`feat_req__persistency__support_datatype_value`,
`feat_req__persistency__support_datatype_keys`,
`feat_req__persistency__store_data`

---

#### `feature_integration_tests/test_cases/tests/persistency/test_default_values.py`

**Removed**
- `_PARITY_OVERRIDE_VALUE = 432.1` constant (only used by removed `TestDefaultValues`)
- `_reset_override_value(index)` helper function (only used by removed `TestDefaultValuesResetSingleKey`)
- `TestDefaultValues` class (parametrised over `optional/required/without` defaults)
- `TestDefaultValuesRemoveKey` class (parametrised over `optional/required/without` defaults)
- `TestDefaultValuesResetAllKeys` class (parametrised over `optional/required` defaults)
- `TestDefaultValuesResetSingleKey` class (parametrised over `optional/required` defaults)

**Fixed**
- `TestDefaultValuesMissingDefaultsFile.scenario_name` — was pointing to the now-removed
  `persistency.default_values.default_values`; updated to `persistency.default_values.checksum`
- `TestDefaultValuesMalformedDefaultsFile.scenario_name` — same fix

**Added**
- `_SEL_KEY_COUNT = 6` constant
- `_SEL_DEFAULT_VALUE = 50.0` constant
- `_sel_override_value(index)` helper returning `100.0 * (index + 1)`
- `TestSelectiveReset(FitScenario)` class with:
  - `scenario_name` → `persistency.default_values.selective_reset`
  - `temp_dir`, `defaults_file` (optional defaults for all 6 `sel_key_i`), `test_config` fixtures
  - `test_selective_reset_state` method: even-indexed keys must be absent, odd-indexed present
    with their override values

**Requirement traceability**:
`feat_req__persistency__reset_to_default`,
`feat_req__persistency__default_values`,
`feat_req__persistency__default_value_file`,
`feat_req__persistency__store_data`

---

## Current Passing Tests

All 18 test cases pass for both `rust` and `cpp` implementations (36 total test runs).

### `fit_rust` — `bazel test //feature_integration_tests/test_cases:fit_rust`

| Test | Status |
|------|--------|
| `TestAllTypesWithUtf8Keys::test_utf8_keys_present[rust]` | PASSED |
| `TestAllTypesWithUtf8Keys::test_value_types_persisted[rust]` | PASSED |
| `TestPartialOverrideSnapshot::test_only_overridden_key_in_snapshot[rust]` | PASSED |
| `TestUtf8KeysWithDefaults::test_emoji_override_persisted[rust]` | PASSED |
| `TestUtf8KeysWithDefaults::test_default_only_utf8_keys_absent[rust]` | PASSED |
| `TestUtf8DefaultValueGet::test_utf8_default_value_readable[rust]` | PASSED |
| `TestAllValueTypes::test_all_types_in_snapshot[rust]` | PASSED |
| `TestDefaultValuesIgnored::test_explicit_set_persisted[rust]` | PASSED |
| `TestDefaultValuesChecksum::test_checksum[optional-rust]` | PASSED |
| `TestDefaultValuesChecksum::test_checksum[required-rust]` | PASSED |
| `TestDefaultValuesMissingDefaultsFile::test_missing_defaults_file[rust]` | PASSED |
| `TestDefaultValuesMalformedDefaultsFile::test_malformed_defaults_file[optional-rust]` | PASSED |
| `TestDefaultValuesMalformedDefaultsFile::test_malformed_defaults_file[required-rust]` | PASSED |
| `TestGetDefaultValue::test_default_value_readable[rust]` | PASSED |
| `TestSelectiveReset::test_selective_reset_state[rust]` | PASSED |
| `TestMultipleInstanceIds::test_logged_execution[rust]` | PASSED |
| `TestMultipleInstanceIds::test_kvs_write_results[rust]` | PASSED |
| `TestResetToDefault::test_storage_state[rust]` | PASSED |

### `fit_cpp` — `bazel test --config=linux-x86_64 //feature_integration_tests/test_cases:fit_cpp`

| Test | Status |
|------|--------|
| `TestAllTypesWithUtf8Keys::test_utf8_keys_present[cpp]` | PASSED |
| `TestAllTypesWithUtf8Keys::test_value_types_persisted[cpp]` | PASSED |
| `TestPartialOverrideSnapshot::test_only_overridden_key_in_snapshot[cpp]` | PASSED |
| `TestUtf8KeysWithDefaults::test_emoji_override_persisted[cpp]` | PASSED |
| `TestUtf8KeysWithDefaults::test_default_only_utf8_keys_absent[cpp]` | PASSED |
| `TestUtf8DefaultValueGet::test_utf8_default_value_readable[cpp]` | PASSED |
| `TestAllValueTypes::test_all_types_in_snapshot[cpp]` | PASSED |
| `TestDefaultValuesIgnored::test_explicit_set_persisted[cpp]` | PASSED |
| `TestDefaultValuesChecksum::test_checksum[optional-cpp]` | PASSED |
| `TestDefaultValuesChecksum::test_checksum[required-cpp]` | PASSED |
| `TestDefaultValuesMissingDefaultsFile::test_missing_defaults_file[cpp]` | PASSED |
| `TestDefaultValuesMalformedDefaultsFile::test_malformed_defaults_file[optional-cpp]` | PASSED |
| `TestDefaultValuesMalformedDefaultsFile::test_malformed_defaults_file[required-cpp]` | PASSED |
| `TestGetDefaultValue::test_default_value_readable[cpp]` | PASSED |
| `TestSelectiveReset::test_selective_reset_state[cpp]` | PASSED |
| `TestMultipleInstanceIds::test_logged_execution[cpp]` | PASSED |
| `TestMultipleInstanceIds::test_kvs_write_results[cpp]` | PASSED |
| `TestResetToDefault::test_storage_state[cpp]` | PASSED |

---

## Test Files and their Source Scenario Files

| Python test file | Rust scenario file | C++ scenario file |
|---|---|---|
| `test_combined_requirements.py` | `utf8_defaults.rs`, `supported_datatypes.rs` | `utf8_defaults.cpp`, `supported_datatypes.cpp` |
| `test_datatype_support.py` | `supported_datatypes.rs` | `supported_datatypes.cpp` |
| `test_default_values.py` | `default_values.rs` | `default_values.cpp` |
| `test_multiple_kvs_per_app.py` | `mod.rs` (flat scenario) | `mod.cpp` (flat scenario) |
| `test_reset_to_default.py` | `mod.rs` (flat scenario) | `mod.cpp` (flat scenario) |

---

## Rationale

CIT tests each KVS operation in isolation (one type per test, one operation per test).  FIT tests
should validate that requirements hold in combination — observable at the storage layer without log
assertions.

- `AllValueTypes` proves that all nine types coexist in one flush without overwriting each other —
  a multi-requirement interaction CIT cannot test.
- `SelectiveReset` proves that `reset_key` leaves the correct subset of keys absent while unaffected
  keys retain their override values — combining `reset_to_default`, `default_values`,
  `default_value_file`, and `store_data` in one observable storage outcome.
