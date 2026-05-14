# KvsInstance Dead Code Analysis — PR #9

**Date:** May 4, 2026
**PR:** [qorix-group/reference_integration#9](https://github.com/qorix-group/reference_integration/pull/9)
**Files analysed:**
- `feature_integration_tests/test_scenarios/cpp/src/internals/persistency/kvs_instance.h`
- `feature_integration_tests/test_scenarios/cpp/src/internals/persistency/kvs_instance.cpp`

---

## 1. Finding: 13 Dead Methods in `KvsInstance`

`KvsInstance` was written with a wide API covering all KVS value types. After the final scenario
design was settled the following methods are **never called from any scenario file**:

### 1.1 Unused `set_value` overloads

| Method | `.h` line | `.cpp` line |
|--------|-----------|-------------|
| `set_value(const std::string& key, int32_t value)` | 34 | 242 |
| `set_value(const std::string& key, int64_t value)` | 35 | 247 |
| `set_value(const std::string& key, uint32_t value)` | 36 | 252 |
| `set_value(const std::string& key, uint64_t value)` | 37 | 257 |
| `set_value(const std::string& key, bool value)` | 39 | 262 |
| `set_value(const std::string& key, const std::string& value)` | 40 | 268 |

Every `KvsInstance`-based scenario call passes a `double` literal and routes through the one
**kept** overload `set_value(const std::string& key, double value)`.

### 1.2 Unused typed `get_value_*` methods

| Method | `.h` line | `.cpp` line |
|--------|-----------|-------------|
| `get_value_i32(const std::string& key)` | 43 | 297 |
| `get_value_i64(const std::string& key)` | 44 | 310 |
| `get_value_u32(const std::string& key)` | 45 | 323 |
| `get_value_u64(const std::string& key)` | 46 | 336 |
| `get_value_bool(const std::string& key)` | 48 | 362 |
| `get_value_string(const std::string& key)` | 49 | 378 |

### 1.3 Unused `is_value_default`

| Method | `.h` line | `.cpp` line |
|--------|-----------|-------------|
| `is_value_default(const std::string& key)` | 55 | 391 |

This 50-line synthesized implementation was written as a workaround for a missing native
`is_value_default()` API (described in `docs/Difference_in_framework`). The final scenario
design never needed it — see section 3 below.

### 1.4 Verification: zero callers in scenario code

```
grep -rn "get_value_i32\|get_value_i64\|get_value_u32\|get_value_u64\|get_value_bool\|get_value_string\|is_value_default" \
     feature_integration_tests/test_scenarios/cpp/src/scenarios/
# → 0 matches
```

All 13 methods exist only as definitions in `internals/` — no scenario ever calls them.

---

## 2. Methods That Are Used and Must Be Kept

| Method | Caller(s) |
|--------|-----------|
| `set_value(double)` | All KvsInstance-based scenarios: `default_values.cpp`, `multiple_kvs_per_app.cpp`, `reset_to_default.cpp`, `utf8_defaults.cpp`, `multi_instance_isolation.cpp`, `default_values_ignored.cpp` |
| `get_value()` (multi-type switch) | `multiple_kvs_per_app.cpp` lines 157, 163 — reads back a value whose type is unknown at compile time |
| `get_value_f64()` | `default_values.cpp` — `SelectiveReset` (line 178) and `FullReset` (line 228) read the default value after a reset |
| `remove_key()` | Not currently called but declared to complete the public key-management surface |
| `reset()` | `default_values.cpp` `FullReset` |
| `reset_key()` | `default_values.cpp` `SelectiveReset` |
| `flush()` | All KvsInstance-based scenarios |
| `create()` | All KvsInstance-based scenarios |
| `normalize_snapshot_file_to_rust_envelope()` | All scenarios that need Python-readable snapshots |

---

## 3. How Datatype Requirements Are Verified in PR #9

> **Question**: If `KvsInstance::set_value(int32_t/bool/string/...)` and all typed `get_value_*`
> methods are never called, how does the PR verify
> `feat_req__persistency__support_datatype_value` and
> `feat_req__persistency__support_datatype_keys`?

### Answer: Verification is snapshot-based, not read-back-based

The datatype scenario (`supported_datatypes.cpp`) does **not** use `KvsInstance` at all. It uses
the raw `Kvs` API from `kvs_build_helpers::create_kvs()`, passing pre-typed `KvsValue` objects
directly:

```cpp
// supported_datatypes.cpp  (uses raw Kvs, not KvsInstance)
Kvs kvs = create_kvs(params);

kvs.set_value("i32_key", KvsValue(static_cast<int32_t>(-321)));   // type encoded in KvsValue
kvs.set_value("u32_key", KvsValue(static_cast<uint32_t>(1234)));
kvs.set_value("i64_key", KvsValue(static_cast<int64_t>(-123456789)));
kvs.set_value("u64_key", KvsValue(static_cast<uint64_t>(123456789)));
kvs.set_value("f64_key", KvsValue(-5432.1));
kvs.set_value("bool_key", KvsValue(true));
kvs.set_value("str_key", KvsValue("example"));
kvs.set_value("arr_key", KvsValue(arr));
kvs.set_value("obj_key", KvsValue(nested_obj));

kvs.flush();
KvsInstance::normalize_snapshot_file_to_rust_envelope(params);   // only static method used
```

After flush the snapshot JSON file contains type-tagged entries such as:

```json
{"t":"obj","v":{
  "i32_key": {"t":"i32","v":-321},
  "u32_key": {"t":"u32","v":1234},
  "bool_key": {"t":"bool","v":true},
  ...
}}
```

The Python test (`test_datatype_support.py / TestAllValueTypes`) reads this file and verifies every
key has the correct `"t"` type tag and value:

```python
def test_all_types_in_snapshot(self, results: ScenarioResult, temp_dir: Path) -> None:
    snapshot = read_kvs_snapshot(temp_dir, 1)
    for key, expected_tagged in self._EXPECTED_ALL_TYPES.items():
        assert key in snapshot
        self._assert_tagged_value(snapshot[key], expected_tagged)   # checks "t" and "v"
```

The type is proven by the presence of `"t":"i32"` in the persisted file. No typed getter on
`KvsInstance` is needed.

### Why `is_value_default()` was never needed

`docs/Difference_in_framework` stated that `KvsInstance::is_value_default()` was a necessary
workaround because the pinned `kvs.hpp` has no native `is_value_default()` API. In practice the
final scenario design (`default_values.cpp`) does not need to test "is this value the default?" at
all. Instead:

- `GetDefaultValue` scenario: calls `kvs->get_value_f64("default_probe_key")` on a **never-set
  key** — the KVS library returns the default value directly.
- `SelectiveReset` / `FullReset`: call `kvs->get_value_f64(key)` after `reset_key()` / `reset()`
  — the KVS library again returns the default.

The default-vs-override distinction is verified by comparing the logged value to the known default
in the Python assertion, not by any `is_value_default()` call.

`docs/Difference_in_framework` is therefore **stale** on this point — the workaround was
implemented but the scenario design evolved to not require it.

---

## 4. Root Cause

The typed overloads were written speculatively during early development when it was unclear whether
scenarios would need to read back values by type. The final design converged on:

- **Write path**: raw `Kvs` API with `KvsValue` for typed writes in `supported_datatypes.cpp`;
  `KvsInstance::set_value(double)` for all other scenarios (which only use `f64`).
- **Read path**: Python reads the snapshot JSON file for type verification; `get_value_f64()` for
  the specific post-reset value assertions.

Because `KvsInstance` was never extended to handle typed scenarios, the typed overloads became
dead code.

---

## 5. Cleanup Plan

Remove the 13 dead declarations and implementations. The following diagram shows what survives:

### `kvs_instance.h` — remove lines 34–40 and 43–49 and 55; also remove `#include <cstdint>` (no longer needed in the header after cleanup)

Keep:
```cpp
// Set value
bool set_value(const std::string& key, double value);

// Get value methods
std::optional<double> get_value(const std::string& key);
std::optional<double> get_value_f64(const std::string& key);

// Key management methods
bool remove_key(const std::string& key);
bool reset();
bool reset_key(const std::string& key);
```

### `kvs_instance.cpp` — remove two blocks

**Block A** (lines 242–270): six `set_value` overloads after `set_value(double)`.

**Block B** (lines 297–440): `get_value_i32`, `get_value_i64`, `get_value_u32`,
`get_value_u64`, `get_value_bool`, `get_value_string`, `is_value_default`.

Keep `#include <cstdint>` in `.cpp` — it is needed by the `get_value()` multi-type switch
(`int32_t`, `uint32_t`, `int64_t`, `uint64_t`).

### Impact

- All 13 scenarios continue to compile and pass.
- No requirements traceability is affected.
- Binary size reduction: ~150 lines of dead code removed.

---

## 6. Impact on `docs/Difference_in_framework`

The section describing `is_value_default` as "not a cleanup item but a correct workaround" is
outdated. Once the dead code is removed, that section should be updated to note that
`is_value_default()` was removed because the final scenario design reads default values via
`get_value_f64()` on unset/reset keys, making the workaround unnecessary.
