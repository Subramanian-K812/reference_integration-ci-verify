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

load("@rules_rust//rust:defs.bzl", "rust_binary")
load("//bazel_common:bundlers.bzl", "score_pkg_bundle")

# Full-stack showcase binary.
#
# Combines the SCORE Orchestration, Persistency and Lifecycle health-monitoring
# modules into a single Rust binary demonstrating their integration:
#   - Kyron async runtime for safe multi-threaded execution
#   - Orchestration design with a timer-triggered run action
#   - KVS-backed state persistence written from the program's stop action
#   - Lifecycle alive deadline supervision on a dedicated OS thread
rust_binary(
    name = "full_stack_example",
    srcs = ["main.rs"],
    rustc_flags = [
        "-Clink-arg=-lm",
        "-Clink-arg=-lc",
    ] + select({
        "@platforms//os:qnx": [
            "-Clink-arg=-lc++",
        ],
        "//conditions:default": [
            "-Clink-arg=-lrt",
            "-Clink-arg=-lstdc++",
        ],
    }),
    visibility = ["//visibility:public"],
    deps = [
        "@score_kyron//src/kyron:libkyron",
        "@score_kyron//src/kyron-foundation:libkyron_foundation",
        "@score_kyron//src/logging_tracing:liblogging_tracing",
        "@score_lifecycle_health//src/health_monitoring_lib",
        "@score_lifecycle_health//src/launch_manager_daemon/lifecycle_client_lib/rust_bindings:lifecycle_client_rs",
        "@score_orchestrator//src/orchestration:liborchestration",
        "@score_persistency//src/rust/rust_kvs",
    ],
)

score_pkg_bundle(
    name = "full_stack",
    bins = [":full_stack_example"],
    config_data = ["//showcases/full_stack:full_stack.score.json"],
    package_dir = "full_stack",
)
