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
 * @brief Single-instance: verify write operations are reset-resistant.
 *
 * Phase 1: Write data_key=50.0 and flush.  This produces the first snapshot.
 * Phase 2: Re-open KVS, write data_key=100.0 and flush.  Snapshot rotation
 *          occurs: the previous snapshot is preserved as kvs_1_1.json while
 *          the new snapshot becomes kvs_1_0.json.
 *
 * The Python test verifies both snapshot files exist with the expected values,
 * proving the old state was preserved (reset resistant).
 *
 * Partially verifies: feat_req__persistency__reset_resistant
 */
class ResetResistant final : public Scenario {
public:
    /**
     * @brief Return the scenario name used by the test runner.
     * @return Scenario name string.
     */
    std::string name() const final {
        return "reset_resistant";
    }

    /**
     * @brief Execute the reset-resistant storage scenario.
     * @param input JSON string containing kvs_parameters_1.
     */
    void run(const std::string& input) const final {
        KvsParameters params =
            KvsParameters::from_json_section(input, "kvs_parameters_1");

        // Phase 1: write initial value and flush → creates first snapshot.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) {
                throw std::runtime_error("Phase 1: failed to create KVS instance");
            }
            auto kvs = *kvs_opt;

            if (!kvs->set_value("data_key", 50.0)) {
                throw std::runtime_error("Phase 1: failed to set data_key");
            }
            if (!kvs->flush()) {
                throw std::runtime_error("Phase 1: failed to flush");
            }
        }

        // Phase 2: re-open, write new value and flush → snapshot rotation.
        // kvs_1_1.json (value=50.0) and kvs_1_0.json (value=100.0) both exist.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) {
                throw std::runtime_error("Phase 2: failed to create KVS instance");
            }
            auto kvs = *kvs_opt;

            if (!kvs->set_value("data_key", 100.0)) {
                throw std::runtime_error("Phase 2: failed to set data_key");
            }
            if (!kvs->flush()) {
                throw std::runtime_error("Phase 2: failed to flush");
            }

            const auto current_val = kvs->get_value("data_key");
            if (!current_val.has_value()) {
                throw std::runtime_error("Phase 2: failed to read data_key");
            }
            kvs_build_helpers::log_info(
                "\"key\":\"data_key\",\"value\":"
                + kvs_build_helpers::format_double_python(current_val.value()),
                "cpp_test_scenarios::scenarios::persistency::reset_resistant");

            // Normalize both snapshots to the Rust envelope format for Python assertions.
            if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params)) {
                throw std::runtime_error("Phase 2: failed to normalize snapshot_0");
            }
            if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params, 1U)) {
                throw std::runtime_error("Phase 2: failed to normalize snapshot_1");
            }
        }
    }
};

/**
 * @brief Multi-instance: snapshot rotation for two instances sharing the same
 *        directory must not corrupt each other's snapshot files.
 *
 * Both instance 1 (kvs_parameters_1) and instance 2 (kvs_parameters_2) use
 * the same storage directory.  Each undergoes two flushes independently.
 *
 * After rotation:
 *   kvs_1_0.json = instance-1 new value (110.0)
 *   kvs_1_1.json = instance-1 old value (10.0)
 *   kvs_2_0.json = instance-2 new value (220.0)
 *   kvs_2_1.json = instance-2 old value (20.0)
 *
 * The Python test checks all four snapshot files for the correct values,
 * confirming complete isolation between instances.
 *
 * Partially verifies: feat_req__persistency__reset_resistant
 */
class ResetResistantMultiInstance final : public Scenario {
public:
    /**
     * @brief Return the scenario name used by the test runner.
     * @return Scenario name string.
     */
    std::string name() const final {
        return "reset_resistant_multi_instance";
    }

    /**
     * @brief Execute the multi-instance snapshot-isolation scenario.
     * @param input JSON string containing kvs_parameters_1 and kvs_parameters_2.
     */
    void run(const std::string& input) const final {
        KvsParameters params1 =
            KvsParameters::from_json_section(input, "kvs_parameters_1");
        KvsParameters params2 =
            KvsParameters::from_json_section(input, "kvs_parameters_2");

        // Instance 1 — Phase 1: write inst1_key=10.0 and flush.
        {
            auto kvs_opt = KvsInstance::create(params1);
            if (!kvs_opt) {
                throw std::runtime_error("Inst1-P1: failed to create KVS instance");
            }
            auto kvs = *kvs_opt;
            if (!kvs->set_value("inst1_key", 10.0)) {
                throw std::runtime_error("Inst1-P1: failed to set inst1_key");
            }
            if (!kvs->flush()) {
                throw std::runtime_error("Inst1-P1: failed to flush");
            }
        }

        // Instance 2 — Phase 1: write inst2_key=20.0 and flush.
        {
            auto kvs_opt = KvsInstance::create(params2);
            if (!kvs_opt) {
                throw std::runtime_error("Inst2-P1: failed to create KVS instance");
            }
            auto kvs = *kvs_opt;
            if (!kvs->set_value("inst2_key", 20.0)) {
                throw std::runtime_error("Inst2-P1: failed to set inst2_key");
            }
            if (!kvs->flush()) {
                throw std::runtime_error("Inst2-P1: failed to flush");
            }
        }

        // Instance 1 — Phase 2: write inst1_key=110.0 and flush (triggers rotation).
        {
            auto kvs_opt = KvsInstance::create(params1);
            if (!kvs_opt) {
                throw std::runtime_error("Inst1-P2: failed to create KVS instance");
            }
            auto kvs = *kvs_opt;
            if (!kvs->set_value("inst1_key", 110.0)) {
                throw std::runtime_error("Inst1-P2: failed to set inst1_key");
            }
            if (!kvs->flush()) {
                throw std::runtime_error("Inst1-P2: failed to flush");
            }
            // Normalize both instance-1 snapshots for Python assertions.
            if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params1)) {
                throw std::runtime_error("Inst1-P2: failed to normalize snapshot_0");
            }
            if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params1, 1U)) {
                throw std::runtime_error("Inst1-P2: failed to normalize snapshot_1");
            }
        }

        // Instance 2 — Phase 2: write inst2_key=220.0 and flush (triggers rotation).
        {
            auto kvs_opt = KvsInstance::create(params2);
            if (!kvs_opt) {
                throw std::runtime_error("Inst2-P2: failed to create KVS instance");
            }
            auto kvs = *kvs_opt;
            if (!kvs->set_value("inst2_key", 220.0)) {
                throw std::runtime_error("Inst2-P2: failed to set inst2_key");
            }
            if (!kvs->flush()) {
                throw std::runtime_error("Inst2-P2: failed to flush");
            }
            // Normalize both instance-2 snapshots for Python assertions.
            if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params2)) {
                throw std::runtime_error("Inst2-P2: failed to normalize snapshot_0");
            }
            if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params2, 1U)) {
                throw std::runtime_error("Inst2-P2: failed to normalize snapshot_1");
            }
        }
    }
};

}  // namespace

/**
 * @brief Factory function for ResetResistant scenario.
 * @return Shared pointer to the constructed scenario.
 */
Scenario::Ptr make_reset_resistant_scenario() {
    return std::make_shared<ResetResistant>();
}

/**
 * @brief Factory function for ResetResistantMultiInstance scenario.
 * @return Shared pointer to the constructed scenario.
 */
Scenario::Ptr make_reset_resistant_multi_instance_scenario() {
    return std::make_shared<ResetResistantMultiInstance>();
}
