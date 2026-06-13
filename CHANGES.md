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
- Man pages for `fplaunch-config`, `fplaunch-launch`, and `fplaunch-monitor`

### Fixed
- `get_temp_dir` now raises `OSError` when no candidate is writable, instead of returning an unwritable path
- `resolve_bin_dir` falls back to the default bin dir when `expanduser` rejects the input (e.g. embedded null byte), instead of silently using the malformed path
- `WrapperManager` and `AppLauncher` propagate `--verbose` and the active profile through the Click context
- `EnhancedConfigManager` now persists the active profile across instances
- Path-safety exceptions in wrapper lookup fail closed instead of silently allowing unsafe access
- `subprocess.run` calls in `lib/launch.py` set `check=False` explicitly to avoid raising on non-zero exit
- Stale `PydanticAppPreferences` import paths and `ValidationError` references in `config_manager`
- `--config-dir` was silently ignored by both the `fplaunch config` (Click) and `fplaunch-config` (argparse) subcommands. `EnhancedConfigManager` and `create_config_manager()` now accept a `config_dir` argument and the Click command reads it from `ctx.obj`. Regression tests pin the new behaviour.
- Skipped tests that were silently no-oping; full suite now runs
- Locale-dependent test (`test_name_property`) pins `LANG=en_US`

### Changed
- `lib/config_manager.py` split into `config_manager`, `config_models`, `config_validation`, `config_manager_cli`, `config_manager_presets`, and `config_constants`
- `lib/cli.py` split into `cli_generation`, `cli_inspect`, `cli_profiles`, `cli_presets`, `cli_system`, `cli_systemd`, and `cli_utils`
- `LaunchMethod` and `HookFailureMode` enums replace string-based dispatch
- `black` replaced by `ruff format` as the sole formatter
- `pydantic` moved from `robustness` to `dev` dependencies
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
