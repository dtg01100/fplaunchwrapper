#!/usr/bin/env python3
"""Pytest tests for final fplaunchwrapper validation."""

import io
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
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
    from fplaunch.manage import WrapperManager
    from fplaunch.systemd_setup import SystemdSetup

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
class TestFinalValidation:
    """Final validation tests for fplaunchwrapper."""

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

    def test_core_emit_functionality(self, temp_env) -> None:
        """Test core emit functionality works."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # In emit mode, operations should succeed without modifying files
        result = manager.set_preference("firefox", "flatpak")
        assert result is True
        
        # Verify no files were actually created (emit mode doesn't modify)
        pref_file = Path(temp_env["config_dir"]) / "firefox.pref"
        assert not pref_file.exists()

    def test_safety_features(self, temp_env) -> None:
        """Test safety features - no side effects."""
        # Count files before
        before_files = {f for f in temp_env["temp_dir"].rglob("*") if f.is_file()}

        # Run emit operations
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=True,
            emit_verbose=True,
        )
        manager.set_preference("firefox", "flatpak")

        setup = SystemdSetup(
            bin_dir=str(temp_env["bin_dir"]), emit_mode=True, emit_verbose=True,
        )
        setup.install_systemd_units()

        # Count files after
        after_files = {f for f in temp_env["temp_dir"].rglob("*") if f.is_file()}

        # Should be no new files
        assert before_files == after_files

    def test_error_handling(self, temp_env) -> None:
        """Test error handling in emit mode."""
        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=True, emit_mode=True,
        )

        # Test invalid preference
        output = io.StringIO()
        with redirect_stdout(output):
            result = manager.set_preference("test", "invalid")

        assert result is False

    def test_performance(self, temp_env) -> None:
        """Test performance - emit operations are fast."""
        import time

        manager = WrapperManager(
            config_dir=str(temp_env["config_dir"]), verbose=False, emit_mode=True,
        )

        start_time = time.time()
        for i in range(10):
            manager.set_preference(f"app{i}", "flatpak")
        end_time = time.time()

        # Should complete quickly
        duration = end_time - start_time
        assert duration < 1.0  # Less than 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
