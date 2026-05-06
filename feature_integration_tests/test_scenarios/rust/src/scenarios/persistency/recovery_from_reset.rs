// *******************************************************************************
// Copyright (c) 2026 Contributors to the Eclipse Foundation
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

//! Scenario: Verify that persistency automatically recovers to the last
//! consistent (flushed) state after a simulated reset.
//!
//! A "reset" is modelled by writing data to the in-memory KVS store and then
//! dropping the instance *without* calling `flush()`.  The un-flushed write
//! represents work that was in progress when the power was cut.  The
//! requirement states that after recovery the store must reflect the last
//! *successful* flush — the partial write must not be visible.
//!
//! Partially verifies: feat_req__persistency__recovery_from_reset

use crate::internals::persistency::{kvs_instance::kvs_instance, kvs_parameters::KvsParameters};
use rust_kvs::prelude::KvsApi;
use serde_json::Value;
use test_scenarios_rust::scenario::Scenario;

/// Scenario that demonstrates automatic recovery to the last flushed state.
pub struct RecoveryFromReset;

impl Scenario for RecoveryFromReset {
    /// Return the unique scenario name used by the test runner.
    fn name(&self) -> &str {
        "recovery_from_reset"
    }

    /// Execute the auto-recovery scenario.
    ///
    /// Phase 1: Create KVS, write `data_key` = 50.0, flush.
    ///          This is the last-known-good (LKG) state on disk (`kvs_1_0.json` = 50.0).
    ///
    /// Phase 2: Re-open the KVS handle, write `data_key` = 100.0, **do NOT flush**.
    ///          Dropping the handle simulates a hard reset mid-write.
    ///          The Rust KVS instance pool shares in-process memory for the same
    ///          `instance_id`, so Phase 2 modifies the in-memory state but does
    ///          NOT touch the snapshot file.  The on-disk snapshot still holds 50.0.
    ///
    /// The Python test reads `kvs_1_0.json` directly (no API call) and asserts
    /// `data_key = 50.0`, proving that the un-flushed write never reached
    /// persistent storage.  This is the observable guarantee of recovery from
    /// reset: a post-reset boot loads from disk and sees the last-flushed state.
    fn run(&self, input: &str) -> Result<(), String> {
        let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
        let params = KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())?;

        // Phase 1: write the last-known-good value and flush to disk.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("data_key", 50.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Phase 2: write a new value WITHOUT flushing — simulates reset mid-write.
        // The Rust KVS pool shares in-memory state within the process, so the
        // 100.0 write is visible in-memory but is NOT persisted to the snapshot
        // file.  The Python test verifies the disk state via file inspection.
        {
            let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("data_key", 100.0_f64).map_err(|e| format!("{e:?}"))?;
            // Instance dropped without flush — 100.0 never reaches kvs_1_0.json.
        }

        Ok(())
    }
}
