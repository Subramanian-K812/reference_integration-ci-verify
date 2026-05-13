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

/// Write a single f64 key, flush, drop the KVS handle, reopen, and read back.
///
/// Tests the basic load-from-persistent-storage guarantee: a value written and
/// flushed in one KVS lifetime is readable in the next.
///
/// Partially verifies feat_req__persistency__load_data.
class LoadData final : public Scenario {
public:
    /**
     * @brief Return the scenario name for runner identification.
     * @return Scenario name string.
     */
    std::string name() const final { return "load_data"; }

    /**
     * @brief Execute the load_data scenario.
     *
     * Phase 1: creates KVS, writes data_key=42.0, flushes.
     * Phase 2: reopens KVS (reload from disk), reads data_key, logs the value.
     *
     * @param input JSON string containing kvs_parameters_1.
     */
    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");

        // Phase 1: write and flush.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) { throw std::runtime_error("Phase 1: failed to create KVS instance"); }
            auto kvs = *kvs_opt;
            if (!kvs->set_value("data_key", 42.0)) { throw std::runtime_error("Failed to set data_key"); }
            if (!kvs->flush()) { throw std::runtime_error("Phase 1: flush failed"); }
            // Normalize is deferred until after Phase 2 — normalising here would
            // convert the file to Rust envelope format, preventing C++ Phase 2
            // from reopening it.
        }

        // Phase 2: reopen and read back from disk.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) { throw std::runtime_error("Phase 2: failed to reopen KVS instance"); }
            auto kvs = *kvs_opt;
            auto loaded = kvs->get_value_f64("data_key");
            if (!loaded.has_value()) { throw std::runtime_error("Phase 2: data_key not found after reload"); }
            kvs_build_helpers::log_info(
                "\"key\":\"data_key\",\"value\":" + kvs_build_helpers::format_double_python(loaded.value()) +
                    ",\"phase\":\"reload\"",
                "cpp_test_scenarios::scenarios::persistency::load_data");
        }

        // Normalise to Rust envelope format so Python can read the snapshot.
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params)) {
            throw std::runtime_error("Failed to normalise snapshot");
        }
    }
};

/// Write and flush three values in succession (V1→V2→V3).
/// On reload the KVS must return V3 (latest snapshot), not V1 or V2.
///
/// Partially verifies feat_req__persistency__load_data.
class LoadDataAfterMultipleFlushes final : public Scenario {
public:
    std::string name() const final { return "load_data_after_multiple_flushes"; }

    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");

        // Phase 1: write V1, V2, V3 with a flush each.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) { throw std::runtime_error("Phase 1: failed to create KVS instance"); }
            auto kvs = *kvs_opt;
            for (double v : {10.0, 20.0, 30.0}) {
                if (!kvs->set_value("data_key", v)) { throw std::runtime_error("Failed to set data_key"); }
                if (!kvs->flush()) { throw std::runtime_error("Phase 1: flush failed"); }
                // Normalise is deferred until after Phase 2 so C++ Phase 2 can
                // still read the snapshot written here.
            }
        }

        // Phase 2: reopen — must load the most recent snapshot (V3 = 30.0).
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) { throw std::runtime_error("Phase 2: failed to reopen KVS"); }
            auto kvs = *kvs_opt;
            auto loaded = kvs->get_value_f64("data_key");
            if (!loaded.has_value()) { throw std::runtime_error("Phase 2: data_key not found after reload"); }
            kvs_build_helpers::log_info(
                "\"key\":\"data_key\",\"value\":" + kvs_build_helpers::format_double_python(loaded.value()) +
                    ",\"phase\":\"reload_latest\"",
                "cpp_test_scenarios::scenarios::persistency::load_data");
        }

        // Normalise to Rust envelope format so Python can read the snapshot.
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params)) {
            throw std::runtime_error("Failed to normalise snapshot");
        }
    }
};

/// Instance 1 writes key_a, instance 2 writes key_b; both flush; both reopen.
/// Each must load only its own key — cross-instance snapshot isolation.
///
/// Partially verifies feat_req__persistency__load_data and
/// feat_req__persistency__store_data.
class LoadDataMultiInstance final : public Scenario {
public:
    std::string name() const final { return "load_data_multi_instance"; }

    void run(const std::string& input) const final {
        KvsParameters params1 = KvsParameters::from_json_section(input, "kvs_parameters_1");
        KvsParameters params2 = KvsParameters::from_json_section(input, "kvs_parameters_2");

        // Phase 1: write and flush each instance.
        {
            auto kvs1_opt = KvsInstance::create(params1);
            if (!kvs1_opt) { throw std::runtime_error("Phase 1: failed to create KVS 1"); }
            auto kvs1 = *kvs1_opt;
            if (!kvs1->set_value("key_a", 10.0)) { throw std::runtime_error("Failed to set key_a"); }
            if (!kvs1->flush()) { throw std::runtime_error("Phase 1: flush instance 1 failed"); }
            // Normalise deferred — see Phase 2.

            auto kvs2_opt = KvsInstance::create(params2);
            if (!kvs2_opt) { throw std::runtime_error("Phase 1: failed to create KVS 2"); }
            auto kvs2 = *kvs2_opt;
            if (!kvs2->set_value("key_b", 20.0)) { throw std::runtime_error("Failed to set key_b"); }
            if (!kvs2->flush()) { throw std::runtime_error("Phase 1: flush instance 2 failed"); }
            // Normalise deferred — see Phase 2.
        }

        // Phase 2: reload both instances and verify isolation.
        {
            auto kvs1_opt = KvsInstance::create(params1);
            if (!kvs1_opt) { throw std::runtime_error("Phase 2: failed to reopen KVS 1"); }
            auto kvs1 = *kvs1_opt;
            auto val_a = kvs1->get_value_f64("key_a");
            if (!val_a.has_value()) { throw std::runtime_error("Instance 1 failed to load key_a"); }
            kvs_build_helpers::log_info(
                "\"instance\":\"1\",\"key\":\"key_a\",\"value\":" + kvs_build_helpers::format_double_python(val_a.value()) +
                    ",\"phase\":\"reload\"",
                "cpp_test_scenarios::scenarios::persistency::load_data");

            // key_b must NOT be visible in instance 1.
            if (kvs1->get_value_f64("key_b").has_value()) {
                throw std::runtime_error("Isolation broken: instance 1 loaded key_b");
            }

            auto kvs2_opt = KvsInstance::create(params2);
            if (!kvs2_opt) { throw std::runtime_error("Phase 2: failed to reopen KVS 2"); }
            auto kvs2 = *kvs2_opt;
            auto val_b = kvs2->get_value_f64("key_b");
            if (!val_b.has_value()) { throw std::runtime_error("Instance 2 failed to load key_b"); }
            kvs_build_helpers::log_info(
                "\"instance\":\"2\",\"key\":\"key_b\",\"value\":" + kvs_build_helpers::format_double_python(val_b.value()) +
                    ",\"phase\":\"reload\"",
                "cpp_test_scenarios::scenarios::persistency::load_data");

            // key_a must NOT be visible in instance 2.
            if (kvs2->get_value_f64("key_a").has_value()) {
                throw std::runtime_error("Isolation broken: instance 2 loaded key_a");
            }
        }

        // Normalise both instances after Phase 2 so Python can read their snapshots.
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params1)) {
            throw std::runtime_error("Failed to normalise snapshot 1");
        }
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params2)) {
            throw std::runtime_error("Failed to normalise snapshot 2");
        }
    }
};

/// Write 5 distinct keys in one session, flush once, drop the KVS handle, reopen.
/// All 5 keys must be loadable from the new session.
///
/// Partially verifies feat_req__persistency__load_data.
class LoadDataMultipleKeys final : public Scenario {
public:
    std::string name() const final { return "load_data_multiple_keys"; }

    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");

        // Phase 1: write 5 keys and flush once.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) { throw std::runtime_error("Failed to create KVS instance"); }
            auto kvs = *kvs_opt;
            for (int i = 0; i < 5; ++i) {
                std::string key = "mk_key_" + std::to_string(i);
                if (!kvs->set_value(key, static_cast<double>(i) * 10.0)) {
                    throw std::runtime_error("Failed to set key: " + key);
                }
            }
            if (!kvs->flush()) { throw std::runtime_error("Failed to flush"); }
            // Normalise deferred until after Phase 2.
        }

        // Phase 2: reopen and verify every key is present.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) { throw std::runtime_error("Failed to reopen KVS instance"); }
            auto kvs = *kvs_opt;
            for (int i = 0; i < 5; ++i) {
                std::string key = "mk_key_" + std::to_string(i);
                auto got = kvs->get_value_f64(key);
                if (!got.has_value()) { throw std::runtime_error("Failed to load key: " + key); }
                kvs_build_helpers::log_info(
                    "\"key\":\"" + key + "\",\"value\":" + kvs_build_helpers::format_double_python(got.value()) +
                        ",\"phase\":\"multi_key_reload\"",
                    "cpp_test_scenarios::scenarios::persistency::load_data");
            }
        }

        // Normalise to Rust envelope format so Python can read the snapshot.
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params)) {
            throw std::runtime_error("Failed to normalize snapshot");
        }
    }
};

}  // namespace

Scenario::Ptr make_load_data_scenario() {
    return std::make_shared<LoadData>();
}

Scenario::Ptr make_load_data_after_multiple_flushes_scenario() {
    return std::make_shared<LoadDataAfterMultipleFlushes>();
}

Scenario::Ptr make_load_data_multi_instance_scenario() {
    return std::make_shared<LoadDataMultiInstance>();
}

Scenario::Ptr make_load_data_multiple_keys_scenario() {
    return std::make_shared<LoadDataMultipleKeys>();
}
