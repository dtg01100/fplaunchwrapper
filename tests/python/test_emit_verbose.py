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
                check=False, capture_output=True,
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
        code = """
from fplaunch.generate import WrapperGenerator
import io
from contextlib import redirect_stdout
g = WrapperGenerator('/tmp/test', True, True, True)
output = io.StringIO()
with redirect_stdout(output):
    g.generate_wrapper('org.mozilla.firefox')
content = output.getvalue()
print('SUCCESS' if 'File content for' in content and '#!/usr/bin/env bash' in content else 'FAILED')
"""
        success = self.run_emit_verbose_test(code, "generate emit verbose")
        assert success

    def test_manage_emit_verbose(self) -> None:
        """Test manage emit verbose shows preference content."""
        code = """
from fplaunch.manage import WrapperManager
import io
from contextlib import redirect_stdout
m = WrapperManager('/tmp/config', True, True, True)
output = io.StringIO()
with redirect_stdout(output):
    m.set_preference('firefox', 'flatpak')
content = output.getvalue()
print('SUCCESS' if 'File content for' in content and 'flatpak' in content else 'FAILED')
"""
        success = self.run_emit_verbose_test(code, "manage emit verbose")
        assert success

    def test_systemd_emit_verbose(self) -> None:
        """Test systemd emit verbose shows unit content."""
        code = """
from fplaunch.systemd_setup import SystemdSetup
import io
from contextlib import redirect_stdout
s = SystemdSetup(emit_mode=True, emit_verbose=True)
output = io.StringIO()
with redirect_stdout(output):
    s.install_systemd_units()
content = output.getvalue()
print('SUCCESS' if '[Unit]' in content and '[Service]' in content else 'FAILED')
"""
        success = self.run_emit_verbose_test(code, "systemd emit verbose")
        assert success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
