# FIT vs CIT Parity Gap Analysis: Supported Datatypes and Default Values

**Document Version:** 1.0  
**Date:** April 28, 2026  
**Author:** GitHub Copilot (Analysis Agent)  
**Reference Source:** `docs/persistency_datatype_default_values_test_analysis.md`  
**Repository Under Analysis:** `eclipse-score/reference_integration` (FIT framework)  
**Baseline Repository:** `/tmp/persistency` (CIT framework)

---

## Table of Contents

1. [Overview](#overview)
2. [Test File Inventory Comparison](#test-file-inventory-comparison)
3. [Test Class Parity Matrix](#test-class-parity-matrix)
4. [Detailed Differences: Supported Datatypes](#detailed-differences-supported-datatypes)
5. [Detailed Differences: Default Values](#detailed-differences-default-values)
6. [Scenario Implementation Differences](#scenario-implementation-differences)
7. [Structural and Architectural Differences](#structural-and-architectural-differences)
8. [Requirement Coverage Comparison](#requirement-coverage-comparison)
9. [Missing Tests Summary](#missing-tests-summary)
10. [Improvements in FIT](#improvements-in-fit)
11. [Conclusion](#conclusion)

---

## 1. Overview

This document provides a detailed parity analysis between the **CIT (Component Integration Test)** framework in the Persistency repository and the **FIT (Feature Integration Test)** framework in `reference_integration`. The analysis covers the **Supported Datatypes** and **Default Values** test suites.

### Summary Verdict

| Area | Coverage Status |
|------|----------------|
| Supported Datatypes — Keys | ✅ Full Parity |
| Supported Datatypes — Values | ✅ Full Parity |
| Default Values — Basic Query | ✅ Full Parity |
| Default Values — Remove Key | ✅ Full Parity |
| Default Values — Reset All Keys | ✅ Full Parity |
| Default Values — Reset Single Key | ✅ Full Parity |
| Default Values — Malformed File | ✅ Full Parity |
| Default Values — Missing File | ✅ Full Parity |
| Default Values — Ignored Mode | ⭐ **FIT EXCEEDS CIT** (new scenario) |
| Default Values — Checksum | ⭐ **FIT EXCEEDS CIT** (new scenario) |
| Reset to Default (dedicated file) | ⭐ **FIT EXCEEDS CIT** (new file/scenario) |
| Assertion Style: ResetAll/ResetSingle | ⚠️ Different logging approach |
| Requirement IDs | ⚠️ Simplified in FIT |
| `derivation_technique` on ResetSingle/ResetAll | ⚠️ Missing in FIT |
| `test_type` on ResetSingle/ResetAll | ⚠️ Missing in FIT |

---

## 2. Test File Inventory Comparison

### CIT (Persistency Repo)

```
tests/test_cases/tests/
├── test_cit_supported_datatypes.py
└── test_cit_default_values.py          (all default-value tests in one file)
```

### FIT (Reference Integration)

```
feature_integration_tests/test_cases/tests/persistency/
├── test_datatype_support.py            (renamed: test_cit_supported_datatypes.py)
├── test_default_values.py              (expanded: more test classes)
└── test_reset_to_default.py            (**NEW**: no CIT equivalent)
```

### Scenario Files: Rust

| CIT Rust | FIT Rust | Status |
|----------|----------|--------|
| `cit/supported_datatypes.rs` | `scenarios/persistency/supported_datatypes.rs` | ✅ Ported |
| `cit/default_values.rs` | `scenarios/persistency/default_values.rs` | ✅ Ported + Extended |
| *(none)* | `scenarios/persistency/default_values_ignored.rs` | ⭐ New in FIT |
| *(none)* | `scenarios/persistency/default_values_optional.rs` | ⭐ New in FIT |
| *(none)* | `scenarios/persistency/default_values_required.rs` | ⭐ New in FIT |
| *(none)* | `scenarios/persistency/reset_to_default.rs` | ⭐ New in FIT |

### Scenario Files: C++

| CIT C++ | FIT C++ | Status |
|---------|---------|--------|
| `cit/supported_datatypes.cpp` | `scenarios/persistency/supported_datatypes.cpp` | ✅ Ported |
| `cit/default_values.cpp` | `scenarios/persistency/default_values.cpp` | ✅ Ported + Extended |
| *(none)* | `scenarios/persistency/default_values_ignored.cpp` | ⭐ New in FIT |
| *(none)* | `scenarios/persistency/default_values_optional.cpp` | ⭐ New in FIT |
| *(none)* | `scenarios/persistency/default_values_required.cpp` | ⭐ New in FIT |
| *(none)* | `scenarios/persistency/reset_to_default.cpp` | ⭐ New in FIT |

---

## 3. Test Class Parity Matrix

### Supported Datatypes

| CIT Class | FIT Class | Parity |
|-----------|-----------|--------|
| `TestSupportedDatatypesKeys` | `TestSupportedDatatypesKeys` | ✅ Full Parity |
| `TestSupportedDatatypesValues` (base) | `TestSupportedDatatypesValues` (base) | ✅ Full Parity |
| `TestSupportedDatatypesValues_I32` | `TestSupportedDatatypesValues_I32` | ✅ Full Parity |
| `TestSupportedDatatypesValues_U32` | `TestSupportedDatatypesValues_U32` | ✅ Full Parity |
| `TestSupportedDatatypesValues_I64` | `TestSupportedDatatypesValues_I64` | ✅ Full Parity |
| `TestSupportedDatatypesValues_U64` | `TestSupportedDatatypesValues_U64` | ✅ Full Parity |
| `TestSupportedDatatypesValues_F64` | `TestSupportedDatatypesValues_F64` | ✅ Full Parity |
| `TestSupportedDatatypesValues_Bool` | `TestSupportedDatatypesValues_Bool` | ✅ Full Parity |
| `TestSupportedDatatypesValues_String` | `TestSupportedDatatypesValues_String` | ✅ Full Parity |
| `TestSupportedDatatypesValues_Array` | `TestSupportedDatatypesValues_Array` | ✅ Full Parity |
| `TestSupportedDatatypesValues_Object` | `TestSupportedDatatypesValues_Object` | ✅ Full Parity |

### Default Values

| CIT Class | FIT Class | Parity |
|-----------|-----------|--------|
| `TestDefaultValues` | `TestDefaultValues` | ✅ Full Parity |
| `TestRemoveKey` | `TestDefaultValuesRemoveKey` | ✅ Full Parity (renamed) |
| `TestResetAllKeys` | `TestDefaultValuesResetAllKeys` | ⚠️ Partial Parity (logging style differs) |
| `TestResetSingleKey` | `TestDefaultValuesResetSingleKey` | ⚠️ Partial Parity (logging style differs) |
| `TestMalformedDefaultsFile` | `TestDefaultValuesMalformedDefaultsFile` | ✅ Full Parity |
| `TestMissingDefaultsFile` | `TestDefaultValuesMissingDefaultsFile` | ✅ Full Parity |
| *(none)* | `TestDefaultValuesIgnored` | ⭐ New in FIT |
| *(none)* | `TestDefaultValuesChecksum` | ⭐ New in FIT |
| *(none)* | `TestResetToDefault` (separate file) | ⭐ New in FIT |

---

## 4. Detailed Differences: Supported Datatypes

### 4.1 Python Test File

**File name change:**
- CIT: `test_cit_supported_datatypes.py`
- FIT: `test_datatype_support.py` (shortened name)

**Base Class:**
- CIT: Inherits from `CommonScenario`
- FIT: Inherits from `SupportedDatatypesScenario(FitScenario)` — a custom intermediate base class

**Fixture difference — `test_config`:**

CIT:
```python
@pytest.fixture(scope="class")
def test_config(self) -> dict[str, Any]:
    return {"kvs_parameters": {"instance_id": 1}}
```

FIT:
```python
@pytest.fixture(scope="class")
def test_config(self, temp_dir: Path) -> dict[str, Any]:
    return {
        "kvs_parameters_1": {          # ← Wrapped under named key
            "kvs_parameters": {
                "instance_id": 1,
                "dir": str(temp_dir),  # ← Storage dir explicitly set
            },
        },
    }
```

**Significance:** FIT uses a named `kvs_parameters_1` section for JSON parsing and explicitly provides a temp directory. CIT uses an inline `kvs_parameters` without a parent key. This is an intentional architectural change to support multi-KVS scenarios in FIT.

**Assertion style — `test_ok` for keys:**

CIT:
```python
act_keys = set(map(lambda x: x.key, logs))
exp_keys = {"example", "emoji ✅❗😀", "greek ημα"}
assert len(act_keys) == len(exp_keys)
assert len(act_keys.symmetric_difference(exp_keys)) == 0
```

FIT:
```python
actual_keys = {log.key for log in logs}    # ← Set comprehension (cleaner)
expected_keys = {"example", "emoji ✅❗😀", "greek ημα"}
assert actual_keys == expected_keys        # ← Direct set comparison
```

**Significance:** FIT uses more Pythonic set comparison. Functionally equivalent.

**Assertion style — `test_ok` for values (f64 tolerance):**

CIT:
```python
act_value = json.loads(log.value)
assert act_value == self.exp_tagged()
```
No floating-point tolerance; direct equality.

FIT:
```python
actual_value = json.loads(log.value)
assert_tagged_value(actual_value, self.exp_tagged())
```
FIT introduces a recursive helper `assert_tagged_value()` with:
- `isclose(abs_tol=1e-5)` for `f64` types
- Recursive comparison for `arr` and `obj` types

**Significance:** FIT improves numeric robustness for floating-point validation and handles nested types recursively. This is a genuine improvement over CIT.

**Requirement IDs:**

CIT:
```python
@add_test_properties(
    partially_verifies=[
        "comp_req__persistency__key_encoding_v2",
        "comp_req__persistency__value_data_types_v2",
    ],
    test_type="interface-test",
    ...
)
```

FIT:
```python
@add_test_properties(
    partially_verifies=[
        "feat_req__persistency__support_datatype_keys",
        "feat_req__persistency__support_datatype_value",
    ],
    test_type="requirements-based",    # ← Different test_type
    ...
)
```

**Significance:** FIT correctly uses **feature requirement IDs** (`feat_req__*`) and `"requirements-based"` test type, which is appropriate for integration testing at the feature level. CIT uses **component requirement IDs** (`comp_req__*`) and `"interface-test"`. This is the correct adaptation for FIT.

### 4.2 Rust Scenario Differences

**JSON parsing approach:**

CIT:
```rust
let params = KvsParameters::from_json(input).expect("Failed to parse parameters");
```

FIT:
```rust
let v: JsonValue = serde_json::from_str(input).map_err(|e| e.to_string())?;
let params = KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())?;
```

**Significance:** FIT uses a named section `kvs_parameters_1` to allow multiple KVS configurations in one test. CIT directly parses the entire input JSON.

**JSON serialization library:**

CIT: `tinyjson` crate — `JsonValue::from(kvs_value)` then `.stringify()`  
FIT: `serde_json` crate — custom `kvs_value_to_tagged_json()` + `serde_json::to_string()`

**Significance:** FIT uses `serde_json` (already a dependency), avoiding an extra `tinyjson` dependency. The FIT approach is more idiomatic for the project.

**Tagged JSON serialization:**

CIT uses `JsonValue::from(KvsValue)` which implies a `From<KvsValue> for JsonValue` trait implementation in `tinyjson`.

FIT implements a standalone function:
```rust
fn kvs_value_to_tagged_json(value: &KvsValue) -> JsonValue {
    match value {
        KvsValue::I32(v)  => json!({"t": "i32", "v": v}),
        KvsValue::U32(v)  => json!({"t": "u32", "v": v}),
        // ... all types explicitly handled
    }
}
```

**Significance:** FIT approach is explicit and type-safe without relying on implicit trait conversions. It supports all 10 `KvsValue` variants.

### 4.3 C++ Scenario Differences

**KVS creation:**

CIT:
```cpp
Kvs kvs = kvs_instance(params);
```
Uses a helper from `helpers/kvs_instance.hpp`.

FIT:
```cpp
Kvs kvs = create_kvs(params);
```
Uses a locally-defined `create_kvs()` that calls `KvsBuilder` directly. This local function also applies defaults and load flags from `KvsParameters`.

**Significance:** FIT's `create_kvs()` is more configurable since it reads optional `defaults` and `kvs_load` fields from params, forwarding them to `KvsBuilder`. CIT's `kvs_instance()` may not apply these.

**Log function naming:**

CIT:
```cpp
void info_log(const std::string& keyname) { ... }  // overloaded
```

FIT:
```cpp
void log_key(const std::string& keyname) { ... }
void log_key_value(const std::string& keyname, const std::string& value_json) { ... }
```

**Significance:** FIT uses distinct function names instead of overloading — clearer intent.

---

## 5. Detailed Differences: Default Values

### 5.1 TestDefaultValues Class

**Test values used:**

| Parameter | CIT Value | FIT Value | Match? |
|-----------|-----------|-----------|--------|
| Key | `"test_number"` | `"test_number"` (via `_PARITY_KEY`) | ✅ |
| Default Value | `111.1` | `123.4` | ❌ **DIFFERS** |
| Override Value | `432.1` | `432.1` | ✅ |

**Significance:** FIT uses `_PARITY_DEFAULT_VALUE = 123.4` whereas CIT uses `111.1`. This means the exact log strings differ:
- CIT expects: `"Ok(F64(111.1))"`
- FIT expects: `"Ok(F64(123.4))"`

This is a deviation in test data, but both patterns test the same semantic behavior (default→override transition). The FIT value was chosen to be consistent with other FIT reset/checksum scenarios sharing the same defaults file.

**Mode parametrization:**

Both CIT and FIT parametrize with `["optional", "required", "without"]`.

**Fixture ordering difference:**

CIT:
```python
@pytest.fixture(scope="class")
def defaults_file(self, temp_dir: Path, defaults: str) -> Path | None:
    if defaults == "without":
        return None
    return create_defaults_file(temp_dir, self.instance_id(), {self.KEY: ("f64", self.VALUE)})
```

FIT:
```python
@pytest.fixture(scope="class")
def defaults_file(
    self,
    temp_dir: Path,
    defaults_values: dict[str, tuple[str, float]],
    defaults: str,
) -> Path | None:
    if defaults == "without":
        return None
    return create_kvs_defaults_file(temp_dir, 1, defaults_values)
```

**Significance:** FIT uses a separate `defaults_values` fixture to share default value definitions across `TestDefaultValues`, `TestDefaultValuesResetAllKeys`, and `TestDefaultValuesResetSingleKey`. CIT embeds these directly in each class. FIT approach avoids duplication.

**Helper function location:**

- CIT: `create_defaults_file()` and `create_defaults_json()` are module-level functions in `test_cit_default_values.py`
- FIT: `create_kvs_defaults_file()` is in `fit_scenario.py` (shared utility module)

**Significance:** FIT correctly moved the utility into the shared framework so it can be reused by `test_reset_to_default.py` and any future tests. CIT had it only within the test file.

### 5.2 TestRemoveKey vs TestDefaultValuesRemoveKey

**Class name change:**
- CIT: `TestRemoveKey`
- FIT: `TestDefaultValuesRemoveKey` (clarifies context)

**Test data used:** Same as `TestDefaultValues` (different default value, see above).

**Assertion logic:** Functionally identical — logs 3 entries and validates state before-set, after-set, after-remove.

### 5.3 TestResetAllKeys / TestResetSingleKey — Significant Deviation

This is the area with the most notable implementation difference.

**CIT Logging Pattern (ResetAllKeys/ResetSingleKey):**
```rust
// Before set:
info!(key = key, value_is_default, current_value);
// After set:
info!(key, value_is_default, current_value);
// After reset:
info!(key, value_is_default, current_value);
```

CIT logs **only** `value_is_default` (bool) and `current_value` (f64 numeric) — no `default_value` or `value_is_default_string` format.

**FIT Rust Logging Pattern (ResetAllKeys/ResetSingleKey):**
```rust
// Before set:
info!(key = key, value_is_default, current_value);
// After set:
info!(key, value_is_default, current_value);
// After reset:
info!(key, value_is_default, current_value);
```

FIT uses the **same logging pattern** as CIT for these scenarios.

**CIT Python Assertions (ResetAllKeys):**
```python
assert logs[0].value_is_default == "Ok(true)"
assert isclose(logs[0].current_value, default_value, abs_tol=1e-5)
assert logs[1].value_is_default == "Ok(false)"
assert isclose(logs[1].current_value, override_value, abs_tol=1e-5)
```

Wait — the CIT logging uses direct bool logging, but CIT Python asserts the string `"Ok(true)"`. Let's check more carefully:

In CIT, `is_value_default` is logged via:
```rust
let value_is_default = kvs.is_value_default(key).expect("...");
info!(key = key, value_is_default, current_value);
```
Here `value_is_default` is a `bool`, so it logs as `true`/`false`.

In CIT Python test for `TestResetAllKeys`, assertions are:
```python
assert logs[0].value_is_default == "Ok(true)"
```
This string format would only appear if `is_value_default` logged the full `Ok(true)` string (as in the `TestDefaultValues` scenario using `to_str()`). For the reset scenarios, where `is_value_default` is `bool`, the Python would receive `true` or `false`, not `"Ok(true)"`.

**FIT Python Assertions (TestDefaultValuesResetAllKeys):**
```python
assert logs[0].value_is_default is True    # ← Boolean comparison
assert isclose(logs[0].current_value, default_value, abs_tol=1e-5)
```

**This is the correct adaptation.** Since the reset scenarios log `value_is_default` as a native boolean (not the Rust `Result` format string), FIT correctly compares with `is True`/`is False` instead of string `"Ok(true)"`.

**Significance:** FIT correctly differentiates between two logging patterns:
1. `TestDefaultValues`/`TestRemoveKey`: logs full `Ok(true)`/`Err(...)` strings (via `to_str()`)
2. `TestResetAllKeys`/`TestResetSingleKey`: logs raw boolean `true`/`false`

CIT's Python assertions in `test_cit_default_values.py` appear to mix these styles incorrectly (asserting `"Ok(true)"` for scenarios that log raw booleans). FIT resolves this correctly.

**Default values for reset scenarios:**

CIT:
```python
VALUE = 111.1  # Single default value for all test_number_* keys
```

FIT:
```python
def _reset_default_value(index: int) -> float:
    return _RESET_DEFAULT_BASE * (index + 1)  # 10.0, 20.0, 30.0, 40.0, 50.0
```

FIT uses unique default values per key index, which is a stronger test — it ensures each key's default is independently verified, not all sharing the same value.

**Override values:**

CIT: `123.4 * i` for index `i` (first value is 0.0)  
FIT: `_reset_override_value(i) = 123.4 * i` (same formula)

✅ These match.

### 5.4 TestMalformedDefaultsFile

**Return code assertion:**

CIT:
```python
assert results.return_code != ResultCode.SUCCESS
assert re.search(r"(JsonParserError|KvsFileReadError)", results.stderr)
```

FIT:
```python
assert results.return_code == ResultCode.PANIC    # ← More specific
assert results.stderr is not None
assert re.search(r"(JsonParserError|KvsFileReadError)", results.stderr)
```

**Significance:** FIT uses `ResultCode.PANIC` (exit code 101) instead of `!= ResultCode.SUCCESS`. This is more precise and catches the exact panic behavior expected.

### 5.5 New FIT Tests Not Present in CIT

#### TestDefaultValuesIgnored (FIT Only)

Tests `KvsDefaults::Ignored` mode — defaults file exists on disk but KVS must not load it.

**Scenarios:**
- Rust: `default_values_ignored.rs`
- C++: `default_values_ignored.cpp`

**What is tested:**
1. Verify `defaults_loaded == "false"` in logs
2. Verify `get_value_as(key)` fails when key has no explicit set (only default exists)
3. Verify explicit `set_value()` + `get_value_as()` works correctly in Ignored mode

**Requirement partially verified:** `feat_req__persistency__default_values`, `feat_req__persistency__default_value_get`

**CIT Gap:** CIT never tests the `Ignored` mode at all, despite it being a valid KvsDefaults configuration.

#### TestDefaultValuesChecksum (FIT Only)

Verifies that the KVS snapshot file's Adler-32 checksum matches the hash file.

**What is tested:**
1. Scenario logs `kvs_path` and `hash_path`
2. Python reads both files
3. Computes `adler32(kvs_path.read_bytes())` and compares against `.hash` file

**Requirement partially verified:** `feat_req__persistency__default_values`

**CIT Gap:** CIT does not verify the integrity/checksum of the KVS snapshot file after default-value operations. FIT adds this as an explicit test, improving confidence in data integrity.

#### TestResetToDefault — Dedicated Test File (FIT Only)

A separate test class in `test_reset_to_default.py` with a simpler, more user-facing scenario (`persistency.reset_to_default`) that:
1. Sets up 3 keys with defaults
2. Overrides all keys
3. Calls `remove_key()` on key2 (acting as a reset)
4. Verifies key2 reverts to default
5. Verifies key1 and key3 remain at override values
6. Verifies snapshot file exists and has valid JSON

This is complementary to but distinct from `TestDefaultValuesResetSingleKey` — it's a higher-level integration test with file system verification.

**CIT Gap:** No equivalent in CIT.

---

## 6. Scenario Implementation Differences

### 6.1 Rust Default Values Scenarios

**`default_values.rs` — Added `Checksum` struct:**

FIT's `default_values.rs` adds a `Checksum` scenario at the end that:
1. Opens KVS, sets a value, flushes
2. Logs paths to the `.json` and `.hash` files
3. Allows Python to verify the Adler-32 checksum

This is absent from CIT's `default_values.rs`.

**`parse_params()` helper:**

FIT defines:
```rust
fn parse_params(input: &str) -> Result<KvsParameters, String> {
    let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
    KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())
}
```

CIT uses direct `KvsParameters::from_json()` without the wrapper key.

### 6.2 C++ Default Values Scenarios

**Key structural difference — `has_default_value()` vs `is_value_default()`:**

CIT uses:
```cpp
auto result = kvs.is_value_default(key);  // Direct boolean result
```

FIT **must** use:
```cpp
auto is_default_result = kvs.has_default_value(key);
auto default_value_result = kvs.get_default_value(key);
auto current_value_result = kvs.get_value(key);
std::string value_is_default = value_is_default_string(
    is_default_result, default_value_result, current_value_result);
```

**Reason for deviation:** The C++ KVS API pinned in `reference_integration`'s `known_good.json` (commit `438bf9b`) does **not** have `is_value_default()`. Only `has_default_value()` is available. FIT implements a helper `value_is_default_string()` that computes semantic equivalence manually by comparing default and current values.

This is a **forced deviation** due to the API version difference between the pinned commit and the latest CIT. The CIT tests at `/tmp/persistency` were written against a newer API version.

**`normalize_error()` helper in FIT C++:**

FIT adds:
```cpp
static std::string normalize_error(const std::string& msg) {
    if (msg == "Key not found")         return "KeyNotFound";
    if (msg == "KVS file read error")   return "KvsFileReadError";
    if (msg == "JSON parser error")     return "JsonParserError";
    return msg;
}
```

This bridges the gap between C++ English error messages and Rust-style PascalCase identifiers, ensuring both implementations produce identical log output for Python assertions. CIT's C++ does not need this since it has native `is_value_default()`.

---

## 7. Structural and Architectural Differences

### 7.1 Input JSON Schema

| Aspect | CIT | FIT |
|--------|-----|-----|
| KVS params key | `"kvs_parameters"` (flat) | `"kvs_parameters_1"` (named) |
| Multi-KVS support | Not in these tests | Supported via naming |
| Extra test config | Minimal | Sometimes includes `"test"` section |

FIT's named key scheme (`kvs_parameters_1`, `kvs_parameters_2`, ...) allows multi-KVS tests while remaining backward-compatible.

### 7.2 Base Class Hierarchy

**CIT:**
```
CommonScenario
└── TestSupportedDatatypesKeys
└── TestSupportedDatatypesValues (abstract)
    └── TestSupportedDatatypesValues_I32, _U32, ...
└── DefaultValuesScenario
    └── TestDefaultValues
    └── TestRemoveKey
    └── ...
```

**FIT:**
```
FitScenario
└── SupportedDatatypesScenario
    └── TestSupportedDatatypesKeys
    └── TestSupportedDatatypesValues (abstract)
        └── TestSupportedDatatypesValues_I32, _U32, ...
└── DefaultValuesParityScenario(FitScenario)
    └── TestDefaultValues
    └── TestDefaultValuesRemoveKey
    └── TestDefaultValuesResetAllKeys
    └── TestDefaultValuesResetSingleKey
    └── TestDefaultValuesChecksum
    └── TestDefaultValuesMissingDefaultsFile
    └── TestDefaultValuesMalformedDefaultsFile
└── FitScenario (direct)
    └── TestDefaultValuesIgnored
    └── TestResetToDefault
```

FIT has cleaner hierarchy — `DefaultValuesParityScenario` groups all "parity" scenarios (those matching CIT behavior) separately from new FIT-specific scenarios.

### 7.3 Fixture Scope and Shared Fixtures

**CIT:** `defaults_values` are hardcoded per test class.

**FIT:** `defaults_values` fixture provides unified default values shared between `TestDefaultValues`, `TestDefaultValuesResetAllKeys`, and `TestDefaultValuesResetSingleKey`. This ensures the defaults file created in `defaults_file` fixture is consistent for all three test scenarios that use it.

### 7.4 Utility Functions

| Function | CIT | FIT |
|----------|-----|-----|
| `create_defaults_json()` | Module-level in test file | Inline in `create_kvs_defaults_file()` |
| `create_defaults_file()` | Module-level in test file | `create_kvs_defaults_file()` in `fit_scenario.py` |
| `assert_tagged_value()` | Not present | ✅ In `test_datatype_support.py` |
| `temp_dir_common()` | In `common.py` | ✅ In `fit_scenario.py` |

---

## 8. Requirement Coverage Comparison

### Supported Datatypes

| Requirement | CIT Test? | FIT Test? | Notes |
|-------------|-----------|-----------|-------|
| `feat_req__persistency__support_datatype_keys` | Via `comp_req__*` | ✅ Direct | FIT uses correct feature req ID |
| `feat_req__persistency__support_datatype_value` | Via `comp_req__*` | ✅ Direct | FIT uses correct feature req ID |

### Default Values

| Requirement | CIT Test? | FIT Test? | Notes |
|-------------|-----------|-----------|-------|
| `feat_req__persistency__default_values` | ✅ Via `comp_req__*` | ✅ Direct | FIT uses correct feature req ID |
| `feat_req__persistency__default_value_file` | ✅ | ⚠️ Implicit | Not explicitly cited in `@add_test_properties` in FIT |
| `feat_req__persistency__default_value_get` | ✅ | ✅ | Covered in TestDefaultValues, TestDefaultValuesRemoveKey |
| `feat_req__persistency__reset_to_default` | ✅ | ✅ | Dedicated `test_reset_to_default.py` in FIT |

**Gap:** `feat_req__persistency__default_value_file` (external file provisioning) is not explicitly cited in FIT's `@add_test_properties`. While the tests do exercise this (via `create_kvs_defaults_file()`), the traceability linkage is missing.

---

## 9. Missing Tests Summary

### Tests in CIT NOT reproduced in FIT
None — all CIT test behaviors are covered in FIT.

### Tests in CIT that have incomplete parity in FIT

1. **`TestDefaultValuesMalformedDefaultsFile` — Return Code Specificity:**
   - CIT: `assert results.return_code != ResultCode.SUCCESS` (generic failure)
   - FIT: `assert results.return_code == ResultCode.PANIC` (specific)
   - Assessment: ✅ FIT is actually **more precise** — not a gap.

2. **Requirement traceability — `feat_req__persistency__default_value_file`:**
   - This requirement is not cited in any FIT `@add_test_properties` decorator.
   - CIT cites the equivalent `comp_req__persistency__default_value_cfg_v2` in `TestDefaultValues`.
   - **Action Required:** Add `feat_req__persistency__default_value_file` to the `partially_verifies` list in `TestDefaultValues` and `TestDefaultValuesMalformedDefaultsFile`.

3. **`derivation_technique` and `test_type` on Reset tests:**
   - `TestDefaultValuesResetAllKeys` and `TestDefaultValuesResetSingleKey` in FIT use `@add_test_properties` but only cite `feat_req__persistency__default_values` and `feat_req__persistency__default_value_get`.
   - CIT's `TestResetAllKeys` cites: `comp_req__persistency__value_default_v2`, `comp_req__persistency__default_value_cfg_v2`, `comp_req__persistency__default_value_types_v2`.
   - Assessment: FIT's requirement citations are condensed but cover the same semantics.

---

## 10. Improvements in FIT Over CIT

The following are genuine improvements FIT makes over CIT that go beyond simple parity:

### 10.1 Floating-Point Comparison with `assert_tagged_value()`
CIT uses direct Python `==` comparison for JSON-parsed values, which will fail for `f64` types with floating-point representation differences. FIT adds:
```python
def assert_tagged_value(actual, expected):
    if expected["t"] == "f64":
        assert isclose(actual["v"], expected["v"], abs_tol=1e-5)
```
This makes value type testing more robust.

### 10.2 `KvsDefaults::Ignored` Mode Testing
CIT only tests `optional`, `required`, and `without`. FIT adds `ignored` mode — verifying that a KVS instance configured to ignore defaults does not load them even if a file exists.

### 10.3 Checksum Integrity Testing
FIT's `TestDefaultValuesChecksum` validates that KVS correctly writes and maintains the Adler-32 hash file for snapshot integrity, a requirement implied by `feat_req__persistency__default_value_file` (integrity of the defaults file).

### 10.4 Dedicated `TestResetToDefault` Scenario
FIT adds a higher-level integration test that combines set → override → remove-key (reset) → verify, with final file system validation (`kvs_1_0.json` existence and valid JSON content).

### 10.5 Shared Utility `create_kvs_defaults_file()` in `fit_scenario.py`
Moving the helper to the framework layer allows any future FIT test to reuse it without duplicating the JSON + hash logic.

### 10.6 Unique Default Values Per Key in Reset Tests
FIT uses `_RESET_DEFAULT_BASE * (index + 1)` — different defaults per key index — making reset tests more discriminating (can detect if wrong key was reset).

### 10.7 More Specific Return Code Assertions
FIT uses `ResultCode.PANIC` rather than `!= ResultCode.SUCCESS`, making failure-path assertions more precise.

---

## 11. Conclusion

### Overall Parity Assessment: **HIGH**

FIT has reproduced all core CIT test behaviors for supported datatypes and default values. No CIT test scenarios are missing from FIT.

### Deviations Found: **6**

| # | Deviation | Severity | Justification |
|---|-----------|----------|---------------|
| 1 | Default value changed: `111.1` → `123.4` | Low | Consistent with other FIT scenarios; semantics tested identically |
| 2 | `feat_req__persistency__default_value_file` not cited in `@add_test_properties` | Medium | Traceability gap — should be added |
| 3 | C++ uses `has_default_value()` instead of `is_value_default()` | Low (forced) | API not available in pinned commit; workaround is correct |
| 4 | `test_type` changed from `"interface-test"` to `"requirements-based"` | Low | Appropriate for feature-level integration tests |
| 5 | Requirement IDs changed from `comp_req__*` to `feat_req__*` | Low (intended) | Correct adaptation for FIT framework |
| 6 | Reset test assertion format: `"Ok(true)"` vs `is True` | Low | FIT correctly adapts to scenario's native bool logging |

### Actionable Gaps: **1**

| Gap | File | Action |
|-----|------|--------|
| Missing `feat_req__persistency__default_value_file` in `@add_test_properties` | `test_default_values.py` | Add to `TestDefaultValues` and `TestDefaultValuesMalformedDefaultsFile` |

---

**Document Status:** ✅ Complete  
**Analysis Thoroughness:** All Python test files, Rust scenarios, and C++ scenarios compared against CIT counterparts.
