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

use crate::internals::persistency::{kvs_instance::kvs_instance, kvs_parameters::KvsParameters};
use rust_kvs::prelude::KvsApi;
use serde_json::Value;
use test_scenarios_rust::scenario::Scenario;
use tracing::info;

/// Write 10 keys and call flush() once.
///
/// Python verifies that exactly one snapshot file and one hash file were
/// created — not one per key.  This proves that a single flush() batches all
/// pending writes into one storage operation, minimising write amplification.
///
/// Partially verifies feat_req__persistency__write_amplification.
pub struct WriteAmplification;

impl Scenario for WriteAmplification {
    fn name(&self) -> &str {
        "write_amplification"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;
        let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

        // Write 10 keys — all pending in the in-memory cache.
        for i in 0..10_u32 {
            kvs.set_value(format!("wa_key_{i}"), i as f64)
                .map_err(|e| format!("{e:?}"))?;
        }

        // Single flush — must produce exactly 1 snapshot + 1 hash file.
        kvs.flush().map_err(|e| format!("{e:?}"))?;

        // Log the snapshot count so Python can assert it equals 1.
        let count = kvs.snapshot_count();
        info!(snapshot_count = count, phase = "after_single_flush");

        Ok(())
    }
}

/// Write keys A, B, C in one flush.
/// Python reads the snapshot and confirms all three keys are present in a single
/// file — the entire state is captured atomically in one storage write.
///
/// Partially verifies feat_req__persistency__write_amplification.
pub struct WriteAmplificationSingleFlushCoversAllKeys;

impl Scenario for WriteAmplificationSingleFlushCoversAllKeys {
    fn name(&self) -> &str {
        "write_amplification_single_flush_covers_all_keys"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;
        let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

        kvs.set_value("wa_key_a", 1.0_f64).map_err(|e| format!("{e:?}"))?;
        kvs.set_value("wa_key_b", 2.0_f64).map_err(|e| format!("{e:?}"))?;
        kvs.set_value("wa_key_c", 3.0_f64).map_err(|e| format!("{e:?}"))?;

        // One flush must capture all three keys in a single file.
        kvs.flush().map_err(|e| format!("{e:?}"))?;

        Ok(())
    }
}

/// Instance 1 writes key_a and flushes; instance 2 writes key_b and flushes.
///
/// Python verifies that kvs_1_0.json contains ONLY key_a and kvs_2_0.json
/// contains ONLY key_b.  This proves that each flush is instance-scoped:
/// no cross-contamination of snapshots, and no redundant writes to the
/// other instance's storage file.
///
/// Partially verifies feat_req__persistency__write_amplification.
pub struct WriteAmplificationMultiInstance;

impl Scenario for WriteAmplificationMultiInstance {
    fn name(&self) -> &str {
        "write_amplification_multi_instance"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
        let params1 = KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())?;
        let params2 = KvsParameters::from_value(&v["kvs_parameters_2"]).map_err(|e| e.to_string())?;

        let kvs1 = kvs_instance(params1).map_err(|e| format!("{e:?}"))?;
        kvs1.set_value("wa_key_a", 1.0_f64).map_err(|e| format!("{e:?}"))?;
        kvs1.flush().map_err(|e| format!("{e:?}"))?;

        let kvs2 = kvs_instance(params2).map_err(|e| format!("{e:?}"))?;
        kvs2.set_value("wa_key_b", 2.0_f64).map_err(|e| format!("{e:?}"))?;
        kvs2.flush().map_err(|e| format!("{e:?}"))?;

        Ok(())
    }
}

/// Overwrite the same key 3 times without flushing, then flush once.
///
/// The snapshot must contain the key exactly once with the latest value (V3=3.0).
/// If the serializer wrote one entry per set_value call, that would be write
/// amplification.  This verifies that the cache deduplicates pending writes
/// per key before serializing.
///
/// Partially verifies feat_req__persistency__write_amplification.
pub struct WriteAmplificationOverwriteSameKey;

impl Scenario for WriteAmplificationOverwriteSameKey {
    fn name(&self) -> &str {
        "write_amplification_overwrite_same_key"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;
        let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

        // Overwrite the same key three times — cache must deduplicate.
        kvs.set_value("ow_key", 1.0_f64).map_err(|e| format!("{e:?}"))?;
        kvs.set_value("ow_key", 2.0_f64).map_err(|e| format!("{e:?}"))?;
        kvs.set_value("ow_key", 3.0_f64).map_err(|e| format!("{e:?}"))?;
        // Single flush — must produce 1 snapshot containing ow_key=3.0 exactly once.
        kvs.flush().map_err(|e| format!("{e:?}"))?;

        // Log the final value so Python can cross-check against the snapshot.
        let final_val: f64 = kvs
            .get_value_as("ow_key")
            .map_err(|e| format!("get_value failed after flush: {e:?}"))?;
        info!(key = "ow_key", value = final_val, phase = "after_overwrite_flush");

        Ok(())
    }
}

/// Perform two separate write+flush cycles with snapshot_max_count=2.
///
/// After each flush the snapshot count increments by exactly one.  After 2
/// flushes there must be exactly 2 snapshot files on disk — one per flush, not
/// one per key-write (which would be amplification).
///
/// Partially verifies feat_req__persistency__write_amplification.
pub struct WriteAmplificationMultipleFlushes;

impl Scenario for WriteAmplificationMultipleFlushes {
    fn name(&self) -> &str {
        "write_amplification_multiple_flushes"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;
        let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

        // First write + flush.
        kvs.set_value("mf_key_1", 1.0_f64).map_err(|e| format!("{e:?}"))?;
        kvs.flush().map_err(|e| format!("{e:?}"))?;
        let count1 = kvs.snapshot_count();
        info!(snapshot_count = count1, phase = "after_flush_1");

        // Second write + flush.
        kvs.set_value("mf_key_2", 2.0_f64).map_err(|e| format!("{e:?}"))?;
        kvs.flush().map_err(|e| format!("{e:?}"))?;
        let count2 = kvs.snapshot_count();
        info!(snapshot_count = count2, phase = "after_flush_2");

        Ok(())
    }
}
