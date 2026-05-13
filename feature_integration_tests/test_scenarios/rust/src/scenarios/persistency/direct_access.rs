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

/// Write 5 keys, flush, reopen (reload from disk), then read one specific key by name.
///
/// The targeted key access after reload verifies that individual key-value pairs
/// can be retrieved by name without iterating over the full storage — the
/// foundation of feat_req__persistency__direct_access.
///
/// Partially verifies feat_req__persistency__direct_access.
pub struct DirectAccess;

impl Scenario for DirectAccess {
    fn name(&self) -> &str {
        "direct_access"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;

        // Phase 1: write 5 keys and flush.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            for i in 0..5_u32 {
                kvs.set_value(format!("da_key_{i}"), i as f64 * 10.0)
                    .map_err(|e| format!("{e:?}"))?;
            }
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Phase 2: reopen (load from disk) and access one specific key directly.
        {
            let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;
            let val: f64 = kvs
                .get_value_as("da_key_3")
                .map_err(|e| format!("Direct access to da_key_3 failed: {e:?}"))?;
            info!(key = "da_key_3", value = val, phase = "direct_access");
        }

        Ok(())
    }
}

/// Request get_value for a key that was never written.
/// The KVS must return a KeyNotFound error — direct access semantics require
/// correct error reporting when no value exists.
///
/// Partially verifies feat_req__persistency__direct_access.
pub struct DirectAccessAbsentKey;

impl Scenario for DirectAccessAbsentKey {
    fn name(&self) -> &str {
        "direct_access_absent_key"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;
        let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

        // Key was never written — must return an error.
        let result = kvs.get_value_as::<f64>("nonexistent_key");
        match result {
            Err(_) => {
                info!(key = "nonexistent_key", result = "key_not_found", phase = "absent_key");
                Ok(())
            },
            Ok(_) => Err("Expected KeyNotFound error for nonexistent_key but got a value".to_string()),
        }
    }
}

/// Write a present key and flush.  On reload call key_exists() for the present
/// key (expect true) and for an absent key (expect false).
///
/// Partially verifies feat_req__persistency__direct_access.
pub struct DirectAccessKeyExists;

impl Scenario for DirectAccessKeyExists {
    fn name(&self) -> &str {
        "direct_access_key_exists"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;

        // Phase 1: write and flush.
        {
            let kvs = kvs_instance(params.clone()).map_err(|e| format!("{e:?}"))?;
            kvs.set_value("present_key", 7.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Phase 2: reload and check key_exists.
        {
            let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

            let exists_present = kvs
                .key_exists("present_key")
                .map_err(|e| format!("key_exists failed for present_key: {e:?}"))?;
            info!(key = "present_key", exists = exists_present, phase = "key_exists");

            let exists_absent = kvs
                .key_exists("absent_key")
                .map_err(|e| format!("key_exists failed for absent_key: {e:?}"))?;
            info!(key = "absent_key", exists = exists_absent, phase = "key_exists");
        }

        Ok(())
    }
}

/// Instance 1 has key_a; instance 2 has key_b.  After flush and reload, each
/// instance's key_exists() must confirm its own key present and the other's
/// key absent — direct access is instance-scoped.
///
/// Partially verifies feat_req__persistency__direct_access.
pub struct DirectAccessMultiInstance;

impl Scenario for DirectAccessMultiInstance {
    fn name(&self) -> &str {
        "direct_access_multi_instance"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let v: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
        let params1 = KvsParameters::from_value(&v["kvs_parameters_1"]).map_err(|e| e.to_string())?;
        let params2 = KvsParameters::from_value(&v["kvs_parameters_2"]).map_err(|e| e.to_string())?;

        // Phase 1: write and flush.
        {
            let kvs1 = kvs_instance(params1.clone()).map_err(|e| format!("{e:?}"))?;
            kvs1.set_value("key_a", 10.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs1.flush().map_err(|e| format!("{e:?}"))?;

            let kvs2 = kvs_instance(params2.clone()).map_err(|e| format!("{e:?}"))?;
            kvs2.set_value("key_b", 20.0_f64).map_err(|e| format!("{e:?}"))?;
            kvs2.flush().map_err(|e| format!("{e:?}"))?;
        }

        // Phase 2: reload and check cross-instance key_exists isolation.
        {
            let kvs1 = kvs_instance(params1).map_err(|e| format!("{e:?}"))?;
            let a_in_1 = kvs1.key_exists("key_a").map_err(|e| format!("{e:?}"))?;
            let b_in_1 = kvs1.key_exists("key_b").map_err(|e| format!("{e:?}"))?;
            info!(instance = "1", key = "key_a", exists = a_in_1, phase = "multi_instance");
            info!(instance = "1", key = "key_b", exists = b_in_1, phase = "multi_instance");

            let kvs2 = kvs_instance(params2).map_err(|e| format!("{e:?}"))?;
            let a_in_2 = kvs2.key_exists("key_a").map_err(|e| format!("{e:?}"))?;
            let b_in_2 = kvs2.key_exists("key_b").map_err(|e| format!("{e:?}"))?;
            info!(instance = "2", key = "key_a", exists = a_in_2, phase = "multi_instance");
            info!(instance = "2", key = "key_b", exists = b_in_2, phase = "multi_instance");
        }

        Ok(())
    }
}

/// Call key_exists() on a key written to the in-memory cache but never flushed.
///
/// If key_exists() only inspects the on-disk snapshot and ignores the cache,
/// it would return false for an unflushed key — a correctness bug invisible
/// to the flushed-path scenarios.  This scenario tests the cache-only path.
///
/// Partially verifies feat_req__persistency__direct_access.
pub struct DirectAccessKeyExistsUnflushed;

impl Scenario for DirectAccessKeyExistsUnflushed {
    fn name(&self) -> &str {
        "direct_access_key_exists_unflushed"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;
        let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

        // Write — but do NOT flush.
        kvs.set_value("unflushed_key", 3.0_f64).map_err(|e| format!("{e:?}"))?;

        // key_exists must find the key in the cache even without a flush.
        let exists_written = kvs
            .key_exists("unflushed_key")
            .map_err(|e| format!("key_exists failed for unflushed_key: {e:?}"))?;
        info!(
            key = "unflushed_key",
            exists = exists_written,
            phase = "unflushed_check"
        );

        // An absent key must still return false.
        let exists_absent = kvs
            .key_exists("never_written_key")
            .map_err(|e| format!("key_exists failed for never_written_key: {e:?}"))?;
        info!(
            key = "never_written_key",
            exists = exists_absent,
            phase = "unflushed_check"
        );

        Ok(())
    }
}
