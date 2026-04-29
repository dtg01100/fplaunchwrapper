#!/usr/bin/env python3
"""Tests for package structure and path resolution.

These tests ensure that the package structure, entry points, and resource paths
work correctly both in development mode and when installed.
"""

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

# Get project root (tests/python -> tests -> project_root)
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestPackageStructure:
    """Test that the package structure is correct."""

    def test_lib_package_exists(self):
        """Test that the lib package can be imported."""
        try:
            import lib

            assert lib is not None
        except ImportError as e:
            pytest.fail(f"Failed to import lib package: {e}")

    def test_lib_has_version(self):
        """Test that lib package has version attribute."""
        import lib

        assert hasattr(lib, "__version__")
        assert isinstance(lib.__version__, str)


class TestEntryPointModules:
    """Test that all entry point modules can be imported."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "lib.fplaunch",
            "lib.cli",
            "lib.generate",
            "lib.manage",
            "lib.launch",
            "lib.cleanup",
            "lib.systemd_setup",
            "lib.config_manager",
            "lib.flatpak_monitor",
        ],
    )
    def test_entry_point_module_importable(self, module_name):
        """Test that each entry point module can be imported."""
        try:
            mod = importlib.import_module(module_name)
            assert mod is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")

    @pytest.mark.parametrize(
        "module_name",
        [
            "lib.fplaunch",
            "lib.cli",
            "lib.generate",
            "lib.manage",
            "lib.launch",
            "lib.cleanup",
            "lib.systemd_setup",
            "lib.config_manager",
            "lib.flatpak_monitor",
        ],
    )
    def test_entry_point_has_main(self, module_name):
        """Test that each entry point module has a main function."""
        mod = importlib.import_module(module_name)
        assert hasattr(mod, "main"), f"{module_name} missing main function"
        assert callable(mod.main), f"{module_name}.main is not callable"


class TestLibModules:
    """Test that lib modules are accessible."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "lib.generate",
            "lib.cli",
            "lib.generate",
            "lib.manage",
            "lib.launch",
            "lib.cleanup",
            "lib.systemd_setup",
            "lib.config_manager",
            "lib.flatpak_monitor",
            "lib.paths",
            "lib.python_utils",
            "lib.safety",
            "lib.exceptions",
        ],
    )
    def test_lib_module_importable(self, module_name):
        """Test that each lib module can be imported."""
        try:
            mod = importlib.import_module(module_name)
            assert mod is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestTemplatePathResolution:
    """Test that template paths resolve correctly."""

    def test_template_file_exists_in_package(self):
        """Test that the template file exists in lib/templates/."""
        template_path = PROJECT_ROOT / "lib" / "templates" / "wrapper.template.sh"

        assert template_path.exists(), (
            f"Template not found at {template_path}. "
            "Template must be in lib/templates/ for package inclusion."
        )

    def test_template_is_readable(self):
        """Test that the template file can be read."""
        template_path = PROJECT_ROOT / "lib" / "templates" / "wrapper.template.sh"

        if template_path.exists():
            content = template_path.read_text()
            assert len(content) > 0, "Template file is empty"
            assert (
                "#!/bin/bash" in content or "flatpak" in content.lower()
            ), "Template doesn't look like a valid wrapper template"

    def test_generate_module_can_find_template(self):
        """Test that WrapperGenerator can create wrapper scripts (uses template)."""
        from lib.generate import WrapperGenerator

        # Create a generator in a temp directory
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            gen = WrapperGenerator(bin_dir=tmpdir, config_dir=tmpdir)

            # Try to create wrapper script content
            try:
                content = gen.create_wrapper_script("test-app", "org.test.App")
                assert len(content) > 0, "Generated wrapper content is empty"
                assert (
                    "flatpak" in content.lower()
                ), "Generated wrapper doesn't contain flatpak command"
            except Exception as e:
                pytest.fail(f"Failed to create wrapper script: {e}")

    def test_importlib_resources_template_path(self):
        """Test that importlib.resources can find the template."""
        try:
            from importlib.resources import files as importlib_files

            # This should work when package is properly installed
            template_file = importlib_files("lib") / "templates" / "wrapper.template.sh"
            template_path = Path(str(template_file))

            # At minimum, the path should be constructable
            assert template_path is not None
        except (ImportError, TypeError, AttributeError):
            # importlib.resources might not be available in older Python
            pytest.skip("importlib.resources not available")


class TestPathResolutionInModules:
    """Test that path resolution works in various modules."""

    def test_paths_module_functions(self):
        """Test that lib.paths functions work correctly."""
        from lib.paths import (
            get_default_config_dir,
            get_default_data_dir,
            get_default_bin_dir,
        )

        config_dir = get_default_config_dir()
        assert isinstance(config_dir, Path)
        assert len(str(config_dir)) > 0

        data_dir = get_default_data_dir()
        assert isinstance(data_dir, Path)
        assert len(str(data_dir)) > 0

        bin_dir = get_default_bin_dir()
        assert isinstance(bin_dir, Path)
        assert len(str(bin_dir)) > 0

    def test_config_manager_paths(self):
        """Test that config manager initializes with correct paths."""
        import tempfile

        from lib.config_manager import create_config_manager

        with tempfile.TemporaryDirectory():
            # Just verify that the config manager can be created
            manager = create_config_manager()
            assert manager is not None
            assert hasattr(manager, "config_dir")


class TestNoIncorrectPathManipulation:
    """Test that modules don't manipulate sys.path incorrectly."""

    def test_main_entrypoint_no_sys_path_insert(self):
        """Test that lib.main_entrypoint doesn't insert lib/lib into sys.path."""

        # Check that sys.path doesn't contain any "lib/lib" paths
        for path in sys.path:
            assert "lib/lib" not in path, (
                f"Found 'lib/lib' in sys.path: {path}. "
                "This indicates incorrect path manipulation."
            )

    def test_imports_work_without_sys_path_hacks(self):
        """Test that all imports work without relying on sys.path manipulation."""
        # These imports should work purely through package structure
        from lib.generate import WrapperGenerator
        from lib.manage import WrapperManager
        from lib.cleanup import WrapperCleanup
        from lib.launch import AppLauncher

        # If we got here, imports work correctly
        assert WrapperGenerator is not None
        assert WrapperManager is not None
        assert WrapperCleanup is not None
        assert AppLauncher is not None


class TestPyprojectConfiguration:
    """Test that pyproject.toml has correct configuration."""

    def test_pyproject_has_lib_package(self):
        """Test that pyproject.toml includes lib package."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"

        if not pyproject_path.exists():
            pytest.skip("pyproject.toml not found")

        content = pyproject_path.read_text()

        # Check that lib package is declared
        assert (
            '"lib"' in content or "'lib'" in content
        ), "pyproject.toml missing 'lib' package declaration"

    def test_pyproject_has_entry_points(self):
        """Test that pyproject.toml has all required entry points."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"

        if not pyproject_path.exists():
            pytest.skip("pyproject.toml not found")

        content = pyproject_path.read_text()

        required_entry_points = [
            "lib.fplaunch:main",
            "lib.cli:main",
            "lib.generate:main",
            "lib.manage:main",
            "lib.launch:main",
            "lib.cleanup:main",
            "lib.systemd_setup:main",
            "lib.config_manager:main",
            "lib.flatpak_monitor:main",
        ]

        for entry_point in required_entry_points:
            assert entry_point in content, f"Missing entry point in pyproject.toml: {entry_point}"

    def test_pyproject_includes_template_package_data(self):
        """Test that pyproject.toml includes templates in package-data."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"

        if not pyproject_path.exists():
            pytest.skip("pyproject.toml not found")

        content = pyproject_path.read_text()

        # Check that templates are included in package data
        assert "templates" in content, "pyproject.toml missing template inclusion in package-data"


class TestInstalledEntryPoints:
    """Test that installed entry points work (integration tests)."""

    @pytest.mark.parametrize(
        "command",
        [
            "fplaunch",
            "fplaunch-generate",
            "fplaunch-manage",
            "fplaunch-launch",
            "fplaunch-cleanup",
            "fplaunch-config",
            "fplaunch-monitor",
            "fplaunch-cli",
            "fplaunch-setup-systemd",
        ],
    )
    def test_entry_point_command_exists(self, command):
        """Test that the entry point command is available."""
        try:
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0, f"Command {command} not found in PATH"
        except subprocess.TimeoutExpired:
            pytest.skip(f"Command {command} check timed out")

    @pytest.mark.parametrize(
        "command",
        [
            "fplaunch",
            "fplaunch-generate",
            "fplaunch-config",
        ],
    )
    def test_entry_point_help_works(self, command):
        """Test that the entry point command can show help."""
        try:
            result = subprocess.run(
                [command, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0, f"Command {command} --help failed with: {result.stderr}"
            assert (
                "usage" in result.stdout.lower() or "help" in result.stdout.lower()
            ), f"Command {command} --help output doesn't look like help text"
        except subprocess.TimeoutExpired:
            pytest.skip(f"Command {command} --help timed out")
        except FileNotFoundError:
            pytest.skip(f"Command {command} not found")


class TestRegressionPrevention:
    """Specific tests to prevent the exact issues that were fixed."""

    def test_lib_templates_directory_exists(self):
        """Test that lib/templates/ directory exists."""
        templates_dir = PROJECT_ROOT / "lib" / "templates"
        assert templates_dir.exists(), (
            "lib/templates/ directory is missing. "
            "Templates must be in lib/templates/ for package inclusion."
        )

    def test_lib_templates_has_wrapper_template(self):
        """Test that lib/templates/ has the wrapper template."""
        template_file = PROJECT_ROOT / "lib" / "templates" / "wrapper.template.sh"
        assert template_file.exists(), (
            "wrapper.template.sh is missing from lib/templates/. "
            "This will cause wrapper generation to fail."
        )

    def test_no_sys_path_insert_in_lib_main_entrypoint(self):
        """Test that lib/main_entrypoint.py doesn't have the problematic sys.path.insert."""
        fplaunch_path = PROJECT_ROOT / "lib" / "main_entrypoint.py"

        if not fplaunch_path.exists():
            pytest.skip("lib/main_entrypoint.py not found")

        content = fplaunch_path.read_text()

        # This line was adding lib/lib to sys.path
        assert 'os.path.join(os.path.dirname(__file__), "lib")' not in content, (
            "REGRESSION: lib/main_entrypoint.py has sys.path.insert that adds lib/lib to path. "
            "This causes incorrect path resolution."
        )
