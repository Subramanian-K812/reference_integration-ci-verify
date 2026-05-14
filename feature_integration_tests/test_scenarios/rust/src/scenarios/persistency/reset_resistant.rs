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

//! Scenarios verifying `feat_req__persistency__reset_resistant`.
//!
//! Two distinct scenarios are provided:
//!
//! 1. `reset_resistant` — single instance: after two flushes the previous
//!    snapshot is preserved on disk alongside the new one.
//!
//! 2. `reset_resistant_multi_instance` — two instances sharing the same
//!    directory: snapshot rotation for instance 1 must not corrupt or
//!    overwrite snapshot files that belong to instance 2.

use crate::internals::persistency::{kvs_instance::kvs_instance, kvs_parameters::KvsParameters};
use rust_kvs::prelude::KvsApi;
use serde_json::Value;
use test_scenarios_rust::scenario::Scenario;
use tracing::info;

/// Single-instance reset-resistance: previous snapshot is preserved after rotation.
pub struct ResetResistant;

impl Scenario for ResetResistant {
    /// Return the unique scenario name used by the test runner.
    fn name(&self) -> &str {
        "reset_resistant"
    }

    /// Execute the reset-resistant storage scenario.
    ///
    /// Phase 1: Create KVS, write `data_key` = 50.0, flush.
    ///          This produces the first snapshot (`kvs_1_0.json`).
    ///
    /// Phase 2: Re-open KVS, write `data_key` = 100.0, flush.
    ///          Snapshot rotation occurs: the previous snapshot is moved to
    ///          `kvs_1_1.json` and the new snapshot becomes `kvs_1_0.json`.
    ///
    /// The Python test verifies both snapshot files exist and contain the
    /// expected values, proving that the old state was preserved.
    fn run(&self, input: &str) -> Result<(), String> {
        let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
        let params = KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())?;

        // Phase 1: write initial value and flush to create the first snapshot.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("data_key", 50.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Phase 2: re-open, write updated value and flush — triggers rotation.
        // kvs_1_1.json (value=50.0) and kvs_1_0.json (value=100.0) both exist.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("data_key", 100.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.flush().map_err(|e| format!("{e:?}"))?;

            let current_val: f64 = kvs.get_value_as("data_key").map_err(|e| format!("{e:?}"))?;
            info!(key = "data_key", value = current_val);
        }

        // Phase 3: simulate an interruption — write new value WITHOUT flushing.
        // Simulates a hard reset mid-write after the rotation.
        // The existing snapshots (kvs_1_0.json=100.0, kvs_1_1.json=50.0) must
        // remain intact; the un-flushed write must not corrupt either file.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("data_key", 150.0_f64).map_err(|e| format!("{e:?}"))?;
            // Instance dropped without flush — 150.0 never reaches disk.
        }

        // Phase 4: re-open KVS from disk after the simulated interruption.
        // Must load the last successfully flushed value (100.0 from Phase 2),
        // proving that the previous snapshot survives the interrupted write.
        {
            let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;
            let val: f64 = kvs.get_value_as("data_key").map_err(|e| format!("{e:?}"))?;
            info!(phase = "after_interruption", key = "data_key", value = val);
        }

        Ok(())
    }
}

/// Multi-instance reset-resistance: snapshot files for two instances sharing
/// the same directory must not interfere with each other during rotation.
pub struct ResetResistantMultiInstance;

impl Scenario for ResetResistantMultiInstance {
    /// Return the unique scenario name used by the test runner.
    fn name(&self) -> &str {
        "reset_resistant_multi_instance"
    }

    /// Execute the multi-instance snapshot-isolation scenario.
    ///
    /// Both instance 1 (`kvs_parameters_1`) and instance 2 (`kvs_parameters_2`)
    /// use the **same** storage directory.  Each instance undergoes two flushes
    /// (triggering snapshot rotation) independently.
    ///
    /// After rotation:
    /// - `kvs_1_0.json` = instance-1 new value, `kvs_1_1.json` = instance-1 old value
    /// - `kvs_2_0.json` = instance-2 new value, `kvs_2_1.json` = instance-2 old value
    ///
    /// The Python test checks all four snapshot files and confirms that the
    /// values are correct for each instance — no cross-contamination.
    fn run(&self, input: &str) -> Result<(), String> {
        let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
        let params1 = KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())?;
        let params2 = KvsParameters::from_value(&v["kvs_parameters_2"]).map_err(|e| e.to_string())?;

        // Instance 1 — Phase 1: write inst1_key = 10.0, flush.
        {
            let kvs = kvs_instance(params1.clone()).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("inst1_key", 10.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Instance 2 — Phase 1: write inst2_key = 20.0, flush.
        {
            let kvs = kvs_instance(params2.clone()).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("inst2_key", 20.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Instance 1 — Phase 2: write inst1_key = 110.0, flush (triggers rotation).
        {
            let kvs = kvs_instance(params1).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("inst1_key", 110.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Instance 2 — Phase 2: write inst2_key = 220.0, flush (triggers rotation).
        {
            let kvs = kvs_instance(params2).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("inst2_key", 220.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        Ok(())
    }
}
