#!/usr/bin/env python3
"""Pytest tests for emit verbose functionality."""

import subprocess
import sys
from pathlib import Path

import pytest


# Add lib to path
class TestEmitVerbose:
    """Test emit verbose content inspection."""

    def run_emit_verbose_test(self, python_code, description):
        """Run Python code and check for success markers."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", python_code],
                check=False,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                timeout=30,
            )
            output = result.stdout + result.stderr
            return "SUCCESS" in output and result.returncode == 0
        except Exception:
            return False

    def test_generate_emit_verbose(self) -> None:
        """Test generate emit verbose shows wrapper content."""
        from lib.generate import WrapperGenerator

        content = WrapperGenerator("/tmp/test", None, True, True, True).create_wrapper_script(
            "firefox",
            "org.mozilla.firefox",
        )
        assert "#!/usr/bin/env bash" in content

    def test_manage_emit_verbose(self) -> None:
        """Test manage emit verbose shows preference content."""
        from lib.manage import WrapperManager
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp())
        m = WrapperManager(config_dir=str(tmp), verbose=False, emit_mode=False)
        assert m.set_preference("firefox", "flatpak") is True
        content = (tmp / "firefox.pref").read_text()
        assert "flatpak" in content

    def test_systemd_emit_verbose(self) -> None:
        """Test systemd emit verbose shows unit content."""
        from lib.systemd_setup import SystemdSetup

        s = SystemdSetup(emit_mode=True, emit_verbose=True)
        service = s.create_service_unit()
        assert "[Unit]" in service and "[Service]" in service


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
