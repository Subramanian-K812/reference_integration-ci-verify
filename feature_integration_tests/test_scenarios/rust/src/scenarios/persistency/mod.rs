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
mod cached_access;
mod default_values;
mod default_values_ignored;
mod direct_access;
mod load_data;
mod multi_instance_isolation;
mod multiple_kvs_per_app;
mod reset_to_default;
mod supported_datatypes;
mod utf8_defaults;
mod write_amplification;

use cached_access::{CachedAccess, CachedAccessAfterFlush, CachedAccessMultiKey, CachedAccessUpdate};
use default_values::default_values_group;
use default_values_ignored::DefaultValuesIgnored;
use direct_access::{
    DirectAccess, DirectAccessAbsentKey, DirectAccessKeyExists, DirectAccessKeyExistsUnflushed,
    DirectAccessMultiInstance,
};
use load_data::{LoadData, LoadDataAfterMultipleFlushes, LoadDataMultiInstance, LoadDataMultipleKeys};
use multi_instance_isolation::MultiInstanceIsolation;
use multiple_kvs_per_app::MultipleKvsPerApp;
use reset_to_default::ResetToDefault;
use supported_datatypes::supported_datatypes_group;
use test_scenarios_rust::scenario::{ScenarioGroup, ScenarioGroupImpl};
use utf8_defaults::Utf8DefaultValueGet;
use utf8_defaults::Utf8Defaults;
use write_amplification::{
    WriteAmplification, WriteAmplificationMultiInstance, WriteAmplificationMultipleFlushes,
    WriteAmplificationOverwriteSameKey, WriteAmplificationSingleFlushCoversAllKeys,
};

pub fn persistency_group() -> Box<dyn ScenarioGroup> {
    Box::new(ScenarioGroupImpl::new(
        "persistency",
        vec![
            Box::new(MultipleKvsPerApp),
            Box::new(DefaultValuesIgnored),
            Box::new(ResetToDefault),
            Box::new(Utf8Defaults),
            Box::new(Utf8DefaultValueGet),
            Box::new(MultiInstanceIsolation),
            Box::new(LoadData),
            Box::new(LoadDataAfterMultipleFlushes),
            Box::new(LoadDataMultiInstance),
            Box::new(LoadDataMultipleKeys),
            Box::new(CachedAccess),
            Box::new(CachedAccessUpdate),
            Box::new(CachedAccessMultiKey),
            Box::new(CachedAccessAfterFlush),
            Box::new(DirectAccess),
            Box::new(DirectAccessAbsentKey),
            Box::new(DirectAccessKeyExists),
            Box::new(DirectAccessMultiInstance),
            Box::new(DirectAccessKeyExistsUnflushed),
            Box::new(WriteAmplification),
            Box::new(WriteAmplificationSingleFlushCoversAllKeys),
            Box::new(WriteAmplificationMultiInstance),
            Box::new(WriteAmplificationOverwriteSameKey),
            Box::new(WriteAmplificationMultipleFlushes),
        ],
        vec![supported_datatypes_group(), default_values_group()],
    ))
}
