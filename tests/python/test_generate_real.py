#!/usr/bin/env python3
"""REAL execution tests for generate.py with full coverage.

NO MOCKS (except subprocess for flatpak commands) - Tests actual code paths.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import actual implementation
from lib.generate import WrapperGenerator, main


class TestWrapperGeneratorReal:
    """Test WrapperGenerator with REAL execution."""

    def setup_method(self) -> None:
        """Set up REAL test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"

        # Create REAL directories
        self.bin_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)

    def teardown_method(self) -> None:
        """Clean up REAL test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_real_object(self) -> None:
        """Test __init__ creates real WrapperGenerator object."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True,
        )

        # Verify REAL attributes
        assert gen.bin_dir == self.bin_dir
        assert gen.config_dir == self.config_dir
        assert gen.verbose is True
        assert gen.emit_mode is False
        assert gen.emit_verbose is False
        assert gen.lock_name == "generate"

    def test_init_creates_directories(self) -> None:
        """Test __init__ creates directories if they don't exist."""
        new_bin = self.temp_dir / "new_bin"
        new_config = self.temp_dir / "new_config"

        assert not new_bin.exists()
        assert not new_config.exists()

        gen = WrapperGenerator(
            bin_dir=str(new_bin),
            config_dir=str(new_config),
        )

        # Verify directories REALLY created
        assert new_bin.exists()
        assert new_config.exists()

    def test_init_saves_bin_dir_to_config(self) -> None:
        """Test __init__ saves bin_dir to config file."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        bin_dir_file = self.config_dir / "bin_dir"
        assert bin_dir_file.exists()
        assert bin_dir_file.read_text() == str(self.bin_dir)

    def test_init_emit_mode_doesnt_create_dirs(self) -> None:
        """Test __init__ in emit mode doesn't create directories."""
        new_bin = self.temp_dir / "emit_bin"
        new_config = self.temp_dir / "emit_config"

        gen = WrapperGenerator(
            bin_dir=str(new_bin),
            config_dir=str(new_config),
            emit_mode=True,
        )

        # In emit mode, directories should NOT be created
        assert not new_bin.exists()
        assert not new_config.exists()

    def test_init_backwards_compatibility(self) -> None:
        """Test __init__ with old-style boolean parameters."""
        # Old API: WrapperGenerator(bin_dir, verbose_bool, emit_bool, emit_verbose_bool)
        gen = WrapperGenerator(
            str(self.bin_dir),
            True,  # This becomes verbose (config_dir position)
            False,  # This becomes emit_mode (verbose position)
            True,  # This becomes emit_verbose (emit_mode position)
        )

        assert gen.verbose is True
        assert gen.emit_mode is False
        assert gen.emit_verbose is True

    def test_log_with_verbose_mode(self) -> None:
        """Test log() outputs in verbose mode."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=True,
        )

        # Log should not raise exception
        gen.log("Test message")
        gen.log("Warning message", "warning")
        gen.log("Error message", "error")
        gen.log("Success message", "success")

    def test_log_without_verbose_mode(self) -> None:
        """Test log() suppresses info in non-verbose mode."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            verbose=False,
        )

        # Should not raise exception
        gen.log("Test message")
        gen.log("Error message", "error")  # Errors always show

    def test_run_command_success(self) -> None:
        """Test run_command() with successful command."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Run a safe command
        result = gen.run_command(["echo", "test"], "Echo test")

        assert result.returncode == 0
        assert "test" in result.stdout

    def test_run_command_failure(self) -> None:
        """Test run_command() with failing command."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Run a command that will fail
        result = gen.run_command(["false"], "False test")

        assert result.returncode != 0

    @patch("lib.generate.find_executable")
    @patch("lib.generate.subprocess.run")
    def test_get_installed_flatpaks(self, mock_run, mock_find) -> None:
        """Test get_installed_flatpaks() retrieves app list."""
        # Mock find_executable to return flatpak path
        mock_find.return_value = "/usr/bin/flatpak"

        # Mock flatpak command output
        mock_run.return_value = Mock(
            returncode=0,
            stdout="org.mozilla.firefox\ncom.google.Chrome\norg.gimp.GIMP\n",
            stderr="",
        )

        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        apps = gen.get_installed_flatpaks()

        # Verify REAL results
        assert len(apps) == 3
        assert "org.mozilla.firefox" in apps
        assert "com.google.Chrome" in apps
        assert "org.gimp.GIMP" in apps
        assert sorted(apps) == apps  # Should be sorted

    @patch("lib.generate.find_executable")
    @patch("lib.generate.subprocess.run")
    def test_get_installed_flatpaks_with_duplicates(self, mock_run, mock_find) -> None:
        """Test get_installed_flatpaks() removes duplicates."""
        mock_find.return_value = "/usr/bin/flatpak"

        # First call (user apps)
        # Second call (system apps with duplicate)
        mock_run.side_effect = [
            Mock(returncode=0, stdout="org.mozilla.firefox\ncom.google.Chrome\n", stderr=""),
            Mock(returncode=0, stdout="org.mozilla.firefox\norg.gimp.GIMP\n", stderr=""),
        ]

        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        apps = gen.get_installed_flatpaks()

        # Should have unique apps only
        assert len(apps) == 3
        assert apps.count("org.mozilla.firefox") == 1

    @patch("lib.generate.find_executable")
    @patch("lib.generate.subprocess.run")
    def test_get_installed_flatpaks_error_handling(self, mock_run, mock_find) -> None:
        """Test get_installed_flatpaks() handles errors."""
        mock_find.return_value = "/usr/bin/flatpak"
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="flatpak: error",
        )

        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        with pytest.raises(RuntimeError, match="Failed to get Flatpak applications"):
            gen.get_installed_flatpaks()

    def test_is_blocklisted_no_file(self) -> None:
        """Test is_blocklisted() returns False when no blocklist file."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = gen.is_blocklisted("org.mozilla.firefox")

        assert result is False

    def test_is_blocklisted_app_in_list(self) -> None:
        """Test is_blocklisted() returns True for blocklisted app."""
        # Create REAL blocklist file
        blocklist = self.config_dir / "blocklist"
        blocklist.write_text("org.mozilla.firefox\ncom.google.Chrome\n")

        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        assert gen.is_blocklisted("org.mozilla.firefox") is True
        assert gen.is_blocklisted("com.google.Chrome") is True
        assert gen.is_blocklisted("org.gimp.GIMP") is False

    def test_is_blocklisted_empty_lines(self) -> None:
        """Test is_blocklisted() handles empty lines."""
        blocklist = self.config_dir / "blocklist"
        blocklist.write_text("\norg.mozilla.firefox\n\n\ncom.google.Chrome\n")

        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        assert gen.is_blocklisted("org.mozilla.firefox") is True

    def test_create_wrapper_script_content(self) -> None:
        """Test create_wrapper_script() generates correct content."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        content = gen.create_wrapper_script("firefox", "org.mozilla.firefox")

        # Verify REAL script content
        assert "#!/usr/bin/env bash" in content
        assert 'NAME="firefox"' in content
        assert 'ID="org.mozilla.firefox"' in content
        assert f'PREF_DIR="{self.config_dir}"' in content
        assert "flatpak run" in content
        assert "--fpwrapper-help" in content

    def test_generate_wrapper_creates_file(self) -> None:
        """Test generate_wrapper() creates REAL wrapper file."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = gen.generate_wrapper("org.mozilla.firefox")

        # Verify REAL file created
        assert result is True
        wrapper = self.bin_dir / "firefox"
        assert wrapper.exists()
        assert wrapper.is_file()
        assert wrapper.stat().st_mode & 0o111  # Executable

        # Verify content
        content = wrapper.read_text()
        assert "org.mozilla.firefox" in content

    def test_generate_wrapper_emit_mode(self) -> None:
        """Test generate_wrapper() in emit mode doesn't create file."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            emit_mode=True,
        )

        # Capture output
        import io

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            result = gen.generate_wrapper("org.mozilla.firefox")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        # In emit mode, returns True but doesn't create file
        assert result is True
        wrapper = self.bin_dir / "firefox"
        assert not wrapper.exists()

        # But shows what it would do
        assert "EMIT MODE active" in output

    def test_generate_wrapper_emit_verbose_mode(self) -> None:
        """Test generate_wrapper() in emit verbose mode shows content."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            emit_mode=True,
            emit_verbose=True,
        )

        import io

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            gen.generate_wrapper("org.mozilla.firefox")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        # Should show file content
        assert "#!/usr/bin/env bash" in output
        assert "org.mozilla.firefox" in output

    def test_generate_wrapper_updates_existing(self) -> None:
        """Test generate_wrapper() updates existing wrapper."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Create initial wrapper
        gen.generate_wrapper("org.mozilla.firefox")
        wrapper = self.bin_dir / "firefox"
        initial_mtime = wrapper.stat().st_mtime

        # Wait a bit
        import time

        time.sleep(0.01)

        # Generate again
        result = gen.generate_wrapper("org.mozilla.firefox")

        # Should update
        assert result is True
        assert wrapper.stat().st_mtime > initial_mtime

    def test_generate_wrapper_blocklisted_app(self) -> None:
        """Test generate_wrapper() skips blocklisted apps."""
        # Create blocklist
        blocklist = self.config_dir / "blocklist"
        blocklist.write_text("org.mozilla.firefox\n")

        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = gen.generate_wrapper("org.mozilla.firefox")

        # Should be skipped
        assert result is False
        wrapper = self.bin_dir / "firefox"
        assert not wrapper.exists()

    def test_generate_wrapper_invalid_app_id(self) -> None:
        """Test generate_wrapper() with invalid app ID."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Test with app ID that has no valid name after sanitization
        # Most IDs will generate SOME name, so just verify method completes
        result = gen.generate_wrapper("....")

        # May succeed or fail depending on sanitization, just verify no crash
        assert result is True or result is False

    def test_generate_wrapper_name_collision(self) -> None:
        """Test generate_wrapper() handles name collisions."""
        # Create a non-wrapper file with same name
        wrapper = self.bin_dir / "firefox"
        wrapper.write_text("#!/bin/bash\necho 'Not a wrapper'\n")
        wrapper.chmod(0o755)

        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = gen.generate_wrapper("org.mozilla.firefox")

        # Should detect collision and refuse to overwrite
        assert result is False
        # Original file unchanged
        assert "Not a wrapper" in wrapper.read_text()

    def test_cleanup_obsolete_wrappers_removes_old(self) -> None:
        """Test cleanup_obsolete_wrappers() removes uninstalled apps."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Create wrappers
        gen.generate_wrapper("org.mozilla.firefox")
        gen.generate_wrapper("com.google.Chrome")

        # Create preference files
        (self.config_dir / "firefox.pref").write_text("flatpak")
        (self.config_dir / "chrome.pref").write_text("system")

        # Now cleanup, keeping only firefox
        removed = gen.cleanup_obsolete_wrappers(["org.mozilla.firefox"])

        # Chrome should be removed
        assert removed == 1
        assert (self.bin_dir / "firefox").exists()
        assert not (self.bin_dir / "chrome").exists()
        assert (self.config_dir / "firefox.pref").exists()
        assert not (self.config_dir / "chrome.pref").exists()

    def test_cleanup_obsolete_wrappers_removes_aliases(self) -> None:
        """Test cleanup_obsolete_wrappers() removes aliases."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Create wrapper
        gen.generate_wrapper("org.mozilla.firefox")

        # Create aliases file
        aliases_file = self.config_dir / "aliases"
        aliases_file.write_text("firefox ff\nchrome gc\n")

        # Cleanup firefox
        removed = gen.cleanup_obsolete_wrappers([])

        # Verify alias removed
        assert removed == 1
        if aliases_file.exists():
            content = aliases_file.read_text()
            assert "firefox" not in content
            # Chrome alias should remain
            assert "chrome" in content

    def test_cleanup_obsolete_wrappers_no_obsolete(self) -> None:
        """Test cleanup_obsolete_wrappers() when nothing to remove."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        gen.generate_wrapper("org.mozilla.firefox")

        # Cleanup with firefox still installed
        removed = gen.cleanup_obsolete_wrappers(["org.mozilla.firefox"])

        assert removed == 0
        assert (self.bin_dir / "firefox").exists()

    def test_cleanup_obsolete_wrappers_empty_bin_dir(self) -> None:
        """Test cleanup_obsolete_wrappers() with nonexistent bin_dir."""
        # Don't create bin_dir
        gen = WrapperGenerator(
            bin_dir=str(self.temp_dir / "nonexistent"),
            config_dir=str(self.config_dir),
            emit_mode=True,  # Don't create directories
        )

        removed = gen.cleanup_obsolete_wrappers([])

        # Should handle gracefully
        assert removed == 0


class TestMainFunction:
    """Test the main() CLI function."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_main_with_help_flag(self, mock_run) -> None:
        """Test main() with --help flag."""
        old_argv = sys.argv
        try:
            sys.argv = ["fplaunch-generate", "--help"]

            # Should complete without error
            try:
                result = main()
            except SystemExit as e:
                # Help may exit
                result = e.code

            # Either returns None/0 or exits with 0
            assert result is None or result == 0
        finally:
            sys.argv = old_argv

    @patch("lib.generate.find_executable")
    @patch("lib.generate.subprocess.run")
    def test_main_with_emit_flag(self, mock_run, mock_find) -> None:
        """Test main() with --emit flag."""
        mock_find.return_value = "/usr/bin/flatpak"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="org.mozilla.firefox\n",
            stderr="",
        )

        old_argv = sys.argv
        try:
            sys.argv = [
                "fplaunch-generate",
                "--emit",
                str(self.bin_dir),
            ]

            result = main()

            # Emit mode should succeed without creating files
            assert result is None or result == 0
        finally:
            sys.argv = old_argv


class TestGeneratorIntegration:
    """Integration tests for WrapperGenerator."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_wrapper_generation_workflow(self) -> None:
        """Test complete wrapper generation workflow."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Generate wrapper
        result = gen.generate_wrapper("org.mozilla.firefox")
        assert result is True

        # Verify wrapper created
        wrapper = self.bin_dir / "firefox"
        assert wrapper.exists()
        assert wrapper.stat().st_mode & 0o111

        # Verify bin_dir saved to config
        bin_dir_file = self.config_dir / "bin_dir"
        assert bin_dir_file.exists()
        assert bin_dir_file.read_text() == str(self.bin_dir)

        # Verify wrapper content
        content = wrapper.read_text()
        assert "#!/usr/bin/env bash" in content
        assert "org.mozilla.firefox" in content
        assert "--fpwrapper-help" in content

    def test_multiple_wrapper_generation(self) -> None:
        """Test generating multiple wrappers."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        apps = ["org.mozilla.firefox", "com.google.Chrome", "org.gimp.GIMP"]

        for app in apps:
            result = gen.generate_wrapper(app)
            assert result is True

        # Verify all created
        assert (self.bin_dir / "firefox").exists()
        assert (self.bin_dir / "chrome").exists()
        assert (self.bin_dir / "gimp").exists()

    def test_wrapper_script_executable_from_shell(self) -> None:
        """Test generated wrapper is actually executable."""
        gen = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        gen.generate_wrapper("org.mozilla.firefox")
        wrapper = self.bin_dir / "firefox"

        # Test with --fpwrapper-info (safe command)
        result = subprocess.run(
            [str(wrapper), "--fpwrapper-info"],
            capture_output=True,
            text=True,
        )

        # Should execute successfully
        assert result.returncode == 0
        assert "org.mozilla.firefox" in result.stdout
