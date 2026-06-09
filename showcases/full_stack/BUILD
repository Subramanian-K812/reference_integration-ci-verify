# *******************************************************************************
# Copyright (c) 2026 Qorix GmbH
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
#   - Orchestration design with sequential and timer-based actions
#   - KVS-backed state persistence on shutdown
#   - Lifecycle alive deadline supervision
rust_binary(
    name = "full_stack_example",
    srcs = ["main.rs"],
    visibility = ["//visibility:public"],
    deps = [
        "@score_kyron//src/kyron:libkyron",
        "@score_kyron//src/kyron-foundation:libkyron_foundation",
        "@score_kyron//src/logging_tracing:liblogging_tracing",
        "@score_lifecycle_health//src/health_monitoring_lib",
        "@score_lifecycle_health//src/lifecycle_client_rs",
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
