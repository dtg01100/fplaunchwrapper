# Changelog

All notable changes to fplaunchwrapper are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
