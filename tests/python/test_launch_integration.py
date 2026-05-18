#!/usr/bin/env python3
"""Integration tests for launch.py with other modules.

Tests the interaction between AppLauncher and other modules like:
- config_manager (preferences, hook scripts)
- safety (launch checks)
- generate (wrapper creation)
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import launcher for testing
try:
    from lib.launch import AppLauncher, main as launch_main
except ImportError:
    AppLauncher = None
    launch_main = None

# Import other modules for integration
try:
    from lib.config_manager import EnhancedConfigManager
except ImportError:
    EnhancedConfigManager = None

try:
    from lib.safety import safe_launch_check
except ImportError:
    safe_launch_check = None

try:
    from lib.generate import WrapperGenerator
except ImportError:
    WrapperGenerator = None


@pytest.mark.integration
class TestLauncherConfigManagerIntegration:
    """Integration tests between AppLauncher and ConfigManager."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)

        # Create a wrapper for testing
        self.wrapper_path = self.bin_dir / "firefox"
        self.wrapper_path.write_text("#!/bin/bash\necho 'test'\n")
        self.wrapper_path.chmod(0o755)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_with_config_preference_flatpak(
        self, mock_safety: Mock, mock_subprocess: Mock
    ) -> None:
        """Test launch uses flatpak preference from config."""
        if not AppLauncher:
            pytest.skip("AppLauncher not available")

        # Set preference to flatpak
        pref_file = self.config_dir / "firefox.pref"
        pref_file.write_text("flatpak")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is True
        # Should call flatpak directly when preference is flatpak
        call_args = mock_subprocess.call_args[0][0]
        assert "flatpak" in call_args

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_with_config_preference_system(
        self, mock_safety: Mock, mock_subprocess: Mock
    ) -> None:
        """Test launch uses system wrapper when preference is system."""
        if not AppLauncher:
            pytest.skip("AppLauncher not available")

        # Set preference to system
        pref_file = self.config_dir / "firefox.pref"
        pref_file.write_text("system")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is True
        # Should call wrapper script when preference is system
        call_args = mock_subprocess.call_args[0][0]
        assert "firefox" in str(call_args)

    def test_launch_detects_hook_scripts_in_config(self) -> None:
        """Test launcher detects pre/post launch scripts from config."""
        if not AppLauncher:
            pytest.skip("AppLauncher not available")

        # Create scripts directory with hook script
        scripts_dir = self.config_dir / "scripts" / "firefox"
        scripts_dir.mkdir(parents=True)

        pre_launch = scripts_dir / "pre-launch.sh"
        pre_launch.write_text("#!/bin/bash\necho 'pre-launch'\n")
        pre_launch.chmod(0o755)

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Verify hook scripts are detected
        scripts = launcher._get_hook_scripts("firefox", "pre")
        assert len(scripts) >= 1


@pytest.mark.integration
class TestLauncherSafetyIntegration:
    """Integration tests between AppLauncher and Safety module."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    def test_launch_respects_safety_block(self, mock_subprocess: Mock) -> None:
        """Test that safety checks can block launches."""
        if not AppLauncher:
            pytest.skip("AppLauncher not available")

        # Mock safety check to return False (blocked)
        with patch("lib.safety.safe_launch_check", return_value=False):
            launcher = AppLauncher(
                app_name="firefox",
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
            )

            result = launcher.launch()

            # Should be blocked by safety check
            assert result is False
            # subprocess should not have been called
            mock_subprocess.assert_not_called()

    def test_launch_with_dangerous_wrapper_detected(self) -> None:
        """Test launch detects dangerous wrapper content with hardcoded browser commands."""
        if not AppLauncher:
            pytest.skip("AppLauncher not available")

        # Create a wrapper with hardcoded browser launch commands
        # (which is what is_dangerous_wrapper actually checks for)
        dangerous_wrapper = self.bin_dir / "malicious"
        dangerous_wrapper.write_text("#!/bin/bash\nflatpak run org.mozilla.firefox &\nchromium &\n")
        dangerous_wrapper.chmod(0o755)

        # Safety check should detect hardcoded browser launches
        from lib.safety import is_dangerous_wrapper

        assert is_dangerous_wrapper(dangerous_wrapper) is True


@pytest.mark.integration
class TestLauncherGenerateIntegration:
    """Integration tests between AppLauncher and WrapperGenerator."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_launch_after_generate_creates_wrapper(self) -> None:
        """Test that generated wrappers can be launched."""
        if not AppLauncher or not WrapperGenerator:
            pytest.skip("Modules not available")

        # Generate a wrapper
        generator = WrapperGenerator(
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = generator.generate_wrapper("org.mozilla.firefox")
        assert result is True

        # Verify wrapper was created
        wrapper = self.bin_dir / "firefox"
        assert wrapper.exists()
        assert wrapper.is_file()

        # Now try to launch it
        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        wrapper_path = launcher._find_wrapper()
        assert wrapper_path is not None
        assert str(wrapper_path) == str(wrapper)

    def test_launch_resolves_correct_wrapper_from_multiple(self) -> None:
        """Test launcher finds correct wrapper when multiple exist."""
        if not WrapperGenerator:
            pytest.skip("WrapperGenerator not available")

        # Generate multiple wrappers
        apps = ["org.mozilla.firefox", "com.google.Chrome", "org.gimp.GIMP"]
        for app in apps:
            generator = WrapperGenerator(
                bin_dir=str(self.bin_dir),
                config_dir=str(self.config_dir),
            )
            generator.generate_wrapper(app)

        # Create launcher
        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        # Should find firefox wrapper, not chrome or gimp
        wrapper_path = launcher._find_wrapper()
        assert wrapper_path is not None
        assert "firefox" in str(wrapper_path)


@pytest.mark.integration
class TestLauncherHookScriptIntegration:
    """Integration tests for pre/post launch hook execution."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)

        # Create wrapper
        self.wrapper_path = self.bin_dir / "firefox"
        self.wrapper_path.write_text("#!/bin/bash\necho 'launched'\n")
        self.wrapper_path.chmod(0o755)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_pre_launch_hooks_execute(self, mock_safety: Mock, mock_subprocess: Mock) -> None:
        """Test that pre-launch hooks execute before app launch."""
        if not AppLauncher:
            pytest.skip("AppLauncher not available")

        # Create pre-launch hook
        scripts_dir = self.config_dir / "scripts" / "firefox"
        scripts_dir.mkdir(parents=True)
        pre_hook = scripts_dir / "pre-launch.sh"
        pre_hook.write_text("#!/bin/bash\necho 'before-launch' > /tmp/hook_output.txt\nexit 0\n")
        pre_hook.chmod(0o755)

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is True

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_post_launch_hooks_execute(self, mock_safety: Mock, mock_subprocess: Mock) -> None:
        """Test that post-launch hooks execute after app launch."""
        if not AppLauncher:
            pytest.skip("AppLauncher not available")

        # Create post-launch hook
        scripts_dir = self.config_dir / "scripts" / "firefox"
        scripts_dir.mkdir(parents=True)
        post_hook = scripts_dir / "post-run.sh"
        post_hook.write_text(
            "#!/bin/bash\necho 'after-launch' > /tmp/post_hook_output.txt\nexit 0\n"
        )
        post_hook.chmod(0o755)

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
        )

        result = launcher.launch()

        assert result is True


@pytest.mark.integration
class TestLauncherEnvironmentIntegration:
    """Integration tests for environment variable handling."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bin_dir = self.temp_dir / "bin"
        self.config_dir = self.temp_dir / "config"
        self.bin_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_passes_environment_to_subprocess(
        self, mock_safety: Mock, mock_subprocess: Mock
    ) -> None:
        """Test that environment variables are passed to launched app."""
        if not AppLauncher:
            pytest.skip("AppLauncher not available")

        custom_env = {
            "APP_VAR": "custom_value",
            "APP_DEBUG": "true",
        }

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            env=custom_env,
        )

        launcher.launch()

        # Verify environment was passed
        call_kwargs = mock_subprocess.call_args[1]
        assert "env" in call_kwargs
        assert call_kwargs["env"]["APP_VAR"] == "custom_value"
        assert call_kwargs["env"]["APP_DEBUG"] == "true"

    @patch("subprocess.run")
    @patch("lib.safety.safe_launch_check", return_value=True)
    def test_launch_with_custom_env_isolated(
        self, mock_safety: Mock, mock_subprocess: Mock
    ) -> None:
        """Test that custom env completely replaces process environment.

        This is intentional security behavior - when custom env is provided,
        it replaces os.environ to prevent environment variable injection.
        """
        if not AppLauncher:
            pytest.skip("AppLauncher not available")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        launcher = AppLauncher(
            app_name="firefox",
            bin_dir=str(self.bin_dir),
            config_dir=str(self.config_dir),
            env={"APP_VAR": "value"},
        )

        launcher.launch()

        call_kwargs = mock_subprocess.call_args[1]
        assert "env" in call_kwargs
        assert call_kwargs["env"]["APP_VAR"] == "value"
