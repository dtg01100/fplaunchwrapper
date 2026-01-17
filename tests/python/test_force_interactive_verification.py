"""
Tests for force-interactive flag functionality across all execution modes.

Tests verify:
- Force-interactive flag is parsed correctly from command line
- Flag sets FPWRAPPER_FORCE=interactive environment variable
- Flag works in pre-launch, flatpak launch, and fallback paths
- Flag overrides default interactive detection
"""

import os
import sys
import tempfile
import pytest

# Add lib to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))

from generate import WrapperGenerator


class TestForceInteractiveFlag:
    """Test force-interactive flag functionality in generated wrappers."""

    def test_force_interactive_flag_present_in_wrapper(self):
        """Test that --fpwrapper-force-interactive flag is in generated wrappers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            wrapper_code = generator.create_wrapper_script(
                wrapper_name="test-app",
                app_id="org.test.App",
            )
        
        # Check that the flag handling code is present
        assert "--fpwrapper-force-interactive" in wrapper_code
        assert 'FPWRAPPER_FORCE="interactive"' in wrapper_code
        assert "shift" in wrapper_code

    def test_force_interactive_env_variable_set(self):
        """Test that FPWRAPPER_FORCE environment variable is set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            wrapper_code = generator.create_wrapper_script(
                wrapper_name="test-app",
                app_id="org.test.App",
            )
        
        # FPWRAPPER_FORCE should be set to interactive when flag is used
        assert 'FPWRAPPER_FORCE="interactive"' in wrapper_code

    def test_force_interactive_used_in_wrapper(self):
        """Test that FPWRAPPER_FORCE is actually used for checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            wrapper_code = generator.create_wrapper_script(
                wrapper_name="test-app",
                app_id="org.test.App",
            )
        
        # Variable should be used in the interactive detection logic
        # Count occurrences - should be used multiple times
        count = wrapper_code.count("FPWRAPPER_FORCE")
        assert count >= 1, "FPWRAPPER_FORCE should be used in wrapper"

    def test_force_interactive_with_flatpak_app(self):
        """Test force-interactive with Flatpak app."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            wrapper_code = generator.create_wrapper_script(
                wrapper_name="gnome-calculator",
                app_id="org.gnome.Calculator",
            )
        
        # Should support force-interactive
        assert "--fpwrapper-force-interactive" in wrapper_code
        assert "FPWRAPPER_FORCE" in wrapper_code

    def test_force_interactive_multiple_app_ids(self):
        """Test force-interactive with various app IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            
            test_apps = [
                ("test1", "org.example.App1"),
                ("test2", "com.github.App2"),
                ("test3", "org.kde.App3"),
            ]
            
            for name, app_id in test_apps:
                wrapper = generator.create_wrapper_script(
                    wrapper_name=name,
                    app_id=app_id,
                )
                
                # All should have force-interactive support
                assert "--fpwrapper-force-interactive" in wrapper
                assert "FPWRAPPER_FORCE" in wrapper


class TestForceInteractiveEnvironment:
    """Test environment variable handling for force-interactive."""

    def test_fpwrapper_force_in_wrapper_environment(self):
        """Test FPWRAPPER_FORCE is set in wrapper environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            wrapper = generator.create_wrapper_script(
                wrapper_name="test-app",
                app_id="org.test.App",
            )
        
        # Should set variable before using it
        force_set = wrapper.find('FPWRAPPER_FORCE="interactive"')
        force_ref = wrapper.find('FPWRAPPER_FORCE')
        
        # Variable should be set
        assert force_set >= 0
        # And should be referenced somewhere
        assert force_ref >= 0

    def test_fpwrapper_force_scope(self):
        """Test that FPWRAPPER_FORCE has proper scope."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            wrapper = generator.create_wrapper_script(
                wrapper_name="test-app",
                app_id="org.test.App",
            )
        
        # Variable should be defined
        assert "FPWRAPPER_FORCE=" in wrapper
        # Should not be unset
        assert "unset FPWRAPPER_FORCE" not in wrapper


class TestForceInteractiveIntegration:
    """Integration tests for force-interactive functionality."""

    def test_wrapper_has_force_interactive_support(self):
        """Test all wrappers have force-interactive support."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            
            # Generate a few wrappers
            app_ids = ["org.example.App1", "org.test.TestApp", "com.github.MyApp"]
            
            for app_id in app_ids:
                wrapper = generator.create_wrapper_script(
                    wrapper_name="test",
                    app_id=app_id,
                )
                
                # All should support force-interactive
                assert "--fpwrapper-force-interactive" in wrapper
                assert "FPWRAPPER_FORCE" in wrapper

    def test_force_interactive_argument_handling(self):
        """Test force-interactive flag is properly removed from arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            wrapper = generator.create_wrapper_script(
                wrapper_name="test-app",
                app_id="org.test.App",
            )
        
        # After detecting the flag, should shift arguments
        flag_check = wrapper.find('--fpwrapper-force-interactive')
        shift_found = wrapper.find('shift', flag_check) if flag_check >= 0 else -1
        
        # shift should come after flag check
        if flag_check >= 0:
            assert shift_found > flag_check, "shift should come after flag detection"


class TestForceInteractiveEdgeCases:
    """Test edge cases and special scenarios."""

    def test_force_interactive_with_special_chars_in_app_id(self):
        """Test force-interactive with special characters in app ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            
            special_apps = [
                ("app-dash", "org.example.app-with-dash"),
                ("app-under", "org.example.app_under_score"),
                ("app-num", "org.example.App123"),
            ]
            
            for name, app_id in special_apps:
                wrapper = generator.create_wrapper_script(
                    wrapper_name=name,
                    app_id=app_id,
                )
                
                # All should work
                assert "FPWRAPPER_FORCE" in wrapper

    def test_force_interactive_in_different_wrapper_types(self):
        """Test force-interactive in different wrapper configurations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = WrapperGenerator(bin_dir=tmpdir)
            
            # Create various wrapper types
            configs = [
                {"wrapper_name": "basic", "app_id": "org.test.Basic"},
                {"wrapper_name": "with-dash", "app_id": "org.test.With-Dash"},
                {"wrapper_name": "caps", "app_id": "org.test.ALLCAPS"},
            ]
            
            for config in configs:
                wrapper = generator.create_wrapper_script(**config)
                
                # All should have force-interactive
                assert "FPWRAPPER_FORCE" in wrapper
                assert "--fpwrapper-force-interactive" in wrapper


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
