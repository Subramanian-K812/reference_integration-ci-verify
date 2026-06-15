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
load("//bazel_common:bundlers.bzl", "score_pkg_bundle")

score_pkg_bundle(
    name = "comm",
    bins = ["@score_communication//score/mw/com/example/ipc_bridge:ipc_bridge_cpp"],
    config_data = [
        "//showcases/standalone:com.score.json",
    ],
    custom_layout = {
        "@score_communication//score/mw/com/example/ipc_bridge:etc/mw_com_config.json": "etc/mw_com_config.json",
    },
    package_dir = "standalone",
)

score_pkg_bundle(
    name = "kyron",
    bins = [
        "@score_kyron//examples:select",
        "@score_kyron//examples:safety_task",
        "@score_kyron//examples:main_macro",
        "@score_kyron//examples:mpmc",
    ],
    config_data = [
        "//showcases/standalone:kyron.score.json",
    ],
    package_dir = "standalone",
)

score_pkg_bundle(
    name = "orchestrator",
    bins = [
        "@score_orchestrator//examples:basic",
        "@score_orchestrator//examples:branching",
        "@score_orchestrator//examples:catch_error",
        "@score_orchestrator//examples:dag",
        "@score_orchestrator//examples:events_across_local_programs",
        "@score_orchestrator//examples:shutdown",
        "@score_orchestrator//examples:shutdown_using_signals",
    ],
    config_data = [
        "//showcases/standalone:orchestrator.score.json",
    ],
    package_dir = "standalone",
)

score_pkg_bundle(
    name = "comm_rust",
    bins = ["@score_communication//score/mw/com/example/com-api-example:com-api-example"],
    config_data = [
        "//showcases/standalone:com_rust.score.json",
    ],
    custom_layout = {
        "@score_communication//score/mw/com/example/com-api-example:etc/mw_com_config.json": "etc/mw_com_config.json",
    },
    package_dir = "standalone",
)

score_pkg_bundle(
    name = "persistency",
    bins = ["//showcases/standalone/persistency_kvs:persistency_kvs_example"],
    config_data = [
        "//showcases/standalone:persistency.score.json",
    ],
    package_dir = "standalone",
)

score_pkg_bundle(
    name = "persistency_cpp",
    bins = ["//showcases/standalone/persistency_kvs_cpp:persistency_kvs_cpp_example"],
    config_data = [
        "//showcases/standalone:persistency_cpp.score.json",
    ],
    package_dir = "standalone",
)

score_pkg_bundle(
    name = "logging_rust",
    bins = ["@score_baselibs_rust//examples/log_builtin:log_builtin"],
    config_data = [
        "//showcases/standalone:logging_rust.score.json",
    ],
    package_dir = "standalone",
)

# Gives the generic upstream binary name "example" a descriptive name in
# the bundle's bin/ directory (the bundler names files after the target).
alias(
    name = "logging_cpp_example",
    actual = "@score_logging//score/mw/log/rust/score_log_bridge_cpp_init:example",
)

score_pkg_bundle(
    name = "logging_cpp",
    bins = [":logging_cpp_example"],
    config_data = [
        "//showcases/standalone:logging_cpp.score.json",
    ],
    package_dir = "standalone",
)
