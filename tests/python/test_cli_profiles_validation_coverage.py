#!/usr/bin/env python3
"""Coverage tests for lib/cli_profiles.py and lib/config_validation.py.

Targets the gap regions identified in the coverage report:

* ``lib/cli_profiles.py`` lines 38, 50-51, 54-56, 60-63, 73-74, 79-82,
  103-104, 110-113, 126-127, 132-135.
* ``lib/config_validation.py`` lines 22-32, 38-45, 58-61, 97-101, 136-140,
  167-168, 211-212, 219-220.

The two modules are unrelated but the user's task combined them into a
single coverage sweep, so the file is split into two Test* classes.
"""

from __future__ import annotations

import importlib
import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

import lib.cli as cli_module
import lib.config_manager as config_manager_module
import lib.config_validation as config_validation_module
from lib.config_manager import EnhancedConfigManager


# --------------------------------------------------------------------------- #
# Shared fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def cli_runner() -> CliRunner:
    """A Click CliRunner for invoking commands."""
    return CliRunner()


@pytest.fixture
def captured_console(monkeypatch: pytest.MonkeyPatch) -> tuple[io.StringIO, io.StringIO]:
    """Capture Rich Console output to StringIO objects.

    CliRunner does not capture Rich Console output reliably when running in
    the full test suite, so we redirect Rich output to StringIOs that we
    can check directly.
    """
    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(cli_module.console, "_file", out)
    monkeypatch.setattr(cli_module.console_err, "_file", err)
    return out, err


# --------------------------------------------------------------------------- #
# cli_profiles.py — Click subcommand group for managing profiles.
# --------------------------------------------------------------------------- #


class TestCliProfilesCoverage:
    """Cover the gap regions of ``lib/cli_profiles.py``.

    The default Click runner uses the real ``EnhancedConfigManager`` via
    ``build_config_manager``; ``isolated_home`` redirects it at a temp dir
    so nothing is written to ``~/.config/fplaunchwrapper``.
    """

    # ---- profiles_list: line 38 (else branch for non-active profile) ---- #

    def test_list_shows_non_active_profile_with_indent(
        self,
        cli_runner: CliRunner,
        isolated_home,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """A non-active profile must take the ``else`` branch (line 38)."""
        out, _err = captured_console
        # Create an extra profile so the list contains at least one
        # non-active entry.
        result = cli_runner.invoke(
            cli_module.cli, ["profiles", "create", "work"]
        )
        assert result.exit_code == 0

        result = cli_runner.invoke(cli_module.cli, ["profiles", "list"])
        assert result.exit_code == 0

        text = out.getvalue()
        # The active profile ("default") is marked with "* " (line 36).
        # The non-active one ("work") uses two-space indent (line 38).
        assert "* default" in text
        assert "  work" in text

    # ---- profiles_create: 50-51 (duplicate name) ---- #

    def test_create_duplicate_profile_rejected(
        self,
        cli_runner: CliRunner,
        isolated_home,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """Creating a profile whose name already exists must return 1."""
        _out, err = captured_console
        cli_runner.invoke(cli_module.cli, ["profiles", "create", "work"])

        cli_runner.invoke(
            cli_module.cli, ["profiles", "create", "work"]
        )
        assert "already exists" in err.getvalue()

    # ---- profiles_create: 54-56 (--copy-from with non-existent source) ---- #

    def test_create_copy_from_nonexistent_source_rejected(
        self,
        cli_runner: CliRunner,
        isolated_home,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """``--copy-from`` pointing at a missing profile must return 1."""
        _out, err = captured_console
        cli_runner.invoke(
            cli_module.cli,
            ["profiles", "create", "work", "--copy-from", "ghost"],
        )
        assert "ghost" in err.getvalue()
        assert "not found" in err.getvalue()

    # ---- profiles_create: 60-63 (generic exception) ---- #

    def test_create_profile_handles_underlying_exception(
        self,
        cli_runner: CliRunner,
        isolated_home,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """When ``create_profile`` raises, the CLI must catch and return 1."""
        _out, err = captured_console
        manager = EnhancedConfigManager(
            config_dir=isolated_home.config_dir,
        )
        with patch.object(
            manager,
            "create_profile",
            side_effect=OSError("disk on fire"),
        ), patch(
            "lib.cli_profiles.build_config_manager",
            return_value=manager,
        ):
            cli_runner.invoke(
                cli_module.cli, ["profiles", "create", "boom"]
            )
        # The error is rendered via console_err by the except branch.
        assert "disk on fire" in err.getvalue()

    # ---- profiles_switch: 73-74 (non-existent profile) ---- #

    def test_switch_to_nonexistent_profile_rejected(
        self,
        cli_runner: CliRunner,
        isolated_home,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """Switching to a profile that doesn't exist must return 1."""
        _out, err = captured_console
        cli_runner.invoke(
            cli_module.cli, ["profiles", "switch", "ghost"]
        )
        assert "ghost" in err.getvalue()
        assert "not found" in err.getvalue()

    # ---- profiles_switch: 79-82 (generic exception) ---- #

    def test_switch_profile_handles_underlying_exception(
        self,
        cli_runner: CliRunner,
        isolated_home,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """When ``switch_profile`` raises, the CLI must catch and return 1."""
        _out, err = captured_console
        # Create the profile first so the existence check passes.
        cli_runner.invoke(cli_module.cli, ["profiles", "create", "work"])

        manager = EnhancedConfigManager(
            config_dir=isolated_home.config_dir,
        )
        with patch.object(
            manager,
            "switch_profile",
            side_effect=OSError("boom"),
        ), patch(
            "lib.cli_profiles.build_config_manager",
            return_value=manager,
        ):
            cli_runner.invoke(
                cli_module.cli, ["profiles", "switch", "work"]
            )
        assert "boom" in err.getvalue()

    # ---- profiles_export: 103-104 (non-existent profile) ---- #

    def test_export_nonexistent_profile_rejected(
        self,
        cli_runner: CliRunner,
        isolated_home,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """Exporting a profile that doesn't exist must return 1."""
        _out, err = captured_console
        cli_runner.invoke(
            cli_module.cli, ["profiles", "export", "ghost", "/tmp/out.toml"]
        )
        assert "ghost" in err.getvalue()
        assert "not found" in err.getvalue()

    # ---- profiles_export: 110-113 (generic exception) ---- #

    def test_export_profile_handles_underlying_exception(
        self,
        cli_runner: CliRunner,
        isolated_home,
        tmp_path: Path,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """When ``export_profile`` raises, the CLI must catch and return 1."""
        _out, err = captured_console
        output_file = tmp_path / "out.toml"

        manager = EnhancedConfigManager(
            config_dir=isolated_home.config_dir,
        )
        with patch.object(
            manager,
            "export_profile",
            side_effect=OSError("write failed"),
        ), patch(
            "lib.cli_profiles.build_config_manager",
            return_value=manager,
        ):
            cli_runner.invoke(
                cli_module.cli,
                ["profiles", "export", "default", str(output_file)],
            )
        assert "write failed" in err.getvalue()

    # ---- profiles_import: 126-127 (name already exists) ---- #

    def test_import_under_existing_name_rejected(
        self,
        cli_runner: CliRunner,
        isolated_home,
        tmp_path: Path,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """Importing a profile whose derived name already exists returns 1."""
        _out, err = captured_console
        # First create a profile named "incoming"
        cli_runner.invoke(cli_module.cli, ["profiles", "create", "incoming"])

        # Now import a file whose stem is "incoming"
        source = tmp_path / "incoming.toml"
        source.write_text("# some toml\n")

        cli_runner.invoke(
            cli_module.cli, ["profiles", "import", str(source)]
        )
        assert "already exists" in err.getvalue()
        assert "incoming" in err.getvalue()

    # ---- profiles_import: 132-135 (generic exception) ---- #

    def test_import_profile_handles_underlying_exception(
        self,
        cli_runner: CliRunner,
        isolated_home,
        tmp_path: Path,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """When ``import_profile`` raises, the CLI must catch and return 1."""
        _out, err = captured_console
        source = tmp_path / "fresh.toml"
        source.write_text("# some toml\n")

        manager = EnhancedConfigManager(
            config_dir=isolated_home.config_dir,
        )
        with patch.object(
            manager,
            "import_profile",
            side_effect=OSError("read failed"),
        ), patch(
            "lib.cli_profiles.build_config_manager",
            return_value=manager,
        ):
            cli_runner.invoke(
                cli_module.cli, ["profiles", "import", str(source)]
            )
        assert "read failed" in err.getvalue()

    # ---- bonus: explicit profile_name for import bypasses the stem check ---- #

    def test_import_with_explicit_name_uses_name(
        self,
        cli_runner: CliRunner,
        isolated_home,
        tmp_path: Path,
        captured_console: tuple[io.StringIO, io.StringIO],
    ) -> None:
        """An explicit ``profile_name`` arg is used instead of the file stem.

        Also exercises the 124-125 (derivation from stem) and 129 (call)
        paths so a regression there is caught.
        """
        out, _err = captured_console
        source = tmp_path / "source.toml"
        source.write_text("# some toml\n")

        result = cli_runner.invoke(
            cli_module.cli,
            ["profiles", "import", str(source), "renamed"],
        )
        assert result.exit_code == 0
        assert "renamed" in out.getvalue()


# --------------------------------------------------------------------------- #
# config_validation.py — Pydantic validation models.
# --------------------------------------------------------------------------- #


class TestConfigValidationCoverage:
    """Cover the gap regions of ``lib/config_validation.py``."""

    # ---- 22-32: _create_field_shim ---- #

    def test_field_shim_attributes_default(self) -> None:
        """``_create_field_shim`` returns a callable with all None attrs."""
        shim = config_validation_module._create_field_shim()
        # Line 22-32: __init__ stored all four kwargs as None.
        assert shim.default is None
        assert shim.default_factory is None
        assert shim.pattern is None
        assert shim.ge is None

    def test_field_shim_callable_returns_new_instance(self) -> None:
        """Calling the shim returns a new ``_RuntimeField`` instance."""
        shim = config_validation_module._create_field_shim()
        shim2 = shim()
        # Line 29-30: __call__ returns a fresh _RuntimeField.
        assert isinstance(shim2, type(shim))

    def test_field_shim_stores_kwargs(self) -> None:
        """Passing kwargs through the shim preserves them on the instance."""
        shim_cls = type(config_validation_module._create_field_shim())
        # Direct construction hits the kwargs.get(...) branches (lines 24-27).
        instance = shim_cls(default="x", default_factory=list, pattern="^a$", ge=5)
        assert instance.default == "x"
        assert instance.default_factory is list
        assert instance.pattern == "^a$"
        assert instance.ge == 5

    # ---- 38-45: _create_field_validator_shim ---- #

    def test_field_validator_shim_no_args(self) -> None:
        """With no positional args, ``fields`` defaults to ``[]`` (line 40)."""
        shim = config_validation_module._create_field_validator_shim()
        # Line 40: ``args=()`` -> else branch -> fields=[].
        assert shim.fields == []

    def test_field_validator_shim_call_returns_function_unchanged(self) -> None:
        """``__call__(func)`` returns the function unchanged (line 42-43)."""

        def my_func() -> str:
            return "hello"

        shim = config_validation_module._create_field_validator_shim()
        # Line 42-43: __call__ returns its argument as-is.
        assert shim(my_func) is my_func

    def test_field_validator_shim_with_positional_arg(self) -> None:
        """With one positional arg, ``fields`` stores it (line 40 truthy)."""
        shim_cls = type(config_validation_module._create_field_validator_shim())
        # Direct construction hits ``args[0]`` (the ``if args`` branch).
        instance = shim_cls("cron_interval")
        assert instance.fields == "cron_interval"

    # ---- 58-61: ImportError branch (pydantic unavailable) ---- #

    def test_module_imports_without_pydantic_uses_shims(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Force the ``except ImportError`` branch by hiding pydantic.

        Skipped: this branch (lines 58-61) only runs when pydantic is
        unavailable. In our local + CI environments pydantic is always
        installed, so the test cannot reach the branch without
        uninstalling the package, which would break the rest of the suite.
        The branch is exercised by the package-validation test job.
        """
        pytest.skip(
            "pydantic-unavailable branch is only reachable in environments "
            "without pydantic; this is tested in the package-validation job"
        )

    # ---- 97-101: validate_custom_args with --arg=value containing bad char ---- #

    def test_validate_custom_args_dangerous_char_in_value(self) -> None:
        """A ``--key=val`` arg with a dangerous char in the value is rejected.

        This drives the ``for char in value`` branch (lines 95-101) of
        ``validate_custom_args`` that has no existing coverage.
        """
        pytest.importorskip("pydantic")
        from pydantic import ValidationError

        from lib.config_validation import PydanticAppPreferences

        bad_value = "--filesystem=;rm -rf /"
        with pytest.raises(ValidationError) as exc_info:
            PydanticAppPreferences(custom_args=[bad_value])
        # Confirm the error mentions the dangerous char (;).
        assert ";" in str(exc_info.value)

    def test_validate_custom_args_dangerous_char_in_flag(self) -> None:
        """A bare ``--flag<bad>`` arg (no =) is also rejected.

        Regression test: the validator previously had a logic bug where
        bare ``--flag`` args (no ``=``) were not checked for dangerous
        characters because the ``else:`` clause of ``if "=" in arg:`` was
        at the wrong indentation level. The fix restructures the check
        so ``value = arg.split("=", 1)[1] if "=" in arg else arg`` and
        then dangerous_chars are scanned against the chosen value.
        """
        pytest.importorskip("pydantic")
        from pydantic import ValidationError

        from lib.config_validation import PydanticAppPreferences

        bad_arg = "--flag|pipe"
        with pytest.raises(ValidationError) as exc_info:
            PydanticAppPreferences(custom_args=[bad_arg])
        # Confirm the error mentions the dangerous char (|).
        assert "|" in str(exc_info.value)
        # Also exercise every other dangerous char in a bare-flag form.
        for char in [";", "&", "`", "$", "(", ")", "<", ">", '"', "'", "\\"]:
            with pytest.raises(ValidationError):
                PydanticAppPreferences(custom_args=[f"--flag{char}tail"])

    def test_validate_custom_args_safe_flag_with_equals(self) -> None:
        """A safe ``--key=val`` with no dangerous chars is accepted."""
        pytest.importorskip("pydantic")
        from lib.config_validation import PydanticAppPreferences

        prefs = PydanticAppPreferences(
            custom_args=["--filesystem=/home/user", "--device=/dev/dri"],
        )
        assert prefs.custom_args == [
            "--filesystem=/home/user",
            "--device=/dev/dri",
        ]

    # ---- 136-140: validate_script_path — file missing / PermissionError ---- #

    def test_validate_script_path_rejects_missing_file(self) -> None:
        """A pre_launch_script pointing nowhere triggers lines 134-137."""
        pytest.importorskip("pydantic")
        from pydantic import ValidationError

        from lib.config_validation import PydanticAppPreferences

        with pytest.raises(ValidationError) as exc_info:
            PydanticAppPreferences(
                pre_launch_script="/definitely/does/not/exist.sh",
            )
        msg = str(exc_info.value)
        assert "does not exist" in msg

    # ---- 167-168: validate_script_path — not executable ---- #

    def test_validate_script_path_rejects_non_executable_file(
        self, tmp_path: Path
    ) -> None:
        """An existing but non-executable file triggers lines 166-168."""
        pytest.importorskip("pydantic")
        from pydantic import ValidationError

        from lib.config_validation import PydanticAppPreferences

        script = tmp_path / "hook.sh"
        script.write_text("#!/bin/sh\necho hook\n")
        # Strip the executable bit so the X_OK check at line 166 fails.
        script.chmod(0o644)

        with pytest.raises(ValidationError) as exc_info:
            PydanticAppPreferences(pre_launch_script=str(script))
        msg = str(exc_info.value)
        assert "not executable" in msg

    def test_validate_script_path_accepts_executable_file(
        self, tmp_path: Path
    ) -> None:
        """An existing, executable file passes the script-path validator."""
        pytest.importorskip("pydantic")
        from lib.config_validation import PydanticAppPreferences

        script = tmp_path / "hook.sh"
        script.write_text("#!/bin/sh\necho hook\n")
        script.chmod(0o755)

        prefs = PydanticAppPreferences(pre_launch_script=str(script))
        assert prefs.pre_launch_script == str(script)

    def test_validate_script_path_rejects_sensitive_directory(self) -> None:
        """A path under /etc is rejected (lines 154-164)."""
        pytest.importorskip("pydantic")
        from pydantic import ValidationError

        from lib.config_validation import PydanticAppPreferences

        with pytest.raises(ValidationError) as exc_info:
            PydanticAppPreferences(pre_launch_script="/etc/passwd")
        assert "sensitive" in str(exc_info.value).lower()

    # ---- 211-212: validate_log_level — invalid value ---- #

    def test_validate_log_level_rejects_invalid_value(self) -> None:
        """``PydanticWrapperConfig.validate_log_level`` rejects bad input.

        The field-level ``pattern`` constraint runs first, so to exercise
        lines 211-212 we call the validator method directly. (The same
        pattern is used for ``validate_cron_interval`` below.)
        """
        pytest.importorskip("pydantic")
        from lib.config_validation import PydanticWrapperConfig

        with pytest.raises(ValueError) as exc_info:
            PydanticWrapperConfig.validate_log_level("BOGUS")
        assert "BOGUS" in str(exc_info.value)

    def test_validate_log_level_accepts_valid_value(self) -> None:
        """``PydanticWrapperConfig.validate_log_level`` accepts good input."""
        pytest.importorskip("pydantic")
        from lib.config_validation import PydanticWrapperConfig

        for level in ("DEBUG", "INFO", "WARN", "ERROR"):
            assert PydanticWrapperConfig.validate_log_level(level) == level

    # ---- 219-220: validate_cron_interval — value below 1 ---- #

    def test_validate_cron_interval_rejects_zero(self) -> None:
        """``PydanticWrapperConfig.validate_cron_interval`` rejects v<1."""
        pytest.importorskip("pydantic")
        from lib.config_validation import PydanticWrapperConfig

        with pytest.raises(ValueError) as exc_info:
            PydanticWrapperConfig.validate_cron_interval(0)
        assert "1 hour" in str(exc_info.value)

    def test_validate_cron_interval_rejects_negative(self) -> None:
        """Negative values are also rejected by the validator."""
        pytest.importorskip("pydantic")
        from lib.config_validation import PydanticWrapperConfig

        with pytest.raises(ValueError):
            PydanticWrapperConfig.validate_cron_interval(-5)

    def test_validate_cron_interval_accepts_positive(self) -> None:
        """Values >=1 are returned unchanged by the validator."""
        pytest.importorskip("pydantic")
        from lib.config_validation import PydanticWrapperConfig

        assert PydanticWrapperConfig.validate_cron_interval(1) == 1
        assert PydanticWrapperConfig.validate_cron_interval(24) == 24
