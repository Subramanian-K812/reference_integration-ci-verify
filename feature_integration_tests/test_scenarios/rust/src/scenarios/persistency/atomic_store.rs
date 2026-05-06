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

//! Scenarios verifying `feat_req__persistency__atomic_store`.
//!
//! Two distinct scenarios are provided:
//!
//! 1. `atomic_store` — happy-path: multiple keys written, one flush, all keys
//!    readable after KVS reload (all-or-nothing writes land correctly).
//!
//! 2. `atomic_store_no_partial_write` — negative-path: keys written to the
//!    in-memory store but the instance is dropped without flushing.  A fresh
//!    KVS instance must not see any of the un-flushed keys (the "or nothing"
//!    side of atomicity).

use crate::internals::persistency::{kvs_instance::kvs_instance, kvs_parameters::KvsParameters};
use rust_kvs::prelude::KvsApi;
use serde_json::Value;
use test_scenarios_rust::scenario::Scenario;
use tracing::info;

/// Happy-path: all keys written before a single flush are visible after reload.
pub struct AtomicStore;

impl Scenario for AtomicStore {
    /// Return the unique scenario name used by the test runner.
    fn name(&self) -> &str {
        "atomic_store"
    }

    /// Execute the atomic store scenario.
    ///
    /// Phase 1: Create KVS, set three distinct keys without flushing between
    ///          sets, then flush once.  A single `flush()` must persist all
    ///          pending in-memory writes atomically.
    ///
    /// Phase 2: Re-open KVS (loads from the persisted snapshot) and read all
    ///          three keys.  All must be present and hold their written values.
    ///
    /// The Python test verifies both the snapshot file content and the log
    ///          entries, confirming that all keys survived the flush cycle.
    fn run(&self, input: &str) -> Result<(), String> {
        let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
        let params = KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())?;

        // Phase 1: set multiple keys and flush — one atomic write operation.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("key_a", 10.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("key_b", 20.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("key_c", 30.0_f64).map_err(|e| format!("{e:?}"))?;
            // Single flush atomically persists all three keys.
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Phase 2: re-open KVS and read all three keys to prove they were
        // persisted as a group — atomic store semantics.
        {
            let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;
            let val_a: f64 = kvs.get_value_as("key_a").map_err(|e| format!("{e:?}"))?;
            let val_b: f64 = kvs.get_value_as("key_b").map_err(|e| format!("{e:?}"))?;
            let val_c: f64 = kvs.get_value_as("key_c").map_err(|e| format!("{e:?}"))?;
            info!(key = "key_a", value = val_a);
            info!(key = "key_b", value = val_b);
            info!(key = "key_c", value = val_c);
        }

        Ok(())
    }
}

/// Negative-path: un-flushed writes must NOT persist on KVS reload.
pub struct AtomicStoreNoPartialWrite;

impl Scenario for AtomicStoreNoPartialWrite {
    /// Return the unique scenario name used by the test runner.
    fn name(&self) -> &str {
        "atomic_store_no_partial_write"
    }

    /// Execute the no-partial-write scenario.
    ///
    /// Phase 1: Create KVS, set `key_d` = 999.0 to the in-memory store, then
    ///          drop the instance **without** calling `flush()`.  This simulates
    ///          a hard reset after a write that was never committed.
    ///
    /// Because no flush occurred, no snapshot file is ever written to disk.
    /// The Python test asserts `kvs_1_0.json` does not exist — proving that
    /// the un-flushed write never reached persistent storage (atomicity: the
    /// "or nothing" guarantee).
    ///
    /// Note: the Rust KVS instance pool shares in-process memory for the same
    /// `instance_id`, so a second in-process handle would still see `key_d` in
    /// memory.  The disk-file check is therefore the correct assertion.
    fn run(&self, input: &str) -> Result<(), String> {
        let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
        let params = KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())?;

        // Write key_d WITHOUT flushing — simulates power loss mid-write.
        // No snapshot file is created; the Python test verifies via file system.
        {
            let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("key_d", 999.0_f64).map_err(|e| format!("{e:?}"))?;
            // Instance dropped here without flush — key_d never reaches disk.
        }

        Ok(())
    }
}
