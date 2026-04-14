"""
Tests for systemd_setup bug fixes.

This test file validates fixes for critical bugs found during code review:
1. Timer unit structure (removed incorrect [Service] section)
2. Bounds checking for split operations
3. Prerequisite checking with shutil.which()
4. Return value semantics
"""

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest


class TestTimerUnitStructureFix:
    """Test fix for timer unit structure (removed [Service] section)."""

    def test_timer_unit_has_no_service_section(self):
        """Verify timer unit does not contain [Service] section."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup(emit_mode=True)
        timer_content = setup.create_timer_unit()

        assert "[Unit]" in timer_content
        assert "[Timer]" in timer_content
        assert "[Install]" in timer_content
        assert "[Service]" not in timer_content

    def test_timer_unit_references_service(self):
        """Verify timer unit properly references the service unit."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup(emit_mode=True)
        timer_content = setup.create_timer_unit()

        assert "Unit=fplaunch-wrapper.service" in timer_content

    def test_timer_unit_has_correct_sections(self):
        """Verify timer unit has all required sections and no extras."""
        from lib.systemd_setup import SystemdSetup

        setup = SystemdSetup(emit_mode=True)
        timer_content = setup.create_timer_unit()

        sections = [
            line.strip() for line in timer_content.split("\n") if line.startswith("[")
        ]

        assert "[Unit]" in sections
        assert "[Timer]" in sections
        assert "[Install]" in sections
        assert len([s for s in sections if s.startswith("[")]) == 3


class TestBoundsCheckingFix:
    """Test fix for bounds checking in check_systemd_status()."""

    def test_check_systemd_status_handles_malformed_output(self):
        """Verify check_systemd_status() handles output without '=' separator."""
        from lib.systemd_setup import SystemdSetup

        temp_dir = Path(tempfile.mkdtemp(prefix="test_systemd_"))
        systemd_dir = temp_dir / "systemd" / "user"
        systemd_dir.mkdir(parents=True, exist_ok=True)

        try:
            setup = SystemdSetup(emit_mode=False)
            setup.systemd_unit_dir = systemd_dir

            (systemd_dir / "fplaunch-wrapper.service").write_text("[Unit]\n")

            with patch("shutil.which", return_value="/usr/bin/systemctl"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(
                        returncode=0,
                        stdout="MalformedOutput",
                    )

                    status = setup.check_systemd_status()

                    assert isinstance(status, dict)
                    assert "service" in status
                    assert "timer" in status

        finally:
            shutil.rmtree(temp_dir)

    def test_check_systemd_status_handles_empty_output(self):
        """Verify check_systemd_status() handles empty output."""
        from lib.systemd_setup import SystemdSetup

        temp_dir = Path(tempfile.mkdtemp(prefix="test_systemd_"))
        systemd_dir = temp_dir / "systemd" / "user"
        systemd_dir.mkdir(parents=True, exist_ok=True)

        try:
            setup = SystemdSetup(emit_mode=False)
            setup.systemd_unit_dir = systemd_dir

            (systemd_dir / "flatpak-wrappers.timer").write_text("[Timer]\n")

            with patch("shutil.which", return_value="/usr/bin/systemctl"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(
                        returncode=0,
                        stdout="",
                    )

                    status = setup.check_systemd_status()

                    assert isinstance(status, dict)

        finally:
            shutil.rmtree(temp_dir)


class TestPrerequisiteCheckingFix:
    """Test fix for prerequisite checking with shutil.which()."""

    def test_check_prerequisites_with_path_command(self):
        """Verify prerequisite check uses shutil.which() for commands in PATH."""
        from lib.systemd_setup import SystemdSetup

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: (
                "/usr/bin/flatpak"
                if cmd == "flatpak"
                else "/usr/bin/python"
                if cmd == "python"
                else None
            )

            setup = SystemdSetup(wrapper_script="python")

            with patch("os.access", return_value=True):
                result = setup.check_prerequisites()

            assert result is True

    def test_check_prerequisites_with_absolute_path(self):
        """Verify prerequisite check uses os.path.exists() for absolute paths."""
        from lib.systemd_setup import SystemdSetup

        temp_dir = Path(tempfile.mkdtemp(prefix="test_bin_"))
        script = temp_dir / "wrapper.sh"
        script.write_text("#!/bin/bash\necho test")
        script.chmod(0o755)

        try:
            with patch("shutil.which", return_value="/usr/bin/flatpak"):
                setup = SystemdSetup(wrapper_script=str(script))
                result = setup.check_prerequisites()

            assert result is True

        finally:
            shutil.rmtree(temp_dir)

    def test_check_prerequisites_with_python_module(self):
        """Verify prerequisite check handles 'python -m module' correctly."""
        from lib.systemd_setup import SystemdSetup

        with patch("shutil.which", return_value="/usr/bin/flatpak"):
            setup = SystemdSetup(
                wrapper_script=f"{sys.executable} -m fplaunch.generate"
            )
            result = setup.check_prerequisites()

        assert result is True


class TestReturnValueSemanticsFix:
    """Test fix for return value semantics."""

    def test_disable_systemd_units_returns_true_when_nothing_to_disable(self):
        """Verify disable_systemd_units() returns True when no units exist."""
        from lib.systemd_setup import SystemdSetup

        temp_dir = Path(tempfile.mkdtemp(prefix="test_systemd_"))

        try:
            setup = SystemdSetup(emit_mode=False)
            setup.systemd_unit_dir = temp_dir / "nonexistent"

            result = setup.disable_systemd_units()

            assert result is True

        finally:
            shutil.rmtree(temp_dir)

    def test_disable_systemd_units_returns_true_on_success(self):
        """Verify disable_systemd_units() returns True on successful removal."""
        from lib.systemd_setup import SystemdSetup

        temp_dir = Path(tempfile.mkdtemp(prefix="test_systemd_"))
        systemd_dir = temp_dir / "systemd" / "user"
        systemd_dir.mkdir(parents=True, exist_ok=True)

        try:
            setup = SystemdSetup(emit_mode=False)
            setup.systemd_unit_dir = systemd_dir

            (systemd_dir / "flatpak-wrappers.service").write_text("[Unit]\n")

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = setup.disable_systemd_units()

            assert result is True

        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
