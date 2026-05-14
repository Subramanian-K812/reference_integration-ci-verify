Overview
The goal was to implement integration tests (FIT) for two persistency feature requirement areas:

Supported Datatypes — KVS supports UTF-8 string keys and all documented value types (i32, u32, i64, u64, f64, bool, string, null, array, object).
Default Values — KVS correctly initializes from a defaults file, reports whether a value is default, and restores defaults via remove_key, reset, reset_key.
Every test scenario is implemented twice — in Rust and C++ — and a single Python test class exercises both via @pytest.mark.parametrize("version", ["rust", "cpp"]).

Architecture: How the FIT Framework Works
Each scenario binary accepts a --scenario path (dot-separated group hierarchy) and a --input JSON string, executes the code, and writes structured JSON log lines to stdout. The Python test reads those log lines through LogContainer.

Files Created
1. supported_datatypes.rs
Purpose: Rust implementation of 10 scenarios under persistency.supported_datatypes.*.

Structure:

kvs_value_tag() — maps a KvsValue variant to its short type tag ("i32", "f64", etc.)
kvs_value_to_tagged_json() — recursively converts a KvsValue to {"t": "...", "v": ...} JSON — handles arrays and objects recursively
SupportedDatatypesKeys scenario (keys): creates a KVS instance, stores three UTF-8 keys (ASCII, emoji, Greek), calls get_all_keys(), logs each key as info!(key)
SupportedDatatypesValues scenario (one per type): stores a typed value, reads it back, serializes it as tagged JSON, logs info!(key = type_tag, value = json_str)
supported_datatypes_group() — returns a ScenarioGroupImpl("supported_datatypes", [keys], [values subgroup]) with 9 typed value sub-scenarios
2. default_values.rs
Purpose: Rust implementation of 5 scenarios under persistency.default_values.*.

Helper: to_str<T: Debug>(v) → String uses {:?} formatting to produce Rust-style output like Ok(F64(123.4)), Err(KeyNotFound).

Scenarios:

Name	What it does
default_values	Opens KVS twice: before and after set_value + flush; logs value_is_default, default_value, current_value for key "test_number" both times
remove_key	Logs state before override, after override, and after remove_key() (which should restore the default)
reset_all_keys	Sets 5 numbered keys to override values, calls kvs.reset(), logs before/after state for all keys
reset_single_key	Same 5 keys, but only calls kvs.reset_key(key_2) and logs final state per key
checksum	Writes and flushes KVS, then logs the paths of the .json and .hash snapshot files so Python can verify the adler32 checksum
default_values_group() exports all 5 as a ScenarioGroupImpl("default_values", [...], []).

3. supported_datatypes.cpp
Purpose: C++ parity implementation of the same 10 scenarios.

Key design decisions:

SupportedDatatypesValues is both a Scenario and a value holder — name() returns the type tag, run() stores and retrieves the value
kvs_value_to_string() converts a KvsValue to the "v" portion of tagged JSON (handles all 10 types, including recursive array/object serialization)
value_types_group() factory method bundles 9 typed instances into a sub-group
Uses score::mw::per::kvs::InstanceId{} (fully-qualified) to avoid ambiguity with using namespace
4. default_values.cpp
Purpose: C++ parity implementation of the same 5 default value scenarios.

Key design decisions:

normalize_error(msg) — maps C++ human-readable error messages to Rust-style identifiers so both implementations produce identical log output:
result_value_to_string() — formats a Result<KvsValue> as Ok(F64(x.x)) or Err(...), matching Rust's Debug output format
value_is_default_string() — synthesizes the is_value_default() result by combining has_default_value() + value comparison (C++ has no single is_value_default() API)
Two overloads of log_state() — one for string-tagged output (parity scenarios), one for boolean/numeric output (older scenarios)
Five classes matching the Rust scenarios, each implementing Scenario::name() and Scenario::run()
5. test_datatype_support.py
Purpose: Python FIT test cases for supported datatypes.

Structure:

assert_tagged_value(actual, expected) — recursive comparison helper that uses math.isclose for f64, recurses for arr/obj
SupportedDatatypesScenario — base class with shared temp_dir and test_config fixtures
TestSupportedDatatypesKeys — asserts the exact set of 3 UTF-8 keys appears in logs
TestSupportedDatatypesValues — abstract base with exp_key() / exp_value() interface; test_ok retrieves the log entry for that type, parses the value field as JSON, calls assert_tagged_value
9 concrete subclasses: _I32, _U32, _I64, _U64, _F64, _Bool, _String, _Array, _Object — each supplies expected key and value
Each test runs for both "rust" and "cpp" via the pytestmark parametrize.

6. test_default_values.py
Purpose: Python FIT test cases for default values (extended from existing file).

New additions:

DefaultValuesParityScenario base class — provides shared fixtures:

defaults_values — builds a dict of all test keys ("test_number" + 5 numbered keys) with ("f64", value) entries
defaults_file — calls create_kvs_defaults_file() to write kvs_1_default.json + kvs_1_default.hash
test_config — injects kvs_parameters_1 with dir and defaults mode
8 test classes using @add_test_properties for requirements traceability:

Class	Scenario	What is verified
TestDefaultValues	default_values	value_is_default is Ok(true) before override, Ok(false) after
TestDefaultValuesRemoveKey	remove_key	3-step sequence: default → override → remove restores default
TestDefaultValuesResetAllKeys	reset_all_keys	All 5 keys revert to defaults after reset()
TestDefaultValuesResetSingleKey	reset_single_key	Only key index 2 reverts; others keep override
TestDefaultValuesChecksum	checksum	adler32(kvs_file_bytes) matches .hash file content
TestDefaultValuesWithoutDefaultsFile	(optional, no file)	value_is_default is Err(KeyNotFound) before set, Ok(false) after set
TestDefaultValuesMissingDefaultsFile	(required, no file)	Binary exits non-zero; stderr matches `KvsFileReadError
TestDefaultValuesMalformedDefaultsFile	(required, corrupt file)	Binary exits non-zero; stderr matches JsonParserError
Files Modified
mod.rs
Added mod supported_datatypes and mod default_values modules; registered supported_datatypes_group() and default_values_group() as sub-groups in persistency_group().

mod.cpp
Added forward declarations for supported_datatypes_group() and default_values_group(); added both to the persistency_scenario_group() subgroups vector.

cpp_log.h
Added escape_json() private helper and updated str() to use it. Without this, a JSON-string value field like {"t":"i32","v":-321} would produce malformed outer JSON (unescaped inner quotes), causing json.loads() to fail in the Python test setup fixture.
