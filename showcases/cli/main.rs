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
use anyhow::{Context, Result};
use clap::Parser;
use serde::Deserialize;
use std::{collections::HashMap, env, fs, path::Path};

use cliclack::{clear_screen, confirm, intro, multiselect, outro};
use std::process::Child;
use std::process::Command;
use std::time::Duration;

#[derive(Parser)]
#[command(name = "SCORE CLI")]
#[command(about = "SCORE CLI showcase entrypoint", long_about = None)]
struct Args {
    /// Examples to run (comma-separated names, or "all" to run all examples, skips interactive selection)
    #[arg(long)]
    examples: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
struct AppConfig {
    path: String,
    dir: Option<String>,
    args: Vec<String>,
    env: HashMap<String, String>,
    delay: Option<u64>,        // delay in seconds before running the next app
    timeout_secs: Option<u64>, // send SIGTERM after this many seconds; wait 5s then SIGKILL
}

#[derive(Debug, Deserialize, Clone)]
struct ScoreConfig {
    name: String,
    description: String,
    apps: Vec<AppConfig>,
}

fn print_banner() {
    let color_code = "\x1b[38;5;99m";
    let reset_code = "\x1b[0m";

    let banner = r#"
   ███████╗       ██████╗ ██████╗ ██████╗ ███████╗
   ██╔════╝      ██╔════╝██╔═══██╗██╔══██╗██╔════╝
   ███████╗█████╗██║     ██║   ██║██████╔╝█████╗  
   ╚════██║╚════╝██║     ██║   ██║██╔══██╗██╔══╝  
   ███████║      ╚██████╗╚██████╔╝██║  ██║███████╗
   ╚══════╝       ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
"#;

    println!("{}{}{}", color_code, banner, reset_code);
}

fn pause_for_enter() -> Result<()> {
    let result = confirm("Do you want to select examples to run?")
        .initial_value(true)
        .interact()?;
    if !result {
        outro("Falling back to the console. Goodbye!")?;
        std::process::exit(0);
    }
    Ok(())
}

fn main() -> Result<()> {
    let args = Args::parse();

    // Determine the showcases root directory.
    //
    // Priority:
    // 1. SCORE_CLI_INIT_DIR environment variable (explicit override).
    // 2. Running from the extracted bundle: binary is at <root>/bin/cli,
    //    so parent/parent is the root that contains configs/ and bin/.
    // 3. Running via `bazel run //showcases/cli`: binary is at
    //    <output>/showcases/cli/cli and the extracted bundle lives at
    //    <output>/showcases/showcases/showcases/ (parent/parent/showcases/showcases).
    // 4. Fall back to the hard-coded Docker deployment path /showcases.
    let root_dir = env::var("SCORE_CLI_INIT_DIR").unwrap_or_else(|_| {
        std::env::current_exe()
            .ok()
            .and_then(|exe| {
                let grandparent = exe.parent().and_then(|p| p.parent())?;
                // Case 2: running from extracted bundle – configs/ is directly here.
                if grandparent.join("configs").exists() {
                    return Some(grandparent.to_string_lossy().into_owned());
                }
                // Case 3: running via `bazel run` – bundle is nested one level deeper.
                let nested = grandparent.join("showcases/showcases");
                if nested.join("configs").exists() {
                    return Some(nested.to_string_lossy().into_owned());
                }
                None
            })
            .unwrap_or_else(|| "/showcases".to_string())
    });

    let mut configs = Vec::new();
    visit_dir(Path::new(&root_dir), &mut configs)?;

    // Rewrite app paths that were authored with the hard-coded Docker deployment
    // prefix (/showcases) so they resolve correctly under any root_dir.
    let showcases_prefix = "/showcases";
    if root_dir != showcases_prefix {
        let rewrite = |value: &str| -> Option<String> {
            value
                .starts_with(showcases_prefix)
                .then(|| format!("{}{}", root_dir, &value[showcases_prefix.len()..]))
        };
        for config in &mut configs {
            for app in &mut config.apps {
                if let Some(rewritten) = rewrite(&app.path) {
                    app.path = rewritten;
                }
                if let Some(ref mut dir) = app.dir {
                    if let Some(rewritten) = rewrite(dir) {
                        *dir = rewritten;
                    }
                }
                // Arguments may also embed the hard-coded Docker deployment prefix
                // (e.g. a --service-instance-manifest path), so rewrite them too.
                for arg in &mut app.args {
                    if let Some(rewritten) = rewrite(arg) {
                        *arg = rewritten;
                    }
                }
            }
        }
    }

    if configs.is_empty() {
        anyhow::bail!("No *.score.json files found under {}", root_dir);
    }

    let selected = if let Some(examples_str) = args.examples {
        // Non-interactive mode: use provided examples
        let mut selected_indices = Vec::new();

        if examples_str.to_lowercase() == "all" {
            // Select all available examples
            selected_indices = (0..configs.len()).collect();
            println!("Running all {} examples", configs.len());
        } else {
            // Match specific examples
            let requested_examples: Vec<&str> = examples_str.split(',').map(|s| s.trim()).collect();

            for (i, config) in configs.iter().enumerate() {
                if requested_examples.contains(&config.name.as_str()) {
                    selected_indices.push(i);
                }
            }

            if selected_indices.is_empty() {
                anyhow::bail!(
                    "No examples found matching: {}. Available examples: {}",
                    examples_str,
                    configs.iter().map(|c| c.name.as_str()).collect::<Vec<_>>().join(", ")
                );
            }

            println!("Running examples: {}", examples_str);
        }

        selected_indices
    } else {
        // Interactive mode
        print_banner();
        intro("WELCOME TO SHOWCASE ENTRYPOINT")?;
        pause_for_enter()?;

        clear_screen()?;

        // Create options for multiselect
        let options: Vec<(usize, String, String)> = configs
            .iter()
            .enumerate()
            .map(|(i, c)| (i, c.name.clone(), c.description.clone()))
            .collect();

        let selected: Vec<usize> =
            multiselect("Select examples to run (use space to select (multiselect supported), enter to run examples):")
                .items(&options)
                .interact()?;

        if selected.is_empty() {
            outro("No examples selected. Goodbye!")?;
            return Ok(());
        }

        selected
    };

    let mut failed_examples: Vec<String> = Vec::new();
    for index in selected {
        if let Err(e) = run_score(&configs[index]) {
            eprintln!("✗ {:#}", e);
            failed_examples.push(configs[index].name.clone());
        }
    }

    if !failed_examples.is_empty() {
        anyhow::bail!(
            "{} example(s) failed: {}",
            failed_examples.len(),
            failed_examples.join(", ")
        );
    }

    outro("All done!")?;

    Ok(())
}

fn visit_dir(dir: &Path, configs: &mut Vec<ScoreConfig>) -> Result<()> {
    for entry in fs::read_dir(dir).with_context(|| format!("Failed to read directory {:?}", dir))? {
        let entry = entry?;
        let path = entry.path();

        if path.is_symlink() {
            continue;
        }

        if path.is_dir() {
            visit_dir(&path, configs)?;
            continue;
        }

        if is_score_file(&path) {
            let content = fs::read_to_string(&path).with_context(|| format!("Failed reading {:?}", path))?;
            let value: serde_json::Value =
                serde_json::from_str(&content).with_context(|| format!("Invalid JSON in {:?}", path))?;
            if value.is_array() {
                let found: Vec<ScoreConfig> =
                    serde_json::from_value(value).with_context(|| format!("Invalid JSON array in {:?}", path))?;
                configs.extend(found);
            } else {
                let config: ScoreConfig =
                    serde_json::from_value(value).with_context(|| format!("Invalid JSON in {:?}", path))?;
                configs.push(config);
            }
        }
    }
    Ok(())
}

fn is_score_file(path: &Path) -> bool {
    path.file_name()
        .and_then(|n| n.to_str())
        .map(|n| n.ends_with(".score.json"))
        .unwrap_or(false)
}

fn run_score(config: &ScoreConfig) -> Result<()> {
    println!("▶ Running example: {}", config.name);

    let mut children: Vec<(usize, String, Child)> = Vec::new();
    let mut failures: Vec<String> = Vec::new();

    let now = std::time::Instant::now();
    println!("{:?} Starting example '{}'", now.elapsed(), config.name);
    for (i, app) in config.apps.iter().enumerate() {
        let app = app.clone(); // Clone for ownership

        if let Some(delay_secs) = app.delay {
            if delay_secs > 0 {
                println!(
                    "{:?}  App {}: waiting {} seconds before start...",
                    now.elapsed(),
                    i + 1,
                    delay_secs
                );
                std::thread::sleep(Duration::from_secs(delay_secs));
            }
        }

        println!("{:?} App {}: starting {}", now.elapsed(), i + 1, app.path);

        let mut cmd = Command::new(&app.path);
        cmd.args(&app.args);
        cmd.envs(&app.env);
        if let Some(ref dir) = app.dir {
            cmd.current_dir(dir);
        }

        let child = cmd
            .spawn()
            .with_context(|| format!("Failed to start app {}: {}", i + 1, app.path))?;

        println!("App {}: spawned command {:?}", i + 1, cmd);

        children.push((i + 1, app.path.clone(), child));
    }

    // Wait for all children, honouring per-app timeout_secs
    for (i, path, mut child) in children {
        let timeout = config.apps.get(i - 1).and_then(|a| a.timeout_secs);
        // Apps configured with a timeout are long-running services that we stop
        // on purpose; their non-zero exit status after SIGTERM is expected and
        // must not be reported as a failure.
        let mut terminated_by_timeout = false;
        let status = if let Some(secs) = timeout {
            // Poll until timeout, then send SIGTERM
            let deadline = std::time::Instant::now() + Duration::from_secs(secs);
            loop {
                match child
                    .try_wait()
                    .with_context(|| format!("Failed to poll app {}: {}", i, path))?
                {
                    Some(s) => break s,
                    None if std::time::Instant::now() >= deadline => {
                        println!("App {}: timeout reached, sending SIGTERM to {}", i, path);
                        terminated_by_timeout = true;
                        send_sigterm(&child)
                            .with_context(|| format!("Failed to send SIGTERM to app {}: {}", i, path))?;

                        // Give the process a chance to perform graceful shutdown.
                        let grace_deadline = std::time::Instant::now() + Duration::from_secs(5);
                        loop {
                            match child
                                .try_wait()
                                .with_context(|| format!("Failed to poll app {} during grace period: {}", i, path))?
                            {
                                Some(s) => break s,
                                None if std::time::Instant::now() >= grace_deadline => {
                                    println!("App {}: grace period expired, sending SIGKILL to {}", i, path);
                                    let _ = child.kill();
                                    break child.wait().with_context(|| {
                                        format!("Failed to wait after SIGKILL for app {}: {}", i, path)
                                    })?;
                                },
                                None => std::thread::sleep(Duration::from_millis(100)),
                            }
                        }
                    },
                    None => std::thread::sleep(Duration::from_millis(100)),
                }
            }
        } else {
            child
                .wait()
                .with_context(|| format!("Failed to wait for app {}: {}", i, path))?
        };

        if terminated_by_timeout {
            println!("App {}: stopped after timeout {}", i, path);
        } else if status.success() {
            println!("App {}: finished {}", i, path);
        } else {
            println!("App {}: FAILED ({}) {}", i, status, path);
            failures.push(format!("app {} ({}) exited with {}", i, path, status));
        }
    }

    if failures.is_empty() {
        println!("✅ Example '{}' finished successfully.", config.name);
        Ok(())
    } else {
        anyhow::bail!("Example '{}' failed: {}", config.name, failures.join("; "))
    }
}

fn send_sigterm(child: &Child) -> Result<()> {
    let pid = child.id().to_string();
    let status = Command::new("kill")
        .args(["-TERM", &pid])
        .status()
        .with_context(|| format!("Failed to execute kill -TERM for pid {}", pid))?;

    if status.success() {
        Ok(())
    } else {
        anyhow::bail!("kill -TERM {} exited with status {}", pid, status)
    }
}
