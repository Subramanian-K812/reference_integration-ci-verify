# PR #9 — add persistency fit datatypes

Implements feature integration tests verifying persistency requirements for KVS datatype
support, default value loading, and reset-to-default behaviour. Both Rust and C++ scenario
implementations are provided with full parity.

New test scenarios (Rust + C++):
- `persistency.supported_datatypes.all_value_types` — verify all nine KVS value types
  (i32, u32, i64, u64, f64, bool, str, arr, obj) coexist in a single flushed snapshot
- `persistency.supported_datatypes.all_types_utf8` — verify all value types stored under
  ASCII, emoji, and Greek key names are all present in a single snapshot
- `persistency.default_values.checksum` — verify adler32 hash file is written and matches
  the snapshot bytes after flush
- `persistency.default_values.partial_override` — verify only the explicitly written key
  appears in the snapshot when a defaults file provides more keys
- `persistency.default_values.get_default_value` — verify get_value returns the default
  value for a key provisioned via the defaults file but never explicitly set
- `persistency.default_values.selective_reset` — verify reset_key on even-indexed keys
  reverts them to absent while odd-indexed keys keep their override values
- `persistency.default_values.full_reset` — verify reset() clears all written keys and
  that keys written after reset are correctly persisted
- `persistency.default_values_ignored` — verify KVS ignores defaults when configured with
  KvsDefaults::Ignored
- `persistency.utf8_defaults` — verify UTF-8 encoded keys with provisioned defaults load,
  report default state, and accept overrides correctly
- `persistency.utf8_default_value_get` — verify get_default_value retrieves the correct
  value for a UTF-8 emoji key provisioned via the defaults file
- `persistency.multi_instance_isolation` — verify that default values loaded for one KVS
  instance do not leak into a second instance sharing the same working directory
- `persistency.reset_to_default` — verify reset_to_default persists correct values and
  leaves other keys unchanged

---

## Scenarios

### Rust & C++ (parity implementations)

| Scenario Name | Test Class | Test File |
|---|---|---|
| `persistency.supported_datatypes.all_value_types` | `TestAllValueTypes` | `test_datatype_support.py` |
| `persistency.supported_datatypes.all_types_utf8` | `TestAllTypesWithUtf8Keys` | `test_combined_requirements.py` |
| `persistency.default_values_ignored` | `TestDefaultValuesIgnored` | `test_default_values.py` |
| `persistency.default_values.checksum` | `TestDefaultValuesChecksum` | `test_default_values.py` |
| `persistency.default_values.checksum` | `TestDefaultValuesMissingDefaultsFile` | `test_default_values.py` |
| `persistency.default_values.checksum` | `TestDefaultValuesMalformedDefaultsFile` | `test_default_values.py` |
| `persistency.default_values.checksum` | `TestOptionalModeWithoutDefaults` | `test_default_values.py` |
| `persistency.default_values.partial_override` | `TestPartialOverrideSnapshot` | `test_combined_requirements.py` |
| `persistency.default_values.get_default_value` | `TestGetDefaultValue` | `test_default_values.py` |
| `persistency.default_values.selective_reset` | `TestSelectiveReset` | `test_default_values.py` |
| `persistency.default_values.full_reset` | `TestFullReset` | `test_default_values.py` |
| `persistency.utf8_defaults` | `TestUtf8KeysWithDefaults` | `test_combined_requirements.py` |
| `persistency.utf8_default_value_get` | `TestUtf8DefaultValueGet` | `test_combined_requirements.py` |
| `persistency.multi_instance_isolation` | `TestMultiInstanceDefaultIsolation` | `test_default_values.py` |
| `persistency.reset_to_default` | `TestResetToDefault` | `test_reset_to_default.py` |

---

## Requirements Traceability

| Test Class | Requirement IDs |
|---|---|
| `TestAllValueTypes` | `feat_req__persistency__support_datatype_value` <br> `feat_req__persistency__support_datatype_keys` <br> `feat_req__persistency__store_data` |
| `TestAllTypesWithUtf8Keys` | `feat_req__persistency__support_datatype_keys` <br> `feat_req__persistency__support_datatype_value` <br> `feat_req__persistency__store_data` |
| `TestDefaultValuesIgnored` | `feat_req__persistency__default_values` <br> `feat_req__persistency__default_value_get` |
| `TestDefaultValuesChecksum` | `feat_req__persistency__default_values` |
| `TestDefaultValuesMissingDefaultsFile` | `feat_req__persistency__default_values` <br> `feat_req__persistency__default_value_file` |
| `TestDefaultValuesMalformedDefaultsFile` | `feat_req__persistency__default_values` <br> `feat_req__persistency__default_value_file` |
| `TestOptionalModeWithoutDefaults` | `feat_req__persistency__default_values` <br> `feat_req__persistency__default_value_file` <br> `feat_req__persistency__store_data` |
| `TestPartialOverrideSnapshot` | `feat_req__persistency__default_values` <br> `feat_req__persistency__default_value_file` <br> `feat_req__persistency__store_data` |
| `TestGetDefaultValue` | `feat_req__persistency__default_value_get` (fully) <br> `feat_req__persistency__default_values` <br> `feat_req__persistency__default_value_file` |
| `TestSelectiveReset` | `feat_req__persistency__reset_to_default` <br> `feat_req__persistency__default_values` <br> `feat_req__persistency__default_value_file` <br> `feat_req__persistency__store_data` |
| `TestFullReset` | `feat_req__persistency__reset_to_default` <br> `feat_req__persistency__default_values` <br> `feat_req__persistency__default_value_file` <br> `feat_req__persistency__store_data` |
| `TestUtf8KeysWithDefaults` | `feat_req__persistency__support_datatype_keys` <br> `feat_req__persistency__default_values` <br> `feat_req__persistency__default_value_file` |
| `TestUtf8DefaultValueGet` | `feat_req__persistency__default_value_get` (fully) <br> `feat_req__persistency__support_datatype_keys` |
| `TestMultiInstanceDefaultIsolation` | `feat_req__persistency__default_values` <br> `feat_req__persistency__multiple_kvs` |
| `TestResetToDefault` | `feat_req__persistency__reset_to_default` |
