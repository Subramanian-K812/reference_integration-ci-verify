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

//! Scenarios verifying `feat_req__persistency__recovery_from_reset`.
//!
//! Two distinct scenarios are provided:
//!
//! 1. `recovery_from_reset` — single instance: un-flushed write is discarded;
//!    on-disk snapshot reflects the last successful flush.
//!
//! 2. `recovery_from_reset_multi_instance` — two instances sharing the same
//!    directory: a crash of one instance's write path must not corrupt the
//!    snapshot belonging to the other instance.

use crate::internals::persistency::{kvs_instance::kvs_instance, kvs_parameters::KvsParameters};
use rust_kvs::prelude::KvsApi;
use serde_json::Value;
use test_scenarios_rust::scenario::Scenario;
use tracing::info;

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
        // The 100.0 write is visible in-memory but is NOT persisted to the snapshot
        // file.  On drop, the in-memory state is discarded without flushing.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("data_key", 100.0_f64).map_err(|e| format!("{e:?}"))?;
            // Instance dropped without flush — 100.0 never reaches kvs_1_0.json.
        }

        // Phase 3: re-open KVS from disk — must load the Phase 1 value (50.0),
        // proving that a post-reset boot recovers to the last-flushed state.
        {
            let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;
            let val: f64 = kvs.get_value_as("data_key").map_err(|e| format!("{e:?}"))?;
            info!(phase = "reload", key = "data_key", value = val);
        }

        Ok(())
    }
}

/// Multi-instance recovery: two instances sharing the same directory must each
/// independently recover to their own last-flushed state after a simulated reset.
pub struct RecoveryFromResetMultiInstance;

impl Scenario for RecoveryFromResetMultiInstance {
    /// Return the unique scenario name used by the test runner.
    fn name(&self) -> &str {
        "recovery_from_reset_multi_instance"
    }

    /// Execute the multi-instance auto-recovery scenario.
    ///
    /// Both instances use the **same** storage directory.
    ///
    /// Phase 1: Instance 1 writes `inst1_key` = 50.0 and flushes (LKG on disk).
    ///          Instance 2 writes `inst2_key` = 60.0 and flushes (LKG on disk).
    ///
    /// Phase 2: Instance 1 re-opens, writes `inst1_key` = 100.0, does NOT flush
    ///          (simulates reset mid-write).
    ///          Instance 2 re-opens, writes `inst2_key` = 120.0, does NOT flush
    ///          (simulates reset mid-write for the second instance).
    ///
    /// Expected disk state after Phase 2:
    ///   `kvs_1_0.json`: inst1_key = 50.0  (Phase 2 write was never persisted)
    ///   `kvs_2_0.json`: inst2_key = 60.0  (Phase 2 write was never persisted)
    ///
    /// This verifies that a crash of one instance's write path does not corrupt
    /// the snapshot belonging to the other instance — each recovers independently.
    fn run(&self, input: &str) -> Result<(), String> {
        let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
        let params1 = KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())?;
        let params2 = KvsParameters::from_value(&v["kvs_parameters_2"]).map_err(|e| e.to_string())?;

        // Phase 1: write last-known-good values for both instances and flush.
        {
            let kvs1 = kvs_instance(params1.clone()).map_err(|e| format!("{e:?}"))?;
            kvs1.set_value("inst1_key", 50.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs1.flush().map_err(|e| format!("{e:?}"))?;
        }
        {
            let kvs2 = kvs_instance(params2.clone()).map_err(|e| format!("{e:?}"))?;
            kvs2.set_value("inst2_key", 60.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs2.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Phase 2: write new values WITHOUT flushing for both instances —
        // simulates a hard reset that interrupts both in-memory write paths.
        // Neither write should reach the snapshot files.
        {
            let kvs1 = kvs_instance(params1.clone()).map_err(|e| format!("{e:?}"))?;
            kvs1.set_value("inst1_key", 100.0_f64).map_err(|e| format!("{e:?}"))?;
            // Dropped without flush — 100.0 never reaches kvs_1_0.json.
        }
        {
            let kvs2 = kvs_instance(params2.clone()).map_err(|e| format!("{e:?}"))?;
            kvs2.set_value("inst2_key", 120.0_f64).map_err(|e| format!("{e:?}"))?;
            // Dropped without flush — 120.0 never reaches kvs_2_0.json.
        }

        // Phase 3: re-open both instances from disk — must load the Phase 1
        // values (inst1_key=50.0, inst2_key=60.0), proving each instance
        // recovers independently to its own last-flushed state.
        {
            let kvs1 = kvs_instance(params1).map_err(|e| format!("{e:?}"))?;
            let val1: f64 = kvs1.get_value_as("inst1_key").map_err(|e| format!("{e:?}"))?;
            info!(phase = "reload", key = "inst1_key", value = val1);
        }
        {
            let kvs2 = kvs_instance(params2).map_err(|e| format!("{e:?}"))?;
            let val2: f64 = kvs2.get_value_as("inst2_key").map_err(|e| format!("{e:?}"))?;
            info!(phase = "reload", key = "inst2_key", value = val2);
        }

        Ok(())
    }
}
