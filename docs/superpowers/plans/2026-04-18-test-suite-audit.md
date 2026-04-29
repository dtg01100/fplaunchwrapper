# Test Suite Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove redundant and low-value Python tests while preserving or improving meaningful behavioral coverage for the existing CLI and wrapper-management code.

**Architecture:** Keep the existing `tests/python` layout, but reduce broad smoke and edge-case files that mostly assert non-crash behavior or generic Python behavior. Strengthen the remaining suite by keeping focused regression tests, tightening weak CLI assertions to enforce actual command contracts, and updating `tests/README.md` so it describes the current suite accurately.

**Tech Stack:** Python, pytest, Click `CliRunner`, `unittest.mock`, Rich console output, existing `lib.*` modules.

---

## File Structure

- Delete: `tests/python/test_comprehensive.py`
  Why: broad smoke tests that mostly shell out to `python -m lib.cli` and assert commands did not fail, overlapping stronger CLI tests.
- Delete: `tests/python/test_focused.py`
  Why: import/constructor smoke coverage with fake `sys.modules["python_utils"]` stubs and little behavioral signal.
- Modify: `tests/python/test_edge_cases_comprehensive.py`
  Why: reduce broad "returns bool" and generic filesystem/concurrency tests to a small set of project-specific behavior assertions.
- Modify: `tests/python/test_subcommands_no_crash.py`
  Why: replace pure non-crash coverage with strict help/usage/import behavior checks that still exercise the CLI surface area.
- Modify: `tests/python/test_missing_cli_coverage.py`
  Why: remove assertions that normalize known CLI bugs and enforce concrete exit-code/output behavior for profiles, presets, install/uninstall, and manifest commands.
- Modify: `tests/python/test_management_functions_pytest.py`
  Why: trim low-value performance/concurrency/corruption assertions that do not protect a specific manager contract.
- Modify: `tests/python/test_python_utils.py`
  Why: keep direct utility contracts, remove generic bash/config smoke that does not test `lib.python_utils` behavior.
- Modify: `tests/README.md`
  Why: replace stale coverage/benchmark claims and outdated file references with a current description of the suite and how to run it.

### Task 1: Remove Dead-Weight Smoke Suites

**Files:**
- Delete: `tests/python/test_comprehensive.py`
- Delete: `tests/python/test_focused.py`
- Test: `tests/python/test_regression_fixes.py`
- Test: `tests/python/test_missing_cli_coverage.py`
- Test: `tests/python/test_subcommands_no_crash.py`

- [ ] **Step 1: Write the failing test**

Create a temporary audit guard file so the deletion is justified by explicit keeper coverage instead of intuition.

```python
from pathlib import Path


def test_keeper_suites_cover_cli_and_regression_contracts():
    test_dir = Path(__file__).resolve().parent

    assert (test_dir / "test_regression_fixes.py").exists()
    assert (test_dir / "test_missing_cli_coverage.py").exists()
    assert (test_dir / "test_subcommands_no_crash.py").exists()
```

Save it as `tests/python/test_suite_audit_guard.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_suite_audit_guard.py -v`
Expected: FAIL with `file or directory not found` before the guard file exists.

- [ ] **Step 3: Write minimal implementation**

Create `tests/python/test_suite_audit_guard.py` with the exact contents from Step 1, then remove the low-value smoke suites.

```python
from pathlib import Path


def test_keeper_suites_cover_cli_and_regression_contracts():
    test_dir = Path(__file__).resolve().parent

    assert (test_dir / "test_regression_fixes.py").exists()
    assert (test_dir / "test_missing_cli_coverage.py").exists()
    assert (test_dir / "test_subcommands_no_crash.py").exists()
```

Delete these files entirely:

```text
tests/python/test_comprehensive.py
tests/python/test_focused.py
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/python/test_suite_audit_guard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/python/test_suite_audit_guard.py tests/python/test_comprehensive.py tests/python/test_focused.py
git commit -m "test: remove redundant smoke suites"
```

### Task 2: Trim Edge-Case and Manager Tests to Real Contracts

**Files:**
- Modify: `tests/python/test_edge_cases_comprehensive.py:46-583`
- Modify: `tests/python/test_management_functions_pytest.py:151-277`
- Modify: `tests/python/test_python_utils.py:106-199`
- Test: `tests/python/test_edge_cases_comprehensive.py`
- Test: `tests/python/test_management_functions_pytest.py`
- Test: `tests/python/test_python_utils.py`

- [ ] **Step 1: Write the failing test**

Add one new strict behavior test to `tests/python/test_management_functions_pytest.py` that proves invalid preferences are rejected without writing a `.pref` file.

```python
@pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
def test_invalid_preference_does_not_write_file(self, temp_env) -> None:
    wrapper_path = temp_env["bin_dir"] / "firefox"
    wrapper_path.write_text("#!/bin/bash\necho firefox\n")
    wrapper_path.chmod(0o755)

    manager = WrapperManager(
        config_dir=str(temp_env["config_dir"]),
        bin_dir=str(temp_env["bin_dir"]),
        verbose=True,
        emit_mode=False,
    )

    result = manager.set_preference("firefox", "flatpak;rm -rf /")

    assert result is False
    assert not (temp_env["config_dir"] / "firefox.pref").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_management_functions_pytest.py::TestManagementFunctions::test_invalid_preference_does_not_write_file -v`
Expected: FAIL with `not found` because the test does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement the new strict manager test above, then remove low-value cases that only assert non-crash or generic runtime behavior.

Make these reductions in `tests/python/test_management_functions_pytest.py`:

```python
    @pytest.mark.skipif(not MANAGE_AVAILABLE, reason="WrapperManager not available")
    def test_invalid_preference_does_not_write_file(self, temp_env) -> None:
        wrapper_path = temp_env["bin_dir"] / "firefox"
        wrapper_path.write_text("#!/bin/bash\necho firefox\n")
        wrapper_path.chmod(0o755)

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=False,
        )

        result = manager.set_preference("firefox", "flatpak;rm -rf /")

        assert result is False
        assert not (temp_env["config_dir"] / "firefox.pref").exists()
```

Delete these low-signal test methods from the same file because they do not protect a stable manager contract:

```text
test_edge_cases_and_security
test_performance_and_resource_efficiency
test_concurrent_operation_testing
test_data_integrity_validation
```

In `tests/python/test_edge_cases_comprehensive.py`, delete broad tests whose only assertion is `assert isinstance(result, bool)` or which only test generic filesystem/Python behavior. Remove the following methods/classes entirely:

```text
TestInputValidationEdgeCases.test_extremely_long_inputs
TestInputValidationEdgeCases.test_unicode_and_special_characters
TestInputValidationEdgeCases.test_malformed_flatpak_ids
TestInputValidationEdgeCases.test_path_injection_attempts
TestSystemResourceEdgeCases
TestExternalDependencyFailures
TestConcurrencyAndRaceConditions
TestTimeoutAndInterruptHandling
TestMemoryAndResourceLimits
TestEncodingAndUnicodeEdgeCases
TestBoundaryConditionEdgeCases
TestAdditionalSystemResourceEdgeCases
```

Keep the direct `lib.python_utils` contract tests in the lower section only if they assert a concrete return value or sanitization rule.

In `tests/python/test_python_utils.py`, delete sections that do not test `lib.python_utils` directly:

```text
class TestBashIntegration
class TestPerformance
class TestConfiguration
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/python/test_management_functions_pytest.py tests/python/test_edge_cases_comprehensive.py tests/python/test_python_utils.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/python/test_management_functions_pytest.py tests/python/test_edge_cases_comprehensive.py tests/python/test_python_utils.py
git commit -m "test: keep only behavior-driven manager and edge checks"
```

### Task 3: Tighten CLI Tests to Enforce Actual Behavior

**Files:**
- Modify: `tests/python/test_subcommands_no_crash.py:22-276`
- Modify: `tests/python/test_missing_cli_coverage.py:42-393`
- Test: `tests/python/test_subcommands_no_crash.py`
- Test: `tests/python/test_missing_cli_coverage.py`
- Reference: `lib/cli.py:192-245`
- Reference: `lib/cli.py:724-1041`

- [ ] **Step 1: Write the failing test**

Add a strict manifest failure assertion to `tests/python/test_missing_cli_coverage.py`.

```python
@patch("subprocess.run")
def test_manifest_failure_returns_error_exit_and_message(self, mock_run, runner):
    mock_run.return_value = Mock(returncode=1, stderr="App not found")

    result = runner.invoke(cli_module.cli, ["manifest", "org.example.app"])

    assert result.exit_code == 1
    assert "failed to get manifest" in result.output.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_missing_cli_coverage.py::TestManifestCLI::test_manifest_failure_returns_error_exit_and_message -v`
Expected: FAIL with `not found` because the new strict test does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add the new manifest failure test above, then tighten and prune the CLI suites.

In `tests/python/test_missing_cli_coverage.py`, replace permissive assertions with strict ones that match current `lib/cli.py` behavior:

```python
    def test_profiles_create_requires_name(self, runner, temp_config_dir):
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["profiles", "create"])

            assert result.exit_code != 0
            assert "missing argument" in result.output.lower()

    def test_profiles_invalid_action(self, runner, temp_config_dir):
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["profiles", "invalid"])

            assert result.exit_code != 0
            assert "no such command" in result.output.lower()

    def test_presets_get_invalid_preset(self, runner, temp_config_dir):
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["presets", "get", "nonexistent"])

            assert result.exit_code == 1
            assert "not found" in result.output.lower()

    def test_presets_add_requires_name_and_permissions(self, runner, temp_config_dir):
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(temp_config_dir)}):
            result = runner.invoke(cli_module.cli, ["presets", "add", "test"])

            assert result.exit_code == 1
            assert "at least one permission is required" in result.output.lower()

    @patch("subprocess.run")
    def test_manifest_failure_returns_error_exit_and_message(self, mock_run, runner):
        mock_run.return_value = Mock(returncode=1, stderr="App not found")

        result = runner.invoke(cli_module.cli, ["manifest", "org.example.app"])

        assert result.exit_code == 1
        assert "failed to get manifest" in result.output.lower()
```

Delete duplicate or contradictory tests from the same file:

```text
TestProfilesCLI.test_profiles_list_without_action
TestUninstallCLI.test_install_flatpak_failure
TestManifestCLI.test_manifest_failure
TestManifestCLI.test_manifest_without_app_name
TestManifestCLI.test_manifest_requires_app_name
```

In `tests/python/test_subcommands_no_crash.py`, replace generic `result.exception is None` checks with a smaller strict matrix of CLI contracts. Keep only tests that verify help text, usage errors, and command importability. Replace the broad `test_all_commands_with_help_flag_do_not_crash` loop with this exact parametric test:

```python
@pytest.mark.parametrize(
    "cmd",
    [
        [],
        ["generate"],
        ["list"],
        ["launch"],
        ["cleanup"],
        ["config"],
        ["monitor"],
        ["search"],
        ["install"],
        ["uninstall"],
        ["manifest"],
        ["set-pref"],
        ["systemd"],
        ["profiles"],
        ["presets"],
    ],
)
def test_help_pages_return_zero(self, runner, cmd):
    result = runner.invoke(cli, cmd + ["--help"])

    assert result.exit_code == 0
    assert "usage:" in result.output.lower()
```

Delete tests that only assert commands "do not crash" without checking a user-visible contract, including these methods:

```text
test_commands_without_required_args_do_not_crash
test_systemd_subcommands_do_not_crash
test_profiles_subcommands_with_args_do_not_crash
test_presets_add_with_or_without_permission_does_not_crash
test_presets_add_with_permission_does_not_crash
test_presets_remove_does_not_crash
test_emit_mode_prevents_crashes_in_destructive_commands
test_empty_invocation_does_not_crash
test_multiple_flags_do_not_crash
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/python/test_missing_cli_coverage.py tests/python/test_subcommands_no_crash.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/python/test_missing_cli_coverage.py tests/python/test_subcommands_no_crash.py
git commit -m "test: tighten cli behavior assertions"
```

### Task 4: Refresh Test Documentation

**Files:**
- Modify: `tests/README.md:1-216`
- Test: `tests/README.md`

- [ ] **Step 1: Write the failing test**

Add a documentation smoke test that checks the README no longer references deleted files and does mention the current pytest entrypoint.

```python
from pathlib import Path


def test_tests_readme_mentions_pytest_and_not_deleted_files():
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text()

    assert "pytest tests/python -v" in readme
    assert "test_comprehensive.py" not in readme
    assert "test_focused.py" not in readme
```
```

Append it to `tests/python/test_suite_audit_guard.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/python/test_suite_audit_guard.py::test_tests_readme_mentions_pytest_and_not_deleted_files -v`
Expected: FAIL with `not found` because the new test does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Append the audit guard test above to `tests/python/test_suite_audit_guard.py`, then rewrite `tests/README.md` to describe the current suite without stale metrics.

Use this exact README content:

```markdown
# fplaunchwrapper Test Suite

The primary automated test suite lives under `tests/python` and is run with `pytest`.

## What These Tests Cover

- Focused regression tests for previously fixed bugs
- CLI behavior tests using Click's `CliRunner`
- Wrapper generation and wrapper option behavior
- Configuration, profiles, presets, and manager operations
- Utility-level contracts in `lib.python_utils`

## What This Suite Does Not Guarantee

- Exact coverage percentages or benchmark numbers
- Zero real subprocess usage in every test file
- Full end-to-end validation of shell/adversarial test paths

## Running Tests

Run the full Python suite:

```bash
pytest tests/python -v
```

Run one file while iterating:

```bash
pytest tests/python/test_regression_fixes.py -v
```

Run a single test:

```bash
pytest tests/python/test_missing_cli_coverage.py::TestManifestCLI::test_manifest_failure_returns_error_exit_and_message -v
```

## Test Design Guidelines

- Prefer focused behavioral assertions over broad smoke tests.
- Do not keep tests that only prove code "did not crash".
- When fixing a bug, add or update a regression test that states the specific contract.
- Use `tmp_path`, fixtures, and mocking to isolate file-system and subprocess side effects where practical.
- Keep helper logic small inside the test file unless multiple files need the same fixture.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/python/test_suite_audit_guard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/README.md tests/python/test_suite_audit_guard.py
git commit -m "docs: update test suite guidance"
```

### Task 5: Final Verification

**Files:**
- Test: `tests/python/test_suite_audit_guard.py`
- Test: `tests/python/test_management_functions_pytest.py`
- Test: `tests/python/test_edge_cases_comprehensive.py`
- Test: `tests/python/test_python_utils.py`
- Test: `tests/python/test_missing_cli_coverage.py`
- Test: `tests/python/test_subcommands_no_crash.py`
- Test: `tests/python/test_regression_fixes.py`

- [ ] **Step 1: Run focused edited-suite verification**

Run: `pytest tests/python/test_suite_audit_guard.py tests/python/test_management_functions_pytest.py tests/python/test_edge_cases_comprehensive.py tests/python/test_python_utils.py tests/python/test_missing_cli_coverage.py tests/python/test_subcommands_no_crash.py tests/python/test_regression_fixes.py -v`
Expected: PASS

- [ ] **Step 2: Run broader Python suite verification**

Run: `pytest tests/python -v`
Expected: PASS

- [ ] **Step 3: Commit final cleanup state**

```bash
git add tests/python tests/README.md
git commit -m "test: streamline and strengthen suite coverage"
```
