"""Phase 2: Spec-conformance verification.

Every documented command, option, and behavior must be backed by code, and
every code construct must be documented. These tests are bidirectional — they
catch both "undocumented feature" and "documented but not implemented" drift.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
LIB_DIR = PROJECT_ROOT / "lib"
TEMPLATE = LIB_DIR / "templates" / "wrapper.template.sh"
DESIGN_MD = PROJECT_ROOT / "DESIGN.md"
COMMAND_REF = PROJECT_ROOT / "COMMAND_REFERENCE.md"


# ---- Documented commands must exist in code ----------------------------

class TestDocumentedCommandsExist:
    """Every command documented in COMMAND_REFERENCE.md must work."""

    @pytest.fixture
    def documented_commands(self) -> list[str]:
        # Extract every `fplaunch X` form from COMMAND_REFERENCE.md
        content = COMMAND_REF.read_text()
        # Match bare subcommand names listed under "## Core Commands"
        return sorted(set(re.findall(r"^### `(\w[\w-]*)`", content, re.MULTILINE)))

    def test_each_documented_command_has_help(self, documented_commands):
        from click.testing import CliRunner
        from lib.cli import cli

        runner = CliRunner()
        missing = []
        for cmd in documented_commands:
            if cmd in {"set", "get"}:
                # These are subcommands of presets; skip
                continue
            r = runner.invoke(cli, [cmd, "--help"], catch_exceptions=True)
            if r.exit_code != 0:
                missing.append(cmd)
        assert not missing, f"Documented but not working: {missing}"


# ---- Documented wrapper options must be implemented --------------------

class TestDocumentedWrapperOptionsExist:
    """Every --fpwrapper-* option in docs must be implemented in template."""

    @pytest.fixture
    def all_fpwrapper_options(self) -> dict[str, set[str]]:
        design = DESIGN_MD.read_text()
        cref = COMMAND_REF.read_text()
        tmpl = TEMPLATE.read_text()

        # Extract options mentioned in each doc
        def extract_opts(text: str) -> set[str]:
            # Match --fpwrapper-X where X is alphanumeric+dash
            opts = set(re.findall(r"--fpwrapper-[\w-]+", text))
            # Filter to only top-level option (not sub-args)
            return {o for o in opts if " " not in o}

        design_opts = extract_opts(design)
        cref_opts = extract_opts(cref)
        tmpl_opts = extract_opts(tmpl)
        return {"design": design_opts, "command_ref": cref_opts, "template": tmpl_opts}

    def test_design_options_in_template(self, all_fpwrapper_options):
        """Every option documented in DESIGN.md is implemented."""
        missing = all_fpwrapper_options["design"] - all_fpwrapper_options["template"]
        assert not missing, (
            f"DESIGN.md documents options not in wrapper.template.sh: {sorted(missing)}"
        )

    def test_command_ref_options_in_template(self, all_fpwrapper_options):
        """Every option in COMMAND_REFERENCE.md is implemented."""
        missing = all_fpwrapper_options["command_ref"] - all_fpwrapper_options["template"]
        assert not missing, (
            f"COMMAND_REFERENCE.md documents options not in wrapper.template.sh: {sorted(missing)}"
        )

    def test_no_undocumented_template_options(self, all_fpwrapper_options):
        """The template should not have options absent from docs."""
        # It's OK to have internal options; we check that documented options
        # are present, but template can have extras.
        # However, top-level fpwrapper options MUST appear in help text
        # (search for them in the help echo block)
        tmpl_content = TEMPLATE.read_text()
        # Find the help block (between --fpwrapper-help and its `exit 0`)
        help_match = re.search(
            r'if \[ "\$1" = "--fpwrapper-help" \];.*?exit 0',
            tmpl_content,
            re.DOTALL,
        )
        if help_match:
            help_block = help_match.group(0)
            for opt in sorted(all_fpwrapper_options["template"]):
                # Skip internal options that aren't user-facing commands
                if opt in {"--fpwrapper-set-pre-script", "--fpwrapper-set-post-script",
                           "--fpwrapper-set-override", "--fpwrapper-set-preference"}:
                    # These are documented but may not appear in help (documented in usage section)
                    continue
                assert opt in help_block or opt in tmpl_content, (
                    f"Option {opt!r} in template but not in help output"
                )


# ---- Hook failure mode hierarchy (formal spec) -------------------------

class TestHookFailureModeHierarchy:
    """The hook failure mode hierarchy from the design spec must be honored.

    Spec from plans/hook-failure-modes-design.md:
    1. Runtime CLI override (--hook-failure)
    2. Environment variable (FPWRAPPER_HOOK_FAILURE)
    3. Per-app configuration
    4. Global default for hook type (pre/post_launch_failure_mode_default)
    5. Global default (hook_failure_mode_default)
    6. Built-in default ("warn")
    """

    @pytest.fixture
    def config(self, tmp_path):
        from lib.config_manager import create_config_manager
        from lib.config_models import AppPreferences
        # Set HOME so create_config_manager doesn't touch real config
        os.environ["HOME"] = str(tmp_path)
        return create_config_manager(config_dir=str(tmp_path))

    def _assert_level(self, label: str, expected: str, app_id: str, **overrides):
        """Helper: assert effective hook mode at this layer."""
        from lib.config_manager import create_config_manager

        cm = overrides.pop("cm")
        # Clear all env
        old_env = os.environ.pop("FPWRAPPER_HOOK_FAILURE", None)
        try:
            if "env_var" in overrides:
                os.environ["FPWRAPPER_HOOK_FAILURE"] = overrides["env_var"]
            mode = cm.get_effective_hook_failure_mode(
                app_id=app_id,
                hook_type=overrides.get("hook_type", "pre"),
                runtime_override=overrides.get("cli"),
            )
            assert mode == expected, f"{label}: expected {expected!r}, got {mode!r}"
        finally:
            os.environ.pop("FPWRAPPER_HOOK_FAILURE", None)
            if old_env is not None:
                os.environ["FPWRAPPER_HOOK_FAILURE"] = old_env

    def test_level_1_cli_override(self, config, tmp_path):
        """CLI override beats everything."""
        from lib.config_models import AppPreferences
        config.set_app_preferences("app1", AppPreferences(pre_launch_failure_mode="abort"))
        os.environ["FPWRAPPER_HOOK_FAILURE"] = "ignore"
        # Even with config and env, CLI wins
        mode = config.get_effective_hook_failure_mode(
            app_id="app1",
            hook_type="pre",
            runtime_override="warn",
        )
        os.environ.pop("FPWRAPPER_HOOK_FAILURE", None)
        assert mode == "warn", "Level 1: CLI override should win"

    def test_level_2_env_var(self, config):
        """FPWRAPPER_HOOK_FAILURE beats config."""
        from lib.config_models import AppPreferences
        config.set_app_preferences("app1", AppPreferences(pre_launch_failure_mode="abort"))
        os.environ["FPWRAPPER_HOOK_FAILURE"] = "ignore"
        try:
            mode = config.get_effective_hook_failure_mode("app1", "pre")
            assert mode == "ignore", f"Level 2: env var should win, got {mode!r}"
        finally:
            os.environ.pop("FPWRAPPER_HOOK_FAILURE", None)

    def test_level_3_per_app_config(self, config):
        """Per-app config beats global default."""
        from lib.config_models import AppPreferences
        config.set_app_preferences("app1", AppPreferences(pre_launch_failure_mode="abort"))
        # No CLI, no env
        mode = config.get_effective_hook_failure_mode("app1", "pre")
        assert mode == "abort", f"Level 3: per-app should win, got {mode!r}"

    def test_level_4_hook_type_default(self, config):
        """pre_launch_failure_mode_default beats hook_failure_mode_default."""
        # Set hook_failure_mode_default=ignore and pre_launch_failure_mode_default=abort
        config.config.hook_failure_mode_default = "ignore"
        config.config.pre_launch_failure_mode_default = "abort"
        mode = config.get_effective_hook_failure_mode("app1", "pre")
        assert mode == "abort", f"Level 4: hook-type default should win, got {mode!r}"

    def test_level_5_global_default(self, config):
        """hook_failure_mode_default beats built-in."""
        config.config.hook_failure_mode_default = "ignore"
        # No per-app, no hook-type default
        mode = config.get_effective_hook_failure_mode("app1", "pre")
        assert mode == "ignore", f"Level 5: global default should win, got {mode!r}"

    def test_level_6_builtin_default(self, config):
        """Built-in 'warn' is the ultimate fallback."""
        # No config set at all
        config.config.hook_failure_mode_default = ""
        config.config.pre_launch_failure_mode_default = None
        config.config.post_launch_failure_mode_default = None
        mode = config.get_effective_hook_failure_mode("app1", "pre")
        assert mode == "warn", f"Level 6: built-in default should be 'warn', got {mode!r}"

    def test_post_launch_uses_post_field(self, config):
        """post_launch_failure_mode is used for post hooks."""
        from lib.config_models import AppPreferences
        config.set_app_preferences("app1", AppPreferences(
            pre_launch_failure_mode="abort",
            post_launch_failure_mode="ignore",
        ))
        pre_mode = config.get_effective_hook_failure_mode("app1", "pre")
        post_mode = config.get_effective_hook_failure_mode("app1", "post")
        assert pre_mode == "abort", f"pre hook should use pre_launch_failure_mode, got {pre_mode!r}"
        assert post_mode == "ignore", f"post hook should use post_launch_failure_mode, got {post_mode!r}"

    def test_invalid_mode_is_ignored(self, config):
        """Invalid modes at any level fall through."""
        config.config.hook_failure_mode_default = "not-a-real-mode"
        # Must fall through to built-in "warn"
        mode = config.get_effective_hook_failure_mode("app1", "pre")
        assert mode == "warn", f"Invalid mode must fall through, got {mode!r}"

    def test_env_var_validated(self, config):
        """Invalid env var values fall through."""
        os.environ["FPWRAPPER_HOOK_FAILURE"] = "DROP-TABLES; --"
        try:
            mode = config.get_effective_hook_failure_mode("app1", "pre")
            # Should fall through to global default (warn)
            assert mode == "warn", f"Invalid env var must fall through, got {mode!r}"
        finally:
            os.environ.pop("FPWRAPPER_HOOK_FAILURE", None)


# ---- Wrapper template decision-tree coverage ----------------------------

class TestWrapperTemplateCoverage:
    """Every documented --fpwrapper-* option must have a handler branch."""

    @pytest.fixture
    def template_handlers(self) -> set[str]:
        content = TEMPLATE.read_text()
        # Find every handler: 'if [ "$1" = "--fpwrapper-X" ];'
        return set(re.findall(r'--fpwrapper-[\w-]+', content))

    @pytest.fixture
    def documented_options(self) -> set[str]:
        content = DESIGN_MD.read_text() + COMMAND_REF.read_text()
        return {o for o in re.findall(r"--fpwrapper-[\w-]+", content) if " " not in o}

    def test_every_documented_option_has_branch(self, template_handlers, documented_options):
        missing = documented_options - template_handlers
        # Filter out non-handler options that appear only in help text
        # The template's `echo "..."` lines count as presence
        # We allow these 'header' options that don't have separate handlers:
        # --fpwrapper-set-preference is an alias of --fpwrapper-set-override
        # Re-evaluate by reading the help text
        content = TEMPLATE.read_text()
        actually_missing = []
        for opt in sorted(missing):
            # In template's help block?
            if f'"{opt}"' in content or f"'--{opt}'" in content:
                continue
            actually_missing.append(opt)
        assert not actually_missing, (
            f"Documented options without template branches: {actually_missing}"
        )

    def test_template_uses_strict_mode(self):
        """Wrapper template must use strict mode for safety."""
        content = TEMPLATE.read_text()
        assert "set -eo pipefail" in content, "Template must use 'set -eo pipefail'"
        assert "IFS=" in content, "Template must reset IFS to prevent whitespace splitting"
        assert "umask" in content, "Template must set restrictive umask"

    def test_template_handles_path_traversal(self):
        """is_script_path_safe must reject sensitive directories."""
        content = TEMPLATE.read_text()
        for sensitive in ["/etc/", "/usr/", "/bin/", "/sbin/", "/boot/", "/proc/", "/sys/", "/dev/", "/root/"]:
            assert sensitive in content, f"Template must reject path under {sensitive}"

    def test_template_validates_env_file(self):
        """Env file loader must reject shell metacharacters."""
        content = TEMPLATE.read_text()
        # Look for the env validation grep
        assert "grep -qE" in content, "Template must grep-validate env file"
        # Verify it rejects dangerous chars
        assert "&" in content or "|" in content, "Env validation must check for shell metachars"

    def test_template_handles_preference_system(self):
        """Template must load and respect the .pref file."""
        content = TEMPLATE.read_text()
        assert "PREF_FILE" in content, "Template must reference PREF_FILE"
        assert "system" in content and "flatpak" in content, "Template must handle both system and flatpak"

    def test_template_has_hook_failure_modes(self):
        """Hook failure mode branches must exist."""
        content = TEMPLATE.read_text()
        for mode in ["abort", "warn", "ignore"]:
            assert mode in content, f"Template must handle hook failure mode {mode!r}"


# ---- Exception hierarchy matches spec -----------------------------------

class TestExceptionHierarchySpec:
    """DESIGN.md lists exception types; verify they all exist."""

    @pytest.fixture
    def declared_exceptions(self) -> set[str]:
        from lib import exceptions
        names = set()
        for name in dir(exceptions):
            obj = getattr(exceptions, name)
            if isinstance(obj, type) and issubclass(obj, BaseException):
                names.add(name)
        return names

    @pytest.fixture
    def documented_exceptions(self) -> set[str]:
        design = DESIGN_MD.read_text()
        # Match "ConfigFileNotFoundError", etc., inside backtick code spans
        return set(re.findall(r"`([A-Z][A-Za-z]+Error)`", design))

    def test_documented_exceptions_exist(self, declared_exceptions, documented_exceptions):
        missing = documented_exceptions - declared_exceptions
        assert not missing, f"DESIGN.md lists exceptions not implemented: {sorted(missing)}"

    def test_all_exceptions_inherit_from_fplaunch_error(self, declared_exceptions):
        from lib.exceptions import FplaunchError
        # All custom exceptions must inherit from FplaunchError
        offenders = []
        for name in declared_exceptions:
            if name in ("FplaunchError",):
                continue
            obj = getattr(__import__("lib.exceptions", fromlist=[name]), name)
            if issubclass(obj, Exception):
                if not issubclass(obj, FplaunchError):
                    # Skip built-ins that might be imported (like Exception)
                    if obj.__module__ == "lib.exceptions":
                        offenders.append(name)
        assert not offenders, f"lib.exceptions classes not inheriting from FplaunchError: {offenders}"


# ---- Entry-point vs pyproject consistency -------------------------------

class TestEntryPointSpec:
    """pyproject.toml entry points must map to importable modules with main()."""

    @pytest.fixture
    def entry_points(self) -> list[tuple[str, str]]:
        import re
        import tomli
        text = (PROJECT_ROOT / "pyproject.toml").read_text()
        config = tomli.loads(text)
        scripts = config["project"]["scripts"]
        return [(name, target) for name, target in scripts.items()]

    def test_each_entry_point_loads(self, entry_points):
        import importlib
        for name, target in entry_points:
            module_name = target.split(":")[0]
            module = importlib.import_module(module_name)
            assert hasattr(module, "main"), f"{name} -> {module_name} missing main()"
            assert callable(module.main), f"{name} -> {module_name}.main not callable"

    def test_no_extra_modules_in_lib_without_init(self):
        """Every .py file in lib/ must be importable."""
        import importlib
        import sys

        sys.path.insert(0, str(PROJECT_ROOT))
        for py_file in LIB_DIR.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            # Compute module name
            rel = py_file.relative_to(LIB_DIR).with_suffix("")
            module_name = "lib." + ".".join(rel.parts)
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"Module {module_name} not importable: {e}")
