#!/usr/bin/env python3
"""Extra coverage tests for lib/generate.py.

Targets the 76 lines reported as missing by coverage after the existing
test_generate_output.py / test_generate_real.py / test_generated_launchers.py
suites.  Each test class is annotated with the line ranges it exercises
in lib/generate.py so that regressions in coverage are easy to audit.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from lib.generate import WrapperGenerator, main
from lib.exceptions import ForbiddenNameError, WrapperGenerationError


# ---------------------------------------------------------------------------
# Lines 83, 85: __init__ type validation
# ---------------------------------------------------------------------------


class TestInitTypeValidation:
    """Lines 83, 85: __init__ raises TypeError for invalid types."""

    def test_init_rejects_non_pathlike_bin_dir(self) -> None:
        with pytest.raises(TypeError, match="bin_dir"):
            WrapperGenerator(bin_dir=12345)

    def test_init_rejects_non_pathlike_config_dir(self) -> None:
        with pytest.raises(TypeError, match="config_dir"):
            WrapperGenerator(bin_dir="/tmp/anything_safe", config_dir=object())


# ---------------------------------------------------------------------------
# Lines 107-113, 130, 134: _safe_resolve_bin_dir boundary/branch logic
# ---------------------------------------------------------------------------


class TestSafeResolveBinDir:
    """Lines 107-113, 130, 134: bin_dir path resolution branches."""

    def test_bin_dir_outside_home_falls_back(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Lines 107-113: print warning and fall back to ~/bin."""
        # /etc/foo resolves outside home and is not /tmp -> fallback
        gen = WrapperGenerator(bin_dir="/etc/some-fake-bin-dir")
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "resolves outside home" in captured.err
        # The fallback resolves to <home>/bin
        assert str(gen.bin_dir).endswith(os.path.join("bin"))

    def test_tilde_prefix_branch(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Line 130: tilde-prefixed bin_dir is expanduser-resolved."""
        monkeypatch.setenv("HOME", str(tmp_path))
        gen = WrapperGenerator(bin_dir="~/tilde_bin")
        assert str(gen.bin_dir).startswith(str(tmp_path))

    def test_relative_path_branch(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Line 134: non-absolute, non-tilde path goes through expanduser().resolve()."""
        monkeypatch.setenv("HOME", str(tmp_path))
        rel = "rel_bin"
        old_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            gen = WrapperGenerator(bin_dir=rel)
            # resolves under tmp_path
            assert str(gen.bin_dir).startswith(str(tmp_path))
        finally:
            os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# Line 157-159: run_command with verbose=True and description
# ---------------------------------------------------------------------------


class TestRunCommandVerbose:
    """Lines 157-159: run_command verbose + description branch."""

    def test_run_command_verbose_with_description(self, tmp_path: Path) -> None:
        bin_dir = tmp_path / "bin"
        config_dir = tmp_path / "cfg"
        gen = WrapperGenerator(
            bin_dir=bin_dir,
            config_dir=config_dir,
            verbose=True,
        )
        with patch("lib.generate.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="hi", stderr="")
            result = gen.run_command(["echo", "hi"], "doing a thing")
        # Verbose path goes through self.log(..., "debug") and a plain subprocess.run
        assert result.returncode == 0
        assert result.stdout == "hi"
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        # No console.status context manager -> captured_output stays the default True
        assert call_args.kwargs.get("capture_output", True) is True


# ---------------------------------------------------------------------------
# Line 168: get_installed_flatpaks when flatpak binary is missing
# ---------------------------------------------------------------------------


class TestGetInstalledFlatpaksNoBinary:
    """Line 168: WrapperGenerationError when flatpak is not in PATH."""

    def test_missing_flatpak_binary(self, tmp_path: Path) -> None:
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        with patch("lib.generate.find_executable", return_value=None):
            with pytest.raises(WrapperGenerationError, match="Failed to find flatpak"):
                gen.get_installed_flatpaks()


# ---------------------------------------------------------------------------
# Lines 219-221: is_blocklisted OSError path
# ---------------------------------------------------------------------------


class TestIsBlocklistedOSError:
    """Lines 219-221: blocklist file present but read_text raises OSError."""

    def test_is_blocklisted_oserror_returns_false(self, tmp_path: Path) -> None:
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        blocklist = gen.config_dir / "blocklist"
        blocklist.write_text("com.example.blocked\n")
        with patch.object(Path, "read_text", autospec=True, side_effect=OSError("boom")):
            assert gen.is_blocklisted("com.example.blocked") is False


# ---------------------------------------------------------------------------
# Lines 232-233, 251-252, 274-275, 297-299: create_wrapper_script error paths
# ---------------------------------------------------------------------------


class TestCreateWrapperScriptEdgeCases:
    """Lines 232-233, 251-252, 274-275, 297-299: edge cases in template loading."""

    def test_importlib_files_raises_swallowed(self, tmp_path: Path) -> None:
        """Lines 232-233: importlib_files raises, except branch silently swallows."""
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        with patch("lib.generate.importlib_files", side_effect=FileNotFoundError):
            # The lib/templates wrapper exists but the worktree has no
            # project-root templates/ dir, so we end up raising at 251-252.
            # The except at 232-233 was still entered, which is the path
            # we want to exercise.
            with pytest.raises(WrapperGenerationError, match="Wrapper template file not found"):
                gen.create_wrapper_script("foo", "org.example.foo")

    def test_template_not_found(self, tmp_path: Path) -> None:
        """Lines 251-252: WrapperGenerationError when no template candidate exists."""
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )

        def _exists(self: Path) -> bool:  # noqa: D401 - method override
            return False

        with patch.object(Path, "exists", _exists):
            with pytest.raises(WrapperGenerationError, match="Wrapper template file not found"):
                gen.create_wrapper_script("foo", "org.example.foo")

    def test_config_manager_oserror_swallowed(self, tmp_path: Path) -> None:
        """Lines 274-275: config_manager OSError is caught and ignored."""
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        # create_config_manager is imported lazily inside create_wrapper_script
        # via `from .config_manager import create_config_manager`, so patch
        # the source module to raise.
        with patch("lib.config_manager.create_config_manager", side_effect=OSError("cfg down")):
            content = gen.create_wrapper_script("foo", "org.example.foo")
        # Defaults should be used: failure_mode=warn, hooks empty
        assert 'HOOK_FAILURE_MODE="warn"' in content
        assert 'PRE_SCRIPT="$HOOK_DIR/pre-launch.sh"' in content

    def test_template_read_oserror(self, tmp_path: Path) -> None:
        """Lines 297-299: read_text on an existing template raises OSError -> wraps."""
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        # Force read_text to raise even though the file exists
        real_read_text = Path.read_text

        def _boom(self: Path, *args: object, **kwargs: object) -> str:
            if self.name == "wrapper.template.sh":
                raise OSError("read failed")
            return real_read_text(self, *args, **kwargs)

        with patch.object(Path, "read_text", _boom):
            with pytest.raises(WrapperGenerationError, match="Failed to read wrapper template"):
                gen.create_wrapper_script("foo", "org.example.foo")


# ---------------------------------------------------------------------------
# Lines 312-314, 317-318: generate_wrapper sanitization early-outs
# ---------------------------------------------------------------------------


class TestGenerateWrapperSanitization:
    """Lines 312-314, 317-318: forbidden name and empty name short-circuits."""

    def test_sanitize_raises_forbidden_name(self, tmp_path: Path) -> None:
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        with patch("lib.generate.sanitize_id_to_name", side_effect=ForbiddenNameError("x")):
            assert gen.generate_wrapper("com.example.any") is False

    def test_sanitize_returns_empty_string(self, tmp_path: Path) -> None:
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        with patch("lib.generate.sanitize_id_to_name", return_value=""):
            assert gen.generate_wrapper("com.example.any") is False


# ---------------------------------------------------------------------------
# Lines 334-335, 338-342: invalid flatpak_id argument branches
# ---------------------------------------------------------------------------


class TestGenerateWrapperInvalidFlatpakId:
    """Lines 334-335, 338-342: bad flatpak_id arg path."""

    def test_invalid_flatpak_id_arg_skips(self, tmp_path: Path) -> None:
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        # flatpak_id with no dot and invalid chars -> regex fails
        assert gen.generate_wrapper("com.example.foo", flatpak_id="not a valid id!") is False

    def test_invalid_flatpak_id_unsanitizable(self, tmp_path: Path) -> None:
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        with patch("lib.generate.sanitize_id_to_name", return_value=""):
            # flatpak_id invalid -> falls back to sanitize_id_to_name
            # and that returns "" -> 338-342 path
            assert gen.generate_wrapper("com.example.foo", flatpak_id="bad id") is False

    def test_app_id_with_no_dot_and_unsanitizable(self, tmp_path: Path) -> None:
        """Lines 338-342: app_id has no dot and second sanitize returns empty string."""
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        # First sanitize call (line 311) returns a valid wrapper name so we
        # do not exit at line 318; the second call (line 336) returns "" so
        # we enter the "unsanitizable" log block at lines 338-342.
        calls = {"n": 0}

        def _sanitize(id_str: str) -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                return "validname"
            return ""

        with patch("lib.generate.sanitize_id_to_name", side_effect=_sanitize):
            assert gen.generate_wrapper("nodotatall") is False
        assert calls["n"] >= 2


# ---------------------------------------------------------------------------
# Lines 365-368, 394-397: generate_wrapper script creation / write errors
# ---------------------------------------------------------------------------


class TestGenerateWrapperWriteErrors:
    """Lines 365-368, 394-397: create_wrapper_script and write_text failure."""

    def test_create_wrapper_script_raises(self, tmp_path: Path) -> None:
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        with patch.object(
            gen,
            "create_wrapper_script",
            side_effect=WrapperGenerationError("com.example.foo", "nope"),
        ):
            assert gen.generate_wrapper("com.example.foo") is False

    def test_write_text_oserror(self, tmp_path: Path) -> None:
        gen = WrapperGenerator(
            bin_dir=tmp_path / "bin",
            config_dir=tmp_path / "cfg",
        )
        real_write_text = Path.write_text

        def _boom(self: Path, *args: object, **kwargs: object) -> int:
            if self.parent == gen.bin_dir:
                raise OSError("write failed")
            return real_write_text(self, *args, **kwargs)

        with patch.object(Path, "write_text", _boom):
            assert gen.generate_wrapper("com.example.foo") is False


# ---------------------------------------------------------------------------
# Lines 408, 416, 420-426, 435-442, 447, 464, 469, 483-485: cleanup
# ---------------------------------------------------------------------------


class TestCleanupObsoleteWrappers:
    """Lines 408, 416, 420-426, 435-442, 447, 464, 469, 483-485."""

    def setup_method(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.bin_dir = self.tmpdir / "bin"
        self.config_dir = self.tmpdir / "cfg"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_skips_subdirectory(self) -> None:
        """Line 408: subdirectories are skipped, not removed."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        sub = self.bin_dir / "real_dir"
        sub.mkdir()
        assert gen.cleanup_obsolete_wrappers([]) == 0
        assert sub.exists()

    def test_skips_non_file_non_symlink(self) -> None:
        """Line 416: items that are neither file nor symlink are skipped."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )

        weird = Mock(spec=Path)
        weird.name = "weird"
        weird.is_dir.return_value = False
        weird.is_symlink.return_value = False
        weird.is_file.return_value = False

        with patch.object(Path, "iterdir", return_value=iter([weird])):
            assert gen.cleanup_obsolete_wrappers([]) == 0

    def test_symlink_with_missing_target_removed(self) -> None:
        """Lines 420-426: dangling symlinks are removed."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        real = self.tmpdir / "real"
        real.write_text("#!/bin/bash\necho hi\n")
        link = self.bin_dir / "dangling"
        link.symlink_to(real)
        real.unlink()  # dangling

        assert gen.cleanup_obsolete_wrappers([]) == 1
        assert not link.exists()

    def test_symlink_to_uninstalled_wrapper_removed(self) -> None:
        """Lines 420-426: symlink to a wrapper for a removed app is cleaned up."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        # Real wrapper lives OUTSIDE bin_dir so it isn't iterated.
        target = self.tmpdir / "realwrapper"
        target.write_text(
            "#!/usr/bin/env bash\n"
            "# Generated by fplaunchwrapper\n"
            'NAME="realwrapper"\n'
            'ID="com.example.gone"\n'
            'flatpak run "$ID" "$@"\n',
        )
        target.chmod(0o755)
        link = self.bin_dir / "linkwrap"
        link.symlink_to(target)

        # The app behind the wrapper is NOT in the installed list.
        removed = gen.cleanup_obsolete_wrappers(["com.example.kept"])
        # Only the symlink should be removed, not the real target.
        assert removed == 1
        assert not link.exists()
        assert target.exists()

    def test_legacy_shebang_script_removed(self) -> None:
        """Lines 435-442: non-wrapper shebang script is treated as a legacy wrapper."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        legacy = self.bin_dir / "legacywrap"
        legacy.write_text("#!/usr/bin/env bash\necho legacy\n")
        legacy.chmod(0o755)

        assert gen.cleanup_obsolete_wrappers([]) == 1
        assert not legacy.exists()

    def test_emit_mode_counts_without_unlink(self) -> None:
        """Line 447: emit mode increments the counter without unlinking."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
            emit_mode=True,
        )
        wrapper = self.bin_dir / "obs"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "# Generated by fplaunchwrapper\n"
            'NAME="obs"\n'
            'ID="com.example.obs"\n'
            'flatpak run "$ID" "$@"\n',
        )
        wrapper.chmod(0o755)

        assert gen.cleanup_obsolete_wrappers([]) == 1
        # File still exists because we're in emit mode
        assert wrapper.exists()

    def test_env_file_removed_with_wrapper(self) -> None:
        """Line 464: associated .env file is removed alongside the wrapper."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        wrapper = self.bin_dir / "envwrap"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "# Generated by fplaunchwrapper\n"
            'NAME="envwrap"\n'
            'ID="com.example.envwrap"\n'
            'flatpak run "$ID" "$@"\n',
        )
        wrapper.chmod(0o755)
        env_file = self.config_dir / "envwrap.env"
        env_file.write_text("FOO=bar\n")

        assert gen.cleanup_obsolete_wrappers([]) == 1
        assert not wrapper.exists()
        assert not env_file.exists()

    def test_scripts_dir_removed_with_wrapper(self) -> None:
        """Line 469: associated scripts/<name> directory is removed."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        wrapper = self.bin_dir / "scriptwrap"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "# Generated by fplaunchwrapper\n"
            'NAME="scriptwrap"\n'
            'ID="com.example.scriptwrap"\n'
            'flatpak run "$ID" "$@"\n',
        )
        wrapper.chmod(0o755)
        scripts_dir = self.config_dir / "scripts" / "scriptwrap"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "pre-launch.sh").write_text("#!/bin/sh\n")

        assert gen.cleanup_obsolete_wrappers([]) == 1
        assert not wrapper.exists()
        assert not scripts_dir.exists()

    def test_unlink_oserror_is_logged(self) -> None:
        """Lines 483-485: OSError during unlink is logged, not raised."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        wrapper = self.bin_dir / "obs2"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "# Generated by fplaunchwrapper\n"
            'NAME="obs2"\n'
            'ID="com.example.obs2"\n'
            'flatpak run "$ID" "$@"\n',
        )
        wrapper.chmod(0o755)

        with patch.object(Path, "unlink", side_effect=OSError("nope")):
            removed = gen.cleanup_obsolete_wrappers([])
        # Counter is not incremented because unlink failed
        assert removed == 0

    def test_aliases_file_unlink_oserror(self) -> None:
        """Line 484: OSError during aliases_file.unlink is caught and logged."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        wrapper = self.bin_dir / "aliaswrap"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "# Generated by fplaunchwrapper\n"
            'NAME="aliaswrap"\n'
            'ID="com.example.aliaswrap"\n'
            'flatpak run "$ID" "$@"\n',
        )
        wrapper.chmod(0o755)
        # Aliases file that contains ONLY this wrapper's entry, so the
        # rebuild produces an empty string and the cleanup unlinks it.
        aliases = self.config_dir / "aliases"
        aliases.write_text("aliaswrap:aw\n")

        real_unlink = Path.unlink

        def _selective_unlink(self: Path) -> None:
            if self.name == "aliases":
                raise OSError("aliases unlink boom")
            real_unlink(self)

        with patch.object(Path, "unlink", _selective_unlink):
            removed = gen.cleanup_obsolete_wrappers([])
        # Wrapper itself was removed successfully; aliases unlink failed
        # but the except branch caught the OSError.
        assert removed == 1
        assert not wrapper.exists()
        # Aliases file still present because its unlink failed
        assert aliases.exists()

    def test_legacy_script_header_read_oserror(self) -> None:
        """Lines 441-442: OSError while reading the legacy script header is logged."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        # Create a file that is a script header but the actual open() fails
        # under the cleanup's reading code path. We achieve this with a
        # mock that mimics an item with is_dir=False, is_symlink=False,
        # is_file=True, and is_wrapper_file=False.
        weird = Mock(spec=Path)
        weird.name = "weirdscript"
        weird.is_dir.return_value = False
        weird.is_symlink.return_value = False
        weird.is_file.return_value = True
        # The cleanup uses item.open("rb") -> raises OSError to hit 441-442.
        weird.open.side_effect = OSError("cannot open")
        # When treated as a non-wrapper, it must also be executable.
        with (
            patch.object(Path, "iterdir", return_value=iter([weird])),
            patch("lib.generate.os.access", return_value=True),
        ):
            removed = gen.cleanup_obsolete_wrappers([])
        assert removed == 0


# ---------------------------------------------------------------------------
# Lines 493-494, 502-503, 515-518: run() lock and early-exit / error paths
# ---------------------------------------------------------------------------


class TestRunEntryPoint:
    """Lines 493-494, 502-503, 515-518: lock failure, no apps, OSError."""

    def setup_method(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.bin_dir = self.tmpdir / "bin"
        self.config_dir = self.tmpdir / "cfg"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_lock_acquisition_failure(self) -> None:
        """Lines 493-494: lock cannot be acquired -> return 1."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        with patch("lib.generate.acquire_lock", return_value=False):
            assert gen.run() == 1

    def test_no_apps_returns_zero(self) -> None:
        """Lines 502-503: zero apps found -> return 0 with warning."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        with (
            patch("lib.generate.find_executable", return_value="/usr/bin/flatpak"),
            patch(
                "lib.generate.subprocess.run",
                return_value=Mock(returncode=0, stdout="", stderr=""),
            ),
        ):
            assert gen.run() == 0

    def test_oserror_in_run_returns_one(self) -> None:
        """Lines 515-518: top-level OSError -> return 1."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        with patch("lib.generate.acquire_lock", return_value=True), patch.object(
            gen, "get_installed_flatpaks", side_effect=OSError("nope")
        ):
            assert gen.run() == 1


# ---------------------------------------------------------------------------
# Lines 530-533, 553, 557: generate_wrappers existing-wrappers set and counts
# ---------------------------------------------------------------------------


class TestGenerateWrappers:
    """Lines 530-533, 553, 557: existing wrappers cache and created/skipped counts."""

    def setup_method(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.bin_dir = self.tmpdir / "bin"
        self.config_dir = self.tmpdir / "cfg"
        self.bin_dir.mkdir()
        self.config_dir.mkdir()

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_existing_wrappers_seeded_into_set(self) -> None:
        """Lines 530-533: pre-existing wrapper contributes to the 'updated' count."""
        # Pre-create a wrapper that will be detected as 'existing' for the
        # about-to-be-regenerated app.
        existing = self.bin_dir / "firefox"
        existing.write_text(
            "#!/usr/bin/env bash\n"
            "# Generated by fplaunchwrapper\n"
            'NAME="firefox"\n'
            'ID="org.mozilla.firefox"\n'
            'flatpak run "$ID" "$@"\n',
        )
        existing.chmod(0o755)

        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        created, updated, skipped = gen.generate_wrappers(["org.mozilla.firefox"])
        # Updated > 0 because the wrapper already existed
        assert updated == 1
        assert created == 0
        assert skipped == 0

    def test_blocklisted_app_is_skipped(self) -> None:
        """Line 557: blocklisted apps increment the skipped counter."""
        gen = WrapperGenerator(
            bin_dir=self.bin_dir,
            config_dir=self.config_dir,
        )
        # Block one app
        (gen.config_dir / "blocklist").write_text("org.mozilla.firefox\n")
        created, updated, skipped = gen.generate_wrappers(
            ["org.mozilla.firefox", "org.gimp.GIMP"],
        )
        assert skipped == 1
        assert created + updated == 1
        # Firefox was skipped -> no wrapper
        assert not (self.bin_dir / "firefox").exists()
        # Gimp succeeded
        assert (self.bin_dir / "gimp").exists()


# ---------------------------------------------------------------------------
# main() CLI smoke tests for branches that fall through to the default
# ---------------------------------------------------------------------------


class TestMainCLIExtra:
    """Light coverage of main() paths that aren't reached by existing tests."""

    def setup_method(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.bin_dir = self.tmpdir / "bin"
        self.bin_dir.mkdir()

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        # Restore argv
        sys.argv = ["fplaunch-generate"]

    def test_main_with_emit_verbose(self) -> None:
        """--emit-verbose exercises the main() emit_verbose wiring."""
        with (
            patch("lib.generate.find_executable", return_value="/usr/bin/flatpak"),
            patch(
                "lib.generate.subprocess.run",
                return_value=Mock(returncode=0, stdout="org.mozilla.firefox\n", stderr=""),
            ),
        ):
            sys.argv = [
                "fplaunch-generate",
                "--emit",
                "--emit-verbose",
                str(self.bin_dir),
            ]
            # Should run without raising
            result = main()
        assert result is None or result == 0

    def test_main_with_verbose(self) -> None:
        """--verbose exercises the main() verbose wiring path."""
        with (
            patch("lib.generate.find_executable", return_value="/usr/bin/flatpak"),
            patch(
                "lib.generate.subprocess.run",
                return_value=Mock(returncode=0, stdout="org.mozilla.firefox\n", stderr=""),
            ),
        ):
            sys.argv = [
                "fplaunch-generate",
                "--verbose",
                "--emit",
                str(self.bin_dir),
            ]
            result = main()
        assert result is None or result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
