#!/usr/bin/env python3
"""Simple emit functionality tests using pytest."""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add lib to path
# Mock python_utils
sys.modules["python_utils"] = type(sys)("python_utils")
sys.modules["python_utils"].sanitize_string = lambda x: x
sys.modules["python_utils"].canonicalize_path_no_resolve = lambda x: x
sys.modules["python_utils"].validate_home_dir = lambda x: x
sys.modules["python_utils"].is_wrapper_file = lambda x: True
sys.modules["python_utils"].get_wrapper_id = lambda x: "org.test.app"
sys.modules["python_utils"].sanitize_id_to_name = lambda x: x.split(".")[-1].lower()
sys.modules["python_utils"].find_executable = lambda x: f"/usr/bin/{x}"
sys.modules["python_utils"].safe_mktemp = (
    lambda *args: f"/tmp/test_{args[0] if args else 'tmp'}"
)

try:
    from lib.generate import WrapperGenerator
    from lib.manage import WrapperManager
    from lib.systemd_setup import SystemdSetup

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
class TestEmitSimple:
    """Simple emit functionality tests."""

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
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_generate_emit_mode(self, temp_env) -> None:
        """Test generate emit mode."""
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            verbose=True,
            emit_mode=True,
        )

        from unittest.mock import patch

        with patch.object(
            generator,
            "get_installed_flatpaks",
            return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        # Verify no files created
        firefox_wrapper = temp_env["bin_dir"] / "firefox"
        assert not firefox_wrapper.exists()

    def test_manage_emit_mode(self, temp_env) -> None:
        """Test manage emit mode."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=True,
        )

        result = manager.set_preference("firefox", "flatpak")
        assert result is True

        # Verify no files created
        pref_file = temp_env["config_dir"] / "firefox.pref"
        assert not pref_file.exists()

    def test_systemd_emit_mode(self, temp_env) -> None:
        """Test systemd emit mode."""
        setup = SystemdSetup(bin_dir=str(temp_env["bin_dir"]), emit_mode=True)

        result = setup.install_systemd_units()
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
