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

#include "../../internals/persistency/kvs_instance.h"

#include <scenario.hpp>

#include <stdexcept>
#include <string>

namespace {

/**
 * @brief Verify that KVS automatically recovers to the last flushed state
 *        after a simulated reset (un-flushed write is discarded on re-open).
 *
 * Phase 1: Write data_key=50.0 and flush — this is the last-known-good (LKG)
 *          state on disk.
 * Phase 2: Re-open KVS, write data_key=100.0 and intentionally do NOT flush.
 *          The instance goes out of scope (simulates hard reset / power loss
 *          mid-write).  The snapshot on disk still holds 50.0.
 *
 * The Python test reads kvs_1_0.json directly and asserts data_key = 50.0,
 * proving that the un-flushed write never reached persistent storage.
 *
 * Partially verifies: feat_req__persistency__recovery_from_reset
 */
class RecoveryFromReset final : public Scenario {
public:
    /**
     * @brief Return the scenario name used by the test runner.
     * @return Scenario name string.
     */
    std::string name() const final {
        return "recovery_from_reset";
    }

    /**
     * @brief Execute the auto-recovery scenario.
     * @param input JSON string containing kvs_parameters_1.
     */
    void run(const std::string& input) const final {
        KvsParameters params =
            KvsParameters::from_json_section(input, "kvs_parameters_1");

        // Phase 1: write the last-known-good value and flush to disk.
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

        // Phase 2: write a new value WITHOUT flushing — simulates reset mid-write.
        // The KVS instance is destroyed here without flush; the 100.0 write is lost.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) {
                throw std::runtime_error("Phase 2: failed to create KVS instance");
            }
            auto kvs = *kvs_opt;

            if (!kvs->set_value("data_key", 100.0)) {
                throw std::runtime_error("Phase 2: failed to set data_key");
            }
            // Intentionally no flush — instance destroyed here.
        }

        // Normalize snapshot_0 to the Rust envelope format for Python assertions.
        // Must run after Phase 2 so that Phase 2's KVS::create() loads the native
        // C++ snapshot rather than the transformed envelope.
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params)) {
            throw std::runtime_error("Failed to normalize snapshot_0");
        }
    }
};

}  // namespace

/**
 * @brief Factory function for RecoveryFromReset scenario.
 * @return Shared pointer to the constructed scenario.
 */
Scenario::Ptr make_recovery_from_reset_scenario() {
    return std::make_shared<RecoveryFromReset>();
}

namespace {

/**
 * @brief Multi-instance recovery: two instances sharing the same directory
 *        must each independently recover to their own last-flushed state after
 *        a simulated reset.
 *
 * Phase 1: Instance 1 writes inst1_key=50.0 and flushes (LKG on disk).
 *          Instance 2 writes inst2_key=60.0 and flushes (LKG on disk).
 * Phase 2: Instance 1 re-opens, writes inst1_key=100.0, does NOT flush
 *          (simulates hard reset mid-write).
 *          Instance 2 re-opens, writes inst2_key=120.0, does NOT flush
 *          (simulates hard reset mid-write for the second instance).
 *
 * Expected disk state after Phase 2:
 *   kvs_1_0.json: inst1_key = 50.0  (Phase 2 write was never persisted)
 *   kvs_2_0.json: inst2_key = 60.0  (Phase 2 write was never persisted)
 *
 * This verifies that a crash of one instance's write path does not corrupt
 * the snapshot belonging to the other instance.
 *
 * Partially verifies: feat_req__persistency__recovery_from_reset
 */
class RecoveryFromResetMultiInstance final : public Scenario {
public:
    /**
     * @brief Return the scenario name used by the test runner.
     * @return Scenario name string.
     */
    std::string name() const final {
        return "recovery_from_reset_multi_instance";
    }

    /**
     * @brief Execute the multi-instance auto-recovery scenario.
     * @param input JSON string containing kvs_parameters_1 and kvs_parameters_2.
     */
    void run(const std::string& input) const final {
        KvsParameters params1 =
            KvsParameters::from_json_section(input, "kvs_parameters_1");
        KvsParameters params2 =
            KvsParameters::from_json_section(input, "kvs_parameters_2");

        // Phase 1: write last-known-good values for both instances and flush.
        {
            auto kvs1_opt = KvsInstance::create(params1);
            if (!kvs1_opt) {
                throw std::runtime_error("Phase 1 Inst1: failed to create KVS instance");
            }
            auto kvs1 = *kvs1_opt;
            if (!kvs1->set_value("inst1_key", 50.0)) {
                throw std::runtime_error("Phase 1 Inst1: failed to set inst1_key");
            }
            if (!kvs1->flush()) {
                throw std::runtime_error("Phase 1 Inst1: failed to flush");
            }
        }
        {
            auto kvs2_opt = KvsInstance::create(params2);
            if (!kvs2_opt) {
                throw std::runtime_error("Phase 1 Inst2: failed to create KVS instance");
            }
            auto kvs2 = *kvs2_opt;
            if (!kvs2->set_value("inst2_key", 60.0)) {
                throw std::runtime_error("Phase 1 Inst2: failed to set inst2_key");
            }
            if (!kvs2->flush()) {
                throw std::runtime_error("Phase 1 Inst2: failed to flush");
            }
        }

        // Phase 2: write new values WITHOUT flushing — simulates reset mid-write.
        // Neither write should reach the snapshot files.
        {
            auto kvs1_opt = KvsInstance::create(params1);
            if (!kvs1_opt) {
                throw std::runtime_error("Phase 2 Inst1: failed to create KVS instance");
            }
            auto kvs1 = *kvs1_opt;
            if (!kvs1->set_value("inst1_key", 100.0)) {
                throw std::runtime_error("Phase 2 Inst1: failed to set inst1_key");
            }
            // Intentionally no flush — instance destroyed here.
        }
        {
            auto kvs2_opt = KvsInstance::create(params2);
            if (!kvs2_opt) {
                throw std::runtime_error("Phase 2 Inst2: failed to create KVS instance");
            }
            auto kvs2 = *kvs2_opt;
            if (!kvs2->set_value("inst2_key", 120.0)) {
                throw std::runtime_error("Phase 2 Inst2: failed to set inst2_key");
            }
            // Intentionally no flush — instance destroyed here.
        }

        // Normalize both snapshot files to the Rust envelope format.
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params1)) {
            throw std::runtime_error("Failed to normalize snapshot for instance 1");
        }
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params2)) {
            throw std::runtime_error("Failed to normalize snapshot for instance 2");
        }
    }
};

}  // namespace

/**
 * @brief Factory function for RecoveryFromResetMultiInstance scenario.
 * @return Shared pointer to the constructed scenario.
 */
Scenario::Ptr make_recovery_from_reset_multi_instance_scenario() {
    return std::make_shared<RecoveryFromResetMultiInstance>();
}
