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
