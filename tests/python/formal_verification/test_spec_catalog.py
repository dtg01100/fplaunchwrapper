"""Phase 1: Build executable spec catalog from docs and verify coverage.

This file extracts the formal specification from DESIGN.md and COMMAND_REFERENCE.md,
then verifies every claim is backed by either code or test coverage.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DESIGN_MD = PROJECT_ROOT / "DESIGN.md"
COMMAND_REF = PROJECT_ROOT / "COMMAND_REFERENCE.md"


class TestDesignSpecDocumented:
    """DESIGN.md must be a complete specification."""

    def test_design_md_exists(self):
        assert DESIGN_MD.exists(), "DESIGN.md is the project spec — must exist"

    def test_design_md_lists_entry_points(self):
        content = DESIGN_MD.read_text()
        # All entry points from pyproject.toml
        for ep in [
            "fplaunch",
            "fplaunch-cli",
            "fplaunch-generate",
            "fplaunch-manage",
            "fplaunch-launch",
            "fplaunch-cleanup",
            "fplaunch-setup-systemd",
            "fplaunch-config",
            "fplaunch-monitor",
        ]:
            assert ep in content, f"DESIGN.md must document entry point {ep!r}"

    def test_design_md_documents_wrapper_options(self):
        """Every --fpwrapper-* option listed in DESIGN.md must be implemented."""
        content = DESIGN_MD.read_text()
        # Extract all --fpwrapper-* options from the spec
        spec_options = set(re.findall(r"--fpwrapper-[\w-]+", content))
        # Now check the template implements them
        template = (PROJECT_ROOT / "lib" / "templates" / "wrapper.template.sh").read_text()
        impl_options = set(re.findall(r"--fpwrapper-[\w-]+", template))
        # Filter out those that appear only in help/usage text (e.g., --fpwrapper-set-preference, --fpwrapper-remove-pre-script, --fpwrapper-run-unrestricted need to be implemented)

        for opt in sorted(spec_options):
            if opt in impl_options:
                continue
            # Some options are referenced in DESIGN.md but only documented in COMMAND_REF
            # Verify it's at least in the template's help section
            in_help = opt in template
            assert in_help, (
                f"Spec option {opt!r} documented in DESIGN.md but not implemented "
                f"in wrapper.template.sh"
            )


class TestCommandReferenceDocumented:
    """COMMAND_REFERENCE.md must accurately document the CLI."""

    def test_command_ref_documents_global_options(self):
        content = COMMAND_REF.read_text()
        # Required global options from fplaunch --help
        for opt in ["--verbose", "-v", "--emit", "--emit-verbose", "--config-dir", "--version"]:
            assert opt in content, f"COMMAND_REFERENCE.md must document {opt!r}"

    def test_command_ref_documents_subcommand_groups(self):
        content = COMMAND_REF.read_text()
        for group in ["systemd", "profiles", "presets"]:
            assert group in content, f"COMMAND_REFERENCE.md must document {group!r} group"


class TestSpecExtraction:
    """Extract formal properties and confirm code implements them."""

    def test_all_subcommands_have_help(self):
        """Every subcommand in the CLI must have a --help that exits 0."""
        from click.testing import CliRunner
        from lib.cli import cli

        runner = CliRunner()
        # Walk the CLI tree to find every command
        def collect_commands(grp, prefix=""):
            cmds = []
            for name, cmd in grp.commands.items():
                full = f"{prefix}{name}" if prefix else name
                cmds.append(full)
                if hasattr(cmd, "commands"):
                    cmds.extend(collect_commands(cmd, full + " "))
            return cmds

        all_cmds = collect_commands(cli)
        # At minimum these must work
        assert len(all_cmds) >= 10, f"CLI must expose ≥10 subcommands, got {len(all_cmds)}: {all_cmds}"

        # Each must produce valid help
        broken = []
        for cmd_str in all_cmds:
            args = cmd_str.split() + ["--help"]
            result = runner.invoke(cli, args, catch_exceptions=False)
            if result.exit_code != 0:
                broken.append((cmd_str, result.output[:200] if hasattr(result, "output") else ""))
        assert not broken, f"Subcommands with broken --help: {broken[:5]}"

    def test_help_completeness_against_spec(self):
        """Every documented command must be invokable."""
        # Per COMMAND_REFERENCE.md, the following commands are documented
        documented = [
            "generate", "list", "info", "remove", "rm", "cleanup", "clean",
            "launch", "install", "uninstall", "manifest", "search", "discover",
            "config", "set-pref", "pref", "monitor", "files", "systemd-setup",
            "systemd",
        ]
        from click.testing import CliRunner
        from lib.cli import cli

        runner = CliRunner()
        for cmd in documented:
            # --help must succeed
            r = runner.invoke(cli, [cmd, "--help"], catch_exceptions=True)
            assert r.exit_code == 0, f"Documented command {cmd!r} missing or broken"


class TestVersionConsistency:
    """Version numbers must agree across all docs and code."""

    def test_pyproject_version_matches_lib(self):
        import re
        import tomli

        pyproject = tomli.loads((PROJECT_ROOT / "pyproject.toml").read_text())
        pyproject_version = pyproject["project"]["version"]

        lib_init = (PROJECT_ROOT / "lib" / "__init__.py").read_text()
        m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', lib_init)
        assert m, "lib/__init__.py must define __version__"
        assert m.group(1) == pyproject_version, (
            f"pyproject.toml version {pyproject_version!r} != "
            f"lib.__version__ {m.group(1)!r}"
        )

    def test_design_md_version_matches(self):
        """DESIGN.md's stated version must match the actual project version."""
        import re
        import tomli

        pyproject = tomli.loads((PROJECT_ROOT / "pyproject.toml").read_text())
        actual = pyproject["project"]["version"]

        design = DESIGN_MD.read_text()
        # Find "Version | X.Y.Z" or similar
        m = re.search(r"Version\s*\|\s*(\d+\.\d+\.\d+)", design)
        if m:
            doc_version = m.group(1)
            assert doc_version == actual, (
                f"DESIGN.md claims version {doc_version!r} but project is {actual!r}. "
                f"Documentation drift is a real bug."
            )
