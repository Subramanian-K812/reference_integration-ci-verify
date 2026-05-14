# Persistency Supported Datatypes and Default Values Testing Analysis

**Document Version:** 1.0  
**Date:** April 28, 2026  
**Author:** GitHub Copilot (Analysis Agent)  
**Repository:** eclipse-score/persistency  
**Requirements Source:** [Eclipse SCORE Persistency Requirements](https://eclipse-score.github.io/score/main/features/persistency/requirements/index.html)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Requirements Overview](#requirements-overview)
3. [Test Framework Architecture](#test-framework-architecture)
4. [Supported Datatypes Testing](#supported-datatypes-testing)
5. [Default Values Testing](#default-values-testing)
6. [Implementation Details](#implementation-details)
7. [Recommendations for FIT Integration](#recommendations-for-fit-integration)
8. [Appendix: Code Examples](#appendix-code-examples)

---

## 1. Executive Summary

The Persistency module implements comprehensive testing for **supported datatypes** and **default values** functionality using a **Component Integration Test (CIT)** framework. The testing approach validates compliance with the following key requirements:

- **`feat_req__persistency__support_datatype_keys`**: UTF-8 encoded string keys
- **`feat_req__persistency__support_datatype_value`**: Primitive and composite value types
- **`feat_req__persistency__default_values`**: Predefined default values for keys
- **`feat_req__persistency__default_value_file`**: External file-based default provisioning
- **`feat_req__persistency__default_value_get`**: Retrieval of default values
- **`feat_req__persistency__reset_to_default`**: Reset to default values

### Key Findings

| Aspect | Implementation |
|--------|---------------|
| **Test Framework** | CIT (Component Integration Tests) with Python orchestration |
| **Scenario Languages** | Both Rust and C++ implementations (parity testing) |
| **Test Pattern** | Python parametrized tests with scenario execution |
| **Traceability** | `@add_test_properties` decorator links tests to requirements |
| **Data Validation** | Structured logging with JSON parsing for assertions |
| **Coverage** | Comprehensive datatype and default value state testing |

---

## 2. Requirements Overview

### 2.1 Supported Datatypes Requirements

#### **feat_req__persistency__support_datatype_keys** (ASIL-B)
> *The Persistency shall support UTF-8 encoded strings as valid key types.*

**Safety Classification:** ASIL-B  
**Security Relevance:** NO

#### **feat_req__persistency__support_datatype_value** (ASIL-B)
> *The Persistency shall support storing both primitive and non-primitive (composite) datatypes as values.*

**Safety Classification:** ASIL-B  
**Security Relevance:** NO

**Supported Value Types:**
- **Primitive Types:**
  - `i32` - Signed 32-bit integer
  - `u32` - Unsigned 32-bit integer
  - `i64` - Signed 64-bit integer
  - `u64` - Unsigned 64-bit integer
  - `f64` - 64-bit floating point
  - `bool` - Boolean
  - `str` - UTF-8 string
  - `null` - Null/unit type

- **Composite Types:**
  - `arr` - Arrays (heterogeneous, nested)
  - `obj` - Objects (hash maps with typed values)

### 2.2 Default Values Requirements

#### **feat_req__persistency__default_values** (ASIL-B)
> *The Persistency shall support predefined default values for keys.*

#### **feat_req__persistency__default_value_file** (ASIL-B)
> *The Persistency shall support import of default values using an external file.*

**File Format:**
- JSON format with type tags: `{"key": {"t": "f64", "v": 123.4}}`
- Companion hash file (`.hash`) using Adler-32 checksum
- File naming: `kvs_{instance_id}_default.json` and `kvs_{instance_id}_default.hash`

#### **feat_req__persistency__default_value_get** (ASIL-B)
> *The Persistency shall support retrieval of the default value associated with a key.*

**API Methods:**
- `get_default_value(key)` - Returns the default value or error
- `is_value_default(key)` - Checks if current value equals default
- `has_default_value(key)` - Checks if a default exists for the key

#### **feat_req__persistency__reset_to_default** (ASIL-B)
> *The Persistency shall support reset of individual key or all keys to their default values.*

**Reset Operations:**
- `reset()` - Reset all keys to defaults
- `reset_key(key)` - Reset single key to default
- `remove_key(key)` - Remove key (reverts to default if exists)

---

## 3. Test Framework Architecture

### 3.1 Directory Structure

```
/tmp/persistency/tests/
├── test_cases/                      # Python test orchestration
│   ├── tests/
│   │   ├── test_cit_supported_datatypes.py
│   │   ├── test_cit_default_values.py
│   │   └── common.py                 # CommonScenario base class
│   ├── conftest.py                   # Pytest fixtures
│   ├── test_properties.py            # Traceability decorator
│   └── requirements.txt              # Python dependencies
│
└── test_scenarios/                   # Scenario implementations
    ├── rust/src/cit/
    │   ├── supported_datatypes.rs
    │   └── default_values.rs
    └── cpp/src/cit/
        ├── supported_datatypes.cpp
        └── default_values.cpp
```

### 3.2 Test Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Python Test Case (Pytest)                                   │
│  - Inherits from CommonScenario                              │
│  - Defines scenario_name fixture                             │
│  - Defines test_config fixture (JSON parameters)            │
│  - Marks with @add_test_properties for traceability         │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  CommonScenario.results Fixture                              │
│  - Executes Rust or C++ test scenario binary                │
│  - Passes test_config JSON as input                         │
│  - Captures stdout, stderr, return code                     │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Test Scenario (Rust/C++)                                    │
│  - Parses input JSON (KvsParameters)                        │
│  - Creates KVS instance with configuration                  │
│  - Executes test logic                                      │
│  - Logs results via tracing::info! (Rust) or TRACING_INFO   │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Python Test Assertions                                      │
│  - Parses structured logs from LogContainer                 │
│  - Asserts on logged fields (key, value, types)            │
│  - Validates return codes and error messages                │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Key Components

#### **CommonScenario Base Class**
Provides common functionality for CIT tests:
- `results` fixture: Executes scenario binary and captures output
- `logs_info_level` fixture: Parses structured logs at INFO level
- `scenario_name()`: Abstract method defining scenario identifier
- `test_config()`: Abstract method providing JSON configuration

#### **Test Properties Decorator**
```python
@add_test_properties(
    partially_verifies=[
        "comp_req__persistency__key_encoding_v2",
        "comp_req__persistency__value_data_types_v2",
    ],
    test_type="interface-test",
    derivation_technique="requirements-analysis",
)
```

**Purpose:** Links test classes to specific requirements for traceability.

#### **Parametrization**
```python
pytestmark = pytest.mark.parametrize("version", ["rust", "cpp"], scope="class")
```

**Purpose:** Ensures both Rust and C++ implementations are tested with identical test logic.

---

## 4. Supported Datatypes Testing

### 4.1 Test Class: `TestSupportedDatatypesKeys`

**Location:** `/tmp/persistency/tests/test_cases/tests/test_cit_supported_datatypes.py`

**Requirements Verified:**
- `comp_req__persistency__key_encoding_v2`
- `comp_req__persistency__value_data_types_v2`

**Test Strategy:**
1. Create KVS instance
2. Set values with UTF-8 encoded keys:
   - ASCII: `"example"`
   - Emoji: `"emoji ✅❗😀"`
   - Greek characters: `"greek ημα"`
3. Retrieve all keys via `get_all_keys()`
4. Assert all expected keys are present

**Scenario Name:** `"cit.supported_datatypes.keys"`

**Validation Method:**
```python
def test_ok(self, results: ScenarioResult, logs_info_level: LogContainer) -> None:
    assert results.return_code == ResultCode.SUCCESS
    
    logs = logs_info_level.get_logs(field="key")
    act_keys = set(map(lambda x: x.key, logs))
    exp_keys = {"example", "emoji ✅❗😀", "greek ημα"}
    
    assert len(act_keys) == len(exp_keys)
    assert len(act_keys.symmetric_difference(exp_keys)) == 0
```

### 4.2 Test Classes: `TestSupportedDatatypesValues_*`

**Base Class:** `TestSupportedDatatypesValues` (abstract)

**Subclasses (per datatype):**
- `TestSupportedDatatypesValues_I32` → `"i32"` → `-321`
- `TestSupportedDatatypesValues_U32` → `"u32"` → `1234`
- `TestSupportedDatatypesValues_I64` → `"i64"` → `-123456789`
- `TestSupportedDatatypesValues_U64` → `"u64"` → `123456789`
- `TestSupportedDatatypesValues_F64` → `"f64"` → `-5432.1`
- `TestSupportedDatatypesValues_Bool` → `"bool"` → `true`
- `TestSupportedDatatypesValues_String` → `"str"` → `"example"`
- `TestSupportedDatatypesValues_Array` → `"arr"` → nested array with mixed types
- `TestSupportedDatatypesValues_Object` → `"obj"` → `{"sub-number": {"t": "f64", "v": 789}}`

**Test Strategy:**
1. Each subclass defines `exp_key()` and `exp_value()`
2. Scenario sets value in KVS with matching type
3. Scenario retrieves value and logs as JSON string
4. Python test parses JSON and validates type tag and value

**Validation Method:**
```python
def test_ok(self, results: ScenarioResult, logs_info_level: LogContainer) -> None:
    assert results.return_code == ResultCode.SUCCESS
    
    logs = logs_info_level.get_logs(field="key", value=self.exp_key())
    assert len(logs) == 1
    log = logs[0]
    
    assert log.key == self.exp_key()
    
    act_value = json.loads(log.value)
    assert act_value == self.exp_tagged()  # {"t": type, "v": value}
```

### 4.3 Scenario Implementation Patterns

#### **Rust Implementation**
```rust
struct SupportedDatatypesValues {
    value: KvsValue,
}

impl Scenario for SupportedDatatypesValues {
    fn name(&self) -> &str {
        match self.value {
            KvsValue::I32(_) => "i32",
            KvsValue::U32(_) => "u32",
            // ... other types
        }
    }
    
    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::from_json(input).expect("Failed to parse parameters");
        let kvs = kvs_instance(params).expect("Failed to create KVS instance");
        
        kvs.set_value(self.name(), self.value.clone())
            .expect("Failed to set value");
        
        let kvs_value = kvs.get_value(self.name()).expect("Failed to read value");
        let json_value = JsonValue::from(kvs_value);
        let json_str = json_value.stringify().expect("Failed to stringify JSON");
        
        info!(key = self.name(), value = json_str);
        
        Ok(())
    }
}
```

**Key Points:**
- Uses `KvsValue` enum for type-safe value handling
- Converts to JSON with type tags via `JsonValue::from()`
- Logs structured data via `tracing::info!` macro

#### **C++ Implementation**
```cpp
class SupportedDatatypesValues : public Scenario {
private:
    KvsValue value;
    
    static std::string kvs_value_to_string(const KvsValue& v) {
        switch (v.getType()) {
            case KvsValue::Type::i32:
                return std::to_string(std::get<int32_t>(v.getValue()));
            case KvsValue::Type::f64: {
                // High precision formatting with trailing zero removal
                auto val = std::get<double>(v.getValue());
                std::ostringstream oss;
                oss << std::setprecision(15) << val;
                std::string s = oss.str();
                // Remove trailing zeros...
                return s;
            }
            // ... other types
        }
    }
    
public:
    void run(const std::string& input) const final {
        KvsParameters params{KvsParameters::from_json(input)};
        Kvs kvs = kvs_instance(params);
        
        kvs.set_value(name(), value);
        auto kvs_value = kvs.get_value(name()).value();
        
        std::string json = "{\"t\":\"" + name() + 
                          "\",\"v\":" + kvs_value_to_string(kvs_value) + "}";
        
        TRACING_INFO(kTargetName, 
                    std::pair{"key", name()}, 
                    std::pair{"value", json});
    }
};
```

**Key Points:**
- Manual JSON serialization for type-tagged values
- Careful handling of floating-point precision
- Structured logging via `TRACING_INFO` macro

---

## 5. Default Values Testing

### 5.1 Test Class: `TestDefaultValues`

**Location:** `/tmp/persistency/tests/test_cases/tests/test_cit_default_values.py`

**Requirements Verified:**
- `comp_req__persistency__value_default_v2`
- `comp_req__persistency__default_value_cfg_v2`
- `comp_req__persistency__default_value_types_v2`
- `comp_req__persistency__default_value_query_v2`

**Parametrization:**
```python
@pytest.mark.parametrize("defaults", ["optional", "required", "without"], scope="class")
```

**Test Variants:**
1. **`optional`**: Defaults file present, KVS can initialize without it
2. **`required`**: Defaults file present, KVS requires it for initialization
3. **`without`**: No defaults file (uses `"optional"` mode to allow init)

**Test Strategy:**
1. Create defaults file with `{"test_number": {"t": "f64", "v": 111.1}}`
2. Initialize KVS with defaults configuration
3. Query default value state before modification
4. Set new value (`432.1`)
5. Flush and reopen KVS
6. Query default value state after modification
7. Validate state transitions

**Expected Behavior:**

| State | With Defaults | Without Defaults |
|-------|---------------|------------------|
| **Before set** | `is_value_default=Ok(true)`<br>`default_value=Ok(F64(111.1))`<br>`current_value=Ok(F64(111.1))` | `is_value_default=Err(KeyNotFound)`<br>`default_value=Err(KeyNotFound)`<br>`current_value=Err(KeyNotFound)` |
| **After set** | `is_value_default=Ok(false)`<br>`default_value=Ok(F64(111.1))`<br>`current_value=Ok(F64(432.1))` | `is_value_default=Ok(false)`<br>`default_value=Err(KeyNotFound)`<br>`current_value=Ok(F64(432.1))` |

### 5.2 Test Class: `TestRemoveKey`

**Test Strategy:**
1. Initialize KVS with defaults
2. Query state before set
3. Set new value
4. Query state after set
5. Remove key
6. Query state after remove
7. Validate key reverts to default (if defaults enabled)

**Expected Behavior After Remove:**

| Mode | Behavior |
|------|----------|
| **With defaults** | Key reverts to default value<br>`is_value_default=Ok(true)`<br>`current_value=Ok(F64(111.1))` |
| **Without defaults** | Key is completely removed<br>`is_value_default=Err(KeyNotFound)`<br>`current_value=Err(KeyNotFound)` |

### 5.3 Test Class: `TestResetAllKeys`

**Test Strategy:**
1. Initialize KVS with multiple default values
2. Set non-default values for all keys
3. Call `kvs.reset()` to reset all keys
4. Verify all keys revert to their default values

**Key Feature:** Tests bulk reset operation for multiple keys.

### 5.4 Test Class: `TestResetSingleKey`

**Test Strategy:**
1. Initialize KVS with multiple default values
2. Set non-default values for all keys
3. Call `kvs.reset_key(key)` for a single key
4. Verify only the targeted key reverts to default
5. Verify other keys remain unchanged

**Key Feature:** Tests selective reset without affecting other keys.

### 5.5 Test Class: `TestMalformedDefaultsFile`

**Requirements Verified:**
- Error handling for invalid defaults files

**Test Strategy:**
1. Create malformed JSON file (e.g., truncate last 2 characters)
2. Generate correct hash for malformed content
3. Attempt to initialize KVS
4. Validate KVS fails to open with appropriate error

**Error Detection:**
```python
def test_malformed_defaults(self, results: ScenarioResult) -> None:
    assert results.return_code != ResultCode.SUCCESS
    assert re.search(r"(JsonParserError|KvsFileReadError)", results.stderr)
```

### 5.6 Test Class: `TestMissingDefaultsFile`

**Test Strategy:**
1. Configure KVS with `defaults="required"`
2. Do not create defaults file
3. Attempt to initialize KVS
4. Validate KVS fails with `PANIC` (file not found)

**Key Feature:** Ensures required defaults enforcement.

### 5.7 Helper Functions

#### **`create_defaults_json(values)`**
```python
def create_defaults_json(values: dict[str, TaggedValue]) -> str:
    json_value = dict()
    for key, tagged_value in values.items():
        type_tag, value = tagged_value
        json_value[key] = {"t": type_tag, "v": value}
    return json.dumps(json_value)
```

#### **`create_defaults_file(dir_path, instance_id, values)`**
```python
def create_defaults_file(dir_path: Path, instance_id: int, 
                        values: dict[str, TaggedValue]) -> Path:
    defaults_file_path = dir_path / f"kvs_{instance_id}_default.json"
    defaults_hash_file_path = dir_path / f"kvs_{instance_id}_default.hash"
    
    json_str = create_defaults_json(values)
    hash = adler32(json_str.encode()).to_bytes(length=4, byteorder="big")
    
    with open(defaults_file_path, mode="w", encoding="UTF-8") as file:
        file.write(json_str)
    with open(defaults_hash_file_path, mode="wb") as file:
        file.write(hash)
    
    return defaults_file_path
```

**Purpose:** Creates defaults file with correct hash for integrity validation.

---

## 6. Implementation Details

### 6.1 Rust Scenario Implementation

**File:** `/tmp/persistency/tests/test_scenarios/rust/src/cit/default_values.rs`

**Key APIs Used:**
```rust
// Query default state
let value_is_default = kvs.is_value_default(key);  // Result<bool, Error>
let default_value = kvs.get_default_value(key);    // Result<KvsValue, Error>
let current_value = kvs.get_value(key);            // Result<KvsValue, Error>

// Modify values
kvs.set_value(key, value)?;
kvs.remove_key(key)?;

// Reset operations
kvs.reset()?;           // Reset all keys
kvs.reset_key(key)?;    // Reset single key

// Persistence
kvs.flush()?;
```

**Logging Pattern:**
```rust
use tracing::info;

let value_is_default = to_str(&kvs.is_value_default(key));
let default_value = to_str(&kvs.get_default_value(key));
let current_value = to_str(&kvs.get_value(key));

info!(key, value_is_default, default_value, current_value);
```

**Helper Function `to_str()`:**
```rust
pub fn to_str<T: std::fmt::Debug>(result: &Result<T, impl std::fmt::Debug>) -> String {
    match result {
        Ok(v) => format!("Ok({:?})", v),
        Err(e) => format!("Err({:?})", e),
    }
}
```

**Purpose:** Converts `Result<T, E>` to string representation for logging.

### 6.2 C++ Scenario Implementation

**File:** `/tmp/persistency/tests/test_scenarios/cpp/src/cit/default_values.cpp`

**Key APIs Used:**
```cpp
// Query default state
auto result = kvs.is_value_default(key);     // Expected<bool, Error>
auto default_val = kvs.get_default_value(key);  // Expected<KvsValue, Error>
auto current_val = kvs.get_value(key);          // Expected<KvsValue, Error>

// Modify values
kvs.set_value(key, KvsValue{value});
kvs.remove_key(key);

// Reset operations
kvs.reset();             // Reset all keys
kvs.reset_key(key);      // Reset single key

// Persistence
kvs.flush();
```

**Helper Functions:**
```cpp
std::string get_value_is_default(const Kvs& kvs, const std::string& key) {
    auto result = kvs.is_value_default(key);
    if (result.has_value()) {
        return result.value() ? "Ok(true)" : "Ok(false)";
    }
    return "Err(KeyNotFound)";
}

std::string get_default_value(Kvs& kvs, const std::string& key) {
    auto result = kvs.get_default_value(key);
    if (result.has_value() && result.value().getType() == KvsValue::Type::f64) {
        std::ostringstream oss;
        oss.precision(1);
        oss << std::fixed << std::get<double>(result.value().getValue());
        return "Ok(F64(" + oss.str() + "))";
    }
    return "Err(KeyNotFound)";
}
```

**Logging Pattern:**
```cpp
TRACING_INFO(kTargetName,
             std::pair{"key", key},
             std::pair{"value_is_default", value_is_default},
             std::pair{"default_value", default_value},
             std::pair{"current_value", current_value});
```

### 6.3 Structured Logging Format

**Output Format:**
```
INFO cpp_test_scenarios::cit::default_values key="test_number" value_is_default="Ok(true)" default_value="Ok(F64(111.1))" current_value="Ok(F64(111.1))"
```

**Python Parsing:**
```python
logs = logs_info_level.get_logs("key", value="test_number")
assert logs[0].value_is_default == "Ok(true)"
assert logs[0].default_value == "Ok(F64(111.1))"
assert logs[0].current_value == "Ok(F64(111.1))"
```

---

## 7. Recommendations for FIT Integration

### 7.1 Adopt CIT Test Structure

**Recommendation:** Mirror the CIT test structure in `reference_integration` FIT tests.

**Benefits:**
- Proven testing pattern with comprehensive coverage
- Clear separation between orchestration (Python) and execution (Rust/C++)
- Requirement traceability via `@add_test_properties`
- Parametrized testing ensures C++/Rust parity

**Implementation:**
```
reference_integration/feature_integration_tests/
├── test_cases/tests/persistency/
│   ├── test_supported_datatypes.py  # Port from test_cit_supported_datatypes.py
│   └── test_default_values.py       # Port from test_cit_default_values.py
│
└── test_scenarios/
    ├── rust/src/scenarios/persistency/
    │   ├── supported_datatypes.rs    # Port from cit/supported_datatypes.rs
    │   └── default_values.rs         # Port from cit/default_values.rs
    └── cpp/src/scenarios/persistency/
        ├── supported_datatypes.cpp    # Port from cit/supported_datatypes.cpp
        └── default_values.cpp         # Port from cit/default_values.rs (ALREADY EXISTS)
```

### 7.2 Test Coverage Requirements

**Minimum Test Coverage for Supported Datatypes:**

1. **Keys Testing:**
   - ✅ ASCII keys
   - ✅ UTF-8 keys with emojis
   - ✅ UTF-8 keys with non-Latin scripts (Greek, Cyrillic, etc.)

2. **Values Testing (All Types):**
   - ✅ `i32`, `u32`, `i64`, `u64` - Integer types
   - ✅ `f64` - Floating point with precision handling
   - ✅ `bool` - Boolean values
   - ✅ `str` - UTF-8 strings
   - ✅ `null` - Null/unit type
   - ✅ `arr` - Arrays (homogeneous and heterogeneous)
   - ✅ `obj` - Objects (nested structures)

**Minimum Test Coverage for Default Values:**

1. **Configuration Modes:**
   - ✅ `optional` - Defaults file optional
   - ✅ `required` - Defaults file mandatory
   - ✅ `without` - No defaults file


3. **Modification Operations:**
   - ✅ Set value (override default)
   - ✅ Remove key (revert to default)
   - ✅ Reset single key
   - ✅ Reset all keys

4. **Error Handling:**
   - ✅ Malformed defaults file (JSON parse error)
   - ✅ Missing defaults file (required mode)
   - ✅ Hash mismatch validation

5. **Persistence:**
   - ✅ Flush and reload validation
   - ✅ Default state after restart

### 7.3 Implementation Checklist

- [ ] **Create `test_supported_datatypes.py`** in FIT framework
  - [ ] Implement `TestSupportedDatatypesKeys`
  - [ ] Implement base class `TestSupportedDatatypesValues`
  - [ ] Implement subclasses for each datatype (i32, u32, i64, u64, f64, bool, str, arr, obj)
  - [ ] Add `@add_test_properties` with requirement IDs
  - [ ] Parametrize with `version=["rust", "cpp"]`

- [ ] **Create `test_default_values.py`** in FIT framework (if not already exists)
  - [ ] Implement `TestDefaultValues` with parametrization
  - [ ] Implement `TestRemoveKey`
  - [ ] Implement `TestResetAllKeys`
  - [ ] Implement `TestResetSingleKey`
  - [ ] Implement `TestMalformedDefaultsFile`
  - [ ] Implement `TestMissingDefaultsFile`
  - [ ] Add helper functions (`create_defaults_json`, `create_defaults_file`)

- [ ] **Create Rust scenarios** in `test_scenarios/rust/src/scenarios/persistency/`
  - [ ] Port `supported_datatypes.rs` from CIT
  - [ ] Port `default_values.rs` from CIT (if not already exists)
  - [ ] Ensure `to_str()` helper is available

- [ ] **Create C++ scenarios** in `test_scenarios/cpp/src/scenarios/persistency/`
  - [ ] Port `supported_datatypes.cpp` from CIT
  - [✅] `default_values.cpp` already exists (verify coverage)
  - [ ] Ensure helper functions for string formatting exist

- [ ] **Update BUILD files**
  - [ ] Add new test targets to `test_cases/BUILD`
  - [ ] Add new scenario targets to `test_scenarios/rust/BUILD`
  - [ ] Add new scenario targets to `test_scenarios/cpp/BUILD`

- [ ] **Validation**
  - [ ] Run `bazel test //feature_integration_tests/test_cases:fit_rust`
  - [ ] Run `bazel test //feature_integration_tests/test_cases:fit_cpp`
  - [ ] Verify both Rust and C++ scenarios pass
  - [ ] Check test coverage reports

### 7.4 Key Differences: CIT vs FIT

| Aspect | CIT (Persistency Repo) | FIT (Reference Integration) |
|--------|------------------------|----------------------------|
| **Purpose** | Component-level testing of Persistency module | Feature integration testing across modules |
| **Scope** | Single module (Persistency) | Multiple modules (Persistency + Communication + ...) |
| **Base Class** | `CommonScenario` | `FitScenario` |
| **Scenario Prefix** | `cit.*` | `persistency.*` |
| **Fixtures** | `results`, `logs_info_level` | Inherited from `FitScenario` |
| **Requirement IDs** | `comp_req__persistency__*` | `feat_req__persistency__*` |

**Adaptation Required:**
- Change scenario names from `cit.*` to `persistency.*`
- Update requirement IDs from `comp_req__*` to `feat_req__*`
- Inherit from `FitScenario` instead of `CommonScenario`
- Ensure `temp_dir_common` fixture is available

### 7.5 Testing Best Practices

1. **Parametrize Consistently:**
   ```python
   pytestmark = pytest.mark.parametrize("version", ["rust", "cpp"], scope="class")
   ```
   Ensures both implementations are tested identically.

2. **Use Structured Logging:**
   ```rust
   info!(key, value_is_default, default_value, current_value);
   ```
   Makes log parsing reliable and consistent.

3. **Create Temporary Directories:**
   ```python
   yield from temp_dir_common(tmp_path_factory, self.__class__.__name__, version)
   ```
   Isolates test data for each test class and version.

4. **Validate State Transitions:**
   - Query state before modification
   - Perform modification
   - Query state after modification
   - Assert expected state change

5. **Test Error Paths:**
   - Malformed configuration
   - Missing required files
   - Hash validation failures
   - Invalid key/value access

---

## 8. Appendix: Code Examples

### 8.1 Python Test Example: TestSupportedDatatypesKeys

```python
@add_test_properties(
    partially_verifies=[
        "feat_req__persistency__support_datatype_keys",
    ],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class TestSupportedDatatypesKeys(FitScenario):
    """Verifies that KVS supports UTF-8 string keys."""

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.supported_datatypes.keys"

    @pytest.fixture(scope="class")
    def test_config(self) -> dict[str, Any]:
        return {"kvs_parameters": {"instance_id": 1}}

    def test_ok(self, results: ScenarioResult, logs_info_level: LogContainer) -> None:
        assert results.return_code == ResultCode.SUCCESS

        logs = logs_info_level.get_logs(field="key")
        act_keys = set(map(lambda x: x.key, logs))
        exp_keys = {"example", "emoji ✅❗😀", "greek ημα"}

        assert len(act_keys) == len(exp_keys)
        assert len(act_keys.symmetric_difference(exp_keys)) == 0
```

### 8.2 Rust Scenario Example: Default Values

```rust
struct DefaultValues;

impl Scenario for DefaultValues {
    fn name(&self) -> &str {
        "default_values"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let key = "test_number";
        let params = KvsParameters::from_json(input).expect("Failed to parse parameters");
        
        {
            let kvs = kvs_instance(params.clone()).expect("Failed to create KVS instance");

            // Query state before modification
            let value_is_default = to_str(&kvs.is_value_default(key));
            let default_value = to_str(&kvs.get_default_value(key));
            let current_value = to_str(&kvs.get_value(key));

            info!(key, value_is_default, default_value, current_value);

            // Modify value
            kvs.set_value(key, 432.1).expect("Failed to set value");
            kvs.flush().expect("Failed to flush");
        }

        // Reopen and query state after modification
        {
            let kvs = kvs_instance(params).expect("Failed to create KVS instance");

            let value_is_default = to_str(&kvs.is_value_default(key));
            let default_value = to_str(&kvs.get_default_value(key));
            let current_value = to_str(&kvs.get_value(key));

            info!(key, value_is_default, default_value, current_value);
        }

        Ok(())
    }
}
```

### 8.3 C++ Scenario Example: Supported Datatypes

```cpp
class SupportedDatatypesKeys : public Scenario {
public:
    std::string name() const final { return "keys"; }

    void run(const std::string& input) const final {
        KvsParameters params{KvsParameters::from_json(input)};
        Kvs kvs = kvs_instance(params);

        std::vector<std::string> keys_to_check = {
            "example",
            u8"emoji ✅❗😀",
            u8"greek ημα"
        };
        
        for (const auto& key : keys_to_check) {
            kvs.set_value(key, KvsValue(nullptr));
        }

        auto keys_in_kvs = kvs.get_all_keys();
        if (keys_in_kvs.has_value()) {
            for (const auto& key : keys_in_kvs.value()) {
                TRACING_INFO(kTargetName, std::pair{"key", key});
            }
        } else {
            throw keys_in_kvs.error();
        }
    }
};
```

### 8.4 Python Helper: Create Defaults File

```python
def create_defaults_file(dir_path: Path, instance_id: int, 
                        values: dict[str, TaggedValue]) -> Path:
    """
    Create file containing default values with hash.
    
    Args:
        dir_path: Directory for defaults file
        instance_id: KVS instance identifier
        values: Dictionary of key -> (type_tag, value) pairs
    
    Returns:
        Path to created defaults file
    """
    defaults_file_path = dir_path / f"kvs_{instance_id}_default.json"
    defaults_hash_file_path = dir_path / f"kvs_{instance_id}_default.hash"

    # Create JSON string
    json_value = {}
    for key, (type_tag, value) in values.items():
        json_value[key] = {"t": type_tag, "v": value}
    json_str = json.dumps(json_value)

    # Generate hash
    hash_bytes = adler32(json_str.encode()).to_bytes(length=4, byteorder="big")

    # Save files
    with open(defaults_file_path, mode="w", encoding="UTF-8") as f:
        f.write(json_str)
    with open(defaults_hash_file_path, mode="wb") as f:
        f.write(hash_bytes)

    return defaults_file_path
```

---

## Conclusion

The Persistency repository implements comprehensive testing for supported datatypes and default values using a well-structured CIT framework. The testing approach provides:

1. **Comprehensive Coverage:** All datatypes and default value operations tested
2. **C++/Rust Parity:** Parametrized tests ensure both implementations are validated
3. **Requirement Traceability:** `@add_test_properties` links tests to requirements
4. **Structured Validation:** Logging-based assertions with JSON parsing
5. **Error Path Testing:** Malformed files, missing files, and edge cases covered

**Recommendation:** Port the CIT test structure to `reference_integration` FIT framework, adapting scenario names, requirement IDs, and base classes to align with the FIT architecture. This will provide comprehensive validation of the Persistency module within the integrated system context.

---

**Document Status:** ✅ Complete  
**Next Steps:** Begin implementation of supported datatypes tests in FIT framework  
**Contact:** For questions about this analysis, refer to the persistency repository test implementation.
