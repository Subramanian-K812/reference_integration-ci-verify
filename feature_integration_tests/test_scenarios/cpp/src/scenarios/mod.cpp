// *******************************************************************************
// Copyright (c) 2026 Contributors to the Eclipse Foundation
//
// See the NOTICE file(s) distributed with this work for additional
// information regarding copyright ownership.
//
// This program and the accompanying materials are made available under the
// terms of the Apache License Version 2.0 which is available at
// https://www.apache.org/licenses/LICENSE-2.0
//
// SPDX-License-Identifier: Apache-2.0
// *******************************************************************************

#include <scenario.hpp>

#include <vector>

Scenario::Ptr make_multiple_kvs_per_app_scenario();
Scenario::Ptr make_default_values_ignored_scenario();
Scenario::Ptr make_reset_to_default_scenario();
Scenario::Ptr make_utf8_defaults_scenario();
Scenario::Ptr make_utf8_default_value_get_scenario();
Scenario::Ptr make_multi_instance_isolation_scenario();
Scenario::Ptr make_load_data_scenario();
Scenario::Ptr make_load_data_after_multiple_flushes_scenario();
Scenario::Ptr make_load_data_multi_instance_scenario();
Scenario::Ptr make_load_data_multiple_keys_scenario();
Scenario::Ptr make_cached_access_scenario();
Scenario::Ptr make_cached_access_update_scenario();
Scenario::Ptr make_cached_access_multi_key_scenario();
Scenario::Ptr make_cached_access_after_flush_scenario();
Scenario::Ptr make_direct_access_scenario();
Scenario::Ptr make_direct_access_absent_key_scenario();
Scenario::Ptr make_direct_access_key_exists_scenario();
Scenario::Ptr make_direct_access_multi_instance_scenario();
Scenario::Ptr make_direct_access_key_exists_unflushed_scenario();
Scenario::Ptr make_write_amplification_scenario();
Scenario::Ptr make_write_amplification_single_flush_covers_all_keys_scenario();
Scenario::Ptr make_write_amplification_multi_instance_scenario();
Scenario::Ptr make_write_amplification_overwrite_same_key_scenario();
Scenario::Ptr make_write_amplification_multiple_flushes_scenario();
ScenarioGroup::Ptr supported_datatypes_group();
ScenarioGroup::Ptr default_values_group();

ScenarioGroup::Ptr persistency_scenario_group() {
    return std::make_shared<ScenarioGroupImpl>(
        "persistency",
        std::vector<Scenario::Ptr>{
            make_multiple_kvs_per_app_scenario(),
            make_default_values_ignored_scenario(),
            make_reset_to_default_scenario(),
            make_utf8_defaults_scenario(),
            make_utf8_default_value_get_scenario(),
            make_multi_instance_isolation_scenario(),
            make_load_data_scenario(),
            make_load_data_after_multiple_flushes_scenario(),
            make_load_data_multi_instance_scenario(),
            make_load_data_multiple_keys_scenario(),
            make_cached_access_scenario(),
            make_cached_access_update_scenario(),
            make_cached_access_multi_key_scenario(),
            make_cached_access_after_flush_scenario(),
            make_direct_access_scenario(),
            make_direct_access_absent_key_scenario(),
            make_direct_access_key_exists_scenario(),
            make_direct_access_multi_instance_scenario(),
            make_direct_access_key_exists_unflushed_scenario(),
            make_write_amplification_scenario(),
            make_write_amplification_single_flush_covers_all_keys_scenario(),
            make_write_amplification_multi_instance_scenario(),
            make_write_amplification_overwrite_same_key_scenario(),
            make_write_amplification_multiple_flushes_scenario(),
        },
        std::vector<ScenarioGroup::Ptr>{supported_datatypes_group(), default_values_group()});
}

ScenarioGroup::Ptr root_scenario_group() {
    return std::make_shared<ScenarioGroupImpl>(
        "root",
        std::vector<Scenario::Ptr>{},
        std::vector<ScenarioGroup::Ptr>{persistency_scenario_group()});
}
