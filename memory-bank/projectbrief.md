# fplaunchwrapper Project Brief

## Project Overview
fplaunchwrapper is a comprehensive Flatpak wrapper management system written in Python. It provides tools for:
- Generating intelligent wrappers for Flatpak applications
- Managing wrapper preferences and configuration
- Monitoring Flatpak installation changes
- Cleaning up wrapper artifacts
- Setting up systemd user services

## Current Status
- Version: 1.3.0
- Architecture: Hybrid Python/Bash (lib/ contains real implementations, fplaunch/ contains re-export stubs)
- Main entry points:  - fplaunch-cli
  - fplaunch-generate
  - fplaunch-manage
  - fplaunch-launch
  - fplaunch-cleanup
  - fplaunch-setup-systemd
  - fplaunch-config
  - fplaunch-monitor

## Key Implementation Details
- Real module code is in lib/ directory (cleanup.py, generate.py, manage.py, etc.)
- Package is configured as `fplaunch` with `package-dir = {"fplaunch" = "lib"}` in pyproject.toml
- However, a fplaunch/ directory exists containing stub files that re-export from lib/
- During pytest, imports work correctly using the fplaunch/ package directory
- The fplaunch.cli module uses Click framework for CLI parsing

## Test Suite
- 283 tests total in tests/python/
- Tests verify cleanup, configuration, generation, launching, management, and edge cases
- Test infrastructure was fixed to use proper package structure
