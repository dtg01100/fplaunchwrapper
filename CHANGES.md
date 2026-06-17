# Changelog

All notable changes to fplaunchwrapper are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `AGENTS.md` technical reference and CLIO project methodology
- `uv-python-workflow` skill for managing Python development tasks
- `[monitor]` extra to make the watchdog dependency optional
- New `fplaunch` Python package entry point alongside the existing `lib` package
- `--config-dir` flag on `fplaunch-config` (argparse) that was previously missing
- `build_config_manager(ctx)` helper in `lib.cli_imports`, mirroring `build_manager(ctx)` so Click commands can honour `ctx.obj["config_dir"]`
- `fplaunch config` restructured to a Click group with all 7 subcommands: show, init, cron-interval, block, unblock, list-presets, get-preset
- `fplaunch-config` (argparse) extended with the same surface (show, init, cron-interval were previously Click-only)
- Man pages for `fplaunch-config`, `fplaunch-launch`, and `fplaunch-monitor`
- Comprehensive test coverage: 16 new test files (10,211 lines) targeting every previously-under-covered module. 594 new tests, raising the total from 1462 to 2056 (+2 skipped) and bringing total lib coverage from 51% to 99%

### Fixed
- `get_temp_dir` now raises `OSError` when no candidate is writable, instead of returning an unwritable path
- `resolve_bin_dir` falls back to the default bin dir when `expanduser` rejects the input (e.g. embedded null byte), instead of silently using the malformed path
- `WrapperManager` and `AppLauncher` propagate `--verbose` and the active profile through the Click context
- `EnhancedConfigManager` now persists the active profile across instances
- Path-safety exceptions in wrapper lookup fail closed instead of silently allowing unsafe access
- `subprocess.run` calls in `lib/launch.py` set `check=False` explicitly to avoid raising on non-zero exit
- Stale `PydanticAppPreferences` import paths and `ValidationError` references in `config_manager`
- `--config-dir` was silently ignored by both the `fplaunch config` (Click) and `fplaunch-config` (argparse) subcommands. `EnhancedConfigManager` and `create_config_manager()` now accept a `config_dir` argument and the Click command reads it from `ctx.obj`. Regression tests pin the new behaviour.
- `--config-dir` was also dropped by every `profiles` and `presets` Click subcommand. All 10 callsites swapped to `build_config_manager(ctx)` so the override flows through.
- Skipped tests that were silently no-oping; full suite now runs
- Locale-dependent test (`test_name_property`) pins `LANG=en_US`
- CI: pinned `pytest<9.1.0` in `pyproject.toml` and `.github/workflows/ci.yml` to avoid a pytest 9.1.0 regression in `_pytest/fixtures.SubRequest.__init__` that raised `Could not obtain a node for scope "Scope.Session"` on autouse session-scope fixtures. Affected 808 tests across 30+ files; the existing conftest.py workaround for pytest 9.0.x remains effective. PyPI has no 9.2.x or 10.x release yet, so bumping higher is not an option; remove the upper bound once pytest ships a fixed release.
- Pydantic-dependent tests in `test_config_manager_coverage.py` now use `pytest.importorskip("pydantic")` so they skip cleanly in the `.[monitor]` install used by CI, instead of crashing with `ModuleNotFoundError`
- Pre-existing ruff warnings in `test_rich_output.py` (two F841 unused-locals, one W292 missing newline) cleaned up
- **Security**: `PydanticAppPreferences.validate_custom_args` had a logic bug where bare ``--flag`` custom args (no ``=``) bypassed the dangerous-character check. The ``else:`` clause of ``if "=" in arg:`` was at the wrong indentation level and was tied to the outer ``if arg.startswith("--"):`` instead, so bare-flag dangerous chars (e.g. ``--flag|pipe``) were silently accepted. Restructured the validator to set ``value = arg.split("=", 1)[1] if "=" in arg else arg`` and then scan dangerous chars against the chosen value, which catches both ``--key=bad`` and ``--flagbad`` forms. Added a regression test in `test_cli_profiles_validation_coverage.py` that exercises every dangerous char in a bare-flag form.
- **Security**: `EnhancedConfigManager._apply_unvalidated_config` (the fallback path used when Pydantic is not installed) silently bypassed the security-critical checks. When Pydantic is absent, a malicious config could set `pre_launch_script` to `/etc/passwd` or push dangerous chars through `custom_args` without rejection. Refactored `lib/config_validation.py` to extract three pure-Python helpers (`_validate_failure_mode_safety`, `_validate_custom_args_safety`, `_validate_script_path_safety`) that both the Pydantic field validators AND `_apply_unvalidated_config` call. The security model is now identical in both paths: the field-level Pydantic constraints (log_level pattern, cron_interval range, etc.) are still skipped in the unvalidated path, but the security-critical field-level validators (script-path safety, custom-arg dangerous-char rejection, hook-failure-mode whitelist) are ALWAYS enforced regardless of which path runs.
- **Security (C1)**: `flatpak run "$ID" "$@"` invocations in the generated wrapper template, `lib/launch.py`, and `lib/portal_launcher.py` now insert the `--` end-of-options separator before user arguments. A user passing `--filesystem=host` to a wrapper no longer silently widens the sandbox at the flatpak layer.
- **Security (C2)**: Generated wrapper scripts now run with `set -eo pipefail`, `IFS=$'\n\t'`, and `umask 077` at the top of the file. `set -u` is intentionally omitted because the template references `$1`, `$2`, and several optional env vars before the user invokes the wrapper; enforcing `set -u` would make those references blow up on a no-arg call.
- **Security (C3)**: Wrapper, preference, profile, and systemd-unit writes now go through new `atomic_write_text` / `atomic_write_bytes` helpers in `lib/python_utils.py` that write to a sibling temp file and `os.replace` onto the destination. This eliminates the TOCTOU window where an attacker plants a symlink at the destination between the existence check and the write. `Path.write_text` patches no longer reach the write path; tests now patch `tempfile.mkstemp`.
- **Security (C4)**: `cleanup` no longer clobbers the user's crontab when `crontab -l` fails. It now aborts the cron-write step and logs the reason. The old behavior treated a failed read as an empty crontab and overwrote the user's entries via `crontab -`. The same fix is applied to `systemd_setup.install_cron_job`.
- **Security (C5)**: `EnhancedConfigManager.save_config` (TOML and fallback paths) and the three profile writers (`create_profile`, `export_profile`, `import_profile`) now use the atomic write helper. Profile files are written with mode `0o600`.
- **Security (C6)**: `systemd_setup.generate_systemd_service` and the cron-script builder now `shlex.quote` interpolated values (`wrapper_script`, `bin_dir`). A user-supplied path containing shell metacharacters no longer breaks out of the systemd unit syntax or the cron field columns.
- **Cleanup (C7)**: `fplaunch install` and `fplaunch uninstall` accept `--yes` (short `-y`) to skip the confirmation prompt. Without `--yes`, non-TTY invocations are rejected with exit code 1 instead of silently passing `-y` to `flatpak` and executing a typo.
- **Cleanup (C8)**: `--remove-data` is documented as a destructive, irreversible action in its help text.
- **Cleanup (C9)**: `fplaunch systemd disable` now accepts `--yes` for parity with `cleanup` and respects `FPWRAPPER_FORCE=1`. Without `--yes` on a non-TTY stdin, the command aborts instead of silently deleting the user's unit files.
- **Cleanup (M1)**: The `cli.py` -> `cli_commands.py` -> `cli_generation.py` / `cli_inspect.py` circular import is broken. Each `cli_*.py` module now imports `run_command` directly from `lib.cli_utils` at module level, removing the four `from lib.cli import run_command` workarounds scattered through `cli_generation.install`, `cli_generation.uninstall`, `cli_generation.remove`, and `cli_inspect.manifest`.
- **Cleanup (M2)**: `lib.safety` no longer re-exports `python_utils` helpers (`is_wrapper_file`, `get_wrapper_id`, `canonicalize_path_no_resolve`, `validate_home_dir`). Callers import directly from `lib.python_utils`. The `is_wrapper_file = None` shim in `lib.cleanup` is gone, replaced by an unconditional `from .python_utils import is_wrapper_file`. The `safety_mod` alias in `lib.fplaunch` is kept for backward compatibility.
- **Cleanup (M3)**: The 44-line `if __name__ == "__main__":` argv-dispatch ladder that lived at the bottom of `lib/python_utils.py` is now a proper module at `lib/python_utils_cli.py` with `argparse`, an explicit exit-code contract, and `__all__`. `lib/common.sh` was updated to invoke the new module. The utilities module is now a pure library with no side-effects on import.
- **Cleanup (M14-M16)**: Nine `except (OSError, subprocess.CalledProcessError)` clauses were dead code because `subprocess.run(check=False)` never raises `CalledProcessError`. They now catch `(OSError, subprocess.TimeoutExpired)` instead. Affected: `cleanup._cleanup_cron_entries`, `cleanup._scan_cron_entries`, `cleanup.perform_cleanup`, `cleanup.run`, `cleanup.cleanup`, `systemd_setup.install_systemd_units`, `systemd_setup.install_cron_job`, `systemd_setup.disable_systemd_units`, and `launch._resolve_flatpak_id`.
- **Cleanup (M17)**: The system-wide completion scanner in `cleanup._scan_completion_files` no longer uses a broad `*fplaunch*` glob over `/usr/local/share/...`. It matches only the documented filenames (`fplaunch_completion.bash`, `_fplaunch`, `fplaunch.fish`) and only runs when `os.geteuid() == 0`, so a non-root user can no longer accidentally delete unrelated third-party completion files.
- **Cleanup (M18)**: `launch.py` no longer applies the over-broad `_sanitize_arg` allowlist (which accepted `=` and silently mangled values) to user args. Combined with the `--` separator fix (C1), this closes the confused-deputy where `--filesystem=host` was passed to flatpak instead of the app.
- **Tests**: Several tests that previously expected the old behavior (`crontab -l` failure swallowed, broad glob matching, missing `--yes`, no `--` separator, `Path.open` mocking the atomic write path) were updated to match the new contracts. The fallback-config tests now patch `tempfile.mkstemp` instead of `Path.open`. Cleanup-related tests using `os.geteuid=0` mock the new euid check.
- `LaunchMethod` and `HookFailureMode` enums replace string-based dispatch
- `black` replaced by `ruff format` as the sole formatter
- `pydantic` moved from `robustness` to `dev` dependencies (pydantic remains a soft runtime dep — the `_parse_config_data` validator path is guarded by `PYDANTIC_AVAILABLE` and falls back to the unvalidated path when pydantic is absent)
- Pre-commit hooks pinned to Python 3.12, restricted `pydocstyle` to missing-docstring rules
- GitHub Actions updated to `actions/setup-python@v5` and `softprops/action-gh-release@v2`
- `pyproject.toml` and `Makefile` cleaned of dead entries

### Removed
- `lib/fplaunch/` shim package (replaced by direct `lib/` package layout)
- Stale `docs/reports/` and obsolete watchdog integration test
- Unused mypy `[[tool.mypy.overrides]]` and stray type-ignore comments

## [1.4.0] - 2026-04-08

### Added
- Python 3.12 and 3.13 support in classifiers
- MANIFEST.in for complete source distributions
- Comprehensive .gitignore with modern Python patterns
- Python package entry point for main fplaunch command
- Zsh shell completion (`fplaunch_completion.zsh`)
- Fish shell completion (`fplaunch_completion.fish`)

### Fixed
- Entry point format in pyproject.toml for main fplaunch command
- Shell script executable permissions in packaging

### Improved
- Centralized path resolution via `lib/paths.py` (reduces duplication)
- Standardized ImportError handling via `lib/import_utils.py`
- `lib/config_manager.py` now uses centralized path functions
- `lib/python_utils.py` now uses centralized path functions
- Removed legacy dead code (unused shell scripts in lib/)

### Removed
- Legacy shell scripts (alias.sh, env.sh, pref.sh, script.sh, wrapper.sh) - replaced by Python implementation

## [1.3.0] - 2025-11-26

### Added
- Complete Python migration from shell scripts
- Comprehensive wrapper management system
- Flatpak integration with watchdog monitoring
- Configuration management with Pydantic validation
- Multi-platform support (systemd, cron, etc.)
- Enhanced CLI with Click framework
- Rich terminal output with progress indicators
- Comprehensive test suite with pytest

### Fixed
- Critical security issues in shell scripts
- Path handling edge cases
- Permission management improvements

### Changed
- Moved from bash-based to Python-based implementation
- Restructured package organization
- Enhanced error handling throughout

## [1.1.0] - 2025-03-15

### Added
- Initial Flatpak wrapper generation
- Basic wrapper management
- Shell script completion
- Man page documentation
- RPM and Debian packaging

### Fixed
- Shell script robustness issues
- File operation safety improvements

## Earlier Versions

See individual RELEASE_*.md files in the repository root for detailed information about earlier versions.

## Comparison Links

- [1.3.0...HEAD](https://github.com/dtg01100/fplaunchwrapper/compare/v1.3.0...HEAD) - Unreleased changes
- [1.1.0...1.3.0](https://github.com/dtg01100/fplaunchwrapper/compare/v1.1.0...v1.3.0) - Changes in 1.3.0
