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

/// Write 5 keys, flush, reopen (reload from disk), then read one specific key by name.
///
/// The targeted key access after reload verifies that individual key-value pairs
/// can be retrieved by name without iterating over the full storage.
///
/// Partially verifies feat_req__persistency__direct_access.
class DirectAccess final : public Scenario {
public:
    /**
     * @brief Return the scenario name for runner identification.
     * @return Scenario name string.
     */
    std::string name() const final { return "direct_access"; }

    /**
     * @brief Write 5 keys, flush, reopen, read da_key_3 directly.
     * @param input JSON string containing kvs_parameters_1.
     */
    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");

        // Phase 1: write 5 keys and flush.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) { throw std::runtime_error("Phase 1: failed to create KVS"); }
            auto kvs = *kvs_opt;
            for (int i = 0; i < 5; ++i) {
                const std::string key = "da_key_" + std::to_string(i);
                if (!kvs->set_value(key, static_cast<double>(i) * 10.0)) {
                    throw std::runtime_error("Failed to set " + key);
                }
            }
            if (!kvs->flush()) { throw std::runtime_error("Phase 1: flush failed"); }
            // Normalise deferred until after Phase 2.
        }

        // Phase 2: reopen and access one key directly.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) { throw std::runtime_error("Phase 2: failed to reopen KVS"); }
            auto kvs = *kvs_opt;
            auto val = kvs->get_value_f64("da_key_3");
            if (!val.has_value()) { throw std::runtime_error("Direct access: da_key_3 not found"); }
            kvs_build_helpers::log_info(
                "\"key\":\"da_key_3\",\"value\":" + kvs_build_helpers::format_double_python(val.value()) +
                    ",\"phase\":\"direct_access\"",
                "cpp_test_scenarios::scenarios::persistency::direct_access");
        }

        // Normalise to Rust envelope format so Python can read the snapshot.
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params)) {
            throw std::runtime_error("Phase 1: normalise failed");
        }
    }
};

/// Request get_value for a key that was never written.
/// Must return a failure (absent key), not a value.
///
/// Partially verifies feat_req__persistency__direct_access.
class DirectAccessAbsentKey final : public Scenario {
public:
    std::string name() const final { return "direct_access_absent_key"; }

    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");
        auto kvs_opt = KvsInstance::create(params);
        if (!kvs_opt) { throw std::runtime_error("Failed to create KVS instance"); }
        auto kvs = *kvs_opt;

        // Key was never written — must NOT have a value.
        auto result = kvs->get_value_f64("nonexistent_key");
        if (result.has_value()) {
            throw std::runtime_error("Expected absent key but got a value for nonexistent_key");
        }
        kvs_build_helpers::log_info(
            "\"key\":\"nonexistent_key\",\"result\":\"key_not_found\",\"phase\":\"absent_key\"",
            "cpp_test_scenarios::scenarios::persistency::direct_access");
    }
};

/// Write a present key and flush.  On reload call key_exists for the present key
/// (expect true) and for an absent key (expect false).
///
/// Partially verifies feat_req__persistency__direct_access.
class DirectAccessKeyExists final : public Scenario {
public:
    std::string name() const final { return "direct_access_key_exists"; }

    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");

        // Phase 1: write and flush.
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) { throw std::runtime_error("Phase 1: failed to create KVS"); }
            auto kvs = *kvs_opt;
            if (!kvs->set_value("present_key", 7.0)) { throw std::runtime_error("Failed to set present_key"); }
            if (!kvs->flush()) { throw std::runtime_error("Phase 1: flush failed"); }
            // No normalise needed: Python only checks logs for this scenario,
            // not the snapshot file directly.
        }

        // Phase 2: reload and check via get_value (proxy for key_exists).
        {
            auto kvs_opt = KvsInstance::create(params);
            if (!kvs_opt) { throw std::runtime_error("Phase 2: failed to reopen KVS"); }
            auto kvs = *kvs_opt;

            const bool exists_present = kvs->get_value_f64("present_key").has_value();
            kvs_build_helpers::log_info(
                "\"key\":\"present_key\",\"exists\":" + std::string(exists_present ? "true" : "false") +
                    ",\"phase\":\"key_exists\"",
                "cpp_test_scenarios::scenarios::persistency::direct_access");

            const bool exists_absent = kvs->get_value_f64("absent_key").has_value();
            kvs_build_helpers::log_info(
                "\"key\":\"absent_key\",\"exists\":" + std::string(exists_absent ? "true" : "false") +
                    ",\"phase\":\"key_exists\"",
                "cpp_test_scenarios::scenarios::persistency::direct_access");
        }
    }
};

/// Instance 1 has key_a; instance 2 has key_b.  After flush and reload each
/// instance confirms its own key present and the other's absent.
///
/// Partially verifies feat_req__persistency__direct_access.
class DirectAccessMultiInstance final : public Scenario {
public:
    std::string name() const final { return "direct_access_multi_instance"; }

    void run(const std::string& input) const final {
        KvsParameters params1 = KvsParameters::from_json_section(input, "kvs_parameters_1");
        KvsParameters params2 = KvsParameters::from_json_section(input, "kvs_parameters_2");

        // Phase 1: write and flush.
        {
            auto kvs1_opt = KvsInstance::create(params1);
            if (!kvs1_opt) { throw std::runtime_error("Phase 1: failed to create KVS 1"); }
            auto kvs1 = *kvs1_opt;
            if (!kvs1->set_value("key_a", 10.0)) { throw std::runtime_error("Failed to set key_a"); }
            if (!kvs1->flush()) { throw std::runtime_error("Phase 1: flush 1 failed"); }
            // No normalise needed: Python only checks logs for this scenario.

            auto kvs2_opt = KvsInstance::create(params2);
            if (!kvs2_opt) { throw std::runtime_error("Phase 1: failed to create KVS 2"); }
            auto kvs2 = *kvs2_opt;
            if (!kvs2->set_value("key_b", 20.0)) { throw std::runtime_error("Failed to set key_b"); }
            if (!kvs2->flush()) { throw std::runtime_error("Phase 1: flush 2 failed"); }
            // No normalise needed: Python only checks logs for this scenario.
        }

        // Phase 2: reload and verify cross-instance isolation.
        {
            auto kvs1_opt = KvsInstance::create(params1);
            if (!kvs1_opt) { throw std::runtime_error("Phase 2: failed to reopen KVS 1"); }
            auto kvs1 = *kvs1_opt;
            const bool a_in_1 = kvs1->get_value_f64("key_a").has_value();
            const bool b_in_1 = kvs1->get_value_f64("key_b").has_value();
            kvs_build_helpers::log_info(
                "\"instance\":\"1\",\"key\":\"key_a\",\"exists\":" + std::string(a_in_1 ? "true" : "false") + ",\"phase\":\"multi_instance\"",
                "cpp_test_scenarios::scenarios::persistency::direct_access");
            kvs_build_helpers::log_info(
                "\"instance\":\"1\",\"key\":\"key_b\",\"exists\":" + std::string(b_in_1 ? "true" : "false") + ",\"phase\":\"multi_instance\"",
                "cpp_test_scenarios::scenarios::persistency::direct_access");

            auto kvs2_opt = KvsInstance::create(params2);
            if (!kvs2_opt) { throw std::runtime_error("Phase 2: failed to reopen KVS 2"); }
            auto kvs2 = *kvs2_opt;
            const bool a_in_2 = kvs2->get_value_f64("key_a").has_value();
            const bool b_in_2 = kvs2->get_value_f64("key_b").has_value();
            kvs_build_helpers::log_info(
                "\"instance\":\"2\",\"key\":\"key_a\",\"exists\":" + std::string(a_in_2 ? "true" : "false") + ",\"phase\":\"multi_instance\"",
                "cpp_test_scenarios::scenarios::persistency::direct_access");
            kvs_build_helpers::log_info(
                "\"instance\":\"2\",\"key\":\"key_b\",\"exists\":" + std::string(b_in_2 ? "true" : "false") + ",\"phase\":\"multi_instance\"",
                "cpp_test_scenarios::scenarios::persistency::direct_access");
        }
    }
};

/// Call key_exists (via get_value_f64 proxy) on a key written to the cache
/// but never flushed.  If the implementation only checks the on-disk snapshot,
/// it would return false for an unflushed key.
///
/// Partially verifies feat_req__persistency__direct_access.
class DirectAccessKeyExistsUnflushed final : public Scenario {
public:
    std::string name() const final { return "direct_access_key_exists_unflushed"; }

    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");
        auto kvs_opt = KvsInstance::create(params);
        if (!kvs_opt) { throw std::runtime_error("Failed to create KVS instance"); }
        auto kvs = *kvs_opt;

        // Write — but do NOT flush.
        if (!kvs->set_value("unflushed_key", 3.0)) { throw std::runtime_error("Failed to set unflushed_key"); }

        // Proxy: get_value_f64().has_value() == key_exists().
        bool exists_written = kvs->get_value_f64("unflushed_key").has_value();
        kvs_build_helpers::log_info(
            std::string("\"key\":\"unflushed_key\",\"exists\":") + (exists_written ? "true" : "false") +
                ",\"phase\":\"unflushed_check\"",
            "cpp_test_scenarios::scenarios::persistency::direct_access");

        bool exists_absent = kvs->get_value_f64("never_written_key").has_value();
        kvs_build_helpers::log_info(
            std::string("\"key\":\"never_written_key\",\"exists\":") + (exists_absent ? "true" : "false") +
                ",\"phase\":\"unflushed_check\"",
            "cpp_test_scenarios::scenarios::persistency::direct_access");
    }
};

}  // namespace

Scenario::Ptr make_direct_access_scenario() {
    return std::make_shared<DirectAccess>();
}

Scenario::Ptr make_direct_access_absent_key_scenario() {
    return std::make_shared<DirectAccessAbsentKey>();
}

Scenario::Ptr make_direct_access_key_exists_scenario() {
    return std::make_shared<DirectAccessKeyExists>();
}

Scenario::Ptr make_direct_access_multi_instance_scenario() {
    return std::make_shared<DirectAccessMultiInstance>();
}

Scenario::Ptr make_direct_access_key_exists_unflushed_scenario() {
    return std::make_shared<DirectAccessKeyExistsUnflushed>();
}
