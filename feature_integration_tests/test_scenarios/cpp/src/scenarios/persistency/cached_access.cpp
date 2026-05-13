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
#include <vector>

namespace {

/// Write a value via set_value then read it back immediately without flushing.
///
/// The returned value must equal the written value, proving the in-memory cache
/// services reads without requiring a round-trip to persistent storage.
/// The absence of flush is intentional: the requirement is about in-memory
/// access speed, not durability.
///
/// Partially verifies feat_req__persistency__cached_access.
class CachedAccess final : public Scenario {
public:
    /**
     * @brief Return the scenario name for runner identification.
     * @return Scenario name string.
     */
    std::string name() const final { return "cached_access"; }

    /**
     * @brief Write cache_key=1.0 and immediately read it back — no flush.
     * @param input JSON string containing kvs_parameters_1.
     */
    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");
        auto kvs_opt = KvsInstance::create(params);
        if (!kvs_opt) { throw std::runtime_error("Failed to create KVS instance"); }
        auto kvs = *kvs_opt;

        if (!kvs->set_value("cache_key", 1.0)) { throw std::runtime_error("Failed to set cache_key"); }

        // Read from in-memory cache — no flush performed.
        auto cached = kvs->get_value_f64("cache_key");
        if (!cached.has_value()) { throw std::runtime_error("get_value failed for cache_key"); }

        kvs_build_helpers::log_info(
            "\"key\":\"cache_key\",\"value\":" + kvs_build_helpers::format_double_python(cached.value()) +
                ",\"phase\":\"cached_read\"",
            "cpp_test_scenarios::scenarios::persistency::cached_access");
    }
};

/// Write V1, read it back; write V2 over the same key, read it back.
/// Both reads must return the current in-memory value with no stale data.
///
/// Partially verifies feat_req__persistency__cached_access.
class CachedAccessUpdate final : public Scenario {
public:
    std::string name() const final { return "cached_access_update"; }

    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");
        auto kvs_opt = KvsInstance::create(params);
        if (!kvs_opt) { throw std::runtime_error("Failed to create KVS instance"); }
        auto kvs = *kvs_opt;

        // Write V1 and read back — no flush.
        if (!kvs->set_value("update_key", 1.0)) { throw std::runtime_error("Failed to set V1"); }
        auto v1 = kvs->get_value_f64("update_key");
        if (!v1.has_value()) { throw std::runtime_error("get_value failed after V1"); }
        kvs_build_helpers::log_info(
            "\"key\":\"update_key\",\"value\":" + kvs_build_helpers::format_double_python(v1.value()) +
                ",\"phase\":\"after_v1\"",
            "cpp_test_scenarios::scenarios::persistency::cached_access");

        // Overwrite with V2 and read back — cache must reflect new value.
        if (!kvs->set_value("update_key", 2.0)) { throw std::runtime_error("Failed to set V2"); }
        auto v2 = kvs->get_value_f64("update_key");
        if (!v2.has_value()) { throw std::runtime_error("get_value failed after V2"); }
        kvs_build_helpers::log_info(
            "\"key\":\"update_key\",\"value\":" + kvs_build_helpers::format_double_python(v2.value()) +
                ",\"phase\":\"after_v2\"",
            "cpp_test_scenarios::scenarios::persistency::cached_access");
    }
};

/// Write five distinct keys without flushing; read all five back immediately.
/// All must be accessible from the in-memory cache with correct values.
///
/// Partially verifies feat_req__persistency__cached_access.
class CachedAccessMultiKey final : public Scenario {
public:
    std::string name() const final { return "cached_access_multi_key"; }

    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");
        auto kvs_opt = KvsInstance::create(params);
        if (!kvs_opt) { throw std::runtime_error("Failed to create KVS instance"); }
        auto kvs = *kvs_opt;

        // Write five keys — no flush between or after.
        const std::vector<std::string> keys = {"mk_0", "mk_1", "mk_2", "mk_3", "mk_4"};
        for (int i = 0; i < static_cast<int>(keys.size()); ++i) {
            if (!kvs->set_value(keys[i], static_cast<double>(i) * 10.0)) {
                throw std::runtime_error("Failed to set key: " + keys[i]);
            }
        }

        // Read all five back from the cache.
        for (int i = 0; i < static_cast<int>(keys.size()); ++i) {
            auto got = kvs->get_value_f64(keys[i]);
            if (!got.has_value()) { throw std::runtime_error("get_value failed for: " + keys[i]); }
            kvs_build_helpers::log_info(
                "\"key\":\"" + keys[i] + "\",\"value\":" + kvs_build_helpers::format_double_python(got.value()) +
                    ",\"expected\":" + kvs_build_helpers::format_double_python(static_cast<double>(i) * 10.0) +
                    ",\"phase\":\"multi_key_read\"",
                "cpp_test_scenarios::scenarios::persistency::cached_access");
        }
    }
};

/// Write a value, flush, then read it back from the same KVS handle (no reopen).
/// A flush must not evict or invalidate the in-memory cache.
///
/// Partially verifies feat_req__persistency__cached_access.
class CachedAccessAfterFlush final : public Scenario {
public:
    std::string name() const final { return "cached_access_after_flush"; }

    void run(const std::string& input) const final {
        KvsParameters params = KvsParameters::from_json_section(input, "kvs_parameters_1");
        auto kvs_opt = KvsInstance::create(params);
        if (!kvs_opt) { throw std::runtime_error("Failed to create KVS instance"); }
        auto kvs = *kvs_opt;

        if (!kvs->set_value("flush_key", 5.0)) { throw std::runtime_error("Failed to set flush_key"); }
        // Flush — cache must remain valid after this point.
        if (!kvs->flush()) { throw std::runtime_error("Failed to flush"); }
        // Read from the same handle — cache must still serve this read.
        auto cached = kvs->get_value_f64("flush_key");
        if (!cached.has_value()) { throw std::runtime_error("get_value failed after flush"); }
        kvs_build_helpers::log_info(
            "\"key\":\"flush_key\",\"value\":" + kvs_build_helpers::format_double_python(cached.value()) +
                ",\"phase\":\"after_flush\"",
            "cpp_test_scenarios::scenarios::persistency::cached_access");
    }
};

}  // namespace

Scenario::Ptr make_cached_access_scenario() {
    return std::make_shared<CachedAccess>();
}

Scenario::Ptr make_cached_access_update_scenario() {
    return std::make_shared<CachedAccessUpdate>();
}

Scenario::Ptr make_cached_access_multi_key_scenario() {
    return std::make_shared<CachedAccessMultiKey>();
}

Scenario::Ptr make_cached_access_after_flush_scenario() {
    return std::make_shared<CachedAccessAfterFlush>();
}
