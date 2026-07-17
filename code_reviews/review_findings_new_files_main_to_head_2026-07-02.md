# Code Review Findings: new files (main...HEAD)

**Review Date:** 2026-07-02
**File(s):** New reviewable files from `git diff --name-only --diff-filter=A main...HEAD`
**Reviewer:** review-local skill (Strict PR Reviewer)

---

FILE: feature_integration_tests/test_scenarios/cpp/src/scenarios/lifecycle/security_isolation.cpp
LINE: 22
TYPE: bug
COMMENT: `secpol_type_from_input` only recognizes `unknown_type` and maps every other value to `strict`, which can incorrectly mark unsupported policy types as supported. Parse JSON field value explicitly (or reuse the existing JSON library) and preserve actual input for correct validation.

---

FILE: feature_integration_tests/test_scenarios/cpp/src/scenarios/lifecycle/baselibs_integration.cpp
LINE: 44
TYPE: bug
COMMENT: `std::stoul(...)` can throw on malformed or out-of-range input and `run()` does not handle exceptions, so a malformed test payload can terminate the scenario process. Wrap parsing in a guarded conversion path (try/catch + fallback error log) or use safe JSON numeric extraction.

---

FILE: feature_integration_tests/test_scenarios/cpp/src/scenarios/lifecycle/application_if.cpp
LINE: 22
TYPE: improvement
COMMENT: Input decoding relies on raw substring search instead of structured JSON parsing. This pattern appears in all new lifecycle C++ scenarios and is brittle against formatting/key-order changes and accidental substring matches. Consider centralizing robust parsing with `score/json` or a minimal helper that decodes booleans/strings by key.

---

FILE: feature_integration_tests/test_scenarios/cpp/src/scenarios/lifecycle/orchestrator_sync.cpp
LINE: 48
TYPE: testing
COMMENT: Scenario emits hard-coded `from_target`/`to_target` values instead of consuming test input, while Rust version consumes input values. This weakens cross-language parity and can hide regressions if test config changes; read values from input or add a parity test that fails on divergence.

---

FILE: feature_integration_tests/test_cases/tests/lifecycle/test_lifecycle_baselibs_integration.py
LINE: 49
TYPE: testing
COMMENT: Current coverage validates only well-formed config payload structure. Add a malformed/partial config case (e.g., missing `deadline_budget_ms` or non-numeric value) to catch parser robustness issues in C++ scenario code paths.

---

FILE: docs/needs_filters.py
LINE: 2
TYPE: style
COMMENT: Copyright header text does not include `Qorix` (expected by project review guideline: `Copyright (c) Qorix <year> Contributors ...`). Same header variant is repeated across the newly added lifecycle Python/C++/Rust files.

---

## SUMMARY

**Total Issues:** 6
- **Bugs:** 2
- **Improvements:** 1
- **Testing:** 2
- **Style:** 1

**Severity:** 0 critical, 2 major, 4 minor

**Recommendation:** APPROVE WITH CHANGES

## Strengths

✓ New lifecycle FIT coverage is broad and consistently wired for both Rust and C++ implementations.
✓ Requirement tags are present and scenario/test naming is coherent across `test_cases` and `test_scenarios`.
✓ Hygiene checks were executed successfully (`format.fix`, format checks, `copyright.fix`, `copyright.check`).

## Priority Fixes

1. Replace brittle C++ substring-based input decoding with structured parsing, starting with `security_isolation.cpp` and common helper extraction.
2. Harden numeric parsing in `baselibs_integration.cpp` to avoid termination on malformed values.
3. Align C++ scenario payload consumption with Rust behavior for cross-language parity (`orchestrator_sync.cpp` and similar constants).
