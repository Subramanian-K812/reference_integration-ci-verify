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

/// Write a single f64 key, flush, drop the KVS handle, reopen, and read back.
///
/// This tests the basic load-from-persistent-storage guarantee:
/// a value written and flushed in one KVS lifetime is readable in the next.
///
/// Partially verifies feat_req__persistency__load_data.
pub struct LoadData;

impl Scenario for LoadData {
    fn name(&self) -> &str {
        "load_data"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;

        // Phase 1: write and flush.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("data_key", 42.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Phase 2: reopen and read back from disk.
        {
            let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;
            let loaded: f64 = kvs
                .get_value_as("data_key")
                .map_err(|e| format!("Failed to load data_key after reload: {e:?}"))?;
            info!(key = "data_key", value = loaded, phase = "reload");
        }

        Ok(())
    }
}

/// Write and flush three values in succession (V1→V2→V3).
/// On reload, the KVS must return V3 (latest snapshot), not V1 or V2.
///
/// Partially verifies feat_req__persistency__load_data.
pub struct LoadDataAfterMultipleFlushes;

impl Scenario for LoadDataAfterMultipleFlushes {
    fn name(&self) -> &str {
        "load_data_after_multiple_flushes"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;

        // Phase 1: write V1, V2, V3 with separate flushes.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            for &v in &[10.0_f64, 20.0, 30.0] {
                kvs.set_value("data_key", v).map_err(|e| format!("{e:?}"))?;
                kvs.flush().map_err(|e| format!("{e:?}"))?;
            }
        }

        // Phase 2: reopen — must load the most recent snapshot (V3 = 30.0).
        {
            let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;
            let loaded: f64 = kvs
                .get_value_as("data_key")
                .map_err(|e| format!("Failed to load data_key after reload: {e:?}"))?;
            info!(key = "data_key", value = loaded, phase = "reload_latest");
        }

        Ok(())
    }
}

/// Instance 1 writes key_a, instance 2 writes key_b; both flush; both reopen.
/// Each instance must load only its own key — cross-instance snapshot isolation.
///
/// Partially verifies feat_req__persistency__load_data and
/// feat_req__persistency__store_data.
pub struct LoadDataMultiInstance;

impl Scenario for LoadDataMultiInstance {
    fn name(&self) -> &str {
        "load_data_multi_instance"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
        let params1 = KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())?;
        let params2 = KvsParameters::from_value(&v["kvs_parameters_2"]).map_err(|e| e.to_string())?;

        // Phase 1: write and flush each instance.
        {
            let kvs1 = kvs_instance(params1.clone()).map_err(|e| format!("{e:?}"))?;
            kvs1.set_value("key_a", 10.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs1.flush().map_err(|e| format!("{e:?}"))?;

            let kvs2 = kvs_instance(params2.clone()).map_err(|e| format!("{e:?}"))?;
            kvs2.set_value("key_b", 20.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs2.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Phase 2: reopen both and verify each loads only its own key.
        {
            let kvs1 = kvs_instance(params1).map_err(|e| format!("{e:?}"))?;
            let val_a: f64 = kvs1
                .get_value_as("key_a")
                .map_err(|e| format!("Instance 1 failed to load key_a: {e:?}"))?;
            info!(instance = "1", key = "key_a", value = val_a, phase = "reload");

            // key_b must NOT be visible in instance 1.
            if kvs1.get_value_as::<f64>("key_b").is_ok() {
                return Err("Isolation broken: instance 1 loaded key_b from instance 2 snapshot".to_string());
            }

            let kvs2 = kvs_instance(params2).map_err(|e| format!("{e:?}"))?;
            let val_b: f64 = kvs2
                .get_value_as("key_b")
                .map_err(|e| format!("Instance 2 failed to load key_b: {e:?}"))?;
            info!(instance = "2", key = "key_b", value = val_b, phase = "reload");

            // key_a must NOT be visible in instance 2.
            if kvs2.get_value_as::<f64>("key_a").is_ok() {
                return Err("Isolation broken: instance 2 loaded key_a from instance 1 snapshot".to_string());
            }
        }

        Ok(())
    }
}

/// Write 5 distinct keys in one session, flush once, drop the KVS handle, reopen.
/// All 5 keys must be loadable from the new session.
///
/// This closes the gap where only single-key load was verified.  A serializer
/// that silently drops all but the first key would still pass the basic
/// `load_data` scenario — this scenario catches that regression.
///
/// Partially verifies feat_req__persistency__load_data.
pub struct LoadDataMultipleKeys;

impl Scenario for LoadDataMultipleKeys {
    fn name(&self) -> &str {
        "load_data_multiple_keys"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;

        // Phase 1: write 5 keys and flush once.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            for i in 0..5_u32 {
                kvs.set_value(format!("mk_key_{i}"), i as f64 * 10.0)
                    .map_err(|e| format!("{e:?}"))?;
            }
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Phase 2: reopen and verify every key is present.
        {
            let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;
            for i in 0..5_u32 {
                let key = format!("mk_key_{i}");
                let val: f64 = kvs
                    .get_value_as(&key)
                    .map_err(|e| format!("Failed to load {key}: {e:?}"))?;
                info!(key = key.as_str(), value = val, phase = "multi_key_reload");
            }
        }

        Ok(())
    }
}
