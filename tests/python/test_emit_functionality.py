#!/usr/bin/env python3
"""Pytest tests for fplaunchwrapper emit functionality."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add lib to path
# Mock python_utils to avoid import issues
sys.modules["python_utils"] = type(sys)("python_utils")
python_utils_mock = sys.modules["python_utils"]
python_utils_mock.sanitize_string = lambda x: x
python_utils_mock.canonicalize_path_no_resolve = lambda x: x
python_utils_mock.validate_home_dir = lambda x: x
python_utils_mock.is_wrapper_file = lambda x: True
python_utils_mock.get_wrapper_id = lambda x: "org.test.app"
python_utils_mock.sanitize_id_to_name = lambda x: x.split(".")[-1].lower()
python_utils_mock.find_executable = lambda x: f"/usr/bin/{x}"
python_utils_mock.safe_mktemp = lambda *args: f"/tmp/test_{args[0] if args else 'tmp'}"

# Import the module to test
try:
    from fplaunch.generate import WrapperGenerator

    GENERATE_AVAILABLE = True
except ImportError:
    GENERATE_AVAILABLE = False

try:
    from fplaunch.manage import WrapperManager

    MANAGE_AVAILABLE = True
except ImportError:
    MANAGE_AVAILABLE = False

try:
    from fplaunch.systemd_setup import SystemdSetup

    SYSTEMD_AVAILABLE = True
except ImportError:
    SYSTEMD_AVAILABLE = False


@pytest.mark.skipif(
    not GENERATE_AVAILABLE, reason="WrapperGenerator tests disabled when WrapperGenerator not available",
)
class TestEmitFunctionality:
    """Test emit functionality."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp())
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"
        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_generate_emit_mode(self, mock_subprocess, temp_env) -> None:
        """Test wrapper generation in emit mode."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "org.mozilla.firefox"
        mock_subprocess.return_value = mock_result

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]), verbose=True, emit_mode=True,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        # Verify no files created
        firefox_wrapper = temp_env["bin_dir"] / "firefox"
        assert not firefox_wrapper.exists()

    @patch("subprocess.run")
    def test_generate_emit_verbose_mode(self, mock_subprocess, temp_env) -> None:
        """Test wrapper generation with emit verbose."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=True,
            emit_verbose=True,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

    @patch("subprocess.run")
    def test_manage_emit_mode(self, mock_subprocess, temp_env) -> None:
        """Test preference management in emit mode."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        result = manager.set_preference("firefox", "flatpak")
        assert result is True

        # Verify no files created
        pref_file = temp_env["config_dir"] / "firefox.pref"
        assert not pref_file.exists()

    @patch("subprocess.run")
    def test_manage_emit_verbose_mode(self, mock_subprocess, temp_env) -> None:
        """Test preference management with emit verbose."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=True,
            emit_verbose=True,
        )

        result = manager.set_preference("firefox", "flatpak")
        assert result is True

    def test_systemd_emit_mode(self, temp_env) -> None:
        """Test systemd setup in emit mode."""
        if not SYSTEMD_AVAILABLE:
            pytest.skip("SystemdSetup not available")

        setup = SystemdSetup(bin_dir=str(temp_env["bin_dir"]), emit_mode=True)

        result = setup.install_systemd_units()
        assert result is True

    def test_systemd_emit_verbose_mode(self, temp_env) -> None:
        """Test systemd setup with emit verbose."""
        if not SYSTEMD_AVAILABLE:
            pytest.skip("SystemdSetup not available")

        setup = SystemdSetup(
            bin_dir=str(temp_env["bin_dir"]), emit_mode=True, emit_verbose=True,
        )

        result = setup.install_systemd_units()
        assert result is True

    def test_emit_mode_no_side_effects(self, temp_env) -> None:
        """Test that emit mode creates no side effects."""
        if not (GENERATE_AVAILABLE and MANAGE_AVAILABLE and SYSTEMD_AVAILABLE):
            pytest.skip("Required modules not available")

        # Count files before
        before_count = sum(1 for _ in temp_env["temp_dir"].rglob("*") if _.is_file())

        # Run emit operations
        generator = WrapperGenerator(bin_dir=str(temp_env["bin_dir"]), emit_mode=True)
        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.test.app"],
        ):
            generator.generate_wrapper("org.test.app")

        manager = WrapperManager(config_dir=str(temp_env["config_dir"]), emit_mode=True)
        manager.set_preference("test", "flatpak")

        setup = SystemdSetup(bin_dir=str(temp_env["bin_dir"]), emit_mode=True)
        setup.install_systemd_units()

        # Count files after
        after_count = sum(1 for _ in temp_env["temp_dir"].rglob("*") if _.is_file())

        # Should be no new files
        assert before_count == after_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
