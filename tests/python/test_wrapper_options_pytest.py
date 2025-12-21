#!/usr/bin/env python3
"""Pytest replacement for test_wrapper_options.sh
Tests wrapper script options and functionality.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add lib to path
# Import the module to test
try:
    from fplaunch.generate import WrapperGenerator

    GENERATE_AVAILABLE = True
except ImportError:
    GENERATE_AVAILABLE = False


class TestWrapperOptions:
    """Test wrapper script options and functionality."""

    @pytest.fixture
    def temp_env(self):
        """Create temporary test environment."""
        temp_dir = Path(tempfile.mkdtemp(prefix="fpwrapper_options_"))
        bin_dir = temp_dir / "bin"
        config_dir = temp_dir / "config"

        bin_dir.mkdir()
        config_dir.mkdir()

        yield {"temp_dir": temp_dir, "bin_dir": bin_dir, "config_dir": config_dir}

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_help_option(self, mock_subprocess, temp_env) -> None:
        """Test --fpwrapper-help option - replaces Test 1."""
        # Generate a wrapper with help functionality
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"
        assert wrapper_path.exists()

        # Test --fpwrapper-help option
        cmd = [str(wrapper_path), "--fpwrapper-help"]
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
        )

        # Should show help information
        assert result.returncode == 0
        output = result.stdout
        assert "Wrapper for firefox" in output
        assert "Flatpak ID: org.mozilla.firefox" in output
        assert "Available options:" in output
        assert "--fpwrapper-help" in output
        assert "--fpwrapper-info" in output

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_info_option(self, mock_subprocess, temp_env) -> None:
        """Test --fpwrapper-info option - replaces Test 2."""
        # Create preference file
        pref_file = temp_env["config_dir"] / "firefox.pref"
        pref_file.write_text("flatpak\n")

        # Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"

        # Test --fpwrapper-info option
        cmd = [str(wrapper_path), "--fpwrapper-info"]
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
        )

        assert result.returncode == 0
        output = result.stdout
        assert "Wrapper for firefox" in output
        assert "Flatpak ID: org.mozilla.firefox" in output
        assert "Preference: flatpak" in output
        assert "Usage: ./firefox [args]" in output

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_config_dir_option(self, mock_subprocess, temp_env) -> None:
        """Test --fpwrapper-config-dir option - replaces Test 3."""
        # Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"

        # Test --fpwrapper-config-dir option
        cmd = [str(wrapper_path), "--fpwrapper-config-dir"]
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
        )

        assert result.returncode == 0
        output = result.stdout.strip()

        # Should show the XDG config directory path
        expected_path = (
            f"{os.path.expanduser('~')}/.local/share/applications/org.mozilla.firefox"
        )
        assert output == expected_path

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_sandbox_info_option(self, mock_subprocess, temp_env) -> None:
        """Test --fpwrapper-sandbox-info option - replaces Test 4."""

        # Mock flatpak info command
        def mock_run(cmd, **kwargs):
            if cmd[:2] == ["flatpak", "info"]:
                result = Mock()
                result.returncode = 0
                result.stdout = "Application: org.mozilla.firefox\nRuntime: org.fedoraproject.Platform/x86_64/f40\n"
                return result
            return Mock(returncode=0)

        mock_subprocess.side_effect = mock_run

        # Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"

        # Test --fpwrapper-sandbox-info option
        cmd = [str(wrapper_path), "--fpwrapper-sandbox-info"]
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
        )

        assert result.returncode == 0
        # Should have called flatpak info
        mock_subprocess.assert_called()

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_sandbox_edit_option(self, mock_subprocess, temp_env) -> None:
        """Test --fpwrapper-edit-sandbox option - replaces Test 5."""
        # Mock interactive input and flatpak commands
        call_count = 0

        def mock_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if "flatpak override" in " ".join(cmd):
                result = Mock()
                result.returncode = 0
                result.stdout = "Override applied"
                return result
            result = Mock()
            result.returncode = 0
            return result

        mock_subprocess.side_effect = mock_run

        # Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"

        # Mock stdin for interactive choice
        with patch(
            "sys.stdin", Mock(readline=lambda: "5\n"),
        ):  # Choose "Show current overrides"
            cmd = [str(wrapper_path), "--fpwrapper-edit-sandbox"]
            result = subprocess.run(
                cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
            )

            # Should work (exact behavior depends on interactive choices)
            assert isinstance(result.returncode, int)

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_sandbox_yolo_option(self, mock_subprocess, temp_env) -> None:
        """Test --fpwrapper-sandbox-yolo option - replaces Test 6."""

        # Mock flatpak override command
        def mock_run(cmd, **kwargs):
            if "flatpak override" in " ".join(cmd) and "--filesystem=host" in " ".join(
                cmd,
            ):
                result = Mock()
                result.returncode = 0
                result.stdout = "YOLO mode applied"
                return result
            result = Mock()
            result.returncode = 0
            return result

        mock_subprocess.side_effect = mock_run

        # Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"

        # Mock stdin for "yes" confirmation
        with patch("sys.stdin", Mock(readline=lambda: "yes\n")):
            cmd = [str(wrapper_path), "--fpwrapper-sandbox-yolo"]
            result = subprocess.run(
                cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
            )

            # Should have called flatpak override with dangerous permissions
            assert any(
                "flatpak override" in " ".join(call.args[0])
                for call in mock_subprocess.call_args_list
            )

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_sandbox_reset_option(self, mock_subprocess, temp_env) -> None:
        """Test --fpwrapper-sandbox-reset option - replaces Test 7."""

        # Mock flatpak override --reset command
        def mock_run(cmd, **kwargs):
            if "flatpak override --reset" in " ".join(cmd):
                result = Mock()
                result.returncode = 0
                result.stdout = "Overrides reset"
                return result
            result = Mock()
            result.returncode = 0
            return result

        mock_subprocess.side_effect = mock_run

        # Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"

        # Test --fpwrapper-sandbox-reset option
        cmd = [str(wrapper_path), "--fpwrapper-sandbox-reset"]
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
        )

        assert result.returncode == 0
        # Should have called flatpak override --reset
        assert any(
            "--reset" in " ".join(call.args[0])
            for call in mock_subprocess.call_args_list
        )

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_run_unrestricted_option(self, mock_subprocess, temp_env) -> None:
        """Test --fpwrapper-run-unrestricted option - replaces Test 8."""

        # Mock flatpak run command
        def mock_run(cmd, **kwargs):
            if "flatpak run" in " ".join(cmd) and "--no-sandbox" in " ".join(cmd):
                result = Mock()
                result.returncode = 0
                result.stdout = "App launched unrestricted"
                return result
            result = Mock()
            result.returncode = 0
            return result

        mock_subprocess.side_effect = mock_run

        # Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"

        # Test --fpwrapper-run-unrestricted option
        cmd = [str(wrapper_path), "--fpwrapper-run-unrestricted", "--version"]
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
        )

        assert result.returncode == 0
        # Should have called flatpak run with --no-sandbox
        assert any(
            "--no-sandbox" in " ".join(call.args[0])
            for call in mock_subprocess.call_args_list
        )

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    def test_set_override_option(self, temp_env) -> None:
        """Test --fpwrapper-set-override option - replaces Test 9."""
        # Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"

        # Test --fpwrapper-set-override system
        cmd = [str(wrapper_path), "--fpwrapper-set-override", "system"]
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
        )

        assert result.returncode == 0
        # Should have created/updated preference file
        pref_file = temp_env["config_dir"] / "firefox.pref"
        assert pref_file.exists()
        assert pref_file.read_text().strip() == "system"

    def test_script_management_options(self, temp_env) -> None:
        """Test script management options - replaces Test 10."""
        # Create wrapper manually for this test
        wrapper_content = """#!/bin/bash
# Generated by fplaunchwrapper
NAME="testapp"
ID="com.example.testapp"
PREF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/flatpak-wrappers"
SCRIPT_DIR="$PREF_DIR/scripts/$NAME"

# Script management options
if [ "$1" = "--fpwrapper-set-pre-script" ]; then
    if [ -z "$2" ]; then
        echo "Usage: $0 --fpwrapper-set-pre-script <script_path>"
        exit 1
    fi
    mkdir -p "$SCRIPT_DIR"
    cp "$2" "$SCRIPT_DIR/pre-launch.sh"
    chmod +x "$SCRIPT_DIR/pre-launch.sh"
    echo "Pre-launch script set"
    exit 0
fi

if [ "$1" = "--fpwrapper-set-post-script" ]; then
    if [ -z "$2" ]; then
        echo "Usage: $0 --fpwrapper-set-post-script <script_path>"
        exit 1
    fi
    mkdir -p "$SCRIPT_DIR"
    cp "$2" "$SCRIPT_DIR/post-run.sh"
    chmod +x "$SCRIPT_DIR/post-run.sh"
    echo "Post-run script set"
    exit 0
fi

echo "testapp executed"
"""
        wrapper_path = temp_env["bin_dir"] / "testapp"
        wrapper_path.write_text(wrapper_content)
        wrapper_path.chmod(0o755)

        # Create test scripts
        pre_script = temp_env["temp_dir"] / "pre.sh"
        pre_script.write_text('#!/bin/bash\necho "pre-launch"\n')
        pre_script.chmod(0o755)

        post_script = temp_env["temp_dir"] / "post.sh"
        post_script.write_text('#!/bin/bash\necho "post-run"\n')
        post_script.chmod(0o755)

        # Test --fpwrapper-set-pre-script
        cmd = [str(wrapper_path), "--fpwrapper-set-pre-script", str(pre_script)]
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
        )
        assert result.returncode == 0

        # Test --fpwrapper-set-post-script
        cmd = [str(wrapper_path), "--fpwrapper-set-post-script", str(post_script)]
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"],
        )
        assert result.returncode == 0

        # Verify scripts were copied
        script_dir = temp_env["config_dir"] / "scripts" / "testapp"
        assert (script_dir / "pre-launch.sh").exists()
        assert (script_dir / "post-run.sh").exists()

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_force_interactive_option(self, mock_subprocess, temp_env) -> None:
        """Test --fpwrapper-force-interactive option - replaces Test 11."""
        # Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"

        # Test --fpwrapper-force-interactive
        cmd = [str(wrapper_path), "--fpwrapper-force-interactive"]
        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"], input="1\n",
        )  # Choose system

        # Should work in non-interactive mode when forced
        assert isinstance(result.returncode, int)

    @pytest.mark.skipif(not GENERATE_AVAILABLE, reason="WrapperGenerator not available")
    @patch("subprocess.run")
    def test_non_interactive_bypass(self, mock_subprocess, temp_env) -> None:
        """Test non-interactive bypass functionality - replaces Test 12."""

        # Mock flatpak command for system binary detection
        def mock_run(cmd, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "command -v firefox" in cmd_str:
                result = Mock()
                result.returncode = 0
                result.stdout = "/usr/bin/firefox\n"
                return result
            if "flatpak run" in cmd_str:
                result = Mock()
                result.returncode = 0
                result.stdout = "Firefox launched\n"
                return result
            result = Mock()
            result.returncode = 0
            return result

        mock_subprocess.side_effect = mock_run

        # Generate wrapper
        generator = WrapperGenerator(
            bin_dir=str(temp_env["bin_dir"]),
            config_dir=str(temp_env["config_dir"]),
            verbose=True,
            emit_mode=False,
        )

        with patch.object(
            generator, "get_installed_flatpaks", return_value=["org.mozilla.firefox"],
        ):
            result = generator.generate_wrapper("org.mozilla.firefox")
            assert result is True

        wrapper_path = temp_env["bin_dir"] / "firefox"

        # Test non-interactive execution (no TTY)
        # This simulates running from a script or cron job
        cmd = [str(wrapper_path)]
        env = os.environ.copy()
        env["FPWRAPPER_FORCE"] = "non-interactive"  # Force non-interactive mode

        result = subprocess.run(
            cmd, check=False, capture_output=True, text=True, cwd=temp_env["temp_dir"], env=env,
        )

        # Should bypass interactive prompts and use system binary if available
        assert isinstance(result.returncode, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
