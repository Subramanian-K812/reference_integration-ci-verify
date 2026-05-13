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
use test_scenarios_rust::scenario::Scenario;
use tracing::info;

/// Write a value via set_value then read it back immediately without flushing.
///
/// The returned value must equal the written value, proving the in-memory cache
/// services reads without requiring a round-trip to persistent storage.
/// The absence of flush is intentional: the requirement is about in-memory
/// access speed, not durability.
///
/// Partially verifies feat_req__persistency__cached_access.
pub struct CachedAccess;

impl Scenario for CachedAccess {
    fn name(&self) -> &str {
        "cached_access"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;
        let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

        // Write — does NOT flush.
        kvs.set_value("cache_key", 1.0_f64).map_err(|e| format!("{e:?}"))?;

        // Read immediately from the in-memory cache.
        let cached: f64 = kvs
            .get_value_as("cache_key")
            .map_err(|e| format!("get_value failed for cache_key: {e:?}"))?;
        info!(key = "cache_key", value = cached, phase = "cached_read");

        Ok(())
    }
}

/// Write V1, read it back; write V2 over the same key, read it back.
/// Both reads must return the current in-memory value with no stale data.
///
/// Partially verifies feat_req__persistency__cached_access.
pub struct CachedAccessUpdate;

impl Scenario for CachedAccessUpdate {
    fn name(&self) -> &str {
        "cached_access_update"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;
        let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

        // Write V1 and read back — no flush.
        kvs.set_value("update_key", 1.0_f64).map_err(|e| format!("{e:?}"))?;
        let v1: f64 = kvs.get_value_as("update_key").map_err(|e| format!("{e:?}"))?;
        info!(key = "update_key", value = v1, phase = "after_v1");

        // Overwrite with V2 and read back — cache must reflect the new value.
        kvs.set_value("update_key", 2.0_f64).map_err(|e| format!("{e:?}"))?;
        let v2: f64 = kvs.get_value_as("update_key").map_err(|e| format!("{e:?}"))?;
        info!(key = "update_key", value = v2, phase = "after_v2");

        Ok(())
    }
}

/// Write five distinct keys without flushing; read all five back immediately.
/// All must be accessible from the in-memory cache with correct values.
///
/// Partially verifies feat_req__persistency__cached_access.
pub struct CachedAccessMultiKey;

impl Scenario for CachedAccessMultiKey {
    fn name(&self) -> &str {
        "cached_access_multi_key"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;
        let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

        // Write five keys — no flush between writes, no flush at the end.
        let keys = ["mk_0", "mk_1", "mk_2", "mk_3", "mk_4"];
        let expected: Vec<f64> = (0..5).map(|i| i as f64 * 10.0).collect();

        for (key, &val) in keys.iter().zip(expected.iter()) {
            kvs.set_value(*key, val)
                .map_err(|e| format!("set_value failed for {key}: {e:?}"))?;
        }

        // Read all five back — must all come from the cache.
        for (key, &exp) in keys.iter().zip(expected.iter()) {
            let got: f64 = kvs
                .get_value_as(key)
                .map_err(|e| format!("get_value failed for {key}: {e:?}"))?;
            info!(key = *key, value = got, expected = exp, phase = "multi_key_read");
        }

        Ok(())
    }
}

/// Write a value, flush, then read it back from the same KVS handle (no reopen).
///
/// A flush must not evict or invalidate the in-memory cache.  If the
/// implementation clears the cache on flush, the subsequent get_value would
/// need a disk read; if that path is broken the read fails.  This scenario
/// verifies the cache remains valid after flush.
///
/// Partially verifies feat_req__persistency__cached_access.
pub struct CachedAccessAfterFlush;

impl Scenario for CachedAccessAfterFlush {
    fn name(&self) -> &str {
        "cached_access_after_flush"
    }

    fn run(&self, input: &str) -> Result<(), String> {
        let params = KvsParameters::parse_from_section(input, "kvs_parameters_1")?;
        let kvs = kvs_instance(params).map_err(|e| format!("{e:?}"))?;

        kvs.set_value("flush_key", 5.0_f64).map_err(|e| format!("{e:?}"))?;
        // Flush — cache must remain valid after this point.
        kvs.flush().map_err(|e| format!("{e:?}"))?;
        // Read from the same handle — must be served by cache, not a fresh disk read.
        let cached: f64 = kvs
            .get_value_as("flush_key")
            .map_err(|e| format!("get_value failed after flush: {e:?}"))?;
        info!(key = "flush_key", value = cached, phase = "after_flush");

        Ok(())
    }
}
