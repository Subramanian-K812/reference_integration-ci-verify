// *******************************************************************************
// Copyright (c) 2026 Contributors to the Eclipse Foundation
//
// See the NOTICE file(s) distributed with this work for additional
// information regarding copyright ownership.
//
// This program and the accompanying materials are made available under the
// terms of the Apache License Version 2.0 which is available at
// https://www.apache.org/licenses/LICENSE-2.0
//
// SPDX-License-Identifier: Apache-2.0
// *******************************************************************************

#include "../../internals/persistency/kvs_build_helpers.h"
#include "../../internals/persistency/kvs_instance.h"

#include <scenario.hpp>

#include <stdexcept>
#include <string>

namespace {

/**
 * @brief Happy-path: flush() writes all pending changes atomically.
 *
 * Phase 1: Create KVS, set key_a=10.0, key_b=20.0, key_c=30.0, then call
 *          flush() once.  All three writes must be persisted together in a
 *          single snapshot — there is no observable partial-write state.
 *
 * Phase 2: Re-open KVS (loads from persisted snapshot) and read all three
 *          keys.  Their values must match what was written in phase 1.
 *
 * Partially verifies: feat_req__persistency__atomic_store
 */
class AtomicStore final : public Scenario {
public:
    /**
     * @brief Return the scenario name used by the test runner.
     * @return Scenario name string.
     */
    std::string name() const final {
        return "atomic_store";
    }

    /**
     * @brief Execute the atomic store scenario.
     * @param input JSON string containing kvs_parameters_1.
     */
    void run(const std::string& input) const final {
        KvsParameters params =
            KvsParameters::from_json_section(input, "kvs_parameters_1");

        // Phase 1: set multiple keys and flush — one atomic write operation.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) {
                throw std::runtime_error("Phase 1: failed to create KVS instance");
            }
            auto kvs = *kvs_opt;

            if (!kvs->set_value("key_a", 10.0)) {
                throw std::runtime_error("Phase 1: failed to set key_a");
            }
            if (!kvs->set_value("key_b", 20.0)) {
                throw std::runtime_error("Phase 1: failed to set key_b");
            }
            if (!kvs->set_value("key_c", 30.0)) {
                throw std::runtime_error("Phase 1: failed to set key_c");
            }
            // Single flush atomically persists all three keys.
            if (!kvs->flush()) {
                throw std::runtime_error("Phase 1: failed to flush");
            }
        }

        // Phase 2: re-open KVS and read all three keys to prove they were
        // persisted as a group (atomic store semantics).
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) {
                throw std::runtime_error("Phase 2: failed to create KVS instance");
            }
            auto kvs = *kvs_opt;

            const auto val_a = kvs->get_value("key_a");
            const auto val_b = kvs->get_value("key_b");
            const auto val_c = kvs->get_value("key_c");

            if (!val_a.has_value()) {
                throw std::runtime_error("Phase 2: key_a missing after reload");
            }
            if (!val_b.has_value()) {
                throw std::runtime_error("Phase 2: key_b missing after reload");
            }
            if (!val_c.has_value()) {
                throw std::runtime_error("Phase 2: key_c missing after reload");
            }

            kvs_build_helpers::log_info(
                "\"key\":\"key_a\",\"value\":"
                + kvs_build_helpers::format_double_python(val_a.value()),
                "cpp_test_scenarios::scenarios::persistency::atomic_store");
            kvs_build_helpers::log_info(
                "\"key\":\"key_b\",\"value\":"
                + kvs_build_helpers::format_double_python(val_b.value()),
                "cpp_test_scenarios::scenarios::persistency::atomic_store");
            kvs_build_helpers::log_info(
                "\"key\":\"key_c\",\"value\":"
                + kvs_build_helpers::format_double_python(val_c.value()),
                "cpp_test_scenarios::scenarios::persistency::atomic_store");

            // Normalize the snapshot file to the Rust envelope format for Python assertions.
            if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params)) {
                throw std::runtime_error("Phase 2: failed to normalize snapshot_0");
            }
        }
    }
};

/**
 * @brief Negative-path: un-flushed writes must NOT persist on KVS reload.
 *
 * Phase 1: Create KVS, write key_d=999.0 to the in-memory store, then
 *          let the instance go out of scope WITHOUT calling flush().  This
 *          simulates a hard reset before the write was committed.
 *
 * Because no flush ever occurred, no snapshot file is written to disk.
 * The Python test asserts that kvs_1_0.json does not exist.
 *
 * Partially verifies: feat_req__persistency__atomic_store
 */
class AtomicStoreNoPartialWrite final : public Scenario {
public:
    /**
     * @brief Return the scenario name used by the test runner.
     * @return Scenario name string.
     */
    std::string name() const final {
        return "atomic_store_no_partial_write";
    }

    /**
     * @brief Execute the no-partial-write scenario.
     * @param input JSON string containing kvs_parameters_1.
     */
    void run(const std::string& input) const final {
        KvsParameters params =
            KvsParameters::from_json_section(input, "kvs_parameters_1");

        // Phase 1: write key_d WITHOUT flushing — simulates power loss mid-write.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) {
                throw std::runtime_error("Phase 1: failed to create KVS instance");
            }
            auto kvs = *kvs_opt;

            if (!kvs->set_value("key_d", 999.0)) {
                throw std::runtime_error("Phase 1: failed to set key_d");
            }
            // Intentionally no flush — kvs instance destroyed here.
        }
    }
};

}  // namespace

/**
 * @brief Factory function for AtomicStore scenario.
 * @return Shared pointer to the constructed scenario.
 */
Scenario::Ptr make_atomic_store_scenario() {
    return std::make_shared<AtomicStore>();
}

/**
 * @brief Factory function for AtomicStoreNoPartialWrite scenario.
 * @return Shared pointer to the constructed scenario.
 */
Scenario::Ptr make_atomic_store_no_partial_write_scenario() {
    return std::make_shared<AtomicStoreNoPartialWrite>();
}
