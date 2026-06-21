"""Phase 13: Targeted adversarial tests for bugs found in 2026-06 audit.

Each test class targets a specific bug discovered by systematic
auditing of under-tested modules:

- Bug #12: ``validate_wrapper_name`` accepted consecutive dots
- Bug #13: ``lib.safety.validate_flatpak_id`` did not port the
  consecutive-dots fix (Bug #8 in validate_app_id)
- Bug #14: ``_validate_custom_args_safety`` allowed newline, CR,
  NUL, space, and tab — only blocked shell metacharacters
- Bug #15: ``portal_launcher`` passed unvalidated ``flatpak_id``
  positionally to ``flatpak-spawn`` / ``flatpak``, enabling flag
  injection (e.g. ``--help`` would be interpreted as a flag, not
  an app ID)
- Bug #16: ``resolve_bin_dir`` trusted whatever path was in
  ``<config_dir>/bin_dir`` with no validation, allowing arbitrary
  filesystem redirection

These tests are the regression net for the fixes. If a fix is
reverted, the corresponding test must fail.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from lib.config_validation import _validate_custom_args_safety
from lib.paths import resolve_bin_dir
from lib.portal_launcher import (
    get_launch_command,
    launch_direct,
    launch_with_portal,
)
from lib.safety import validate_flatpak_id
from lib.validation import validate_app_id, validate_wrapper_name


# ---------------------------------------------------------------------------
# Bug #12 regression
# ---------------------------------------------------------------------------


class TestWrapperNameRejectsConsecutiveDots:
    """``validate_wrapper_name`` must reject ``..`` and any string
    containing ``..`` (consecutive dots). The fix in lib/validation.py
    treats ``..`` as a path-traversal trap rather than a valid filename
    component.

    Note: the lone string ``".."`` and the substring ``".."`` are both
    rejected. Single dots (``"."``) and the rest of valid POSIX names
    are unaffected.
    """

    @pytest.mark.parametrize(
        "name",
        [
            "..",        # parent-directory reference
            "foo..bar",  # consecutive dots in middle
            "foo..",     # trailing consecutive dots
            "..foo",     # leading consecutive dots
            "a..b..c",   # multiple consecutive dot groups
        ],
    )
    def test_consecutive_dots_rejected(self, name: str) -> None:
        ok, err = validate_wrapper_name(name)
        assert not ok, f"validate_wrapper_name accepted {name!r}: {err!r}"
        assert ".." in err, f"Error message should mention '..': {err!r}"

    def test_slash_containing_path_traversal_rejected(self) -> None:
        """Names with ``/`` are rejected by the slash check (which is
        applied first), and that's a stronger guarantee than the
        consecutive-dot check. This test pins that behavior."""
        for name in ("../", "../foo", "foo/..", "a/b"):
            ok, err = validate_wrapper_name(name)
            assert not ok, f"validate_wrapper_name accepted {name!r}: {err!r}"
        # For these inputs, the rejection is via the slash check, not the
        # consecutive-dot check, so the error message mentions '/'.
        ok, err = validate_wrapper_name("../")
        assert "/" in err


# ---------------------------------------------------------------------------
# Bug #13 regression — differential test for safety vs validation
# ---------------------------------------------------------------------------


class TestSafetyValidateFlatpakIdConsecutiveDots:
    """``lib.safety.validate_flatpak_id`` and ``lib.validation.validate_app_id``
    must agree on every input, including consecutive-dot patterns.
    """

    @pytest.mark.parametrize(
        "app_id",
        [
            "ab..cd",
            "org.foo..bar",
            "..foo",
            "foo..",
            "..",
            "a.b.c..d.e",
        ],
    )
    def test_validators_agree_on_consecutive_dots(self, app_id: str) -> None:
        ok_validation, _ = validate_app_id(app_id)
        ok_safety = validate_flatpak_id(app_id)
        assert ok_validation == ok_safety, (
            f"Validators disagree on {app_id!r}: "
            f"validate_app_id={ok_validation}, validate_flatpak_id={ok_safety}"
        )
        # Both should reject consecutive dots
        assert not ok_validation
        assert not ok_safety

    def test_safety_validator_still_accepts_valid_ids(self) -> None:
        """The fix must not break the happy path."""
        for app_id in ("org.mozilla.firefox", "com.example.App", "io.github.Test"):
            assert validate_flatpak_id(app_id), f"Rejected valid ID: {app_id}"


# ---------------------------------------------------------------------------
# Bug #14 regression — custom args validator
# ---------------------------------------------------------------------------


class TestValidateCustomArgsCatchesNewlinesAndWhitespace:
    """``_validate_custom_args_safety`` must reject newline, carriage
    return, NUL, space, and tab in addition to the original shell
    metacharacters. These chars can be used to break out of a config
    line, terminate a string prematurely, or smuggle arguments.
    """

    @pytest.mark.parametrize(
        "arg",
        [
            "--flag\nfoo",       # newline breaks config parsing
            "--flag\rfoo",       # carriage return
            "--flag\0foo",       # NUL byte
            "--flag\tfoo",       # tab (whitespace, can split args)
            "--flag foo",        # space
            "--flag=foo bar",    # space inside value
            "--flag\n--evil",    # newline followed by another arg
            "arg\nwith\nnewlines",  # multiple newlines
            "arg\twith\ttabs",
        ],
    )
    def test_dangerous_chars_rejected(self, arg: str) -> None:
        # _validate_custom_args_safety raises SecurityValidationError
        # (a ValueError subclass) on dangerous input.
        with pytest.raises(ValueError) as exc:
            _validate_custom_args_safety([arg])
        # The exception message should mention the dangerous char or the arg
        assert arg in str(exc.value) or any(
            c in str(exc.value)
            for c in ["\n", "\r", "\0", "\t", " "]
        )

    def test_safe_args_still_accepted(self) -> None:
        """The fix should not break legitimate args."""
        safe = [
            [],
            ["--flag"],
            ["--flag=value"],
            ["--key=path/to/file"],
            ["--name=my-app"],
            ["-x", "--yes", "value"],
        ]
        for args in safe:
            # Should not raise
            result = _validate_custom_args_safety(list(args))
            assert result == args


# ---------------------------------------------------------------------------
# Bug #15 regression — portal_launcher flag injection
# ---------------------------------------------------------------------------


class TestPortalLauncherRejectsUnsafeFlatpakId:
    """``portal_launcher`` passes ``flatpak_id`` positionally to
    ``flatpak-spawn`` / ``flatpak``. If unvalidated, an attacker could
    pass ``--help`` or ``--env=LD_PRELOAD=...`` and have it interpreted
    as a flag rather than an app ID.
    """

    @pytest.mark.parametrize(
        "hostile_id",
        [
            "--help",            # would be interpreted as a flag
            "--version",         # would print version
            "--env=EVIL=1",      # env injection
            "-h",                # short flag
            "--user",            # subcommand-like
            "-app",              # leading hyphen
            "org.foo --evil",    # whitespace
            "org.foo\nbar",      # newline
            "org.foo\0bar",      # NUL
            ";rm -rf /",         # command injection (irrelevant w/ list-form,
                                 # but still rejected at API boundary)
            "org.foo;rm",
            "org.foo|`evil`",
            "org.foo$EVIL",
            "",                  # empty
        ],
    )
    def test_get_launch_command_rejects_hostile_id(self, hostile_id: str) -> None:
        with pytest.raises(ValueError):
            get_launch_command(hostile_id, use_portal=False)

    def test_get_launch_command_rejects_with_portal(self) -> None:
        """Even with use_portal=True, the unsafe ID must be rejected before
        we even check whether flatpak-spawn is available."""
        with pytest.raises(ValueError):
            get_launch_command("--evil-flag", use_portal=True)

    def test_launch_direct_rejects_hostile_id(self) -> None:
        with pytest.raises(ValueError):
            launch_direct("--help")

    def test_launch_with_portal_rejects_hostile_id(self) -> None:
        with pytest.raises(ValueError):
            launch_with_portal("--help")

    def test_safe_flatpak_ids_accepted(self) -> None:
        """The fix must not break legitimate Flatpak IDs."""
        for safe_id in (
            "org.mozilla.firefox",
            "com.example.App",
            "io.github.User.repo",
        ):
            cmd = get_launch_command(safe_id, use_portal=False)
            # The ID must appear as a positional arg, not interpreted as a flag
            assert safe_id in cmd, f"ID {safe_id!r} not in command: {cmd}"
            # No leading hyphen on the ID
            for arg in cmd:
                if arg == safe_id:
                    assert not arg.startswith("-"), (
                        f"ID should not start with '-': {arg!r}"
                    )

    def test_id_appears_positionally_not_as_flag(self) -> None:
        """If the validator were missing, ``--help`` would be parsed as
        a flag. This test verifies the ID is at the correct position
        (after ``flatpak run``)."""
        cmd = get_launch_command("org.test.app", use_portal=False)
        # Find 'run' index; the next arg should be the app id
        run_idx = cmd.index("run")
        assert cmd[run_idx + 1] == "org.test.app"


# ---------------------------------------------------------------------------
# Bug #16 regression — resolve_bin_dir trusts config
# ---------------------------------------------------------------------------


class TestResolveBinDirRejectsSystemPaths:
    """``resolve_bin_dir`` must not accept a ``bin_dir`` file inside
    ``config_dir`` that points to a sensitive system location. Without
    this check, anyone who can write to the config dir can redirect
    all wrapper output to ``/etc`` or ``/usr``.

    The fix should constrain the resolved bin_dir to live under
    ``Path.home()`` (or an explicit override).
    """

    @pytest.mark.parametrize(
        "hostile_path",
        [
            "/etc",
            "/usr",
            "/usr/local/bin",
            "/bin",
            "/sbin",
            "/root",
            "/var/lib/flatpak-exploit",
            "/tmp/attacker-controlled",
        ],
    )
    def test_system_path_in_bin_dir_file_rejected(
        self, tmp_path: Path, hostile_path: str
    ) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "bin_dir").write_text(hostile_path)

        # Explicit_dir=None, config_dir=ours — should NOT return hostile_path
        result = resolve_bin_dir(explicit_dir=None, config_dir=config_dir)
        # The result should not be the hostile path
        assert str(result) != hostile_path, (
            f"resolve_bin_dir accepted hostile path {hostile_path!r}: "
            f"got {result}"
        )
        # The result should be the default (~/bin) since the config value
        # was rejected
        assert result == Path.home() / "bin", (
            f"Expected fallback to ~/bin, got {result}"
        )

    def test_explicit_dir_still_honored(self, tmp_path: Path) -> None:
        """When the user explicitly passes ``explicit_dir``, the function
        should still honor it (the safety check only applies to the
        untrusted config file path)."""
        explicit = tmp_path / "my_custom_bin"
        explicit.mkdir()
        result = resolve_bin_dir(explicit_dir=str(explicit))
        assert result.resolve() == explicit.resolve()

    def test_home_relative_path_in_bin_dir_accepted(self, tmp_path: Path) -> None:
        """A bin_dir file pointing under $HOME should be accepted."""
        # Create a real subdir under home so the path resolves
        from pathlib import Path as P

        home_bin = P.home() / ".fplaunch_test_bin"
        home_bin.mkdir(exist_ok=True)
        try:
            config_dir = tmp_path / "config"
            config_dir.mkdir()
            (config_dir / "bin_dir").write_text(str(home_bin))
            result = resolve_bin_dir(explicit_dir=None, config_dir=config_dir)
            assert result.resolve() == home_bin.resolve()
        finally:
            import shutil

            if home_bin.exists():
                shutil.rmtree(home_bin)
