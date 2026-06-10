# *******************************************************************************
# Copyright (c) 2025 Contributors to the Eclipse Foundation
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
load("//bazel_common:bundlers.bzl", "score_pkg_bundle")

score_pkg_bundle(
    name = "showcases",
    bins = ["//showcases/cli"],
    other_package_files = [
        "//showcases/standalone:comm_pkg_files",
        "//showcases/standalone:kyron_pkg_files",
        "//showcases/standalone:orchestrator_pkg_files",
        "//showcases/standalone:persistency_pkg_files",
        # logging_rust_pkg_files is excluded from the image bundle because log_builtin
        # (in score_baselibs_rust) transitively uses score_log_fmt which requires Rust >= 1.80,
        # while the CI toolchain (Ferrocene for aarch64 and rules_rust default for x86_64) is older.
        # The standalone target //showcases/standalone:logging_rust still exists for direct use.
        "//showcases/orchestration_persistency:orch_per_pkg_files",
        "//showcases/orchestrator_ipc:orchestrator_ipc_pkg_files",
        "//showcases/simple_lifecycle:simple_lifecycle_pkg_files",
        "//showcases/full_stack:full_stack_pkg_files",
    ],
    package_dir = "showcases",
)
