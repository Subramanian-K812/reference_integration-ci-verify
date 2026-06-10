// *******************************************************************************
// Copyright (c) 2026 Qorix GmbH
//
// See the NOTICE file(s) distributed with this work for additional
// information regarding copyright ownership.
//
// This program and the accompanying materials are made available under the
// terms of the Apache License Version 2.0 which is available at
// <https://www.apache.org/licenses/LICENSE-2.0>
//
// SPDX-License-Identifier: Apache-2.0
// *******************************************************************************

//! Standalone persistency Key-Value Store showcase.
//!
//! Demonstrates the core KVS API:
//!   - Creating a KVS instance with a JSON backend
//!   - Writing values of multiple types (f64, bool, String)
//!   - Reading values back and verifying round-trip correctness
//!   - Flushing state to disk and reloading it into a fresh instance

use std::path::PathBuf;

use rust_kvs::json_backend::JsonBackendBuilder;
use rust_kvs::prelude::*;

/// Working directory used by the JSON backend for snapshot files.
const KVS_WORKING_DIR: &str = "/tmp/score_kvs_showcase";

/// Writes a set of typed values into a KVS instance, flushes to disk, then
/// creates a fresh KVS instance that reloads the persisted state and verifies
/// each value matches what was written.
fn run_kvs_showcase() -> Result<(), ErrorCode> {
    let instance_id = InstanceId(1);
    let working_dir = PathBuf::from(KVS_WORKING_DIR);

    // --- Write phase ---
    let backend_write = JsonBackendBuilder::new().working_dir(working_dir.clone()).build();
    let kvs_write = KvsBuilder::new(instance_id)
        .backend(Box::new(backend_write))
        .kvs_load(KvsLoad::Optional)
        .build()?;

    kvs_write.set_value("speed_kmh", 120.5_f64)?;
    kvs_write.set_value("engine_running", true)?;
    kvs_write.set_value("vehicle_id", "SCORE-DEMO-001".to_string())?;

    println!("[KVS Showcase] Values written:");
    println!("  speed_kmh    = 120.5");
    println!("  engine_running = true");
    println!("  vehicle_id   = \"SCORE-DEMO-001\"");

    kvs_write.flush()?;
    println!("[KVS Showcase] State flushed to disk at: {}", KVS_WORKING_DIR);

    // --- Reload phase ---
    let backend_read = JsonBackendBuilder::new().working_dir(working_dir).build();
    let kvs_read = KvsBuilder::new(instance_id)
        .backend(Box::new(backend_read))
        .kvs_load(KvsLoad::Optional)
        .build()?;

    let speed: f64 = kvs_read.get_value_as::<f64>("speed_kmh")?;
    let running: bool = kvs_read.get_value_as::<bool>("engine_running")?;
    let vid: String = kvs_read.get_value_as::<String>("vehicle_id")?;

    println!("[KVS Showcase] Values reloaded from disk:");
    println!("  speed_kmh      = {}", speed);
    println!("  engine_running = {}", running);
    println!("  vehicle_id     = \"{}\"", vid);

    assert!((speed - 120.5_f64).abs() < 1e-9, "speed_kmh mismatch");
    assert!(running, "engine_running mismatch");
    assert_eq!(vid, "SCORE-DEMO-001", "vehicle_id mismatch");

    println!("[KVS Showcase] All values verified successfully.");
    Ok(())
}

/// Entry point for the persistency KVS showcase binary.
fn main() {
    println!("[KVS Showcase] Starting SCORE Persistency KVS standalone showcase");

    // The JSON backend writes snapshot files into the working directory but does
    // not create it, so ensure it exists before building any KVS instance.
    if let Err(e) = std::fs::create_dir_all(KVS_WORKING_DIR) {
        eprintln!(
            "[KVS Showcase] ERROR: failed to create working dir {}: {}",
            KVS_WORKING_DIR, e
        );
        std::process::exit(1);
    }

    match run_kvs_showcase() {
        Ok(()) => println!("[KVS Showcase] Showcase completed successfully."),
        Err(e) => {
            eprintln!("[KVS Showcase] ERROR: {:?}", e);
            std::process::exit(1);
        },
    }
}
