#!/usr/bin/env python3
"""Regression tests for code-audit findings (lib/cleanup.py, lib/fplaunch.py, lib/portal_launcher.py).

Each test pins one of the three real bugs found in the project review:

1. lib/cleanup.py had ``console = Console()`` twice (duplicate assignment).
2. lib/fplaunch.py aliased ``is_wrapper_file`` to ``safe_launch_check``,
   so ``fplaunch.safe_launch_check`` was the wrong function entirely.
3. lib/portal_launcher.py had two ``subprocess.run`` calls without an
   explicit ``check=`` argument, inconsistent with the rest of the codebase.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest


LIB_DIR = Path(__file__).resolve().parent.parent.parent / "lib"


def _read_source(module_name: str) -> str:
    """Return the source of a lib/ module as text."""
    return (LIB_DIR / f"{module_name}.py").read_text(encoding="utf-8")


def _parse_module(module_name: str) -> ast.Module:
    """Parse a lib/ module and return its AST."""
    return ast.parse(_read_source(module_name), filename=str(LIB_DIR / f"{module_name}.py"))


class TestCleanupDuplicateConsole:
    """lib/cleanup.py must not have a duplicate top-level ``console = Console()`` assignment."""

    def test_cleanup_has_only_one_console_assignment(self) -> None:
        """The cleanup module must create exactly one Console at module scope."""
        tree = _parse_module("cleanup")
        assignments = [
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "console"
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "Console"
        ]
        assert len(assignments) == 1, (
            f"lib/cleanup.py must have exactly one top-level `console = Console()` "
            f"assignment, found {len(assignments)}."
        )

    def test_cleanup_console_is_defined_at_module_level(self) -> None:
        """The console object must still be defined (sanity check the fix didn't drop it)."""
        tree = _parse_module("cleanup")
        has_console_assign = any(
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "console"
            for node in tree.body
        )
        assert has_console_assign, "lib/cleanup.py must still define `console` at module level."


class TestFplaunchSafeLaunchCheck:
    """lib/fplaunch.py must expose the real ``safe_launch_check`` from lib.safety, not is_wrapper_file."""

    def test_fplaunch_safe_launch_check_is_safety_function(self) -> None:
        """fplaunch.safe_launch_check must be the same object as safety.safe_launch_check."""
        from lib import fplaunch
        from lib.safety import safe_launch_check

        assert fplaunch.safe_launch_check is safe_launch_check, (
            "lib.fplaunch.safe_launch_check must be the real safety.safe_launch_check "
            "function, not an alias for is_wrapper_file."
        )

    def test_fplaunch_safe_launch_check_calls_through_to_safety(self) -> None:
        """fplaunch.safe_launch_check must enforce the safety contract (test-env block etc)."""
        import os

        from lib import fplaunch

        # In a test environment the real safety.safe_launch_check allows non-browser
        # apps (returns True) but blocks direct browser launches (returns False).
        # is_wrapper_file would always return False here because no such file exists.
        assert os.environ.get("PYTEST_CURRENT_TEST"), "this assertion requires pytest"

        non_browser_result = fplaunch.safe_launch_check("gedit")
        assert non_browser_result is True, (
            "safe_launch_check must allow non-browser apps in a test environment; "
            "got False, which means fplaunch.safe_launch_check is the wrong function."
        )


class TestPortalLauncherExplicitCheck:
    """lib/portal_launcher.py must pass ``check=`` explicitly to every subprocess.run call."""

    @pytest.mark.parametrize(
        "function_name",
        ["launch_with_portal", "launch_direct"],
    )
    def test_subprocess_run_has_explicit_check(self, function_name: str) -> None:
        """Every subprocess.run inside the launch function must specify check= explicitly."""
        from lib import portal_launcher

        source = inspect.getsource(getattr(portal_launcher, function_name))

        tree = ast.parse(source)
        run_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ]

        assert run_calls, f"expected at least one subprocess.run call in {function_name}"

        for call in run_calls:
            keywords = {kw.arg for kw in call.keywords if kw.arg is not None}
            assert "check" in keywords, (
                f"subprocess.run in {function_name} must pass `check` explicitly. "
                f"Found keywords: {sorted(keywords)}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
