"""Pytest configuration and fixtures for safe, isolated tests."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def mock_flatpak_binary(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
):
    """Provide a mock flatpak binary to prevent real flatpak execution during tests.

    This fixture creates a fake flatpak script that logs calls instead of executing
    actual flatpak commands. This ensures tests don't run real flatpaks when they
    execute generated wrapper scripts.

    The mock flatpak:
    - Logs all calls to a file for debugging
    - Returns appropriate exit codes for common commands
    - Simulates flatpak list, info, and run commands

    Yields path to mock flatpak log file for inspection if needed.
    """
    # Create a mock flatpak binary
    mock_bin_dir = tmp_path_factory.mktemp("mock_bin")
    flatpak_path = mock_bin_dir / "flatpak"
    flatpak_log = mock_bin_dir / "flatpak_calls.log"

    # Create the mock flatpak script
    flatpak_script = f'''#!/bin/sh
# Mock flatpak binary for testing - prevents real flatpak execution

# Log all calls for debugging
echo "$(date -Iseconds): flatpak $@" >> "{flatpak_log}"

# Handle common flatpak commands
case "$1" in
	list)
		# Simulate flatpak list output
		echo "org.mozilla.Firefox\tlatest\tstable\tflathub"
		exit 0
		;;
	info)
		# Simulate flatpak info output
		if [ -n "$2" ]; then
			echo "ID: $2"
			echo "Ref: app/$2/x86_64/stable"
			echo "Arch: x86_64"
			echo "Branch: stable"
			echo "Runtime: org.freedesktop.Platform/x86_64/23.08"
			exit 0
		fi
		exit 1
		;;
	run)
		# Simulate flatpak run - don't actually launch anything
		if [ -n "$2" ]; then
			echo "Mock flatpak run: $@" >> "{flatpak_log}"
			exit 0
		fi
		exit 1
		;;
	override)
		# Simulate flatpak override command
		echo "Mock flatpak override: $@" >> "{flatpak_log}"
		exit 0
		;;
	*)
		# Unknown command
		echo "Mock flatpak: unknown command $1" >> "{flatpak_log}"
		exit 1
		;;
esac
'''

    flatpak_path.write_text(flatpak_script)
    flatpak_path.chmod(0o755)

    # Prepend mock bin dir to PATH
    old_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{mock_bin_dir}:{old_path}")

    yield flatpak_log

    # Cleanup is handled by tmp_path_factory automatically


@pytest.fixture
def isolated_home(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
):
    """Provide an isolated HOME/XDG layout and convenience paths.

    Yields a SimpleNamespace with:
      - home, config_dir, data_dir, cache_dir, bin_dir (Path objects)
      - app_launcher_kwargs: pre-built kwargs for AppLauncher
    Restores the original environment after use and removes the temp tree.
    """

    base_dir = tmp_path_factory.mktemp("fp_home")

    config_root = base_dir / ".config"
    data_root = base_dir / ".local" / "share"
    cache_root = base_dir / ".cache"

    config_dir = config_root / "fplaunchwrapper"
    data_dir = data_root / "fplaunchwrapper"
    cache_dir = cache_root / "fplaunchwrapper"
    bin_dir = base_dir / "bin"

    for path in (config_dir, data_dir, cache_dir, bin_dir):
        path.mkdir(parents=True, exist_ok=True)

    old_env = {
        key: os.environ.get(key)
        for key in (
            "HOME",
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
            "FPLAUNCHWRAPPER_CONFIG",
        )
    }

    monkeypatch.setenv("HOME", str(base_dir))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_root))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_root))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_root))
    # Not currently used, but set for future-proofing
    monkeypatch.setenv("FPLAUNCHWRAPPER_CONFIG", str(config_dir))

    env = SimpleNamespace(
        home=base_dir,
        config_dir=config_dir,
        data_dir=data_dir,
        cache_dir=cache_dir,
        bin_dir=bin_dir,
    )
    env.app_launcher_kwargs = {"config_dir": str(config_dir), "bin_dir": str(bin_dir)}

    try:
        yield env
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        shutil.rmtree(base_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def cleanup_legacy_config():
    """Remove any default config dir created during tests.

    This guards against tests that might hit the legacy ~/.config/fplaunchwrapper path.
    """

    yield

    legacy_config = Path.home() / ".config" / "fplaunchwrapper"
    if legacy_config.exists():
        shutil.rmtree(legacy_config, ignore_errors=True)
