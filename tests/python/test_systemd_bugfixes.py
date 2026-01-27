"""
Tests for systemd_setup bug fixes.

This test file validates fixes for critical bugs found during code review:
1. Glob pattern bug in list_all_units()
2. Shell injection vulnerability in enable_app_service()
3. Timer unit structure (removed incorrect [Service] section)
4. Bounds checking for split operations
5. Prerequisite checking with shutil.which()
6. Error visibility in disable_systemd_units()
7. Return value semantics
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))


class TestGlobPatternFix:
    """Test fix for glob pattern bug in list_all_units()."""

    def test_list_all_units_uses_separate_patterns(self):
        """Verify list_all_units() correctly lists all unit types."""
        from lib.systemd_setup import SystemdSetup

        temp_dir = Path(tempfile.mkdtemp(prefix="test_systemd_"))
        systemd_dir = temp_dir / "systemd" / "user"
        systemd_dir.mkdir(parents=True, exist_ok=True)

        try:
            setup = SystemdSetup(emit_mode=True)
            setup.systemd_unit_dir = systemd_dir

            (systemd_dir / "flatpak-wrappers.service").write_text("[Unit]\n")
            (systemd_dir / "flatpak-wrappers.path").write_text("[Path]\n")
            (systemd_dir / "flatpak-wrappers.timer").write_text("[Timer]\n")
            (systemd_dir / "flatpak-firefox.service").write_text("[Unit]\n")
            (systemd_dir / "other-unit.service").write_text("[Unit]\n")

            units = setup.list_all_units()

            assert len(units) == 4
            assert "flatpak-wrappers.service" in units
            assert "flatpak-wrappers.path" in units
            assert "flatpak-wrappers.timer" in units
            assert "flatpak-firefox.service" in units
            assert "other-unit.service" not in units

        finally:
            shutil.rmtree(temp_dir)

    def test_list_all_units_handles_missing_types(self):
        """Verify list_all_units() works when some unit types are missing."""
        from lib.systemd_setup import SystemdSetup

        temp_dir = Path(tempfile.mkdtemp(prefix="test_systemd_"))
        systemd_dir = temp_dir / "systemd" / "user"
        systemd_dir.mkdir(parents=True, exist_ok=True)

        try:
            setup = SystemdSetup(emit_mode=True)
            setup.systemd_unit_dir = systemd_dir

            (systemd_dir / "flatpak-only.service").write_text("[Unit]\n")

            units = setup.list_all_units()

            assert len(units) == 1
            assert "flatpak-only.service" in units

        finally:
            shutil.rmtree(temp_dir)


class TestShellInjectionFix:
    """Test fix for shell injection vulnerability in enable_app_service()."""

    def test_enable_app_service_with_shell_metacharacters(self):
        """Verify app_id with shell metacharacters is properly quoted."""
        from lib.systemd_setup import SystemdSetup

        temp_dir = Path(tempfile.mkdtemp(prefix="test_systemd_"))
        systemd_dir = temp_dir / "systemd" / "user"
        bin_dir = temp_dir / "bin"
        systemd_dir.mkdir(parents=True, exist_ok=True)
        bin_dir.mkdir(exist_ok=True)

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script="/usr/bin/wrapper",
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            app_id_with_special_chars = "app$var"

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = setup.enable_app_service(app_id_with_special_chars)

            assert result is True

            service_file = (
                systemd_dir / f"flatpak-wrapper-{app_id_with_special_chars}.service"
            )
            assert service_file.exists()

            content = service_file.read_text()
            assert "'app$var'" in content or '"app$var"' in content
            assert "/usr/bin/wrapper" in content

        finally:
            shutil.rmtree(temp_dir)

    def test_enable_app_service_with_spaces_in_paths(self):
        """Verify paths with spaces are properly quoted."""
        from lib.systemd_setup import SystemdSetup

        temp_dir = Path(tempfile.mkdtemp(prefix="test_systemd_"))
        systemd_dir = temp_dir / "systemd" / "user"
        bin_dir = temp_dir / "bin dir with spaces"
        systemd_dir.mkdir(parents=True, exist_ok=True)
        bin_dir.mkdir(exist_ok=True)

        try:
            setup = SystemdSetup(
                bin_dir=str(bin_dir),
                wrapper_script="/path with spaces/wrapper",
                emit_mode=False,
            )
            setup.systemd_unit_dir = systemd_dir

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = setup.enable_app_service("firefox")

            assert result is True

            service_file = systemd_dir / "flatpak-wrapper-firefox.service"
            content = service_file.read_text()

            assert (
                "'/path with spaces/wrapper'" in content
                or '"/path with spaces/wrapper"' in content
            )

        finally:
            shutil.rmtree(temp_dir)


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

        assert "Unit=flatpak-wrappers.service" in timer_content

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

            (systemd_dir / "flatpak-wrappers.service").write_text("[Unit]\n")

            with patch("shutil.which", return_value="/usr/bin/systemctl"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(
                        returncode=0,
                        stdout="MalformedOutput",
                    )

                    status = setup.check_systemd_status()

                    assert isinstance(status, dict)
                    assert "units" in status

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
            mock_which.side_effect = (
                lambda cmd: "/usr/bin/flatpak"
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


class TestErrorVisibilityFix:
    """Test fix for error visibility in disable_systemd_units()."""

    def test_disable_systemd_units_logs_individual_failures(self):
        """Verify disable_systemd_units() logs failures for each unit."""
        from lib.systemd_setup import SystemdSetup

        temp_dir = Path(tempfile.mkdtemp(prefix="test_systemd_"))
        systemd_dir = temp_dir / "systemd" / "user"
        systemd_dir.mkdir(parents=True, exist_ok=True)

        try:
            setup = SystemdSetup(emit_mode=False)
            setup.systemd_unit_dir = systemd_dir

            (systemd_dir / "flatpak-wrappers.service").write_text("[Unit]\n")
            (systemd_dir / "flatpak-wrappers.timer").write_text("[Timer]\n")

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                with patch.object(setup, "log") as mock_log:

                    def unlink_side_effect():
                        raise PermissionError("Cannot remove file")

                    with patch("pathlib.Path.unlink", side_effect=unlink_side_effect):
                        result = setup.disable_systemd_units()

                    error_logs = [
                        call_args
                        for call_args in mock_log.call_args_list
                        if len(call_args[0]) > 1 and call_args[0][1] == "error"
                    ]
                    assert len(error_logs) >= 2

            assert result is False

        finally:
            shutil.rmtree(temp_dir)


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
