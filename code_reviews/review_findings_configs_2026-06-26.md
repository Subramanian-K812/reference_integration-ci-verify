# Code Review Findings: feature_integration_tests/test_cases/configs

**Review Date:** 2026-06-26
**File(s):**
- feature_integration_tests/test_cases/configs/BUILD
- feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json

**Reviewer:** review-local skill (Strict PR Reviewer)

---

## FILE: feature_integration_tests/test_cases/configs/BUILD
**LINE:** 2
**TYPE:** style
**COMMENT:** Copyright header should be '# (c) Qorix 2026' per project standards, not 'Contributors to the Eclipse Foundation'. Update to match project conventions.

---

## FILE: feature_integration_tests/test_cases/configs/BUILD
**LINE:** 14-16
**TYPE:** improvement
**COMMENT:** Missing visibility attribute for exports_files. Add 'visibility = ["//visibility:public"]' or restrict appropriately to control which packages can use these files.

---

## FILE: feature_integration_tests/test_cases/configs/BUILD
**LINE:** 14-16
**TYPE:** documentation
**COMMENT:** No comment explaining the purpose of exported files. Add a comment above exports_files explaining what daemon_launch_manager_config.json is used for and why it needs to be exported.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 1
**TYPE:** style
**COMMENT:** Missing copyright/license header. While JSON doesn't support comments natively, consider adding a "_metadata" or "_license" field at the top, or document ownership in accompanying README.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 8-10
**TYPE:** documentation
**COMMENT:** Magic number 0.5 for delay_before_restart has no explanation. Consider adding a schema definition file or README documenting what this delay represents and why 0.5 seconds is appropriate.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 18-23
**TYPE:** improvement
**COMMENT:** Hardcoded values for alive_supervision (reporting_cycle: 0.1, failed_cycles_tolerance: 1) lack context. These appear to be tight tolerances - document rationale for these specific values in a schema or README.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 32
**TYPE:** improvement
**COMMENT:** Hardcoded transition_timeout of 5 seconds. Consider making this configurable per environment (CI might need different timeouts than production) or document why 5 seconds is the right value.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 65-66
**TYPE:** improvement
**COMMENT:** Environmental variables IDENTIFIER and PROCESSIDENTIFIER have identical values for rust_supervised_app. This redundancy suggests they might serve different purposes - either remove duplication or add documentation explaining why both are needed.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 79-80
**TYPE:** improvement
**COMMENT:** Same redundancy for cpp_supervised_app environmental variables. If IDENTIFIER and PROCESSIDENTIFIER always have the same value, consider using a single variable or document the distinction.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 60
**TYPE:** documentation
**COMMENT:** Process arguments ["--delay", "100"] for rust_supervised_app have no explanation. Document what the delay parameter controls and why 100 (milliseconds?) is the test value.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 75
**TYPE:** documentation
**COMMENT:** Process argument ["-d50"] for cpp_supervised_app uses different format than rust version. Document the argument format and ensure consistency across components where appropriate.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 2
**TYPE:** improvement
**COMMENT:** schema_version is set to 1 but there's no reference to where the schema definition lives. Add a comment or metadata field pointing to schema documentation.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 84-92
**TYPE:** improvement
**COMMENT:** SupervisedApps run_target description mentions "trigger hmproc flatbuffer generation" but this seems like implementation detail leaking into config. Consider whether this is the right abstraction level for the configuration or if this should be handled elsewhere.

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 100
**TYPE:** improvement
**COMMENT:** fallback_run_target has shorter transition_timeout (1.5s) than default (5s). This asymmetry should be documented - why is shutdown faster than startup?

---

## FILE: feature_integration_tests/test_cases/configs/daemon_launch_manager_config.json
**LINE:** 39
**TYPE:** improvement
**COMMENT:** evaluation_cycle appears in two places (line 39 and 103) with the same value (0.5). Consider if this is truly a default that should be referenced, or if these should be independently configurable.

---

## SUMMARY

**Total Issues:** 15
- **Style:** 2
- **Improvement:** 9
- **Documentation:** 4

**Severity:** 0 critical, 0 major, 15 minor

**Recommendation:** APPROVE WITH CHANGES - No critical issues, but configuration files lack documentation and have unexplained magic numbers. Add documentation explaining configuration values and rationale.

## Strengths

✓ Well-structured JSON with clear hierarchical organization
✓ Good use of defaults to avoid repetition
✓ Proper nesting and consistent formatting
✓ Descriptive component and run_target names
✓ Recovery actions properly configured for failure scenarios

## Priority Fixes

1. **Update BUILD file copyright** to match Qorix standards (line 2)
2. **Add visibility attribute** to exports_files in BUILD
3. **Create schema documentation or README** explaining all configuration parameters
4. **Document or eliminate redundant** IDENTIFIER/PROCESSIDENTIFIER variables
5. **Add comments** explaining process arguments and their formats
6. Consider creating a **configs/README.md** to document the Launch Manager configuration schema
