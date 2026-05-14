# PR #9 Review (Follow-up) — add persistency fit datatypes

**Reviewer persona**: PiotrKorkus  
**Date**: 2026-05-04  
**Files reviewed**: 10 source files + BUILD

---

## Summary

All 14 original review comments have been addressed. The helpers are now in
`persistency_scenario.py`, C++ logging was migrated to JSON structured logs via
`kvs_build_helpers::log_info()`, the helper header was moved to `internals/`, module-level
constants were pushed into their owning classes, and log-based assertions were added for
all the scenarios that required them. Two new issues were found — one is blocking.

---

## Positives

- The `kvs_build_helpers::log_info()` implementation is a clean, well-documented abstraction
  that makes C++ log output structurally identical to Rust tracing output — this enables
  fully uniform `find_log()` assertions in Python without any `if version ==` branches.
- Multi-instance isolation implementation (both Rust and C++) is thorough: pre-write default
  reads, cross-access guards that fail the scenario on breach, and three-pronged Python
  verification (snapshot isolation × 2 + log-based default verification).

---

## Original Review Comments — Status

| # | File | Original Comment | Status |
|---|------|-----------------|--------|
| 1 | `fit_scenario.py` | `create_kvs_defaults_file` / `read_kvs_snapshot` not part of scenario class, move to different file | ✅ Moved to `persistency_scenario.py` |
| 2 | `test_combined_requirements.py` | `ascii_null` — "value assert?" | ✅ `assert snapshot["ascii_null"]["v"] is None` added |
| 3 | `test_combined_requirements.py` | `greek_bool αβγ["v"]` — "checks if not None, should check True explicitly" | ✅ `assert snapshot["greek_bool αβγ"]["v"] is True` |
| 4 | `test_combined_requirements.py` | `test_utf8_keys_present` — "next test has same assertions for each key" | ✅ Merged into single `test_value_types_persisted` method |
| 5 | `test_default_values.py` | `_DEFAULT_KEY`, `_OVERRIDE_VALUE`, `_PARITY_KEY` at module level — "define in class directly" | ✅ All moved into owning class bodies |
| 6 | `test_default_values.py` | `TestDefaultValuesIgnored` — "where is defaults file created?" | ✅ `defaults_file` fixture now creates `kvs_1_default.json` with key `999.0` |
| 7 | `test_default_values.py` | `_GET_DEFAULT_KEY` — "used only in one place, makes readability worse" | ✅ Inlined as `{"default_probe_key": ("f64", self._GET_DEFAULT_EXPECTED)}` |
| 8 | `test_default_values.py` | `_SEL_DEFAULT_VALUE` / `_sel_override_value` outside class — "why defined outside?" | ✅ Now `_DEFAULT_VALUE = 50.0` and `@staticmethod _override_value()` in `TestSelectiveReset` |
| 9 | `test_reset_to_default.py` | "verify that KVS still reports default value after reset, check logs" | ✅ `test_default_value_reported_after_reset` added; asserts `find_log("key", value="key2")` |
| 10 | `cpp/scenarios/persistency/` | C++ `std::cout` plain-text logs — "tracing should be used, then parsed into LogContainer" | ✅ All replaced with `kvs_build_helpers::log_info()` emitting JSON matching Rust tracing format |
| 11 | `cpp/scenarios/persistency/kvs_build_helpers.h` | "move to helpers / internals" | ✅ Moved to `cpp/src/internals/persistency/kvs_build_helpers.h` |
| 12 | `test_default_values.py` (`TestMultiInstanceDefaultIsolation`) | "check only saved keys … need to check default values in scenario and assert on logs" | ✅ `test_default_isolation_via_logs` added; Rust + C++ scenarios log defaults before writes |
| 13 | `test_reset_to_default.py` | version-conditional `results.stdout` fallback — "same, use scenario logs" | ✅ Version branch removed; `find_log` used uniformly for both Rust and C++ |
| 14 | General | "consider scenarios with more KVS instances — does defaults file for one instance mix into second?" | ✅ `persistency.multi_instance_isolation` scenario added (Rust + C++) with cross-access guards |

---

## Findings

### [Major] `TestOptionalModeWithoutDefaults` — zero test methods, class is vacuous

**File**: `feature_integration_tests/test_cases/tests/persistency/test_default_values.py`, lines 517–546  
**Evidence**:
```python
class TestOptionalModeWithoutDefaults(DefaultValuesParityScenario):
    """
    Verify that KVS starts and operates normally when defaults=optional but
    no defaults file is present (graceful degradation).
    ...
    """

    @pytest.fixture(scope="class")
    def defaults(self) -> str:
        return "without"

    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.default_values.checksum"
    # <--- no test_* methods
```
**Problem**: `DefaultValuesParityScenario`, `FitScenario`, and `Scenario` define no
`test_*` methods. Pytest collects zero tests from this class. The scenario is executed
(because fixtures run) but nothing is asserted — the graceful degradation behaviour is
never actually verified despite the docstring claiming it is.  
This appears to be a side-effect of removing the dead `assert results.return_code == ResultCode.SUCCESS`
that was previously mis-placed inside the `scenario_name` fixture — the fix removed the
only assertion without replacing it with a proper test method.  
**Fix**:
```python
def test_optional_mode_succeeds(self, results: ScenarioResult) -> None:
    """Verify KVS initialises and completes successfully without a defaults file."""
    assert results.return_code == ResultCode.SUCCESS
```
**Test idea**: This IS the test. Without it, coverage for `feat_req__persistency__default_value_file`
(optional/graceful-degradation path) is zero.

---

### [Minor] `TestSelectiveReset` / `TestFullReset` — no log-based assertion for default value accessibility post-reset

**File**: `feature_integration_tests/test_cases/tests/persistency/test_default_values.py`, lines ~370–500  
**Evidence**: Both `test_selective_reset_state` and `test_full_reset_clears_initial_keys` / `test_full_reset_new_keys_present` only verify snapshot presence/absence via file reads. Neither confirms that a reset key can still be read back as its default value after `reset_key()` / `reset()` is called.  
**Problem**: The same gap that `TestResetToDefault` was specifically asked to fill (PR comment: "verify that KVS still reports default value after reset, check logs for that") exists here too. For `TestSelectiveReset`, the even-indexed keys are reset but no log confirms the KVS returns their default `50.0` post-reset. For `TestFullReset`, no log confirms the KVS state at all — only snapshot absence of old keys is checked.  
**Fix**: Add log emission to the Rust + C++ `selective_reset` and `full_reset` scenarios for at least one reset key, and add a `test_reset_key_returns_default` method in each test class.  
**Test idea**: `find_log("key", value="sel_key_0")` → `assert isclose(float(log.value), 50.0)`.

---

## Suggested Next Steps

1. Add `test_optional_mode_succeeds` to `TestOptionalModeWithoutDefaults` — this is blocking;
   without it the class provides zero test coverage for the graceful-degradation requirement path.
2. Extend `selective_reset` and `full_reset` scenarios to log a reset key's default value post-reset,
   and add a matching log assertion in Python — for parity with what was done for `reset_to_default`.
3. Push and request re-review once item 1 is resolved.

---

## Requirements Traceability Check

| Test Class | `partially_verifies` IDs | Status |
|---|---|---|
| `TestAllTypesWithUtf8Keys` | `feat_req__persistency__support_datatype_keys`, `feat_req__persistency__support_datatype_value`, `feat_req__persistency__store_data` | OK |
| `TestPartialOverrideSnapshot` | `feat_req__persistency__default_values`, `feat_req__persistency__default_value_file`, `feat_req__persistency__store_data` | OK |
| `TestUtf8KeysWithDefaults` | `feat_req__persistency__support_datatype_keys`, `feat_req__persistency__default_values`, `feat_req__persistency__default_value_file` | OK |
| `TestUtf8DefaultValueGet` | `fully_verifies: feat_req__persistency__default_value_get`, `partially_verifies: feat_req__persistency__support_datatype_keys` | OK |
| `TestDefaultValuesIgnored` | `feat_req__persistency__default_values`, `feat_req__persistency__default_value_get` | OK |
| `TestDefaultValuesChecksum` | `feat_req__persistency__default_values` | OK |
| `TestDefaultValuesMissingDefaultsFile` | `feat_req__persistency__default_values`, `feat_req__persistency__default_value_file` | OK |
| `TestDefaultValuesMalformedDefaultsFile` | `feat_req__persistency__default_values`, `feat_req__persistency__default_value_file` | OK |
| `TestOptionalModeWithoutDefaults` | `feat_req__persistency__default_values`, `feat_req__persistency__default_value_file`, `feat_req__persistency__store_data` | **ZERO TESTS** — decorator present but no test methods collect |
| `TestGetDefaultValue` | `fully_verifies: feat_req__persistency__default_value_get` | OK |
| `TestSelectiveReset` | `feat_req__persistency__reset_to_default`, `feat_req__persistency__default_values`, `feat_req__persistency__default_value_file`, `feat_req__persistency__store_data` | OK (snapshot-only) |
| `TestFullReset` | `feat_req__persistency__reset_to_default`, `feat_req__persistency__default_values`, `feat_req__persistency__default_value_file`, `feat_req__persistency__store_data` | OK (snapshot-only) |
| `TestMultiInstanceDefaultIsolation` | `feat_req__persistency__default_values`, `feat_req__persistency__multiple_kvs` | OK |
| `TestResetToDefault` | `feat_req__persistency__reset_to_default` | OK |
