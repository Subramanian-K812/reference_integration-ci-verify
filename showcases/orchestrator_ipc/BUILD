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

load("//bazel_common:bundlers.bzl", "score_pkg_bundle")

# Complex showcase: orchestrator inter-process event communication.
#
# Bundles the IPC event sender and receiver example binaries from the
# score_orchestrator module together with a score.json descriptor that
# launches both processes so the receiver is ready before the sender fires.
score_pkg_bundle(
    name = "orchestrator_ipc",
    bins = [
        "@score_orchestrator//examples:inter_process_event_sender",
        "@score_orchestrator//examples:inter_process_event_receiver",
    ],
    config_data = [
        "//showcases/orchestrator_ipc:orchestrator_ipc.score.json",
    ],
    package_dir = "orchestrator_ipc",
)
