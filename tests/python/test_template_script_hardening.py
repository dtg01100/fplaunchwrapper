#!/usr/bin/env python3
"""Defensive tests for the pre/post-launch script management in the
generated wrapper template.

The wrapper's --fpwrapper-set-pre-script / --fpwrapper-set-post-script
commands and --fpwrapper-remove-pre-script / --fpwrapper-remove-post-script
commands operate on files the user points at. They MUST refuse to:

  - install a script that lives under a sensitive system directory
    (mirrors _validate_script_path_safety in lib/config_validation.py);
  - install a symlink (so the user can't be tricked into pointing at
    /etc/passwd via a link);
  - delete a file that is outside the wrapper's own HOOK_DIR (since
    PRE_SCRIPT / POST_SCRIPT may have been redirected to a configured
    external path; rm on an external path would be a destructive surprise).

These tests exec real generated wrappers against tmp paths so the bash
guards are exercised end-to-end, not just inspected by string-matching.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

from lib.generate import WrapperGenerator


@pytest.fixture
def env(tmp_path):
    """Isolated layout: bin_dir, config_dir, and a temp HOME for the
    generated wrapper to read/write into. Yields (bin_dir, config_dir)."""
    bin_dir = tmp_path / "bin"
    config_dir = tmp_path / "cfg"
    data_dir = tmp_path / "data"
    for d in (bin_dir, config_dir, data_dir):
        d.mkdir(parents=True, exist_ok=True)
    yield bin_dir, config_dir


@pytest.fixture
def wrapper(env):
    """Generate a real wrapper, write it to bin_dir, chmod 755, return Path."""
    bin_dir, config_dir = env
    gen = WrapperGenerator(bin_dir=bin_dir, config_dir=config_dir)
    gen.generate_wrapper("test", "org.example.Test")
    w = bin_dir / "test"
    assert w.exists()
    return w


def _run(wrapper, *args):
    """Run the wrapper with the given args, return CompletedProcess."""
    return subprocess.run(
        [str(wrapper), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def _make_executable(path: Path, body: str = "#!/bin/sh\nexit 0\n") -> Path:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


# ---------------------------------------------------------------------------
# set_pre_script / set_post_script: sensitive-dir rejection
# ---------------------------------------------------------------------------


class TestSetScriptRejectsSensitiveDirs:
    # We test the sensitive-dir rule with two strategies:
    #  1. Non-existent paths under each sensitive dir: the wrapper's
    #     "[ ! -f ]" guard fires first and prints "Script not found".
    #     The contract is that the wrapper exits non-zero and does NOT
    #     install anything -- both outcomes leave the system safe.
    #  2. Real executables that exist on every Linux box: e.g. /bin/sh.
    #     This is the scenario that would actually be exploited, and
    #     the safety check must fire AFTER the [ -f ] check.

    @pytest.mark.parametrize(
        "bad_path",
        [
            "/etc/passwd",
            "/usr/bin/env",
            "/bin/sh",
            "/sbin/init",
            "/boot/grub.cfg",
            "/proc/version",
            "/dev/null",
        ],
    )
    def test_nonexistent_path_under_sensitive_dir_is_rejected(
        self, wrapper, bad_path
    ):
        candidate = f"{bad_path}.nonexistent"
        if Path(candidate).exists():
            pytest.skip(f"test artifact {candidate} unexpectedly exists")
        r = _run(wrapper, "--fpwrapper-set-pre-script", candidate)
        assert r.returncode != 0, (
            f"set-pre-script must refuse sensitive dir {candidate}, "
            f"got exit 0; stdout={r.stdout!r} stderr={r.stderr!r}"
        )
        hook_file = (
            wrapper.parent.parent / "cfg" / "scripts" / "test" / "pre-launch.sh"
        )
        assert not hook_file.exists()

    def test_existing_executable_in_sensitive_dir_is_rejected(self, wrapper):
        # The real attack: a system binary that exists and is executable.
        # /bin/sh is the strongest case because it's both ubiquitous and
        # exactly the kind of "useful" binary an attacker would want to
        # chain as a pre-launch hook.
        r = _run(wrapper, "--fpwrapper-set-pre-script", "/bin/sh")
        assert r.returncode != 0, (
            "set-pre-script must refuse a real executable in a sensitive "
            f"dir; got exit 0; stdout={r.stdout!r} stderr={r.stderr!r}"
        )
        assert "sensitive" in r.stderr.lower() or "refusing" in r.stderr.lower()
        hook_file = (
            wrapper.parent.parent / "cfg" / "scripts" / "test" / "pre-launch.sh"
        )
        assert not hook_file.exists()

    def test_post_script_existing_executable_in_sensitive_dir_is_rejected(
        self, wrapper
    ):
        r = _run(wrapper, "--fpwrapper-set-post-script", "/bin/sh")
        assert r.returncode != 0
        assert "sensitive" in r.stderr.lower() or "refusing" in r.stderr.lower()
        hook_file = (
            wrapper.parent.parent / "cfg" / "scripts" / "test" / "post-run.sh"
        )
        assert not hook_file.exists()
# ---------------------------------------------------------------------------


class TestSetScriptRejectsSymlinks:
    def test_pre_script_symlink_is_rejected(self, wrapper, tmp_path):
        victim = tmp_path / "victim.sh"
        victim.write_text("#!/bin/sh\nexit 0\n")
        link = tmp_path / "looks-like-safe.sh"
        link.symlink_to(victim)
        r = _run(wrapper, "--fpwrapper-set-pre-script", str(link))
        assert r.returncode != 0, (
            f"set-pre-script must refuse symlinks, got exit 0; "
            f"stdout={r.stdout!r} stderr={r.stderr!r}"
        )
        assert "symlink" in r.stderr.lower()

    def test_post_script_symlink_is_rejected(self, wrapper, tmp_path):
        link = tmp_path / "looks-like-safe-post.sh"
        link.symlink_to("/bin/sh")
        r = _run(wrapper, "--fpwrapper-set-post-script", str(link))
        assert r.returncode != 0
        assert "symlink" in r.stderr.lower()


# ---------------------------------------------------------------------------
# set_pre_script / set_post_script: happy path
# ---------------------------------------------------------------------------


class TestSetScriptHappyPath:
    def test_safe_pre_script_is_installed(self, wrapper, tmp_path):
        script = _make_executable(tmp_path / "pre.sh")
        r = _run(wrapper, "--fpwrapper-set-pre-script", str(script))
        assert r.returncode == 0, f"safe script should install; stderr={r.stderr!r}"
        installed = (
            wrapper.parent.parent / "cfg" / "scripts" / "test" / "pre-launch.sh"
        )
        assert installed.exists()
        assert installed.stat().st_mode & stat.S_IXUSR

    def test_safe_post_script_is_installed(self, wrapper, tmp_path):
        script = _make_executable(tmp_path / "post.sh")
        r = _run(wrapper, "--fpwrapper-set-post-script", str(script))
        assert r.returncode == 0
        installed = wrapper.parent.parent / "cfg" / "scripts" / "test" / "post-run.sh"
        assert installed.exists()

    def test_missing_source_path_is_rejected(self, wrapper, tmp_path):
        # File doesn't exist -> [ ! -f ] guard fires before our safety check.
        # The contract is just that the wrapper exits non-zero and prints
        # an error; we don't lock in the exact wording.
        missing = tmp_path / "does-not-exist.sh"
        r = _run(wrapper, "--fpwrapper-set-pre-script", str(missing))
        assert r.returncode != 0


# ---------------------------------------------------------------------------
# remove-pre-script / remove-post-script: refuse to delete outside HOOK_DIR
# ---------------------------------------------------------------------------


class TestRemoveScriptStaysInHookDir:
    def test_remove_pre_installed_script_succeeds(self, wrapper, tmp_path):
        script = _make_executable(tmp_path / "pre.sh")
        r = _run(wrapper, "--fpwrapper-set-pre-script", str(script))
        assert r.returncode == 0
        # Now remove it (PRE_SCRIPT is the default HOOK_DIR location, so
        # this should succeed).
        r = _run(wrapper, "--fpwrapper-remove-pre-script")
        assert r.returncode == 0
        installed = (
            wrapper.parent.parent / "cfg" / "scripts" / "test" / "pre-launch.sh"
        )
        assert not installed.exists()

    def test_remove_post_installed_script_succeeds(self, wrapper, tmp_path):
        script = _make_executable(tmp_path / "post.sh")
        r = _run(wrapper, "--fpwrapper-set-post-script", str(script))
        assert r.returncode == 0
        r = _run(wrapper, "--fpwrapper-remove-post-script")
        assert r.returncode == 0
        installed = wrapper.parent.parent / "cfg" / "scripts" / "test" / "post-run.sh"
        assert not installed.exists()

    def test_remove_redirected_pre_script_is_refused(self, wrapper, tmp_path):
        # Simulate the dangerous case: PRE_SCRIPT has been redirected to
        # an external file via CONFIG_SCRIPT_PRE. The remove command
        # must NOT delete that file.
        external = _make_executable(tmp_path / "external-victim.sh")
        content = wrapper.read_text()
        content2 = content.replace(
            'CONFIG_SCRIPT_PRE=""',
            f'CONFIG_SCRIPT_PRE="{external}"',
        )
        wrapper.write_text(content2)

        r = _run(wrapper, "--fpwrapper-remove-pre-script")
        assert r.returncode != 0, (
            f"remove must refuse external file; got exit 0; "
            f"stdout={r.stdout!r} stderr={r.stderr!r}"
        )
        assert "refusing" in r.stderr.lower() or "outside" in r.stderr.lower()
        # The victim file must still exist
        assert external.exists(), "external file was deleted despite the guard"

    def test_remove_redirected_post_script_is_refused(self, wrapper, tmp_path):
        external = _make_executable(tmp_path / "external-victim-post.sh")
        content = wrapper.read_text()
        content2 = content.replace(
            'CONFIG_SCRIPT_POST=""',
            f'CONFIG_SCRIPT_POST="{external}"',
        )
        wrapper.write_text(content2)

        r = _run(wrapper, "--fpwrapper-remove-post-script")
        assert r.returncode != 0
        assert "refusing" in r.stderr.lower() or "outside" in r.stderr.lower()
        assert external.exists()

    def test_remove_with_no_script_installed_is_a_noop(self, wrapper):
        # Nothing configured: should print a friendly message, exit 0,
        # and definitely not crash.
        r = _run(wrapper, "--fpwrapper-remove-pre-script")
        assert r.returncode == 0
        assert "no pre-launch script" in r.stdout.lower()


# ---------------------------------------------------------------------------
# Static checks: the safety helpers must be present in the rendered wrapper
# ---------------------------------------------------------------------------


class TestTemplateHasSafetyHelpers:
    """Belt-and-suspenders: if a future refactor accidentally drops
    is_script_path_safe / is_path_in_hook_dir, these tests will catch it
    before the runtime tests above go red."""

    def test_is_script_path_safe_present(self):
        bin_dir = Path(tempfile.mkdtemp())
        config_dir = Path(tempfile.mkdtemp())
        try:
            gen = WrapperGenerator(bin_dir=bin_dir, config_dir=config_dir)
            content = gen.create_wrapper_script("test", "org.example.Test")
            assert "is_script_path_safe" in content
            assert "/etc/*" in content  # one of the sensitive-dir prefixes
        finally:
            shutil.rmtree(bin_dir, ignore_errors=True)
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_is_path_in_hook_dir_present(self):
        bin_dir = Path(tempfile.mkdtemp())
        config_dir = Path(tempfile.mkdtemp())
        try:
            gen = WrapperGenerator(bin_dir=bin_dir, config_dir=config_dir)
            content = gen.create_wrapper_script("test", "org.example.Test")
            assert "is_path_in_hook_dir" in content
        finally:
            shutil.rmtree(bin_dir, ignore_errors=True)
            shutil.rmtree(config_dir, ignore_errors=True)
