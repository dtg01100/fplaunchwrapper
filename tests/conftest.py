"""Pytest configuration and fixtures for safe, isolated tests."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def isolated_home(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch):
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

	old_env = {key: os.environ.get(key) for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "FPLAUNCHWRAPPER_CONFIG")}

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

