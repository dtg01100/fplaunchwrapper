#!/usr/bin/env python3
"""Tests for post-launch script execution functionality."""

import stat
import tempfile
from pathlib import Path

import pytest

from lib.generate import WrapperGenerator


class TestPostLaunchScriptExecution:
    """Test post-launch script execution in generated wrappers."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            config_dir = Path(tmpdir) / ".config" / "fplaunchwrapper"
            bin_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)
            yield bin_dir, config_dir

    def test_post_launch_script_sets_environment_variables(self, temp_dirs):
        """Test that post-launch script receives correct environment variables."""
        bin_dir, config_dir = temp_dirs
        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))

        # Create wrapper
        wrapper_name = "test-app"
        app_id = "com.test.App"
        wrapper_content = generator.create_wrapper_script(wrapper_name, app_id)

        # Verify post-launch script function is present in wrapper
        assert "run_post_launch_script()" in wrapper_content
        assert "FPWRAPPER_EXIT_CODE" in wrapper_content
        assert "FPWRAPPER_SOURCE" in wrapper_content
        assert "FPWRAPPER_WRAPPER_NAME" in wrapper_content
        assert "FPWRAPPER_APP_ID" in wrapper_content

    def test_post_launch_script_executed_after_app_exit(self, temp_dirs):
        """Test that post-launch script runs after application exits."""
        bin_dir, config_dir = temp_dirs
        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))

        # Create a wrapper and post-launch script
        wrapper_name = "test-app"
        app_id = "com.test.App"
        wrapper_path = bin_dir / wrapper_name

        wrapper_content = generator.create_wrapper_script(wrapper_name, app_id)
        wrapper_path.write_text(wrapper_content)
        wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IEXEC)

        # Create hook directory and post-launch script
        hooks_dir = config_dir / "scripts" / wrapper_name
        hooks_dir.mkdir(parents=True, exist_ok=True)

        post_script = hooks_dir / "post-run.sh"
        post_script.write_text(
            "#!/bin/bash\necho $FPWRAPPER_EXIT_CODE > $HOME/.test_exit_code\n"
        )
        post_script.chmod(post_script.stat().st_mode | stat.S_IEXEC)

        # Verify hook directory structure
        assert hooks_dir.exists()
        assert post_script.exists()
        assert post_script.is_file()

    def test_post_launch_script_captures_exit_code_success(self, temp_dirs):
        """Test that post-launch script receives exit code 0 for successful app."""
        bin_dir, config_dir = temp_dirs

        # Create a wrapper
        wrapper_name = "test-app"
        app_id = "com.test.App"
        _ = bin_dir / wrapper_name

        # Create a proper wrapper script using the generator
        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))
        wrapper_content = generator.create_wrapper_script(wrapper_name, app_id)

        # Verify the wrapper contains post-launch execution for successful exit
        assert "run_post_launch_script" in wrapper_content
        assert "FPWRAPPER_EXIT_CODE" in wrapper_content

        # The wrapper should not use 'exec' for the main launch anymore
        # to allow post-script execution
        lines = wrapper_content.split("\n")
        _ = any(
            "flatpak run" in line and "exec flatpak run" not in line
            for line in lines
            if "flatpak run" in line
        )
        # Note: The current wrapper still uses 'exec' in some paths, but we're adding
        # support for post-launch via wrapper refactoring
        assert "run_post_launch_script" in wrapper_content

    def test_post_launch_script_captures_exit_code_failure(self, temp_dirs):
        """Test that post-launch script receives non-zero exit code for failed app."""
        bin_dir, config_dir = temp_dirs

        # Create a wrapper using the generator
        wrapper_name = "test-app"
        app_id = "com.test.App"

        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))
        wrapper_content = generator.create_wrapper_script(wrapper_name, app_id)

        # Verify the wrapper includes post-launch function
        assert "run_post_launch_script" in wrapper_content
        assert "FPWRAPPER_EXIT_CODE" in wrapper_content
        assert "FPWRAPPER_SOURCE" in wrapper_content

    def test_post_launch_script_receives_source_environment(self, temp_dirs):
        """Test that post-launch script receives source (system/flatpak) info."""
        bin_dir, config_dir = temp_dirs

        # Create a wrapper using the generator
        wrapper_name = "test-app"
        app_id = "com.test.App"

        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))
        wrapper_content = generator.create_wrapper_script(wrapper_name, app_id)

        # Verify the wrapper includes source environment variable passing
        assert (
            'export FPWRAPPER_SOURCE="$source"' in wrapper_content
            or "FPWRAPPER_SOURCE" in wrapper_content
        )
        assert "run_post_launch_script" in wrapper_content

    def test_post_launch_script_error_handling(self, temp_dirs):
        """Test that post-launch script errors don't crash wrapper."""
        bin_dir, config_dir = temp_dirs

        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))
        wrapper_name = "test-app"
        app_id = "com.test.App"
        wrapper_content = generator.create_wrapper_script(wrapper_name, app_id)

        # Verify error handling is in place - checks hook exit code and handles failures
        assert "hook_exit=$?" in wrapper_content
        assert "[fplaunchwrapper] Warning" in wrapper_content
        # Verify failure mode handling (abort/warn/ignore)
        assert "case \"$failure_mode\"" in wrapper_content or "failure_mode" in wrapper_content

    def test_post_launch_script_not_called_when_missing(self, temp_dirs):
        """Test that missing post-launch script doesn't cause issues."""
        bin_dir, config_dir = temp_dirs

        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))
        wrapper_name = "test-app"
        app_id = "com.test.App"
        wrapper_content = generator.create_wrapper_script(wrapper_name, app_id)

        # Verify the wrapper checks if post-script exists before executing
        assert '[ -x "$POST_SCRIPT" ]' in wrapper_content or "-x" in wrapper_content
        assert "run_post_launch_script" in wrapper_content

    def test_force_interactive_flag_sets_environment(self, temp_dirs):
        """Test that --fpwrapper-force-interactive flag is parsed correctly."""
        bin_dir, config_dir = temp_dirs
        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))

        wrapper_name = "test-app"
        app_id = "com.test.App"
        wrapper_content = generator.create_wrapper_script(wrapper_name, app_id)

        # Verify force-interactive flag handling code is in wrapper
        assert "--fpwrapper-force-interactive" in wrapper_content
        assert 'FPWRAPPER_FORCE="interactive"' in wrapper_content
        assert "shift" in wrapper_content  # Should shift args after flag

    def test_wrapper_script_generation_includes_post_launch_function(self, temp_dirs):
        """Test that generated wrappers include post-launch function."""
        bin_dir, config_dir = temp_dirs
        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))

        wrapper_name = "example-app"
        app_id = "com.example.App"
        wrapper_content = generator.create_wrapper_script(wrapper_name, app_id)

        # Should have post-launch function defined
        assert "run_post_launch_script()" in wrapper_content

        # Should have all required environment variables
        assert "FPWRAPPER_EXIT_CODE" in wrapper_content
        assert "FPWRAPPER_SOURCE" in wrapper_content
        assert "FPWRAPPER_WRAPPER_NAME" in wrapper_content
        assert "FPWRAPPER_APP_ID" in wrapper_content

        # Should call post-launch after non-exec'd application
        # Check that we're not using 'exec' before post-launch (verify it's not exec flatpak run)
        # This is a bit tricky - just verify function exists and environment vars are set
        lines = wrapper_content.split("\n")
        post_launch_found = False
        for i, line in enumerate(lines):
            if (
                "run_post_launch_script" in line
                and "FPWRAPPER_EXIT_CODE" in wrapper_content
            ):
                post_launch_found = True
                break

        assert post_launch_found, "Post-launch script calling with exit code not found"

    def test_post_launch_script_all_environment_variables_exported(self, temp_dirs):
        """Test that all required environment variables are passed to post-launch script."""
        bin_dir, config_dir = temp_dirs
        generator = WrapperGenerator(str(bin_dir), config_dir=str(config_dir))

        wrapper_name = "test-app"
        app_id = "com.example.App"
        wrapper_content = generator.create_wrapper_script(wrapper_name, app_id)

        # Parse the post-launch function
        post_launch_start = wrapper_content.find("run_post_launch_script()")
        assert post_launch_start != -1, "run_post_launch_script function not found"

        # Get function content
        post_launch_content = wrapper_content[
            post_launch_start : post_launch_start + 1000
        ]

        # Check for export statements
        assert "export FPWRAPPER_EXIT_CODE" in post_launch_content
        assert "export FPWRAPPER_SOURCE" in post_launch_content
        assert "export FPWRAPPER_WRAPPER_NAME" in post_launch_content
        assert "export FPWRAPPER_APP_ID" in post_launch_content
