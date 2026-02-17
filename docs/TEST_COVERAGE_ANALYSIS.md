# Test Coverage Analysis Report

**Project:** fplaunchwrapper  
**Date:** 2026-02-17  
**Analysis Type:** Comprehensive Test Coverage Review

---

## Executive Summary

This report presents a comprehensive analysis of test coverage for the fplaunchwrapper project. The analysis identified critical bugs, coverage gaps, and areas requiring immediate attention.

### Key Findings

| Metric | Value |
|--------|-------|
| **Overall Coverage** | 67% |
| **Total Statements** | 4,194 |
| **Missed Statements** | 1,388 |
| **Total Tests** | 872 |
| **Passed Tests** | 861 |
| **Failed Tests** | 11 |

### Priority Issues

1. **2 Critical Bugs** requiring immediate fixes
2. **11 Modules** with coverage below 80%
3. **5 Categories** of missing test scenarios
4. **Complete absence** of tests for shell scripts

---

## Critical Bugs Requiring Immediate Fixes

### Bug 1: Missing Fallback in lib/generate.py

**Severity:** Critical  
**Location:** [`lib/generate.py:140`](lib/generate.py:140)  
**Error Type:** `NameError`

**Description:**  
The code references `get_default_config_dir` without a fallback definition when the primary import fails. This causes a `NameError` at runtime when certain import conditions are not met.

**Error Message:**
```
NameError: name 'get_default_config_dir' is not defined
```

**Recommended Fix:**  
Add a fallback function definition for `get_default_config_dir` in the exception handler or ensure the function is always defined before use:

```python
try:
    from lib.paths import get_default_config_dir
except ImportError:
    def get_default_config_dir():
        """Fallback implementation for get_default_config_dir."""
        # Provide a sensible default or raise a more informative error
        return os.path.expanduser("~/.config/fplaunchwrapper")
```

**Impact:**  
- Runtime failures in environments with incomplete installations
- Affects the `generate` subcommand functionality
- May prevent wrapper generation entirely

---

### Bug 2: Incorrect Imports in Test Files

**Severity:** Medium  
**Location:** Multiple test files

**Description:**  
Several test files are missing the `lib.` prefix in their imports, which causes import failures when running tests in certain configurations.

**Affected Files:**

| File | Line | Issue |
|------|------|-------|
| [`tests/python/test_force_interactive_verification.py`](tests/python/test_force_interactive_verification.py:19) | 19 | Missing `lib.` prefix |
| [`tests/python/test_systemd_cli.py`](tests/python/test_systemd_cli.py:20) | 20 | Missing `lib.` prefix |
| [`tests/python/test_watchdog_integration.py`](tests/python/test_watchdog_integration.py:26) | 26 | Missing `lib.` prefix |

**Example Fix:**
```python
# Incorrect
from config_manager import ConfigManager

# Correct
from lib.config_manager import ConfigManager
```

**Impact:**
- Test failures when running from project root
- Inconsistent test execution across environments
- False negatives in CI/CD pipelines

---

## Coverage Statistics by Module

### Modules Below 80% Coverage (Priority List)

The following modules require immediate attention to improve test coverage:

| Module | Coverage | Missed Lines | Priority |
|--------|----------|--------------|----------|
| [`lib/fplaunch.py`](lib/fplaunch.py) | 40% | 15 | **Critical** |
| [`lib/config_manager.py`](lib/config_manager.py) | 55% | 261 | **High** |
| [`lib/exceptions.py`](lib/exceptions.py) | 54% | 46 | **High** |
| [`lib/launch.py`](lib/launch.py) | 54% | 147 | **High** |
| [`lib/systemd_setup.py`](lib/systemd_setup.py) | 60% | 215 | **High** |
| [`lib/cleanup.py`](lib/cleanup.py) | 66% | 132 | Medium |
| [`lib/manage.py`](lib/manage.py) | 65% | 234 | Medium |
| [`lib/flatpak_monitor.py`](lib/flatpak_monitor.py) | 71% | 79 | Medium |
| [`lib/import_utils.py`](lib/import_utils.py) | 70% | 8 | Medium |
| [`lib/cli.py`](lib/cli.py) | 77% | 130 | Low |
| [`lib/python_utils.py`](lib/python_utils.py) | 79% | 41 | Low |

### Coverage Visualization

```
lib/fplaunch.py          ████████░░░░░░░░░░░░  40%
lib/config_manager.py    ███████████░░░░░░░░░  55%
lib/exceptions.py        ███████████░░░░░░░░░  54%
lib/launch.py            ███████████░░░░░░░░░  54%
lib/systemd_setup.py     ████████████░░░░░░░░  60%
lib/cleanup.py           █████████████░░░░░░░  66%
lib/manage.py            █████████████░░░░░░░  65%
lib/flatpak_monitor.py   ██████████████░░░░░░  71%
lib/import_utils.py      ██████████████░░░░░░  70%
lib/cli.py               ███████████████░░░░░  77%
lib/python_utils.py      ████████████████░░░░  79%
```

---

## Detailed Missing Test Scenarios by Module

### 1. Import Fallback Paths

**Affected Modules:** All modules with optional dependencies

**Description:**  
When optional dependencies are unavailable, the code should gracefully degrade. Currently, these fallback paths are not tested.

**Missing Scenarios:**
- Tests for missing `pydantic` dependency
- Tests for missing `xdg` dependency  
- Tests for missing `gi` (GObject Introspection) dependency
- Tests for missing `dbus` dependency

**Example Test Case:**
```python
def test_missing_pydantic_fallback(monkeypatch):
    """Test that missing pydantic is handled gracefully."""
    monkeypatch.setitem(sys.modules, 'pydantic', None)
    # Import should still work with fallback behavior
    from lib.config_manager import ConfigManager
    # Verify fallback behavior
```

---

### 2. Hook Failure Mode Logic

**Affected Modules:** [`lib/launch.py`](lib/launch.py), [`lib/config_manager.py`](lib/config_manager.py)

**Description:**  
The hook failure modes (abort/warn/ignore) determine behavior when pre-launch or post-launch hooks fail. These code paths lack comprehensive testing.

**Missing Scenarios:**
- Pre-launch hook failure with `abort` mode
- Pre-launch hook failure with `warn` mode
- Pre-launch hook failure with `ignore` mode
- Post-launch hook failure with each mode
- Hook timeout handling
- Hook permission denied scenarios

**Configuration Example:**
```toml
[hooks]
failure_mode = "abort"  # abort | warn | ignore
```

---

### 3. Pydantic Validators

**Affected Modules:** [`lib/config_manager.py`](lib/config_manager.py)

**Description:**  
Pydantic model validators ensure configuration integrity but are not fully tested for edge cases.

**Missing Scenarios:**
- Invalid configuration value types
- Out-of-range numeric values
- Invalid path formats
- Invalid boolean string representations
- Nested configuration validation errors
- Custom validator error messages

**Example Test Case:**
```python
def test_invalid_timeout_value():
    """Test that invalid timeout values are rejected."""
    with pytest.raises(ValidationError):
        ConfigModel(timeout=-1)  # Negative timeout should fail
```

---

### 4. CLI Entry Points

**Affected Modules:** [`lib/cli.py`](lib/cli.py), [`lib/fplaunch.py`](lib/fplaunch.py)

**Description:**  
CLI entry points handle command-line arguments and dispatch to appropriate handlers. Edge cases in argument parsing are not fully covered.

**Missing Scenarios:**
- Empty argument handling
- Invalid subcommand names
- Missing required arguments
- Conflicting argument combinations
- Help text generation for all subcommands
- Version flag handling
- Signal handling (SIGINT, SIGTERM)

---

### 5. Error Handling Paths

**Affected Modules:** All modules

**Description:**  
Error handling code paths are often overlooked in testing, leading to untested exception handlers.

**Missing Scenarios:**
- File permission errors
- Disk space errors
- Network timeout errors (for remote configurations)
- Invalid JSON/TOML parsing errors
- Process spawn failures
- D-Bus connection failures
- Systemd communication errors

---

## Shell Script Coverage Analysis

### Current State

**Critical Finding:** Shell scripts have minimal to no test coverage.

| Script | Unit Tests | Integration Tests | Adversarial Tests |
|--------|------------|-------------------|-------------------|
| [`lib/script.sh`](lib/script.sh) | ❌ None | ❌ None | ❌ None |
| [`lib/common.sh`](lib/common.sh) | ❌ None | ❌ None | ✅ Partial |
| [`lib/wrapper.sh`](lib/wrapper.sh) | ❌ None | ❌ None | ✅ Partial |
| [`lib/alias.sh`](lib/alias.sh) | ❌ None | ❌ None | ✅ Partial |
| [`lib/env.sh`](lib/env.sh) | ❌ None | ❌ None | ✅ Partial |
| [`lib/pref.sh`](lib/pref.sh) | ❌ None | ❌ None | ✅ Partial |

### Detailed Analysis

#### lib/script.sh - NO TESTS

**Severity:** Critical  
**Lines of Code:** ~100

This script has **zero test coverage**. It likely contains critical functionality that is completely untested.

**Recommended Actions:**
1. Identify all functions in the script
2. Create unit tests for each function
3. Add integration tests for script execution
4. Add adversarial tests for error handling

#### Other Shell Scripts

Other shell scripts only have adversarial tests located in:
- [`tests/adversarial/test_fplaunchwrapper_adversarial.sh`](tests/adversarial/test_fplaunchwrapper_adversarial.sh)
- [`tests/adversarial/test_package_adversarial.sh`](tests/adversarial/test_package_adversarial.sh)
- [`tests/adversarial/test_robustness_adversarial.sh`](tests/adversarial/test_robustness_adversarial.sh)
- [`tests/adversarial/test_systemd_adversarial.sh`](tests/adversarial/test_systemd_adversarial.sh)
- [`tests/adversarial/test_wrapper_options_adversarial.sh`](tests/adversarial/test_wrapper_options_adversarial.sh)

**Missing:**
- Positive unit tests for normal operation
- Integration tests for script interactions
- Edge case tests for boundary conditions

### Shell Script Testing Recommendations

1. **Create a shell testing framework** using bats-core or similar
2. **Add unit tests** for each shell function
3. **Mock external dependencies** (flatpak, systemctl, etc.)
4. **Test error handling** paths explicitly
5. **Add coverage reporting** for shell scripts

---

## Recommendations Prioritized by Impact

### Priority 1: Critical (Immediate Action Required)

| Action | Impact | Effort |
|--------|--------|--------|
| Fix Bug #1: Missing fallback in `lib/generate.py` | High | Low |
| Fix Bug #2: Correct imports in test files | Medium | Low |
| Add tests for `lib/fplaunch.py` (40% → 80%) | High | Medium |
| Create tests for `lib/script.sh` (0% → 80%) | High | High |

### Priority 2: High (Within Sprint)

| Action | Impact | Effort |
|--------|--------|--------|
| Improve `lib/config_manager.py` coverage (55% → 80%) | High | High |
| Improve `lib/launch.py` coverage (54% → 80%) | High | Medium |
| Add hook failure mode tests | Medium | Medium |
| Add import fallback path tests | Medium | Medium |

### Priority 3: Medium (Next Sprint)

| Action | Impact | Effort |
|--------|--------|--------|
| Improve `lib/systemd_setup.py` coverage (60% → 80%) | Medium | Medium |
| Improve `lib/cleanup.py` coverage (66% → 80%) | Medium | Low |
| Improve `lib/manage.py` coverage (65% → 80%) | Medium | Medium |
| Add Pydantic validator tests | Medium | Low |

### Priority 4: Low (Backlog)

| Action | Impact | Effort |
|--------|--------|--------|
| Improve `lib/cli.py` coverage (77% → 85%) | Low | Low |
| Improve `lib/python_utils.py` coverage (79% → 85%) | Low | Low |
| Add CLI entry point tests | Low | Low |
| Add error handling path tests | Low | Medium |

---

## Test Failure Summary

### Failed Tests (11 total)

The following tests are currently failing and require investigation:

1. Tests related to import issues (Bug #2)
2. Tests related to missing fallback (Bug #1)
3. Additional failures requiring individual analysis

**Recommended Actions:**
1. Run failed tests individually to capture error details
2. Create issues for each distinct failure
3. Prioritize fixes based on feature impact
4. Add regression tests for each fixed failure

---

## Coverage Improvement Roadmap

### Phase 1: Critical Fixes (Week 1)
- [ ] Fix Bug #1: Missing fallback in `lib/generate.py`
- [ ] Fix Bug #2: Correct test imports
- [ ] Re-run all tests to establish baseline

### Phase 2: Low Coverage Modules (Weeks 2-3)
- [ ] Add tests for `lib/fplaunch.py`
- [ ] Add tests for `lib/config_manager.py`
- [ ] Add tests for `lib/launch.py`
- [ ] Add tests for `lib/exceptions.py`

### Phase 3: Shell Script Testing (Weeks 3-4)
- [ ] Set up shell testing framework
- [ ] Add tests for `lib/script.sh`
- [ ] Add positive unit tests for other shell scripts

### Phase 4: Coverage Refinement (Weeks 5-6)
- [ ] Improve remaining modules to 80%+
- [ ] Add missing test scenarios
- [ ] Achieve target coverage of 85%

---

## Conclusion

The fplaunchwrapper project has a solid foundation of tests (67% coverage, 861 passing tests), but significant gaps exist:

1. **Critical bugs** need immediate attention to prevent runtime failures
2. **11 modules** fall below the 80% coverage threshold
3. **Shell scripts** are critically undertested
4. **Missing test scenarios** leave edge cases uncovered

Addressing these issues systematically will improve code quality, reduce bugs, and increase confidence in the codebase.

---

## Appendix: Test Execution Commands

```bash
# Run all tests with coverage
pytest --cov=lib --cov-report=html --cov-report=term

# Run specific test file
pytest tests/python/test_generate_real.py -v

# Run with verbose output
pytest -v --tb=short

# Run only failed tests
pytest --lf

# Generate coverage report
coverage report --sort=cover
```

---

*Report generated from test coverage analysis conducted on 2026-02-17.*
