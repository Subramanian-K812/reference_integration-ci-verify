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
"""
Helpers for running tests with the Launch Manager daemon.

Provides fixtures and utilities for integration tests that require
a running Launch Manager daemon instance.
"""

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any, TextIO

import pytest


def _bazel_roots(workspace: Path) -> list[Path]:
    """
    Return the filesystem roots a relative Bazel cquery path may be resolved against.

    Generated outputs (``bazel-out/...``) resolve fine under the workspace root
    since Bazel symlinks ``bazel-out`` there. But source files belonging to
    external repos (``external/<repo>+/...``) only exist under the execution
    root, not the workspace root, so both must be tried.
    """
    roots = [workspace]
    exec_root_res = subprocess.run(["bazel", "info", "execution_root"], capture_output=True, text=True, check=False)
    if exec_root_res.returncode == 0:
        roots.append(Path(exec_root_res.stdout.strip()))
    return roots


def _resolve_cquery_paths(workspace: Path, cquery_output: str) -> list[Path]:
    """
    Convert Bazel cquery stdout into concrete filesystem candidate paths.

    Bazel can emit more than one line for executable lookups (for example,
    target and exec configuration paths). This helper keeps each emitted path
    separate and resolves relative entries against both the workspace root and
    the execution root, since not all outputs are reachable from the former.
    """
    roots = _bazel_roots(workspace)
    candidates: list[Path] = []
    for raw_line in cquery_output.splitlines():
        line = raw_line.strip().strip('"')
        if not line:
            continue

        path = Path(line)
        if not path.is_absolute():
            for root in roots:
                candidates.append(root / path)
        else:
            candidates.append(path)

    return candidates


def find_binary_in_runfiles(target_path: str) -> Path | None:
    """
    Find a binary in Bazel runfiles when running under Bazel.

    Parameters
    ----------
    target_path : str
        Bazel target path (e.g., "@score_lifecycle_health//score/launch_manager:launch_manager")

    Returns
    -------
    Path | None
        Path to the binary if found in runfiles, None otherwise.
    """
    # Check if running under Bazel by looking for runfiles
    runfiles_dir = os.environ.get("RUNFILES_DIR")
    if not runfiles_dir:
        # Try to find runfiles relative to current file
        test_srcdir = os.environ.get("TEST_SRCDIR")
        if test_srcdir:
            runfiles_dir = test_srcdir

    if not runfiles_dir:
        # Try to find runfiles from the current working directory
        cwd = Path.cwd()
        if ".runfiles" in str(cwd):
            # We're inside a runfiles directory
            runfiles_parts = str(cwd).split(".runfiles")
            if len(runfiles_parts) > 1:
                runfiles_dir = runfiles_parts[0] + ".runfiles/_main"

    if not runfiles_dir:
        return None

    # Convert Bazel target to runfiles path
    # @score_lifecycle_health//score/launch_manager:launch_manager
    # -> score_lifecycle_health/score/launch_manager/launch_manager
    if target_path.startswith("@"):
        # Remove @ and split by //
        parts = target_path[1:].split("//")
        if len(parts) == 2:
            # Handle bzlmod repository names with + suffix
            repo_name = parts[0]
            # Try both with and without + suffix
            repo_variants = [
                repo_name,
                repo_name.rstrip("+"),
                repo_name + "+",
                repo_name.replace("+", "~"),
            ]

            package_and_target = parts[1].split(":")
            if len(package_and_target) == 2:
                package = package_and_target[0]
                target = package_and_target[1]

                # Try different runfiles path patterns
                candidates = []
                for repo in repo_variants:
                    candidates.extend(
                        [
                            Path(runfiles_dir) / repo / package / target,
                            Path(runfiles_dir) / f"{repo}~" / package / target,
                            Path(runfiles_dir) / "_main" / "external" / repo / package / target,
                            Path(runfiles_dir) / "external" / repo / package / target,
                        ]
                    )

                for candidate in candidates:
                    if candidate.exists() and candidate.is_file():
                        return candidate

                # The target's output may not sit directly at
                # `<package>/<target>` (e.g. a build rule whose executable is
                # nested under a subdirectory, such as
                # `score/launch_manager/src/daemon/launch_manager` for target
                # `score/launch_manager:launch_manager`). Fall back to a
                # recursive search within the package for a file matching the
                # target's basename.
                target_basename = target.rsplit("/", 1)[-1]
                for repo in repo_variants:
                    for package_root in [
                        Path(runfiles_dir) / repo / package,
                        Path(runfiles_dir) / "_main" / "external" / repo / package,
                        Path(runfiles_dir) / "external" / repo / package,
                    ]:
                        if not package_root.is_dir():
                            continue
                        for match in sorted(package_root.rglob(target_basename)):
                            if match.is_file():
                                return match

    return None


def get_binary_path(target: str) -> Path:
    """
    Get path to a binary, either from runfiles or by building it.

    Parameters
    ----------
    target : str
        Bazel target path.
    Returns
    -------
    Path
        Path to the binary.
    """
    # First try to find in runfiles (when running under Bazel)
    binary_path = find_binary_in_runfiles(target)
    if binary_path:
        return binary_path

    # Fall back to a config-aware Bazel build (when running pytest directly).
    # Local plain `bazel build` can fail for this target due to missing default flags.
    bazel_config = os.environ.get("FIT_BAZEL_CONFIG", "linux-x86_64")
    build_cmd = ["bazel", "build", f"--config={bazel_config}", target]
    build_res = subprocess.run(build_cmd, capture_output=True, text=True, check=False)
    if build_res.returncode != 0:
        stderr_tail = "\n".join(build_res.stderr.strip().splitlines()[-20:])
        raise RuntimeError(
            f"Failed to build target {target!r} with --config={bazel_config}.\nstderr (last lines):\n{stderr_tail}"
        )

    ws_info_res = subprocess.run(["bazel", "info", "workspace"], capture_output=True, text=True, check=False)
    if ws_info_res.returncode != 0:
        raise RuntimeError(f"Failed to resolve Bazel workspace path.\nstderr:\n{ws_info_res.stderr.strip()}")

    cquery_cmd = [
        "bazel",
        "cquery",
        f"--config={bazel_config}",
        "--output=starlark",
        "--starlark:expr=target.files_to_run.executable.path",
        target,
    ]
    cquery_res = subprocess.run(cquery_cmd, capture_output=True, text=True, check=False)
    if cquery_res.returncode != 0:
        raise RuntimeError(
            f"Failed to locate built executable with Bazel cquery.\nstderr:\n{cquery_res.stderr.strip()}"
        )

    ws_path = Path(ws_info_res.stdout.strip())
    for binary_path in _resolve_cquery_paths(ws_path, cquery_res.stdout):
        if binary_path.is_file():
            return binary_path

    raise RuntimeError(
        "Executable not found after build. cquery candidates:\n"
        + "\n".join(str(p) for p in _resolve_cquery_paths(ws_path, cquery_res.stdout))
    )


def get_data_file_path(target: str) -> Path:
    """
    Get path to a non-executable Bazel target's output file (e.g. a schema or
    `.fbs` file), either from runfiles or by building it.

    Parameters
    ----------
    target : str
        Bazel target path.

    Returns
    -------
    Path
        Path to the file.
    """
    file_path = find_binary_in_runfiles(target)
    if file_path:
        return file_path

    bazel_config = os.environ.get("FIT_BAZEL_CONFIG", "linux-x86_64")
    build_cmd = ["bazel", "build", f"--config={bazel_config}", target]
    build_res = subprocess.run(build_cmd, capture_output=True, text=True, check=False)
    if build_res.returncode != 0:
        stderr_tail = "\n".join(build_res.stderr.strip().splitlines()[-20:])
        raise RuntimeError(
            f"Failed to build target {target!r} with --config={bazel_config}.\nstderr (last lines):\n{stderr_tail}"
        )

    ws_info_res = subprocess.run(["bazel", "info", "workspace"], capture_output=True, text=True, check=False)
    if ws_info_res.returncode != 0:
        raise RuntimeError(f"Failed to resolve Bazel workspace path.\nstderr:\n{ws_info_res.stderr.strip()}")

    cquery_cmd = [
        "bazel",
        "cquery",
        f"--config={bazel_config}",
        "--output=starlark",
        "--starlark:expr=target.files.to_list()[0].path",
        target,
    ]
    cquery_res = subprocess.run(cquery_cmd, capture_output=True, text=True, check=False)
    if cquery_res.returncode != 0:
        raise RuntimeError(f"Failed to locate {target!r} with Bazel cquery.\nstderr:\n{cquery_res.stderr.strip()}")

    ws_path = Path(ws_info_res.stdout.strip())
    for file_path in _resolve_cquery_paths(ws_path, cquery_res.stdout):
        if file_path.is_file():
            return file_path

    raise RuntimeError(
        "File not found after build. cquery candidates:\n"
        + "\n".join(str(p) for p in _resolve_cquery_paths(ws_path, cquery_res.stdout))
    )


def find_flatbuffer_dir_in_runfiles() -> Path | None:
    """
    Find the generated Launch Manager flatbuffer config directory in Bazel runfiles.

    Returns
    -------
    Path | None
        Path to the `flatbuffer_out` directory if found in runfiles, None otherwise.
    """
    runfiles_dir = os.environ.get("RUNFILES_DIR") or os.environ.get("TEST_SRCDIR")
    if not runfiles_dir:
        return None

    candidate = Path(runfiles_dir) / "_main" / "flatbuffer_out"
    if candidate.is_dir():
        return candidate

    return None


def generate_flatbuffer_daemon_configs(config: dict, etc_dir: Path) -> None:
    """
    Generate Launch Manager flatbuffer config binaries (e.g., lm_demo.bin) directly
    from `config` into `etc_dir`.

    The Launch Manager daemon resolves each component's executable relative to
    `deployment_config.bin_dir` by `chdir`-ing into its directory and then
    re-executing the *same* (unchanged) path, so `bin_dir` must be an absolute
    path or the second path segment gets applied twice and `execve` fails with
    ENOENT. Callers must therefore pass an absolute `bin_dir` in `config`.

    This runs the `lifecycle_config` splitter and `flatc` serializer directly
    instead of shelling out to `bazel build` for a prebuilt target: invoking
    Bazel from inside a running `bazel test` action contends for the same
    Bazel server lock as the outer test invocation and can hang/timeout.
    """
    lifecycle_config_script = get_binary_path("@score_lifecycle_health//scripts/config_mapping:lifecycle_config")
    schema_file = get_data_file_path(
        "@score_lifecycle_health//score/launch_manager/src/daemon/src/configuration/config_schema"
        ":launch_manager.schema.json"
    )
    flatc = get_binary_path("@flatbuffers//:flatc")

    fbs_schemas = {
        "lm_demo": get_data_file_path(
            "@score_lifecycle_health//score/launch_manager/src/daemon/src/configuration/config_schema"
            ":lm_flatcfg.fbs"
        ),
        "hm_demo": get_data_file_path(
            "@score_lifecycle_health//score/launch_manager/src/daemon/src/alive_monitor/config:hm_flatcfg.fbs"
        ),
        "hmcore": get_data_file_path(
            "@score_lifecycle_health//score/launch_manager/src/daemon/src/alive_monitor/config:hmcore_flatcfg.fbs"
        ),
    }

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        config_path = tmp_dir / "daemon_launch_manager_config.json"
        config_path.write_text(json.dumps(config, indent=2))

        split_dir = tmp_dir / "split"
        split_dir.mkdir()
        split_cmd = [
            str(lifecycle_config_script),
            str(config_path),
            "--schema",
            str(schema_file),
            "-o",
            str(split_dir),
        ]
        split_res = subprocess.run(split_cmd, capture_output=True, text=True, check=False)
        if split_res.returncode != 0:
            raise RuntimeError(
                f"lifecycle_config failed to split {config_path}.\n"
                f"stdout:\n{split_res.stdout}\nstderr:\n{split_res.stderr}"
            )

        for stem, fbs_schema in fbs_schemas.items():
            data_json = split_dir / f"{stem}.json"
            if not data_json.is_file():
                raise RuntimeError(f"lifecycle_config did not generate expected {data_json}")

            flatc_cmd = [
                str(flatc),
                "--binary",
                "--strict-json",
                "-o",
                str(etc_dir),
                str(fbs_schema),
                str(data_json),
            ]
            flatc_res = subprocess.run(flatc_cmd, capture_output=True, text=True, check=False)
            if flatc_res.returncode != 0:
                raise RuntimeError(
                    f"flatc failed to serialize {data_json}.\nstdout:\n{flatc_res.stdout}\nstderr:\n{flatc_res.stderr}"
                )


class LaunchManagerDaemon:
    """
    Context manager for Launch Manager daemon lifecycle.

    Starts and stops a Launch Manager daemon instance for testing purposes.

    Parameters
    ----------
    daemon_binary : Path
        Path to the launch_manager executable.
    config_file : Path
        Path to the launch manager configuration JSON file.
    working_dir : Path
        Working directory for the daemon process.
    """

    def __init__(self, daemon_binary: Path, config_file: Path, working_dir: Path):
        self.daemon_binary = daemon_binary
        self.config_file = config_file
        self.working_dir = working_dir
        self.process: subprocess.Popen | None = None
        self.log_file: Path | None = None
        self._log_fd: TextIO | None = None

    def start(self, startup_timeout: float = 2.0) -> None:
        """
        Start the Launch Manager daemon.

        Parameters
        ----------
        startup_timeout : float
            Time to wait after starting the daemon (seconds).
        """
        # If a stale process reference exists from a previous run, clear it.
        if self.process is not None and self.process.poll() is not None:
            self.process = None

        if self.process is not None:
            raise RuntimeError("Daemon already started")

        # Create/append to log file so logs from a prior start() (e.g. before a
        # restart) are preserved instead of being discarded.
        self.log_file = self.working_dir / "launch_manager.log"
        self._log_fd = open(self.log_file, "a")

        # Start daemon process in its own process group so stop() can signal
        # the whole supervision tree, not just the daemon itself. Otherwise
        # supervised child processes are orphaned on daemon crash/restart and
        # linger to pollute later pgrep-based assertions.
        cmd = [str(self.daemon_binary), str(self.config_file)]
        self.process = subprocess.Popen(
            cmd,
            cwd=self.working_dir,
            stdout=self._log_fd,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

        # Wait for daemon to initialize
        time.sleep(startup_timeout)

        # Check if daemon is still running
        if self.process.poll() is not None:
            return_code = self.process.returncode
            log_content = self.log_file.read_text() if self.log_file.exists() else "No logs available"
            self._close_log_fd()
            self.process = None
            raise RuntimeError(f"Launch Manager daemon failed to start. Exit code: {return_code}\nLogs:\n{log_content}")

    def stop(self, shutdown_timeout: float = 5.0) -> None:
        """
        Stop the Launch Manager daemon gracefully.

        Parameters
        ----------
        shutdown_timeout : float
            Maximum time to wait for graceful shutdown (seconds).
        """
        if self.process is None:
            self._close_log_fd()
            return

        try:
            # Send SIGTERM to the whole process group for graceful shutdown if
            # still running, so supervised children are not orphaned.
            if self.process.poll() is None:
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass

            try:
                self.process.wait(timeout=shutdown_timeout)
            except subprocess.TimeoutExpired:
                # Force kill the whole process group if graceful shutdown fails.
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.process.wait()
        finally:
            self.process = None
            self._close_log_fd()

    def _close_log_fd(self) -> None:
        """Close daemon log file descriptor if it is open."""
        if self._log_fd is None:
            return

        try:
            self._log_fd.close()
        finally:
            self._log_fd = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

    def is_running(self) -> bool:
        """Check if the daemon process is still running."""
        return self.process is not None and self.process.poll() is None

    def get_logs(self) -> str:
        """Get the daemon log contents."""
        if self.log_file and self.log_file.exists():
            return self.log_file.read_text()
        return ""


@pytest.fixture(scope="class")
def launch_manager_daemon(
    tmp_path_factory: pytest.TempPathFactory, version: str
) -> Generator[dict[str, Any], None, None]:
    """
    Fixture that provides a running Launch Manager daemon instance.

    The fixture sets up a complete daemon environment including:
    - Building the launch_manager binary
    - Creating a temporary workspace with bin/ and etc/ directories
    - Starting the daemon with a minimal configuration
    - Cleaning up on teardown

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        Pytest temporary path factory.
    version : str
        Parametrized version ("rust" or "cpp").

    Yields
    ------
    dict
        Daemon information containing:
        - daemon: LaunchManagerDaemon instance
        - bin_dir: Path to bin directory for test applications
        - etc_dir: Path to etc directory for configurations
        - work_dir: Path to workspace root
        - config_file: Path to launch manager config

    Examples
    --------
    >>> def test_with_daemon(launch_manager_daemon):
    ...     daemon_info = launch_manager_daemon
    ...     assert daemon_info["daemon"].is_running()
    ...     # Copy test app to daemon_info["bin_dir"]
    ...     # Run your integration test
    """
    # Create workspace structure
    work_dir = tmp_path_factory.mktemp(f"daemon_workspace_{version}")
    bin_dir = work_dir / "bin"
    etc_dir = work_dir / "etc"
    bin_dir.mkdir(exist_ok=True)
    etc_dir.mkdir(exist_ok=True)

    # Get launch_manager daemon binary (from runfiles or build it)
    daemon_target = "@score_lifecycle_health//score/launch_manager:launch_manager"
    daemon_binary = get_binary_path(daemon_target)

    # Copy daemon to bin directory
    daemon_path = bin_dir / "launch_manager"
    shutil.copy2(daemon_binary, daemon_path)
    daemon_path.chmod(0o755)

    # Preload binaries referenced by the generated daemon config run target.
    for app_target, app_name in [
        ("@score_lifecycle_health//examples/rust_supervised_app:rust_supervised_app", "rust_supervised_app"),
        ("@score_lifecycle_health//examples/cpp_supervised_app:cpp_supervised_app", "cpp_supervised_app"),
        ("@score_lifecycle_health//examples/control_application:control_daemon", "control_daemon"),
    ]:
        app_binary = get_binary_path(app_target)
        app_dest = bin_dir / app_name
        shutil.copy2(app_binary, app_dest)
        app_dest.chmod(0o755)

    # Create minimal launch manager configuration
    config = {
        "schema_version": 1,
        "defaults": {
            "deployment_config": {
                "bin_dir": str(bin_dir) + "/",
                # lifecycle_config.py defaults to sandbox uid/gid 1000 when unset, which
                # fails setuid()/setgid() unless the test happens to run as that exact
                # user. Pin it to the actual runtime user instead.
                "sandbox": {
                    "uid": os.getuid(),
                    "gid": os.getgid(),
                },
                "ready_recovery_action": {
                    "restart": {
                        "number_of_attempts": 1,
                        "delay_before_restart": 0.5
                    }
                }
            },
            "component_properties": {
                "application_profile": {
                    "application_type": "Reporting",
                    "is_self_terminating": False,
                    "alive_supervision": {
                        "reporting_cycle": 0.1,
                        "min_indications": 1,
                        "max_indications": 3,
                        "failed_cycles_tolerance": 1
                    }
                },
                "depends_on": [],
                "process_arguments": [],
                "ready_condition": {
                    "process_state": "Running"
                }
            },
            "run_target": {
                "transition_timeout": 5,
                "recovery_action": {
                    "switch_run_target": {
                        "run_target": "fallback_run_target"
                    }
                }
            },
            "alive_supervision": {
                "evaluation_cycle": 0.5
            }
        },
        "components": {
            "state_manager": {
                "description": "State Manager application",
                "component_properties": {
                    "binary_name": "control_daemon",
                    "application_profile": {
                        "application_type": "State_Manager",
                        "alive_supervision": {
                            "min_indications": 0
                        }
                    },
                    "depends_on": []
                }
            },
            f"{version}_supervised_app": {
                "component_properties": {
                    "binary_name": f"{version}_supervised_app",
                    "application_profile": {
                        "application_type": "Reporting_And_Supervised"
                    },
                    "process_arguments": [
                        "-d50"
                    ]
                },
                "deployment_config": {
                    "environmental_variables": {
                        "PROCESSIDENTIFIER": f"{version}_supervised_app",
                        "CONFIG_PATH": str(etc_dir / f"hmproc_{version}_supervised_app.bin"),
                        "IDENTIFIER": f"{version}_supervised_app"
                    }
                }
            }
        },
        "run_targets": {
            "Startup": {
                "description": "Minimal functionality of the system",
                "depends_on": [
                    f"{version}_supervised_app",
                    "state_manager"
                ],
                "recovery_action": {
                    "switch_run_target": {
                        "run_target": "fallback_run_target"
                    }
                }
            }
        },
        "initial_run_target": "Startup",
        "fallback_run_target": {
            "description": "Switching off everything",
            "depends_on": [
                "state_manager"
            ],
            "transition_timeout": 1.5
        },
        "alive_supervision": {
            "evaluation_cycle": 0.5
        }
    }

    config_file = etc_dir / "launch_manager_config.json"
    config_file.write_text(json.dumps(config, indent=2))

    # Launch Manager daemon currently consumes flatbuffer config binaries from
    # `etc/` (e.g., lm_demo.bin), so populate them before startup.
    generate_flatbuffer_daemon_configs(config, etc_dir)

    # Start the daemon
    daemon = LaunchManagerDaemon(daemon_path, config_file, work_dir)
    daemon.start(startup_timeout=10.0)

    try:
        # Verify daemon is running
        if not daemon.is_running():
            raise RuntimeError("Launch Manager daemon failed to stay running")

        print(f"Launch Manager daemon started successfully (PID: {daemon.process.pid})")

        yield {
            "daemon": daemon,
            "bin_dir": bin_dir,
            "etc_dir": etc_dir,
            "work_dir": work_dir,
            "config_file": config_file,
        }
    finally:
        # Cleanup
        print("\nStopping Launch Manager daemon...")
        daemon.stop()
        print(f"Daemon logs:\n{daemon.get_logs()}")
