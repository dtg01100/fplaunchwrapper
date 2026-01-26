# Systemd Setup Bug Fixes

This document details all bugs found and fixed in `lib/systemd_setup.py`.

## Critical Bugs Fixed

### 1. Glob Pattern Bug in `list_all_units()` (Line 861-862)

**Issue**: The glob pattern `"flatpak-*.{service,path,timer}"` used shell brace expansion syntax, which doesn't work with Python's `Path.glob()`. This would literally search for files with `{service,path,timer}` in the name.

**Impact**: `list_all_units()` would always return empty list, breaking unit listing functionality.

**Fix**: Use separate glob patterns in a loop:
```python
for pattern in ["flatpak-*.service", "flatpak-*.path", "flatpak-*.timer"]:
    for unit_file in self.systemd_unit_dir.glob(pattern):
        units.append(unit_file.name)
```

**Test**: `test_systemd_bugfixes.py::TestGlobPatternFix`

---

### 2. Shell Command Injection Vulnerability in `enable_app_service()` (Line 563)

**Issue**: Variables in the shell command were not properly quoted, creating a command injection vulnerability:
```python
ExecStart=/bin/sh -c 'test -x {self.wrapper_script} && {self.wrapper_script} {self.bin_dir} {app_id}'
```

If any of these variables contained shell metacharacters (`;`, `$`, backticks, etc.), they could be exploited.

**Impact**: Security vulnerability allowing arbitrary command execution via malicious app IDs or paths.

**Fix**: Use `shlex.quote()` to properly escape all shell arguments:
```python
import shlex

safe_wrapper_script = shlex.quote(str(self.wrapper_script))
safe_bin_dir = shlex.quote(str(self.bin_dir))
safe_app_id = shlex.quote(str(app_id))
```

**Test**: `test_systemd_bugfixes.py::TestShellInjectionFix`

---

### 3. Timer Unit Structure Error (Line 228-246)

**Issue**: Timer units incorrectly included a `[Service]` section. Timer units should only reference service units, not contain service definitions themselves.

**Impact**: Architecturally incorrect systemd configuration. While systemd would ignore the extra section, it violates systemd unit file conventions and could cause confusion.

**Fix**: Removed `[Service]` section from timer unit, kept only proper `Unit=` reference:
```systemd
[Unit]
Description=Timer for Flatpak wrapper generation

[Timer]
OnCalendar=daily
Persistent=true
Unit=flatpak-wrappers.service

[Install]
WantedBy=timers.target
```

**Test**: `test_systemd_bugfixes.py::TestTimerUnitStructureFix`

---

### 4. Missing Bounds Checking in `check_systemd_status()` (Lines 996, 1012, 1022, 1041)

**Issue**: Multiple `.split("=")[1]` operations lacked bounds checking. If systemctl output didn't contain `"="`, this would raise an `IndexError`.

**Impact**: Crashes when parsing malformed systemctl output.

**Fix**: Add bounds checking for all split operations:
```python
parts = str(result.stdout).strip().split("=", 1)
if len(parts) == 2:
    unit_info["load_state"] = parts[1]
```

**Test**: `test_systemd_bugfixes.py::TestBoundsCheckingFix`

---

## Medium Priority Bugs Fixed

### 5. Incorrect Prerequisite Checking (Line 140-146)

**Issue**: Used `os.path.exists()` to check for commands that should be in PATH, not file paths:
```python
script_path = self.wrapper_script.split()[0]
if not os.path.exists(script_path):
```

For commands like `python`, this would fail incorrectly.

**Impact**: False positives/negatives in prerequisite validation, especially for Python module invocations.

**Fix**: Distinguish between absolute paths, relative paths, and PATH commands:
```python
if script_path.startswith("/") or script_path.startswith("."):
    if not os.path.exists(script_path):
        # handle file path
else:
    if not shutil.which(script_path):
        # handle PATH command
```

**Test**: `test_systemd_bugfixes.py::TestPrerequisiteCheckingFix`

---

### 6. Silent Exception Handling in `disable_systemd_units()` (Line 916-917)

**Issue**: Caught and silently ignored all exceptions when disabling individual units:
```python
except Exception:
    pass
```

**Impact**: Users would think units were disabled when they might still be running. No visibility into failures.

**Fix**: Log individual failures and track overall success:
```python
except Exception as e:
    self.log(f"Failed to remove {unit_name}: {e}", "error")
    success = False
```

**Test**: `test_systemd_bugfixes.py::TestErrorVisibilityFix`

---

### 7. Incorrect Return Value Semantics (Line 890-892)

**Issue**: Returned `False` when systemd unit directory didn't exist, treating "nothing to disable" as an error:
```python
if not self.systemd_unit_dir.exists():
    self.log("Systemd unit directory does not exist", "warning")
    return False
```

**Impact**: Confusing error reporting. "Nothing to disable" is a valid success state, not a failure.

**Fix**: Return `True` when there's nothing to disable:
```python
if not self.systemd_unit_dir.exists():
    self.log("No systemd units to disable", "info")
    return True
```

**Test**: `test_systemd_bugfixes.py::TestReturnValueSemanticsFix`

---

## Test Coverage

All bug fixes are covered by comprehensive tests in `tests/python/test_systemd_bugfixes.py`:

- **15 new tests** specifically for bug validation
- **45 total systemd tests** passing (including existing tests)
- **Test coverage includes**:
  - Edge cases (empty inputs, malformed data)
  - Security scenarios (shell metacharacters, path injection)
  - Error handling (missing files, failed operations)
  - Return value semantics

### Running Tests

```bash
# Run all systemd tests
python3 -m pytest tests/python/test_systemd*.py -v

# Run only bug fix tests
python3 -m pytest tests/python/test_systemd_bugfixes.py -v

# Quick check
python3 -m pytest tests/python/test_systemd*.py -q
```

All tests pass successfully (45/45).

---

## Impact Summary

| Bug | Severity | Impact | Status |
|-----|----------|--------|--------|
| Glob pattern | High | Feature broken | ✅ Fixed |
| Shell injection | Critical | Security vulnerability | ✅ Fixed |
| Timer structure | Medium | Configuration error | ✅ Fixed |
| Bounds checking | High | Crashes | ✅ Fixed |
| Prerequisite check | Medium | False negatives | ✅ Fixed |
| Silent exceptions | Medium | Hidden failures | ✅ Fixed |
| Return semantics | Low | Confusing errors | ✅ Fixed |

---

## Additional Improvements

### Shell Quoting Safety

All shell commands now use `shlex.quote()` for proper escaping, protecting against:
- Paths with spaces
- Shell metacharacters (`$`, `;`, `` ` ``, etc.)
- Command injection attempts

This applies to:
- `enable_app_service()` - app IDs, paths, scripts
- All other shell command constructions

### Error Reporting

- Replaced silent exception handling with explicit error logging
- Added detailed error messages for each failure type
- Improved return value consistency

---

## Maintenance Notes

**For future developers:**

1. **Always use separate glob patterns** - Python's `Path.glob()` doesn't support brace expansion
2. **Always use `shlex.quote()`** for shell arguments - even "safe" values can contain spaces
3. **Always check `split()` bounds** - never assume output format
4. **Never silently catch exceptions** - at minimum, log the error
5. **Use `shutil.which()` for commands** - `os.path.exists()` is only for file paths

**Test requirements:**
- All new shell commands MUST have injection tests
- All string parsing MUST have bounds checking tests
- All error paths MUST be tested
