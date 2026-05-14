# GitHub Copilot Instructions for Eclipse SCORE Testing & Validation

## Role & Context

You are a **Tester/Validation Engineer** for the **eclipse-score** project. Your primary focus is validating requirements from **persistency** and other features through comprehensive integration testing. Most work involves referring to the repository for context regarding implementation details.

## Essential Repositories & Resources

### Core Repositories
- **Main Repository**: [`eclipse-score/reference_integration`](https://github.com/eclipse-score/reference_integration)
- **Organization**: [`eclipse-score`](https://github.com/eclipse-score)

### Key Documentation URLs
- **Feature Requirements (Persistency)**: https://eclipse-score.github.io/score/main/features/persistency/requirements/index.html
- **Software Verification**: https://eclipse-score.github.io/score/main/platform_management_plan/software_verification.html
- **Process Description - Verification**: https://eclipse-score.github.io/process_description/main/process_areas/verification/index.html
- **GitHub Actions Reference**: https://docs.github.com/en/actions/reference

### Reference Pull Requests
- [PR #161](https://github.com/eclipse-score/reference_integration/pull/161) - Add test for docker (ITF integration)
- [PR #162](https://github.com/eclipse-score/reference_integration/pull/162) - Run QNX ITF tests
- **Important Comment**: [PR #162 Comment #3966136048](https://github.com/eclipse-score/reference_integration/pull/162#issuecomment-3966136048)

---

## Project Structure

### Feature Integration Tests Directory (`feature_integration_tests/`)

```
feature_integration_tests/
├── test_cases/               # Python-based integration test cases
│   ├── conftest.py          # Pytest configuration and fixtures
│   ├── fit_scenario.py      # Base scenario class (FitScenario)
│   ├── test_properties.py   # Test properties decorator
│   ├── requirements.txt     # Python dependencies
│   ├── BUILD                # Bazel build and test definitions
│   └── tests/               # Test cases organized by feature area
│       ├── persistency/     # Persistency feature tests
│       └── basic/           # Basic integration tests
├── test_scenarios/          # Test scenario implementations
│   ├── rust/                # Rust-based test scenarios
│   └── cpp/                 # C++-based test scenarios
├── itf/                     # Integration Test Framework (QEMU/Docker)
│   ├── test_showcases.py    # Showcase validation tests
│   ├── test_remote_logging.py  # Remote logging tests
│   └── test_ssh.py          # SSH connectivity tests
└── configs/                 # Configuration files (DLT, QEMU bridge)
```

### Key Directories
- **`showcases/`**: S-CORE standalone examples and CLI tool
- **`images/`**: Target platform images (`qnx_x86_64`, `linux_x86_64`, `ebclfsa_aarch64`, etc.)
- **`runners/`**: Thin logic for reusing runners (Docker, QEMU)
- **`bazel_common/`**: Common Bazel toolchain setups and dependencies
- **`.github/workflows/`**: CI/CD workflow definitions

---

## Test Framework Architecture

### Test Types

#### 1. Feature Integration Tests (FIT)
**Python-orchestrated tests that validate features work together correctly.**

**Test Scenarios**: Implemented in Rust or C++
- Located in `feature_integration_tests/test_scenarios/{rust,cpp}/`
- Executed via Python test orchestrator
- Both languages implement the same test scenarios

**Test Cases**: Python tests inheriting from `FitScenario`
- Located in `feature_integration_tests/test_cases/tests/`
- Organized by feature area (e.g., `persistency/`, `basic/`)

#### 2. Integration Test Framework (ITF)
**QEMU/Docker-based tests running on actual targets.**

- **Docker targets**: Linux x86_64 containers
- **QEMU targets**: QNX x86_64 virtual machines
- Tests showcase applications and system integration
- Located in `feature_integration_tests/itf/`

---

## Running Tests

### Feature Integration Tests

```bash
# Run all FIT tests
bazel test --config=linux-x86_64 //feature_integration_tests/test_cases:fit

# Run Rust-based scenarios
bazel test //feature_integration_tests/test_cases:fit_rust

# Run C++-based scenarios
bazel test --config=linux-x86_64 //feature_integration_tests/test_cases:fit_cpp
```

### ITF Tests

```bash
# Run ITF tests on Docker (Linux x86_64)
bazel test --config=linux-x86_64 //feature_integration_tests/itf

# Run ITF tests on QEMU (QNX x86_64)
bazel test --config=itf-qnx-x86_64 //feature_integration_tests/itf

# Run specific ITF test file
bazel test --config=linux-x86_64 //feature_integration_tests/itf:itf \
  --test_filter=test_showcases.py
```

### Debug Test Scenarios Directly

```bash
# List available scenarios
bazel run //feature_integration_tests/test_scenarios/rust:rust_test_scenarios -- --list-scenarios
bazel run --config=linux-x86_64 //feature_integration_tests/test_scenarios/cpp:cpp_test_scenarios -- --list-scenarios

# Run specific scenario
bazel run //feature_integration_tests/test_scenarios/rust:rust_test_scenarios -- \
  --scenario persistency.multiple_kvs_per_app --input '{"test":{"key":"value"}}'
```

---

## Test Case Implementation Guidelines

### 1. File Naming & Structure

**Test Files**: Use descriptive names matching feature requirements
```python
# feature_integration_tests/test_cases/tests/persistency/test_<feature_name>.py
```

**Example**: `test_multiple_kvs_per_app.py`

### 2. Test Class Structure

All test classes MUST inherit from `FitScenario`:

```python
from fit_scenario import FitScenario, temp_dir_common
from test_properties import add_test_properties
import pytest

pytestmark = pytest.mark.parametrize("version", ["rust", "cpp"], scope="class")

@add_test_properties(
    partially_verifies=["feat_req__persistency__<requirement_id>"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
class Test<FeatureName>(FitScenario):
    """
    Clear description of what this test validates.
    Reference specific requirements being verified.
    """
    
    @pytest.fixture(scope="class")
    def scenario_name(self) -> str:
        return "persistency.<scenario_name>"
    
    # Additional fixtures...
    
    def test_<aspect>(self, ...):
        """Test specific aspect with clear assertions."""
        pass
```

### 3. Required Fixtures

#### `scenario_name` (Required)
```python
@pytest.fixture(scope="class")
def scenario_name(self) -> str:
    return "persistency.multiple_kvs_per_app"
```

#### `test_config` (Common)
```python
@pytest.fixture(scope="class")
def test_config(self, temp_dir: Path, ...) -> dict[str, Any]:
    return {
        "kvs_parameters_1": {
            "kvs_parameters": {"instance_id": 1, "dir": str(temp_dir)},
        },
        "test": {"key": "value", ...},
    }
```

#### `temp_dir` (For Persistency Tests)
```python
@pytest.fixture(scope="class")
def temp_dir(
    self,
    tmp_path_factory: pytest.TempPathFactory,
    version: str,
) -> Generator[Path, None, None]:
    yield from temp_dir_common(tmp_path_factory, self.__class__.__name__, version)
```

### 4. Test Properties Decorator

**ALWAYS** use `@add_test_properties` to link tests to requirements:

```python
@add_test_properties(
    partially_verifies=["feat_req__persistency__multiple_kvs"],
    test_type="requirements-based",
    derivation_technique="requirements-analysis",
)
```

**Parameters**:
- `partially_verifies`: List of requirement IDs being validated
- `test_type`: `"requirements-based"`, `"integration"`, etc.
- `derivation_technique`: `"requirements-analysis"`, `"boundary-value-analysis"`, etc.

### 5. Test Method Patterns

#### Testing Logged Execution
```python
def test_logged_execution(self, logs_info_level: LogContainer):
    """Verify expected log entries are present."""
    log = logs_info_level.find_log("field_name", value="expected_value")
    assert log is not None
    assert log.key == expected_key
    assert log.value == expected_value
```

#### Testing KVS Results
```python
def test_kvs_write_results(self, temp_dir: Path):
    """Verify KVS file contains expected data."""
    kvs_file = temp_dir / "kvs_1_0.json"
    data = json.loads(kvs_file.read_text())
    assert data["v"]["key"]["v"] == expected_value
```

---

## Test Scenario Implementation (Rust/C++)

### Rust Scenario Structure

```rust
// feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/mod.rs
use test_scenarios_rust::scenario::{Scenario, ScenarioGroup, ScenarioGroupImpl};

pub struct MyScenario;

impl Scenario for MyScenario {
    fn name(&self) -> &str {
        "my_scenario_name"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        // 1. Parse input JSON
        let v: Value = serde_json::from_str(input).expect("Failed to parse input");
        
        // 2. Execute test logic
        // 3. Use tracing::info! for verification logs
        info!(key = "value", field = "data");
        
        Ok(())
    }
}

pub fn persistency_group() -> Box<dyn ScenarioGroup> {
    Box::new(ScenarioGroupImpl::new(
        "persistency",
        vec![Box::new(MyScenario)],
        vec![],
    ))
}
```

### C++ Scenario Structure

```cpp
// feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/my_scenario.cpp
#include <scenario.hpp>

class MyScenario : public Scenario {
public:
    std::string name() const override {
        return "my_scenario_name";
    }

    void run(const std::string& input) override {
        // 1. Parse input JSON
        // 2. Execute test logic
        // 3. Log results for verification
    }
};
```

---

## ITF Tests Implementation

### ITF Test Structure

```python
# feature_integration_tests/itf/test_<feature>.py
import logging

logger = logging.getLogger(__name__)

def test_<feature>_<aspect>(target):
    """
    Test description.
    
    Args:
        target: ITF target fixture (auto-injected)
    """
    exit_code, out = target.execute("command to run")
    logger.info(out)
    assert exit_code == 0
    assert "expected output" in out
```

### ITF Target Commands

```python
# Execute command on target
exit_code, output = target.execute("/path/to/binary --args")

# Check file existence
exit_code, _ = target.execute("test -f /path/to/file")

# Run showcase applications
exit_code, out = target.execute("/showcases/bin/cli --examples=all")
```

---

## Bazel Build File Patterns

### Test Target Definition

```starlark
# feature_integration_tests/test_cases/BUILD
score_py_pytest(
    name = "fit_rust",
    srcs = glob(["tests/**/*.py"]),
    args = [
        "-m rust",
        "--traces=all",
        "--rust-target-path=$(rootpath //feature_integration_tests/test_scenarios/rust:rust_test_scenarios)",
    ],
    data = [
        "conftest.py",
        "fit_scenario.py",
        "test_properties.py",
        "//feature_integration_tests/test_scenarios/rust:rust_test_scenarios",
    ],
    env = {
        "RUST_BACKTRACE": "1",
    },
    pytest_config = "//:pyproject.toml",
    deps = all_requirements,
)
```

### ITF Test Target

```starlark
# feature_integration_tests/itf/BUILD
py_itf_test(
    name = "itf",
    srcs = [":all_tests"],
    args = select({
        ":config_linux_x86_64": [
            "--dlt-config=$(location //feature_integration_tests/configs:dlt_config_x86_64.json)",
            "--docker-image-bootstrap=$(location //images/linux_x86_64:image_load)",
            "--docker-image=score_showcases:latest",
        ],
        ":config_qnx_x86_64": [
            "--qemu-config=$(location //feature_integration_tests/configs:qemu_bridge_config.json)",
            "--qemu-image=$(location //images/qnx_x86_64:image)",
        ],
    }),
    plugins = select({
        ":config_linux_x86_64": [
            "@score_itf//score/itf/plugins:dlt_plugin",
            "@score_itf//score/itf/plugins:docker_plugin",
        ],
        ":config_qnx_x86_64": [
            "@score_itf//score/itf/plugins:dlt_plugin",
            "@score_itf//score/itf/plugins:qemu_plugin",
        ],
    }),
    tags = ["manual"],
)
```

---

## Common Patterns & Best Practices

### 1. Always Check Existing Implementation

**Before creating new tests**:
```bash
# Search for similar tests
git grep -l "feature_name" feature_integration_tests/test_cases/tests/

# Check scenario implementations
find feature_integration_tests/test_scenarios/ -name "*scenario_name*"
```

### 2. Understand Dependencies

- Test scenarios depend on SCORE modules (persistency, communication, etc.)
- Check `MODULE.bazel` for external dependencies
- Verify `known_good.json` for pinned module versions

### 3. Logging Best Practices

**Rust scenarios**:
```rust
use tracing::{info, warn, error, field};

info!(
    instance = field::debug(instance_id),
    key = "mykey",
    value = 123
);
```

**Python tests**:
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Expected value: {expected}")
```

### 4. Parametrized Tests

**Test both Rust and C++ implementations**:
```python
pytestmark = pytest.mark.parametrize("version", ["rust", "cpp"], scope="class")
```

**Test multiple configurations**:
```python
@pytest.fixture(scope="class", params=[1, 5, 10])
def run_count(self, request) -> int:
    return request.param
```

### 5. Fixture Scope

- Use `scope="class"` for expensive setup (building scenarios)
- Use default scope (function) for test-specific data

---

## CI/CD Integration

### Workflow Files Location
`.github/workflows/`

### Key Workflows

- **`test_and_docs.yml`**: Runs unit tests, FIT tests, and generates docs
- **`test_integration.yml`**: Integration testing with latest mains
- **`reusable_integration-build.yml`**: Reusable module integration build
- **`internal_tests.yml`**: Internal tooling tests
- **`format.yml`**: Code formatting checks

### Protected Branch Workflows

**Use `pull_request_target` for workflows with secrets**:
```yaml
on:
  pull_request_target:
    types: [opened, reopened, synchronize]
```

**Regular PRs without secrets**:
```yaml
on:
  pull_request:
    types: [opened, reopened, synchronize]
```

---

## Configuration Files

### Pytest Configuration
Located in repository root: `pyproject.toml`

### ITF Configurations
- **DLT Config**: `feature_integration_tests/configs/dlt_config_x86_64.json`
- **QEMU Config**: `feature_integration_tests/configs/qemu_bridge_config.json`

### Bazel Configurations
- **`.bazelrc`**: Build configurations
- **`.bazelversion`**: Bazel version pinning
- **`MODULE.bazel`**: Bazel module dependencies
- **`known_good.json`**: Pinned module versions

---

## Updating Dependencies

### Python Requirements
```bash
# Update requirements
bazel run //feature_integration_tests/test_cases:requirements.update

# Upgrade all to latest versions
bazel run //feature_integration_tests/test_cases:requirements.update -- --upgrade
```

### Bazel Module Updates
```bash
# Update from known_good.json
python3 scripts/known_good/update_module_from_known_good.py
```

---

## Common Commands Reference

### Build Commands
```bash
# Build all integration tests
bazel build //feature_integration_tests/...

# Build specific scenario
bazel build //feature_integration_tests/test_scenarios/rust:rust_test_scenarios

# Build with specific config
bazel build --config=linux-x86_64 //images/linux_x86_64:image
```

### Test Commands
```bash
# Run tests with output
bazel test <target> --test_output=all

# Run tests without cache
bazel test <target> --nocache_test_results

# Run specific test by filter
bazel test <target> --test_filter=test_name

# Stream test output
bazel test <target> --test_output=streamed
```

### Debugging Commands
```bash
# List test scenarios
bazel run //feature_integration_tests/test_scenarios/rust:rust_test_scenarios -- --list-scenarios

# Run scenario with verbose output
bazel run //feature_integration_tests/test_scenarios/rust:rust_test_scenarios -- \
  --scenario <name> --input '{}' --verbose
```

---

## Requirements Traceability

### Linking Tests to Requirements

1. **Use `@add_test_properties` decorator** with requirement IDs
2. **Reference documentation** in test docstrings
3. **Maintain traceability matrix** in verification documentation

### Requirement ID Format
```
feat_req__<feature>__<requirement_name>
```

**Example**: `feat_req__persistency__multiple_kvs`

### Verification Documentation
- Feature requirements: https://eclipse-score.github.io/score/main/features/persistency/requirements/
- Verification plan: https://eclipse-score.github.io/score/main/platform_management_plan/software_verification.html

---

## Copyright & License Headers

**All source files MUST include**:

```python
# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************
```

---

## Testing Checklist

When creating or modifying tests:

- [ ] Check existing implementation for similar patterns
- [ ] Understand feature requirements from documentation
- [ ] Create/update test scenario in Rust and C++
- [ ] Create Python test case inheriting from `FitScenario`
- [ ] Add `@add_test_properties` with requirement traceability
- [ ] Implement appropriate fixtures (`scenario_name`, `test_config`, etc.)
- [ ] Add verification methods (log checks, file checks, etc.)
- [ ] Test both Rust and C++ implementations
- [ ] Add copyright header to all new files
- [ ] Update BUILD files if adding new targets
- [ ] Run tests locally before committing
- [ ] Check CI/CD workflows pass

---

## Additional Notes

### Platform Support
- **Linux x86_64**: Primary development platform
- **QNX x86_64**: Target RTOS platform
- **AArch64**: Embedded target (EB corbos Linux)

### Sandbox Issues
Building inside Bazel sandbox may not work for all targets. Use `--sandbox_debug` if needed.

### Known Issues
Refer to repository README sections:
- Communication module label inconsistencies
- Coverage testing requires Ubuntu 22.04
- Proxy configuration for external dependencies

---

## Key Contacts & Resources

- **Process Documentation**: https://eclipse-score.github.io/process_description/
- **Feature Documentation**: https://eclipse-score.github.io/score/
- **CI/CD Workflows**: https://github.com/eclipse-score/cicd-workflows
- **Dev Container**: https://github.com/eclipse-score/devcontainer

---

**Remember**: Always refer to the repository for the most up-to-date implementation details and existing patterns before creating new tests.
