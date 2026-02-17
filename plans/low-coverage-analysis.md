# Low-Coverage Module Analysis and Test Issues

## Summary

This document analyzes the remaining modules with coverage below 80% and identifies incorrect tests causing failures.

---

## Part 1: Incorrect Tests Causing Failures

### Root Cause: Missing `lib.` Prefix in Imports

Three test files have incorrect import statements that omit the `lib.` package prefix. This causes `NameError: name 'get_default_config_dir' is not defined` because the import fails to find the module.

#### Files with Incorrect Imports

| File | Line | Incorrect Import | Correct Import |
|------|------|------------------|----------------|
| [`test_force_interactive_verification.py`](../tests/python/test_force_interactive_verification.py:19) | 19 | `from generate import WrapperGenerator` | `from lib.generate import WrapperGenerator` |
| [`test_systemd_cli.py`](../tests/python/test_systemd_cli.py:20) | 20 | `from cli import cli` | `from lib.cli import cli` |
| [`test_watchdog_integration.py`](../tests/python/test_watchdog_integration.py:26) | 26 | `from flatpak_monitor import ...` | `from lib.flatpak_monitor import ...` |

#### Fix Required

Change these imports to use the correct `lib.` prefix:

```python
# test_force_interactive_verification.py
from lib.generate import WrapperGenerator

# test_systemd_cli.py  
from lib.cli import cli

# test_watchdog_integration.py
from lib.flatpak_monitor import (
    WATCHDOG_AVAILABLE,
    FlatpakEventHandler,
    FlatpakMonitor,
    start_flatpak_monitoring,
)
```

---

## Part 2: Uncovered Code Analysis by Module

### 2.1 lib/exceptions.py (54% coverage)

#### Exception Classes Without Test Coverage

| Exception Class | Lines Missed | Description | Test Scenarios Needed |
|-----------------|--------------|-------------|----------------------|
| [`WrapperExistsError`](../lib/exceptions.py:103) | 107-113 | Constructor with `wrapper_path` parameter | Test creating exception with and without wrapper_path |
| [`WrapperNotFoundError`](../lib/exceptions.py:116) | 122-128 | Constructor with `searched_paths` parameter | Test creating exception with searched_paths list |
| [`WrapperGenerationError`](../lib/exceptions.py:131) | 140 | Constructor with extra `details` dict | Test with additional details parameter |
| [`AppNotFoundError`](../lib/exceptions.py:157) | 161-163 | Constructor | Test exception creation and app_name attribute |
| [`LaunchBlockedError`](../lib/exceptions.py:166) | 172-178 | Constructor with `details` parameter | Test with blocking reason and details |
| [`ForbiddenNameError`](../lib/exceptions.py:192) | 360-366, 371 | Constructor with `is_builtin=False`, `is_forbidden()` classmethod | Test user blocklist case, test is_forbidden() check |
| [`PathTraversalError`](../lib/exceptions.py:374) | 378-385 | Constructor with `base_dir` parameter | Test path traversal with base directory |
| [`InvalidFlatpakIdError`](../lib/exceptions.py:388) | 392-397 | Constructor with `reason` parameter | Test invalid ID with specific reason |

#### Recommended Tests

```python
# Test all exception constructors
def test_wrapper_exists_error_with_path():
    error = WrapperExistsError("firefox", "/home/user/bin/firefox")
    assert error.wrapper_name == "firefox"
    assert error.wrapper_path == "/home/user/bin/firefox"
    assert "wrapper_path" in error.details

def test_wrapper_not_found_error_with_searched_paths():
    error = WrapperNotFoundError("firefox", ["/bin", "/usr/bin"])
    assert error.searched_paths == ["/bin", "/usr/bin"]

def test_forbidden_name_error_user_blocklist():
    error = ForbiddenNameError("custom-cmd", is_builtin=False)
    assert "user blocklist" in str(error)
    assert error.is_builtin is False

def test_forbidden_name_is_forbidden_classmethod():
    assert ForbiddenNameError.is_forbidden("bash") is True
    assert ForbiddenNameError.is_forbidden("my-custom-app") is False

def test_path_traversal_error_with_base_dir():
    error = PathTraversalError("../../../etc/passwd", "/home/user")
    assert error.base_dir == "/home/user"
    assert "escapes base directory" in str(error)
```

---

### 2.2 lib/systemd_setup.py (60% coverage)

#### Functions Without Test Coverage

| Function | Lines | Description | Test Scenarios Needed |
|----------|-------|-------------|----------------------|
| [`_detect_flatpak_bin_dir()`](../lib/systemd_setup.py:58) | 58-93 | Flatpak binary directory detection with fallback | Test with flatpak --print-updated-env, fallback paths |
| [`check_prerequisites()`](../lib/systemd_setup.py:106) | 106-164 | Prerequisite checking with detailed errors | Test missing flatpak, missing wrapper script, non-writable bin_dir |
| [`install_cron_job()`](../lib/systemd_setup.py:394) | 394-449 | Cron fallback installation | Test crontab addition, existing cron detection |
| [`run()`](../lib/systemd_setup.py:451) | 451-480 | Main setup process | Test full setup flow, systemd available/unavailable |
| [`enable_app_service()`](../lib/systemd_setup.py:482) | 482-553 | App-specific service enable | Test service/timer file creation |
| [`disable_app_service()`](../lib/systemd_setup.py:555) | 555-611 | App-specific service disable | Test service/timer file removal |
| [`reload_services()`](../lib/systemd_setup.py:613) | 613-643 | Systemd daemon reload | Test daemon-reload execution |
| [`start_unit()`](../lib/systemd_setup.py:645) | 645-673 | Start systemd unit | Test unit start command |
| [`stop_unit()`](../lib/systemd_setup.py:675) | 675-703 | Stop systemd unit | Test unit stop command |
| [`restart_unit()`](../lib/systemd_setup.py:705) | 705-733 | Restart systemd unit | Test unit restart command |
| [`reload_unit()`](../lib/systemd_setup.py:735) | 735-763 | Reload systemd unit | Test unit reload command |
| [`show_unit_logs()`](../lib/systemd_setup.py:765) | 765-802 | Journal log viewing | Test journalctl command |
| [`list_all_units()`](../lib/systemd_setup.py:804) | 804-815 | List all flatpak units | Test unit file globbing |
| [`list_app_services()`](../lib/systemd_setup.py:817) | 817-826 | List app-specific services | Test timer file parsing |
| [`disable_systemd_units()`](../lib/systemd_setup.py:828) | 828-876 | Unit removal | Test unit disable and file removal |
| [`check_systemd_status()`](../lib/systemd_setup.py:878) | 878-1037 | Detailed status checking | Test status dict structure |

#### Recommended Tests

```python
def test_detect_flatpak_bin_dir_with_flatpak_env():
    # Mock subprocess to return PATH from flatpak --print-updated-env
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="PATH=/home/user/.local/share/flatpak/exports/bin:..."
        )
        setup = SystemdSetup()
        assert "flatpak" in setup.flatpak_bin_dir

def test_check_prerequisites_missing_flatpak():
    with patch("shutil.which", return_value=None):
        setup = SystemdSetup()
        assert setup.check_prerequisites() is False

def test_install_cron_job_existing_entry():
    with patch("shutil.which", return_value="/usr/bin/crontab"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="0 */6 * * * fplaunch-generate /home/user/bin"
            )
            setup = SystemdSetup()
            assert setup.install_cron_job() is True

def test_enable_app_service_creates_files():
    # Already tested in test_systemd_setup.py but needs more coverage
    pass

def test_check_systemd_status_structure():
    setup = SystemdSetup()
    status = setup.check_systemd_status()
    assert "enabled" in status
    assert "active" in status
    assert "units" in status
```

---

### 2.3 lib/manage.py (65% coverage)

#### Functions Without Test Coverage

| Function | Lines | Description | Test Scenarios Needed |
|----------|-------|-------------|----------------------|
| [`__init__`](../lib/manage.py:38) | 46-48 | Backward compatibility with positional bool args | Test old-style constructor call |
| [`log()`](../lib/manage.py:64) | 80 | Default log level case | Test with unknown level string |
| [`list_wrappers()`](../lib/manage.py:82) | 100-117 | Fallback wrapper detection with content parsing | Test non-wrapper-file detection via content |
| [`remove_wrapper()`](../lib/manage.py:143) | 186-194 | Hook scripts directory removal | Test with hooks_dir present |
| [`remove_wrapper()`](../lib/manage.py:143) | 219-224 | No files removed case | Test when wrapper doesn't exist |
| [`set_preference_all()`](../lib/manage.py:297) | 297-319 | Set preference for all wrappers | Test batch preference setting |
| [`show_info()`](../lib/manage.py:321) | 321-352 | Display wrapper information | Test info display |
| [`search_wrappers()`](../lib/manage.py:354) | 354-382 | Search wrappers by query | Test search functionality |
| [`list_managed_files()`](../lib/manage.py:384) | 384-483 | List all managed files | Test file type filtering |
| [`show_generated_files()`](../lib/manage.py:486) | 486-571 | Show generated files for app | Test with/without app_name |
| [`discover_features()`](../lib/manage.py:573) | 573-609 | Feature discovery display | Test feature list output |
| [`cleanup_obsolete()`](../lib/manage.py:611) | 611-690 | Obsolete wrapper cleanup | Test removal of obsolete wrappers |
| [`_resolve_alias_chain()`](../lib/manage.py:692) | 692-723 | Alias chain resolution | Test circular reference detection |
| [`_check_collision()`](../lib/manage.py:738) | 738-754 | Namespace collision check | Test wrapper and system command collision |
| [`create_alias()`](../lib/manage.py:756) | 756-863 | Alias creation with validation | Test collision detection, circular ref |
| [`block_app()`](../lib/manage.py:865) | 865-888 | Add to blocklist | Test blocklist file creation |
| [`unblock_app()`](../lib/manage.py:890) | 890-917 | Remove from blocklist | Test blocklist removal |
| [`set_environment_variable()`](../lib/manage.py:919) | 919-950 | Set env var for wrapper | Test env file creation/update |
| [`export_preferences()`](../lib/manage.py:952) | 952-993 | Export prefs to JSON | Test JSON export |
| [`import_preferences()`](../lib/manage.py:995) | 995-1041 | Import prefs from JSON | Test JSON import, old format |
| [`set_pre_launch_script()`](../lib/manage.py:1043) | 1043-1059 | Pre-launch script setup | Test script file creation |
| [`set_post_run_script()`](../lib/manage.py:1061) | 1061-1077 | Post-run script setup | Test script file creation |

---

### 2.4 lib/cleanup.py (66% coverage)

#### Functions Without Test Coverage

| Function | Lines | Description | Test Scenarios Needed |
|----------|-------|-------------|----------------------|
| [`_handle_wrapper_symlink()`](../lib/cleanup.py:175) | 177-183 | Symlink handling with target resolution | Test symlink to wrapper, broken symlink |
| [`_scan_man_pages()`](../lib/cleanup.py:185) | 191-194 | Man page scanning | Test man1 and man7 file detection |
| [`_scan_data_files()`](../lib/cleanup.py:210) | 215-217 | Data file scanning | Test recursive file detection |
| [`_scan_systemd_units()`](../lib/cleanup.py:219) | 224-230 | Systemd unit scanning | Test glob patterns for units |
| [`_scan_completion_files()`](../lib/cleanup.py:232) | 232-261 | Shell completion scanning | Test bash, zsh, fish completion detection |
| [`_scan_cron_entries()`](../lib/cleanup.py:263) | 263-290 | Cron entry scanning | Test crontab parsing |
| [`_has_cron_entries()`](../lib/cleanup.py:318) | 318-334 | Cron entry check | Test cron detection |
| [`perform_cleanup()`](../lib/cleanup.py:383) | 387-407 | Backup creation | Test backup functionality |
| [`_cleanup_systemd_units()`](../lib/cleanup.py:439) | 439-481 | Systemd unit cleanup | Test stop, disable, remove |
| [`_cleanup_cron_entries()`](../lib/cleanup.py:483) | 483-514 | Cron entry removal | Test crontab modification |
| [`_cleanup_man_pages()`](../lib/cleanup.py:539) | 544-554 | Empty directory removal | Test man dir cleanup |
| [`_cleanup_config_dir()`](../lib/cleanup.py:556) | 556-563 | Config dir removal | Test config dir cleanup |
| [`run()`](../lib/cleanup.py:589) | 589-613 | Main cleanup process | Test full cleanup flow |
| [`cleanup()`](../lib/cleanup.py:616) | 616-629 | Boolean cleanup method | Test boolean return |
| [`cleanup_app()`](../lib/cleanup.py:636) | 636-652 | Single app cleanup | Test specific app removal |

---

### 2.5 lib/flatpak_monitor.py (71% coverage)

#### Functions Without Test Coverage

| Function | Lines | Description | Test Scenarios Needed |
|----------|-------|-------------|----------------------|
| Import fallbacks | 36-40 | Watchdog not available fallback | Test with watchdog unavailable |
| Systemd import | 62-64 | systemd.daemon not available fallback | Test without systemd Python bindings |
| [`_init_lock()`](../lib/flatpak_monitor.py:85) | 91-92 | Threading lock init fallback | Test without threading module |
| [`_send_systemd_notify()`](../lib/flatpak_monitor.py:233) | 233-242 | Systemd notify support | Test READY=1 notification |
| [`start_monitoring()`](../lib/flatpak_monitor.py:244) | 244-276 | Full monitoring start | Test observer scheduling |
| [`stop_monitoring()`](../lib/flatpak_monitor.py:278) | 278-285 | Monitoring stop | Test observer stop/join |
| [`_on_flatpak_change()`](../lib/flatpak_monitor.py:320) | 320-336 | Change handler with debounce | Test debounce sleep, callback |
| [`_regenerate_wrappers()`](../lib/flatpak_monitor.py:347) | 347-389 | Wrapper regeneration | Test script execution, timeout |
| [`_signal_handler()`](../lib/flatpak_monitor.py:391) | 391-394 | Signal handling | Test SIGINT/SIGTERM |
| [`wait()`](../lib/flatpak_monitor.py:396) | 396-405 | Wait for completion | Test keyboard interrupt |
| [`main()`](../lib/flatpak_monitor.py:426) | 426-517 | CLI entry point | Test argparse, callback loading |

---

### 2.6 lib/cli.py (77% coverage)

#### Functions Without Test Coverage

| Function | Lines | Description | Test Scenarios Needed |
|----------|-------|-------------|----------------------|
| [`_instantiate_compat()`](../lib/cli.py:33) | 43 | self parameter check | Test with various class signatures |
| [`_instantiate_compat()`](../lib/cli.py:33) | 48-64 | TypeError fallback paths | Test fallback positional args |
| [`run_command()`](../lib/cli.py:67) | 87 | Non-description command execution | Test without status message |
| [`find_fplaunch_script()`](../lib/cli.py:94) | 96-105 | Script location search | Test candidate path checking |
| Various commands | Multiple | Many CLI commands | Test each subcommand |

---

### 2.7 lib/python_utils.py (79% coverage)

#### Functions Without Test Coverage

| Function | Lines | Description | Test Scenarios Needed |
|----------|-------|-------------|----------------------|
| [`user_config_dir()`](../lib/python_utils.py:23) | 23-30 | platformdirs fallback | Test without platformdirs package |
| [`user_data_dir()`](../lib/python_utils.py:32) | 32-39 | platformdirs fallback | Test without platformdirs package |
| [`canonicalize_path_no_resolve()`](../lib/python_utils.py:64) | 77-78 | Exception handling | Test with invalid path types |
| [`validate_home_dir()`](../lib/python_utils.py:81) | 81-104 | Home directory validation | Test symlink handling, outside HOME |
| [`is_wrapper_file()`](../lib/python_utils.py:107) | 107-144 | Wrapper file validation | Test size limit, binary content, missing markers |
| [`get_wrapper_id()`](../lib/python_utils.py:147) | 147-166 | ID extraction | Test comment-based ID fallback |
| [`sanitize_id_to_name()`](../lib/python_utils.py:169) | 194-198 | Exception fallback | Test with invalid input types |
| [`find_executable()`](../lib/python_utils.py:201) | 201-218 | Executable search | Test with path in PATH, absolute path |
| [`safe_mktemp()`](../lib/python_utils.py:221) | 221-252 | Temp file creation | Test with custom dir, template |
| [`acquire_lock()`](../lib/python_utils.py:255) | 255-286 | File-based locking | Test lock acquisition, timeout |
| [`release_lock()`](../lib/python_utils.py:289) | 289-313 | Lock release | Test PID validation |
| [`get_temp_dir()`](../lib/python_utils.py:316) | 316-329 | Temp dir selection | Test environment variable priority |
| CLI interface | 332-375 | Command line operations | Test each operation type |

---

## Part 3: Missing Edge Case Tests

### Empty Input Handling

- Test all functions with empty string inputs
- Test with None values where applicable
- Test with whitespace-only strings

### Boundary Conditions

- Test `is_wrapper_file()` with files at size limit (100KB)
- Test `acquire_lock()` at timeout boundary
- Test batch window/cooldown in event handler

### Error Message Validation

- Test that all exceptions include relevant details in messages
- Test that error messages contain actionable information

---

## Action Items

### Immediate Fixes (Incorrect Tests)

1. Fix import in [`test_force_interactive_verification.py`](../tests/python/test_force_interactive_verification.py:19)
2. Fix import in [`test_systemd_cli.py`](../tests/python/test_systemd_cli.py:20)
3. Fix import in [`test_watchdog_integration.py`](../tests/python/test_watchdog_integration.py:26)

### High Priority Test Additions

1. **exceptions.py**: Add tests for all exception constructors with various parameter combinations
2. **systemd_setup.py**: Add tests for cron fallback, status checking, unit management
3. **manage.py**: Add tests for alias management, blocklist, environment variables

### Medium Priority Test Additions

1. **cleanup.py**: Add tests for symlink handling, completion file scanning, cron cleanup
2. **flatpak_monitor.py**: Add tests for watchdog unavailable path, systemd notify
3. **python_utils.py**: Add tests for platformdirs fallback, lock mechanism

### Lower Priority

1. **cli.py**: Add comprehensive CLI subcommand tests
2. Edge case and boundary condition tests across all modules
