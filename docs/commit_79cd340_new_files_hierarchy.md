# New Files Added — Commit 79cd340

**Commit:** [`79cd340`](https://github.com/qorix-group/reference_integration/commit/79cd340c8f2c8130934cc494630c05cba05e3afb)
**Branch:** `Subramanian-K812_add_persistency_fit_datatypes_defaults`
**Summary:** Add persistency FIT tests for datatype support, default values, and reset-to-default

---

## File Hierarchy

```
reference_integration/
└── feature_integration_tests/
    ├── test_cases/
    │   ├── fit_scenario.py                              [MODIFIED] add build_tools version fixture + create_kvs_defaults_file helper
    │   └── tests/
    │       └── persistency/
    │           ├── test_datatype_support.py             [NEW] Python test cases for KVS supported datatypes
    │           ├── test_default_values.py               [NEW] Python test cases for KVS default value loading
    │           └── test_reset_to_default.py             [NEW] Python test cases for KVS reset-to-default behaviour
    └── test_scenarios/
        ├── cpp/
        │   └── src/
        │       ├── internals/
        │       │   └── persistency/
        │       │       ├── kvs_instance.cpp             [MODIFIED] extend KvsInstance::create to accept KvsParameters with defaults/load mode
        │       │       └── kvs_instance.h               [MODIFIED] add KvsParameters overload to factory signature
        │       └── scenarios/
        │           ├── mod.cpp                          [MODIFIED] register new scenario groups in root registry
        │           └── persistency/
        │               ├── default_values.cpp           [NEW] C++ scenarios: default_values.{default_values,remove_key,reset_all_keys,reset_single_key,checksum}
        │               ├── default_values_ignored.cpp   [NEW] C++ scenario: default_values_ignored
        │               ├── reset_to_default.cpp         [NEW] C++ scenario: reset_to_default
        │               └── supported_datatypes.cpp      [NEW] C++ scenarios: supported_datatypes.{values.*,keys}
        └── rust/
            ├── BUILD                                    [MODIFIED] expose new .rs modules as srcs
            └── src/
                └── scenarios/
                    └── persistency/
                        ├── mod.rs                       [MODIFIED] register and re-export new scenario modules
                        ├── default_values.rs            [NEW] Rust scenarios: default_values group
                        ├── default_values_ignored.rs    [NEW] Rust scenario: default_values_ignored
                        ├── reset_to_default.rs          [NEW] Rust scenario: reset_to_default
                        └── supported_datatypes.rs       [NEW] Rust scenarios: supported_datatypes group
```

---

## Summary by Layer

| Layer | New Files | Modified Files |
|-------|-----------|----------------|
| Python test cases | 3 | 1 (`fit_scenario.py`) |
| C++ scenarios | 4 | 3 (`kvs_instance.cpp`, `kvs_instance.h`, `mod.cpp`) |
| Rust scenarios | 4 | 2 (`mod.rs`, `BUILD`) |
| **Total** | **11** | **6** |

---

## Scenarios Added

### Rust & C++ (parity implementations)

| Scenario Name | Test File |
|---|---|
| `persistency.supported_datatypes.values.{i32,u32,i64,u64,f64,bool,str,arr,obj}` | `test_datatype_support.py` |
| `persistency.supported_datatypes.keys` | `test_datatype_support.py` |
| `persistency.default_values.default_values` | `test_default_values.py` |
| `persistency.default_values.remove_key` | `test_default_values.py` |
| `persistency.default_values.reset_all_keys` | `test_default_values.py` |
| `persistency.default_values.reset_single_key` | `test_default_values.py` |
| `persistency.default_values.checksum` | `test_default_values.py` |
| `persistency.default_values_ignored` | `test_default_values.py` |
| `persistency.reset_to_default` | `test_reset_to_default.py` |

---

## Requirements Traceability

| Test File | Requirement ID |
|---|---|
| `test_datatype_support.py` | `feat_req__persistency__supported_datatypes` |
| `test_default_values.py` | `feat_req__persistency__default_values` |
| `test_reset_to_default.py` | `feat_req__persistency__reset_to_default` |
