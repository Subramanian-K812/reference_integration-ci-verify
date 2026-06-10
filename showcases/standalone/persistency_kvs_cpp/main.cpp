/********************************************************************************
 * Copyright (c) 2026 Qorix GmbH
 *
 * See the NOTICE file(s) distributed with this work for additional
 * information regarding copyright ownership.
 *
 * This program and the accompanying materials are made available under the
 * terms of the Apache License Version 2.0 which is available at
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * SPDX-License-Identifier: Apache-2.0
 ********************************************************************************/

// Standalone persistency Key-Value Store showcase (C++).
//
// C++ twin of the Rust persistency_kvs showcase. Demonstrates the core C++
// KVS API:
//   - Opening a KVS instance via KvsBuilder
//   - Writing values of multiple types (f64, bool, String)
//   - Flushing state to disk and reloading it into a fresh instance
//   - Reading values back and verifying round-trip correctness

#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <string>
#include <variant>

#include "kvsbuilder.hpp"

using score::mw::per::kvs::InstanceId;
using score::mw::per::kvs::Kvs;
using score::mw::per::kvs::KvsBuilder;
using score::mw::per::kvs::KvsValue;

namespace
{

/* Working directory used by the KVS backend for snapshot files. */
constexpr const char* kKvsWorkingDir = "/tmp/score_kvs_cpp_showcase";

/* Writes a set of typed values into a KVS instance, flushes to disk, then
 * creates a fresh KVS instance that reloads the persisted state and verifies
 * each value matches what was written. Returns true on success. */
bool RunKvsShowcase()
{
    const InstanceId instance_id{1};

    /* --- Write phase --- */
    auto open_write = KvsBuilder(instance_id)
                          .need_defaults_flag(false)
                          .need_kvs_flag(false)
                          .dir(std::string{kKvsWorkingDir})
                          .build();
    if (!open_write.has_value())
    {
        std::cerr << "[KVS C++ Showcase] ERROR: failed to open KVS for writing\n";
        return false;
    }
    Kvs kvs_write = std::move(open_write.value());

    if (!kvs_write.set_value("speed_kmh", KvsValue(120.5)).has_value() ||
        !kvs_write.set_value("engine_running", KvsValue(true)).has_value() ||
        !kvs_write.set_value("vehicle_id", KvsValue(std::string{"SCORE-DEMO-001"})).has_value())
    {
        std::cerr << "[KVS C++ Showcase] ERROR: set_value failed\n";
        return false;
    }

    std::cout << "[KVS C++ Showcase] Values written:\n";
    std::cout << "  speed_kmh      = 120.5\n";
    std::cout << "  engine_running = true\n";
    std::cout << "  vehicle_id     = \"SCORE-DEMO-001\"\n";

    if (!kvs_write.flush().has_value())
    {
        std::cerr << "[KVS C++ Showcase] ERROR: flush failed\n";
        return false;
    }
    std::cout << "[KVS C++ Showcase] State flushed to disk at: " << kKvsWorkingDir << "\n";

    /* --- Reload phase --- */
    auto open_read = KvsBuilder(instance_id)
                         .need_defaults_flag(false)
                         .need_kvs_flag(true)
                         .dir(std::string{kKvsWorkingDir})
                         .build();
    if (!open_read.has_value())
    {
        std::cerr << "[KVS C++ Showcase] ERROR: failed to reopen KVS for reading\n";
        return false;
    }
    Kvs kvs_read = std::move(open_read.value());

    auto speed_res = kvs_read.get_value("speed_kmh");
    auto running_res = kvs_read.get_value("engine_running");
    auto vid_res = kvs_read.get_value("vehicle_id");
    if (!speed_res.has_value() || !running_res.has_value() || !vid_res.has_value())
    {
        std::cerr << "[KVS C++ Showcase] ERROR: get_value failed after reload\n";
        return false;
    }

    const double speed = std::get<double>(speed_res.value().getValue());
    const bool running = std::get<bool>(running_res.value().getValue());
    const std::string vid = std::get<std::string>(vid_res.value().getValue());

    std::cout << "[KVS C++ Showcase] Values reloaded from disk:\n";
    std::cout << "  speed_kmh      = " << speed << "\n";
    std::cout << "  engine_running = " << (running ? "true" : "false") << "\n";
    std::cout << "  vehicle_id     = \"" << vid << "\"\n";

    if (std::abs(speed - 120.5) >= 1e-9)
    {
        std::cerr << "[KVS C++ Showcase] ERROR: speed_kmh mismatch\n";
        return false;
    }
    if (!running)
    {
        std::cerr << "[KVS C++ Showcase] ERROR: engine_running mismatch\n";
        return false;
    }
    if (vid != "SCORE-DEMO-001")
    {
        std::cerr << "[KVS C++ Showcase] ERROR: vehicle_id mismatch\n";
        return false;
    }

    std::cout << "[KVS C++ Showcase] All values verified successfully.\n";
    return true;
}

}  // namespace

int main()
{
    std::cout << "[KVS C++ Showcase] Starting SCORE Persistency KVS C++ standalone showcase\n";

    /* The KVS backend writes snapshot files into the working directory but
     * does not create it, so ensure it exists before opening any instance. */
    std::error_code ec;
    std::filesystem::create_directories(kKvsWorkingDir, ec);
    if (ec)
    {
        std::cerr << "[KVS C++ Showcase] ERROR: failed to create working dir " << kKvsWorkingDir << ": "
                  << ec.message() << "\n";
        return EXIT_FAILURE;
    }

    if (!RunKvsShowcase())
    {
        return EXIT_FAILURE;
    }

    std::cout << "[KVS C++ Showcase] Showcase completed successfully.\n";
    return EXIT_SUCCESS;
}
