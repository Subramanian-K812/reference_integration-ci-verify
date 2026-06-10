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

load("@rules_cc//cc:defs.bzl", "cc_binary")

# Standalone persistency Key-Value Store showcase binary (C++).
#
# C++ twin of //showcases/standalone/persistency_kvs: opens a KVS instance via
# KvsBuilder, writes typed values, flushes to disk, reloads from disk and
# verifies round-trip correctness.
cc_binary(
    name = "persistency_kvs_cpp_example",
    srcs = ["main.cpp"],
    visibility = ["//visibility:public"],
    deps = [
        "@score_persistency//src/cpp/src:kvs_cpp",
        "@score_persistency//src/cpp/src:kvsvalue",
    ],
)
