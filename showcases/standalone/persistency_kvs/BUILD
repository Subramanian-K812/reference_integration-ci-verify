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

# Standalone persistency Key-Value Store showcase binary.
#
# Demonstrates the core rust_kvs API: creating a KVS instance backed by the
# JSON backend, writing typed values, flushing to disk, reloading from disk
# and verifying round-trip correctness.
rust_binary(
    name = "persistency_kvs_example",
    srcs = ["main.rs"],
    visibility = ["//visibility:public"],
    deps = [
        "@score_persistency//src/rust/rust_kvs",
    ],
)
