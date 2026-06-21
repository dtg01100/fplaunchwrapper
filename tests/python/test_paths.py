#!/usr/bin/env python3
"""Focused pytest coverage for lib.paths."""

from pathlib import Path

import pytest

from lib.paths import (
    ensure_dir,
    get_default_bin_dir,
    get_default_cache_dir,
    get_default_config_dir,
    get_default_data_dir,
    get_lock_dir,
    get_scripts_dir,
    get_systemd_unit_dir,
    resolve_bin_dir,
)


class TestXdgDirResolution:
    """Test XDG directory resolution."""

    def test_default_config_dir_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        result = get_default_config_dir()
        assert result == Path.home() / ".config" / "fplaunchwrapper"

    def test_default_config_dir_with_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
        result = get_default_config_dir()
        assert result == Path("/custom/config/fplaunchwrapper")

    def test_default_config_dir_custom_app_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        result = get_default_config_dir("myapp")
        assert result == Path.home() / ".config" / "myapp"

    def test_default_data_dir_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        result = get_default_data_dir()
        assert result == Path.home() / ".local" / "share" / "fplaunchwrapper"

    def test_default_data_dir_with_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_DATA_HOME", "/custom/data")
        result = get_default_data_dir()
        assert result == Path("/custom/data/fplaunchwrapper")

    def test_default_cache_dir_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        result = get_default_cache_dir()
        assert result == Path.home() / ".cache" / "fplaunchwrapper"

    def test_default_cache_dir_with_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CACHE_HOME", "/custom/cache")
        result = get_default_cache_dir()
        assert result == Path("/custom/cache/fplaunchwrapper")


class TestSystemdUnitDir:
    """Test systemd unit directory resolution."""

    def test_systemd_unit_dir_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        result = get_systemd_unit_dir()
        assert result == Path.home() / ".config" / "systemd" / "user"

    def test_systemd_unit_dir_with_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
        result = get_systemd_unit_dir()
        assert result == Path("/custom/config/systemd/user")


class TestDerivedDirs:
    """Test directories derived from config dir."""

    def test_lock_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        result = get_lock_dir()
        assert result == Path.home() / ".config" / "fplaunchwrapper" / "locks"

    def test_scripts_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        result = get_scripts_dir()
        assert result == Path.home() / ".config" / "fplaunchwrapper" / "scripts"


class TestDefaultBinDir:
    """Test default bin directory."""

    def test_get_default_bin_dir(self) -> None:
        result = get_default_bin_dir()
        assert result == Path.home() / "bin"


class TestEnsureDir:
    """Test ensure_dir creates directories."""

    def test_ensure_dir_creates(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "dirs"
        result = ensure_dir(target)
        assert result == target
        assert target.exists()
        assert target.is_dir()

    def test_ensure_dir_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "existing"
        target.mkdir()
        result = ensure_dir(target)
        assert result == target
        assert target.exists()


class TestResolveBinDir:
    """Test bin directory resolution with fallback chain."""

    def test_explicit_dir(self) -> None:
        result = resolve_bin_dir(explicit_dir="/custom/bin")
        assert result == Path("/custom/bin")

    def test_config_dir_with_file(self, tmp_path: Path) -> None:
        bin_dir_file = tmp_path / "bin_dir"
        bin_dir_file.write_text("/from/config/file\n")
        result = resolve_bin_dir(config_dir=tmp_path)
        # /from/config/file is outside $HOME, so it must be rejected;
        # the function falls through to the default ~/bin.
        assert result == Path.home() / "bin", (
            f"Expected fallback to ~/bin for path outside $HOME, got {result}"
        )

    def test_config_dir_with_empty_file(self, tmp_path: Path) -> None:
        bin_dir_file = tmp_path / "bin_dir"
        bin_dir_file.write_text("   \n")
        result = resolve_bin_dir(config_dir=tmp_path)
        assert result == get_default_bin_dir()

    def test_config_dir_without_file(self, tmp_path: Path) -> None:
        result = resolve_bin_dir(config_dir=tmp_path)
        assert result == get_default_bin_dir()

    def test_fallback_to_default(self) -> None:
        result = resolve_bin_dir()
        assert result == get_default_bin_dir()

    def test_explicit_takes_priority(self, tmp_path: Path) -> None:
        bin_dir_file = tmp_path / "bin_dir"
        bin_dir_file.write_text("/from/config\n")
        result = resolve_bin_dir(explicit_dir="/explicit", config_dir=tmp_path)
        assert result == Path("/explicit")

    def test_explicit_dir_with_null_byte_falls_back(self) -> None:
        """A null-byte explicit_dir must drop to the default, not silently corrupt."""
        # "~\x00foo" triggers ValueError inside expanduser on POSIX.
        result = resolve_bin_dir(explicit_dir="~\x00bad")
        assert result == get_default_bin_dir()

    def test_config_dir_file_with_null_byte_falls_back(self, tmp_path: Path) -> None:
        """A bin_dir file containing a path expanduser rejects falls back too."""
        (tmp_path / "bin_dir").write_text("~\x00bad\n")
        result = resolve_bin_dir(config_dir=tmp_path)
        assert result == get_default_bin_dir()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
