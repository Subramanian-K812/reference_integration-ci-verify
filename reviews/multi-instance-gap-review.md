# Review — Multi-Instance Gap Scenarios (recovery_from_reset + atomic_store)

**Reviewer persona**: PiotrKorkus  
**Date**: 2026-05-07  
**Files reviewed**: 6 files changed (2 Rust, 2 C++, 2 Python)

---

## Summary

This change adds multi-instance variants for `recovery_from_reset` and
`atomic_store`, closing the gap identified in the gap analysis — only
`reset_resistant` previously had a multi-instance scenario.  The structure
mirrors the existing `ResetResistantMultiInstance` pattern faithfully.
Registration in both `mod.rs` and `mod.cpp` is correct and complete.
Two findings require attention before this is considered ready.

---

## Positives

- Both new Rust scenarios correctly use separate `params1` / `params2`
  pulled from distinct JSON keys (`kvs_parameters_1`, `kvs_parameters_2`),
  exactly following the `ResetResistantMultiInstance` pattern.
- Python test methods are single-purpose with clear names and use `isclose`
  throughout — no truthy checks on numeric values.
- `@add_test_properties` is present on both new Python classes with valid
  `partially_verifies` IDs and correct `test_type` / `derivation_technique`.
- `pytestmark` is declared at module level with `scope="class"` for both files.
- `test_no_cross_contamination_after_reset` and `test_no_cross_contamination`
  are strong additions — they directly catch the isolation failure mode the
  reviewer was asking about.
- C++ `RecoveryFromResetMultiInstance` follows the normalization pattern
  correctly: calls `normalize_snapshot_file_to_rust_envelope` for both
  params1 and params2 after all Phase 2 writes are done.

---

## Findings

### [Major] `AtomicStoreMultiInstance` C++ — normalization inside flush scope, wrong order

**File**: `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/atomic_store.cpp`, lines 233–241 and 254–262

**Evidence**:
```cpp
// Instance 1: set two keys and flush atomically.
{
    auto kvs1_opt = KvsInstance::create(params1);
    ...
    if (!kvs1->flush()) { throw ...; }
    // Normalize instance-1 snapshot for Python assertions.
    if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params1)) {
        throw std::runtime_error("Inst1: failed to normalize snapshot_0");
    }
}   // ← kvs1 destroyed here

// Instance 2: ...
{
    ...
    if (!kvs2->flush()) { throw ...; }
    if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params2)) { ... }
}
```

**Problem**: `normalize_snapshot_file_to_rust_envelope` is called while `kvs1`
is still in scope (at end of the same block) and before `params2`'s instance
is even created.  In the existing `AtomicStore` (single-instance) scenario the
normalization is also called while the KVS handle is live — that was acceptable
because the write is done and flush was called.  But for the multi-instance
case, calling normalization for instance 1 before instance 2 has been created
and flushed creates an implicit ordering constraint that is not needed.  More
importantly, compare with `ResetResistantMultiInstance` and the original
`recovery_from_reset_multi_instance` C++ scenario: normalization is always
performed **after all KVS operations are finished** (outside all scopes).
Keeping it inside the per-instance scope is inconsistent and risks issues if
`normalize_snapshot_file_to_rust_envelope` internally re-opens the file or
holds state across calls.

**Fix**: Move both normalization calls to after all instance scopes are closed,
following the pattern in `recovery_from_reset_multi_instance`:

```cpp
        // Instance 1 scope
        {
            ...
            if (!kvs1->flush()) { throw ...; }
            // no normalization here
        }

        // Instance 2 scope
        {
            ...
            if (!kvs2->flush()) { throw ...; }
            // no normalization here
        }

        // Normalize both snapshots after all KVS operations.
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params1)) {
            throw std::runtime_error("Inst1: failed to normalize snapshot_0");
        }
        if (!KvsInstance::normalize_snapshot_file_to_rust_envelope(params2)) {
            throw std::runtime_error("Inst2: failed to normalize snapshot_0");
        }
```

**Test idea**: The test would catch a regression if instance 2's normalization
corrupted instance 1's already-normalized file when called from within
instance 1's scope.

---

### [Major] `AtomicStoreMultiInstance` Rust — no log-based readback after flush

**File**: `feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/atomic_store.rs`, lines 155–170

**Evidence**:
```rust
// Instance 1: set two keys and flush atomically.
{
    let kvs1 = kvs_instance(params1).map_err(|e| format!("{e:?}"))?;
    kvs1.set_value("inst1_key_a", 11.0_f64).map_err(...)?;
    kvs1.set_value("inst1_key_b", 12.0_f64).map_err(...)?;
    kvs1.flush().map_err(...)?;
}
// Instance 2: ...
```

**Problem**: The single-instance `AtomicStore` scenario has a Phase 2 where
the KVS is **re-opened** and all keys are read back and emitted as
`info!(key = ..., value = ...)` logs.  This proves the atomic write survived a
reload from disk (not just that `flush()` returned `Ok`).  `AtomicStoreMultiInstance`
performs no reload and emits no logs — the Python test only inspects snapshot
JSON files.  That means the scenario does not actually exercise the reload path
and `logs_info_level` is unused (this also means `LogContainer` cannot be
added to the test without scenario changes).

The requirement says "all key-value pairs are written" — verifying that the
application can **read them back after a re-open** is how `TestAtomicStore`
validates this.  The multi-instance scenario should do the same per instance.

**Fix**: Add a Phase 2 to `AtomicStoreMultiInstance` (both Rust and C++) that
re-opens each instance and reads back its keys, logging the values via
`tracing::info!` / `kvs_build_helpers::log_info`.  Then add a
`test_all_keys_readable_after_reload` test method in `TestAtomicStoreMultiInstance`
that uses `LogContainer` to assert the log entries.

**Test idea**: A test asserting on `logs_info_level.find_log("key", value="inst1_key_a")`
would immediately fail if the reload did not recover the key.

---

### [Minor] `TestAtomicStoreMultiInstance` — no hash file assertions

**File**: `feature_integration_tests/test_cases/tests/persistency/test_atomic_store.py`, lines 163–255

**Evidence**:
```python
class TestAtomicStoreMultiInstance(PersistencyScenario):
    # ... no test method checking .hash files
```

**Problem**: `TestAtomicStore` (single-instance) has `test_snapshot_hash_file_exists`
asserting `kvs_1_0.hash` is present.  The multi-instance class omits this
check for both instances.  The hash file is the integrity guarantee — if one
instance's flush accidentally overwrites the other instance's `.hash` file, this
is not detected.

**Fix**: Add one test method:

```python
def test_hash_files_exist(self, results: Any, temp_dir: Path) -> None:
    """Verify integrity hash files exist for both instance snapshots."""
    assert results.return_code == ResultCode.SUCCESS
    assert (temp_dir / "kvs_1_0.hash").exists(), "Hash file missing for instance 1"
    assert (temp_dir / "kvs_2_0.hash").exists(), "Hash file missing for instance 2"
```

---

### [Minor] `RecoveryFromResetMultiInstance` Rust — module-level doc comment not updated

**File**: `feature_integration_tests/test_scenarios/rust/src/scenarios/persistency/recovery_from_reset.rs`, lines 14–23

**Evidence**:
```rust
//! Scenario: Verify that persistency automatically recovers to the last
//! consistent (flushed) state after a simulated reset.
//! ...
//! Partially verifies: feat_req__persistency__recovery_from_reset
```

**Problem**: The module-level doc comment describes only the single-instance
`RecoveryFromReset` scenario.  Now that `RecoveryFromResetMultiInstance` is in
the same file, the doc comment should mention both scenarios (same pattern as
`reset_resistant.rs` and `atomic_store.rs` which list their scenarios in the
module doc).

**Fix**:
```rust
//! Scenarios verifying `feat_req__persistency__recovery_from_reset`.
//!
//! Two distinct scenarios are provided:
//!
//! 1. `recovery_from_reset` — single instance: un-flushed write is discarded;
//!    on-disk snapshot reflects the last successful flush.
//!
//! 2. `recovery_from_reset_multi_instance` — two instances sharing the same
//!    directory: a crash of one instance's write path must not corrupt the
//!    snapshot belonging to the other instance.
```

---

### [Nit] `recovery_from_reset.cpp` — `kvs_build_helpers.h` include is unused

**File**: `feature_integration_tests/test_scenarios/cpp/src/scenarios/persistency/recovery_from_reset.cpp`, line 14

**Evidence**:
```cpp
#include "../../internals/persistency/kvs_build_helpers.h"
```

**Problem**: Neither `RecoveryFromReset` nor `RecoveryFromResetMultiInstance`
calls any `kvs_build_helpers::` function (no log emission in this scenario).
The include was already present before this change, but the addition of a
second class that also does not use it makes it more visible.

**Fix**: Remove the include.  If a future variant needs logging, add it back.

---

## Suggested Next Steps

1. **(Must fix)** Move the two `normalize_snapshot_file_to_rust_envelope` calls
   in `AtomicStoreMultiInstance` C++ outside the per-instance scopes.
2. **(Should fix)** Add Phase 2 reload + log emission to `AtomicStoreMultiInstance`
   in both Rust and C++, then add a `test_all_keys_readable_after_reload`
   method to `TestAtomicStoreMultiInstance`.
3. **(Should fix)** Add `test_hash_files_exist` to `TestAtomicStoreMultiInstance`.
4. **(Nice to have)** Update the module-level doc comment in
   `recovery_from_reset.rs` to list both scenarios.
5. **(Nice to have)** Remove the unused `kvs_build_helpers.h` include from
   `recovery_from_reset.cpp`.

---

## Requirements Traceability Check

| Test Class | `partially_verifies` IDs | Status |
|---|---|---|
| `TestRecoveryFromReset` | `feat_req__persistency__recovery_from_reset` | OK |
| `TestRecoveryFromResetMultiInstance` | `feat_req__persistency__recovery_from_reset` | OK |
| `TestAtomicStore` | `feat_req__persistency__atomic_store` | OK |
| `TestAtomicStoreNoPartialWrite` | `feat_req__persistency__atomic_store` | OK |
| `TestAtomicStoreMultiInstance` | `feat_req__persistency__atomic_store` | OK |
