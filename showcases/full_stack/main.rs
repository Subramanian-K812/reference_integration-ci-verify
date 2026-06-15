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

//! Full-stack showcase combining SCORE Orchestration, Persistency and
//! Lifecycle health-monitoring modules.
//!
//! This showcase demonstrates:
//! - Kyron async runtime for safe multi-threaded task execution
//! - Orchestration design with a timer-triggered run action
//! - KVS-backed state persistence written from the program's stop action
//! - Lifecycle alive deadline supervision reporting health checkpoints on a
//!   dedicated OS thread
//!
//! Architecture
//! ============
//! A single `SensorProcessingProgram` runs inside a Kyron runtime:
//!
//!   - Its run action is timer-triggered and, on every tick, increments a
//!     shared counter that simulates accumulated sensor readings.
//!   - Its stop action runs once during shutdown (after the configured number
//!     of cycles) and persists the accumulated counter to a KVS JSON snapshot.
//!
//! In parallel, a supervision thread owns a lifecycle `HealthMonitor` with an
//! alive deadline monitor and brackets each 100 ms supervision cycle with a
//! deadline start/stop checkpoint.
//!
//! When the process is launched by the lifecycle launch manager (detected via
//! the `IDENTIFIER` environment variable the launch manager injects), the
//! health monitor connects to the supervisor and the process reports its
//! RUNNING execution state. When run standalone (e.g. via the showcase CLI),
//! deadline checkpoints are still recorded locally but no supervisor
//! connection is attempted, so the showcase works on every configuration.
//!
//! Persisting from the stop action (rather than a separate event-driven
//! program) mirrors the robust shutdown pattern used by the
//! `orchestration_persistency` showcase and guarantees the snapshot is written
//! exactly once when the program terminates.

use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use health_monitoring_lib::{
    deadline::DeadlineMonitorBuilder, DeadlineTag, HealthMonitorBuilder, MonitorTag, TimeRange,
};
use kyron::runtime::*;
use kyron_foundation::prelude::*;
use logging_tracing::LogAndTraceBuilder;
use orchestration::{
    actions::{invoke::Invoke, sequence::SequenceBuilder, sync::SyncBuilder},
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
/// Health monitor tag owning the alive deadline supervision.
const MONITOR_TAG: &str = "full_stack_monitor";
/// Deadline monitor tag used for alive supervision reporting.
const DEADLINE_TAG: &str = "full_stack_deadline";
/// Supervision cycle period; each cycle is bracketed by a deadline checkpoint.
const SUPERVISION_CYCLE: Duration = Duration::from_millis(100);

/// Shared mutable counter simulating accumulated sensor readings.
type SharedCounter = Arc<Mutex<u32>>;

/// Creates the sensor-processing orchestration design.
///
/// The program's run action is timer-triggered and increments the shared
/// counter on every tick; its stop action persists the accumulated counter to
/// a KVS JSON snapshot exactly once during shutdown.
fn sensor_design(counter: SharedCounter) -> Result<Design, CommonErrors> {
    let mut design = Design::new("FullStackDesign".into(), DesignConfig::default());
    design.register_event(SENSOR_TICK.into())?;

    let counter_for_run = counter.clone();
    let process_tag = design.register_invoke_async("process_sensor".into(), move || {
        let counter = counter_for_run.clone();
        async move {
            let mut guard = counter.lock().expect("lock poisoned");
            *guard += 1;
            info!("Sensor tick #{}", *guard);
            Ok(())
        }
    })?;

    let counter_for_stop = counter;
    let persist_tag = design.register_invoke_async("persist_counter".into(), move || {
        let counter = counter_for_stop.clone();
        async move {
            let final_count = *counter.lock().expect("lock poisoned");
            info!("Persisting final counter value: {}", final_count);

            // The JSON backend writes into the working directory but does not
            // create it, so ensure it exists before building the KVS instance.
            std::fs::create_dir_all(KVS_WORKING_DIR).expect("Failed to create KVS working dir");

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

    design.add_program("SensorProcessingProgram", move |design_instance, builder| {
        builder
            .with_run_action(
                SequenceBuilder::new()
                    .with_step(SyncBuilder::from_design(SENSOR_TICK, design_instance))
                    .with_step(Invoke::from_tag(&process_tag, design_instance.config()))
                    .build(),
            )
            .with_stop_action(
                Invoke::from_tag(&persist_tag, design_instance.config()),
                Duration::from_secs(2),
            );
        Ok(())
    });

    Ok(design)
}

/// Runs lifecycle alive deadline supervision until `stop` becomes true.
///
/// Owns the `HealthMonitor` for its whole lifetime (the monitor types stay on
/// this thread). Every supervision cycle acquires the alive deadline, holds it
/// for the cycle period and stops it again, recording an alive checkpoint that
/// must complete within the configured time range.
///
/// `supervised` selects whether the monitor connects to the lifecycle
/// supervisor: this requires the launch-manager environment and would panic
/// without it, so it is only enabled when running under the launch manager.
fn run_alive_supervision(stop: Arc<AtomicBool>, supervised: bool) {
    let mut hm = HealthMonitorBuilder::new()
        .add_deadline_monitor(
            MonitorTag::from(MONITOR_TAG),
            DeadlineMonitorBuilder::new().add_deadline(
                DeadlineTag::from(DEADLINE_TAG),
                TimeRange::new(Duration::from_millis(50), Duration::from_millis(500)),
            ),
        )
        .with_supervisor_api_cycle(Duration::from_millis(50))
        .with_internal_processing_cycle(Duration::from_millis(50))
        .build()
        .expect("Failed to build HealthMonitor");

    let monitor = hm
        .get_deadline_monitor(MonitorTag::from(MONITOR_TAG))
        .expect("Failed to get deadline monitor");

    if supervised {
        // Connects to the lifecycle supervisor and reports the RUNNING
        // execution state; both need the launch-manager environment.
        hm.start();
        if lifecycle_client_rs::report_execution_state_running() {
            info!("Reported RUNNING execution state to the launch manager");
        } else {
            info!("Failed to report RUNNING execution state to the launch manager");
        }
    } else {
        info!("Running standalone: deadline checkpoints are recorded locally only");
    }

    let mut checkpoints: u32 = 0;
    while !stop.load(Ordering::Relaxed) {
        let mut deadline = monitor
            .get_deadline(DeadlineTag::from(DEADLINE_TAG))
            .expect("Failed to get deadline");

        match deadline.start() {
            Ok(handle) => {
                std::thread::sleep(SUPERVISION_CYCLE);
                handle.stop();
                checkpoints += 1;
            },
            Err(e) => {
                info!("Alive deadline could not be started: {:?}", e);
                break;
            },
        };
    }

    info!("Alive supervision finished after {} checkpoints", checkpoints);
}

/// Entry point for the full-stack showcase.
fn main() {
    let _logger = LogAndTraceBuilder::new()
        .global_log_level(logging_tracing::Level::INFO)
        .enable_logging(true)
        .build();

    info!("Full-stack showcase starting");

    // The launch manager injects IDENTIFIER into processes it supervises; its
    // presence selects full supervisor-connected health monitoring.
    let supervised = std::env::var("IDENTIFIER").is_ok();

    // Lifecycle alive supervision on a dedicated OS thread.
    let supervision_stop = Arc::new(AtomicBool::new(false));
    let supervision_handle = {
        let stop = supervision_stop.clone();
        std::thread::spawn(move || run_alive_supervision(stop, supervised))
    };

    // Shared state between the run and stop actions.
    let counter: SharedCounter = Arc::new(Mutex::new(0));

    // Build orchestration
    let mut orch = Orchestration::new()
        .add_design(sensor_design(counter).expect("Failed to build FullStackDesign"))
        .design_done();

    orch.get_deployment_mut()
        .bind_events_as_timer(&[SENSOR_TICK.into()], Duration::from_millis(200))
        .expect("Failed to bind timer event");

    let mut program_manager = orch.into_program_manager().unwrap();
    let mut programs = program_manager.get_programs();

    // Kyron runtime
    let (builder, _) = kyron::runtime::RuntimeBuilder::new()
        .with_engine(ExecutionEngineBuilder::new().task_queue_size(256).workers(2));
    let mut runtime = builder.build().unwrap();

    runtime.block_on(async move {
        let mut sensor_program = programs.pop().unwrap();

        let h_sensor = kyron::spawn(async move {
            let _ = sensor_program.run_n(CYCLE_COUNT).await;
        });

        let _ = h_sensor.await;

        info!("Full-stack showcase finished");
    });

    // Stop the supervision thread after the orchestration work completed.
    supervision_stop.store(true, Ordering::Relaxed);
    supervision_handle.join().expect("Supervision thread panicked");
}
