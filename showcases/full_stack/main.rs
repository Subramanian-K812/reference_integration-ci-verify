// *******************************************************************************
// Copyright (c) 2026 Qorix GmbH
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

//! Full-stack showcase combining SCORE Orchestration and Persistency modules.
//!
//! This showcase demonstrates:
//! - Kyron async runtime for safe multi-threaded task execution
//! - Orchestration design with sequential and timer-based actions
//! - KVS-backed state persistence written on shutdown
//!
//! Architecture
//! ============
//! The binary runs two concurrent programs inside a Kyron runtime:
//!
//!   1. `SensorProcessingProgram` — timer-triggered, simulates reading sensor
//!      data and accumulating a counter into a shared state.
//!   2. `ShutdownProgram` — executes once, persists the accumulated counter
//!      to a KVS JSON snapshot and reports final statistics.

use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use kyron::runtime::*;
use kyron_foundation::prelude::*;
use logging_tracing::LogAndTraceBuilder;
use orchestration::{
    actions::{invoke::Invoke, sequence::SequenceBuilder},
    api::{design::Design, Orchestration},
    common::DesignConfig,
};
use rust_kvs::json_backend::JsonBackendBuilder;
use rust_kvs::prelude::*;

/// Number of sensor processing cycles before shutdown.
const CYCLE_COUNT: usize = 5;
/// Directory used by the JSON KVS backend.
const KVS_WORKING_DIR: &str = "/tmp/score_full_stack_showcase";
/// Event name triggering the sensor processing action.
const SENSOR_TICK: &str = "SensorTickEvent";

/// Shared mutable counter simulating accumulated sensor readings.
type SharedCounter = Arc<Mutex<u32>>;

/// Creates the sensor-processing orchestration design.
///
/// Registers a timer-triggered event and a sequential run action that
/// increments the shared counter on every tick.
fn sensor_design(counter: SharedCounter) -> Result<Design, CommonErrors> {
    let mut design = Design::new("SensorDesign".into(), DesignConfig::default());
    design.register_event(SENSOR_TICK.into())?;

    let counter_clone = counter.clone();
    let process_tag = design.register_invoke_async("process_sensor".into(), move || {
        let counter = counter_clone.clone();
        async move {
            let mut guard = counter.lock().expect("lock poisoned");
            *guard += 1;
            info!("Sensor tick #{}", *guard);
            Ok(())
        }
    })?;

    design.add_program(
        "SensorProcessingProgram",
        move |design_instance, builder| {
            builder.with_run_action(
                SequenceBuilder::new()
                    .with_step(orchestration::actions::sync::SyncBuilder::from_design(
                        SENSOR_TICK,
                        design_instance,
                    ))
                    .with_step(Invoke::from_tag(&process_tag, design_instance.config()))
                    .build(),
            );
            Ok(())
        },
    );

    Ok(design)
}

/// Creates the shutdown design that persists the counter to a KVS snapshot.
///
/// Triggers once on shutdown to flush the accumulated counter value and
/// print the path of the persisted snapshot file.
fn shutdown_design(counter: SharedCounter) -> Result<Design, CommonErrors> {
    let mut design = Design::new("ShutdownDesign".into(), DesignConfig::default());
    design.register_event("ShutdownEvent".into())?;

    let persist_tag = design.register_invoke_async("persist_counter".into(), move || {
        let counter = counter.clone();
        async move {
            let final_count = *counter.lock().expect("lock poisoned");
            info!("Persisting final counter value: {}", final_count);

            let backend = JsonBackendBuilder::new()
                .working_dir(PathBuf::from(KVS_WORKING_DIR))
                .build();
            let kvs = KvsBuilder::new(InstanceId(2))
                .backend(Box::new(backend))
                .kvs_load(KvsLoad::Optional)
                .build()
                .expect("Failed to build KVS");

            kvs.set_value("sensor_cycles", f64::from(final_count))
                .expect("KVS set_value failed");
            kvs.flush().expect("KVS flush failed");

            info!("KVS state flushed to: {}", KVS_WORKING_DIR);
            Ok(())
        }
    })?;

    design.add_program("ShutdownProgram", move |design_instance, builder| {
        builder.with_run_action(
            SequenceBuilder::new()
                .with_step(orchestration::actions::sync::SyncBuilder::from_design(
                    "ShutdownEvent",
                    design_instance,
                ))
                .with_step(Invoke::from_tag(&persist_tag, design_instance.config()))
                .build(),
        );
        Ok(())
    });

    Ok(design)
}

/// Entry point for the full-stack showcase.
fn main() {
    let _logger = LogAndTraceBuilder::new()
        .global_log_level(logging_tracing::Level::INFO)
        .enable_logging(true)
        .build();

    info!("Full-stack showcase starting");

    // Shared state between orchestration designs
    let counter: SharedCounter = Arc::new(Mutex::new(0));

    // Build orchestration
    let mut orch = Orchestration::new()
        .add_design(sensor_design(counter.clone()).expect("Failed to build SensorDesign"))
        .add_design(shutdown_design(counter.clone()).expect("Failed to build ShutdownDesign"))
        .design_done();

    orch.get_deployment_mut()
        .bind_events_as_timer(&[SENSOR_TICK.into()], Duration::from_millis(200))
        .expect("Failed to bind timer event");
    orch.get_deployment_mut()
        .bind_events_as_local(&["ShutdownEvent".into()])
        .expect("Failed to bind local event");

    let mut program_manager = orch.into_program_manager().unwrap();
    let mut programs = program_manager.get_programs();

    // Kyron runtime
    let (builder, _) = kyron::runtime::RuntimeBuilder::new().with_engine(
        ExecutionEngineBuilder::new()
            .task_queue_size(256)
            .workers(2),
    );
    let mut runtime = builder.build().unwrap();

    runtime.block_on(async move {
        let mut sensor_program = programs.pop().unwrap();
        let mut shutdown_program = programs.pop().unwrap();

        let h_sensor = kyron::spawn(async move {
            let _ = sensor_program.run_n(CYCLE_COUNT).await;
        });

        let h_shutdown = kyron::spawn(async move {
            let _ = shutdown_program.run_n(1).await;
        });

        let _ = h_sensor.await;
        let _ = h_shutdown.await;

        info!("Full-stack showcase finished");
    });
}
