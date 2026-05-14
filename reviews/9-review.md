# PR #9 Review — add persistency fit datatypes

**Reviewer persona**: PiotrKorkus  
**Date**: 2026-04-30 (updated pass 2)  
**Files reviewed**: 22 files changed (local diff vs HEAD)

---

## Summary (Pass 2 — local diff review)

This pass reviews the 22 locally-changed files that fix the CI failures reported in the attachment
(fit_cpp FAILED, ruff FAILED, rustfmt FAILED). The fixes are technically correct and all four root
causes are properly resolved. However, six files that should not be part of a feature PR have been
staged alongside the real changes: two `.github/` infrastructure files, five `docs/` working-note
files, a `reviews/` artifact, and an unreferenced patch file. These must be split out or removed
before the PR is clean.

---

## Positives

- The boolean normalisation approach (`canonicalize_bool_literals` + regex on `"t":"bool","v":1`)
  is minimal and correct — it only fires on tagged KVS boolean fields, not arbitrary `1`/`0`
  occurrences in the JSON.
- `format_double_python()` placed in the shared `kvs_build_helpers.h` rather than duplicated in
  every scenario file — good DRY practice.
- `TestDefaultValuesMalformedDefaultsFile` is now correctly parametrized over `["required"]` only,
  matching the docstring.

---

## Findings

### [Critical] `patches/baselibs/004-add-missing-ecu-vector-vajson-package.patch` is not wired up

**File**: `patches/baselibs/004-add-missing-ecu-vector-vajson-package.patch` (new file)

**Evidence**:
- `known_good.json` references only `003-acl-fixes-for-aarch64.patch`
- `bazel_common/score_modules_target_sw.MODULE.bazel` references only `003-acl-fixes-for-aarch64.patch`
- No file in the workspace references `004-add-missing-ecu-vector-vajson-package.patch`
- The patch file itself contains the same `diff` block duplicated twice (copy-paste artifact)

**Problem**: The patch is committed but has no effect — it will never be applied to any build.
If it was meant to fix a build issue it silently does nothing.

**Fix**: Either wire it up in `known_good.json` / `score_modules_target_sw.MODULE.bazel` alongside
patch `003`, or remove it entirely if it is not needed for this PR.

---

### [Major] `docs/` working-note files do not belong in the feature branch

**Files**: seven new files in `docs/`
- `docs/Difference_in_framework` (no extension)
- `docs/commit_79cd340_new_files_hierarchy.md`
- `docs/fit_persistency_implementation.md`
- `docs/fit_persistency_refactor_2026_04_29.md`
- `docs/fit_vs_cit_parity_gap_analysis.md` (764 lines)
- `docs/persistency_datatype_default_values_test_analysis.md` (945 lines)
- `docs/pr_description_persistency_fit.md` + `docs/pr_description_persistency_fit.txt`

**Problem**: These are internal analysis notes and PR-drafting artifacts generated during
development. They document CIT/FIT comparison, commit diffs, and refactor history — information
that becomes stale immediately after merge. Committing them pollutes the repository history and
will confuse future contributors.

**Fix**: Remove all seven from this PR. If the CIT/FIT parity analysis is considered permanent
documentation, move it to the project's official docs tree with an RST/Sphinx entry — not as
freestanding Markdown in `docs/`.

---

### [Major] `.github/copilot-instructions.md` and `.github/agents/reviewer.agent.md` are unrelated to this feature

**Files**: `.github/copilot-instructions.md` (660 lines), `.github/agents/reviewer.agent.md` (287 lines)

**Problem**: These are Copilot workspace-customization files (developer tooling). They have no
relationship to the persistency FIT feature being merged and should be in a separate infrastructure
PR or kept local.

**Fix**: Remove from this PR. Submit as a standalone infrastructure change if desired.

---

### [Major] `reviews/9-review.md` is a development artifact

**File**: `reviews/9-review.md` (243 lines)

**Problem**: This is a review of the PR itself, generated as a working tool during development.
Committing it to the repository creates a permanent record of internal review notes alongside
production code.

**Fix**: Remove from this PR. Keep locally or in a wiki.

---

### [Major] `TestDefaultValuesIgnored` docstring asserts behavior that C++ no longer tests

**File**: `feature_integration_tests/test_cases/tests/persistency/test_default_values.py`, lines 37–40

**Evidence**:
```python
class TestDefaultValuesIgnored(PersistencyScenario):
    """
    Verifies that with KvsDefaults::Ignored mode, default values are not loaded
    even if a defaults file exists on disk.  The explicitly set value is persisted
    to storage, but no default is accessible before set_value is called.
    """
```

C++ scenario (`default_values_ignored.cpp`):
```cpp
// NOTE: The C++ KvsBuilder API maps both KvsDefaults::Ignored and
// KvsDefaults::Optional to need_defaults_flag(false).  When a defaults
// file is present on disk, the KVS will therefore still load it in this mode.
```

**Problem**: The class docstring and the class name both claim the test verifies that defaults are
_not_ loaded. For C++ this is demonstrably false — the scenario comment acknowledges defaults are
still loaded. The Python test (`test_explicit_set_persisted`) only reads the snapshot, which passes
regardless of whether defaults were loaded. The "Ignored" requirement is verified for Rust only.

**Fix**: Either (a) mark the docstring and `@add_test_properties` as Rust-only for the
"defaults not loaded" assertion, or (b) add a Rust-only sub-test that explicitly checks
`get_value_as(key)` fails before `set_value`, and document that C++ tests only the
"explicit set persists" half of the requirement.

---

### [Minor] `format_double_python()` is not locale-safe

**File**: `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/kvs_build_helpers.h`, lines 40–50

**Evidence**:
```cpp
inline std::string format_double_python(double v) {
    std::ostringstream oss;
    oss << v;   // ← uses global locale; decimal separator may not be '.'
    ...
}
```

**Problem**: `std::ostringstream` uses the global C++ locale. If the process locale is set to a
European locale (e.g., `de_DE`), `oss << 42.0` produces `"42,0"`, breaking the Python assertion.
In the Bazel sandbox the locale is typically `"C"`, but this is an implicit environmental
assumption.

**Fix**:
```cpp
std::ostringstream oss;
oss.imbue(std::locale::classic());
oss << v;
```

---

### [Nit] Rust `multi_instance_isolation.rs` — formatting-only change is noise

**File**: `feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/multi_instance_isolation.rs`

**Evidence**: The diff only unwraps two `let` bindings from multi-line to single-line. This is a
rustfmt artefact with no semantic change.

**Problem**: Purely mechanical reformatting mixed with functional CI fixes. Not a blocker, but
makes the diff harder to read.

**Note**: Acceptable if rustfmt is enforced by CI — keep as-is.

---

## Suggested Next Steps

1. Remove `patches/baselibs/004-add-missing-ecu-vector-vajson-package.patch` or wire it up.
2. Remove all seven `docs/` working-note files from this PR.
3. Remove `.github/copilot-instructions.md` and `.github/agents/reviewer.agent.md`.
4. Remove `reviews/9-review.md`.
5. Update `TestDefaultValuesIgnored` docstring / add Rust-only assertion to honestly represent what is verified.
6. Add `oss.imbue(std::locale::classic())` to `format_double_python()`.

---

## Requirements Traceability Check

| Test Class | `partially_verifies` IDs | Status |
|---|---|---|
| `TestAllValueTypes` | `feat_req__persistency__support_datatype_value`, `feat_req__persistency__support_datatype_keys`, `feat_req__persistency__store_data` | OK |
| `TestDefaultValuesIgnored` | `feat_req__persistency__default_values`, `feat_req__persistency__default_value_get` | ⚠️ C++ path does not verify "ignored" behavior — see Major #4 |
| `TestDefaultValuesChecksum` | `feat_req__persistency__default_values` | OK |
| `TestDefaultValuesMissingDefaultsFile` | `feat_req__persistency__default_values`, `feat_req__persistency__default_value_file` | OK |
| `TestDefaultValuesMalformedDefaultsFile` | `feat_req__persistency__default_values`, `feat_req__persistency__default_value_file` | OK — correctly restricted to `["required"]` |
| `TestGetDefaultValue` | `fully_verifies: feat_req__persistency__default_value_get`; partially: `default_values`, `default_value_file` | OK |
| `TestSelectiveReset` | `feat_req__persistency__reset_to_default`, `default_values`, `default_value_file`, `store_data` | OK |
| `TestFullReset` | `feat_req__persistency__reset_to_default`, `default_values`, `default_value_file`, `store_data` | OK |
| `TestOptionalModeWithoutDefaults` | `feat_req__persistency__default_values`, `default_value_file`, `store_data` | OK |
| `TestResetToDefault` | `feat_req__persistency__reset_to_default` | OK |
| `TestAllTypesWithUtf8Keys` | `feat_req__persistency__support_datatype_keys`, `support_datatype_value`, `store_data` | OK |
| `TestPartialOverrideSnapshot` | `feat_req__persistency__default_values`, `default_value_file`, `store_data` | OK |
| `TestUtf8KeysWithDefaults` | `feat_req__persistency__support_datatype_keys`, `default_values`, `default_value_file` | OK |
| `TestUtf8DefaultValueGet` | `fully_verifies: feat_req__persistency__default_value_get`; partially: `support_datatype_keys` | OK |
| `TestMultiInstanceDefaultIsolation` | `feat_req__persistency__default_values`, `feat_req__persistency__multiple_kvs` | OK |
