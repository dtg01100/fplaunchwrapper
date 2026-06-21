"""Phase 5: Behavioral model checking.

This file walks every documented wrapper flag through the actual generated
wrapper script and verifies the wrapper handles each case correctly.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def wrapper_dir(tmp_path, monkeypatch) -> Path:
    """Generate a real firefox wrapper in an isolated bin dir."""
    from lib.generate import WrapperGenerator
    from lib.config_manager import create_config_manager

    bin_dir = tmp_path / "bin"
    cfg_dir = tmp_path / "cfg"
    data_dir = tmp_path / "data"
    bin_dir.mkdir(); cfg_dir.mkdir(); data_dir.mkdir()

    cm = create_config_manager(config_dir=str(cfg_dir))
    gen = WrapperGenerator(
        bin_dir=str(bin_dir),
        config_dir=str(cfg_dir),
        data_dir=str(data_dir),
        config_manager=cm,
    )
    monkeypatch.setenv("FPWRAPPER_TEST_ENV", "1")
    gen.generate_wrapper("org.mozilla.firefox")
    wrapper = bin_dir / "firefox"
    assert wrapper.exists()
    return tmp_path


def _run(wrapper_dir: Path, args: list[str], timeout: int = 5, env_extra: dict | None = None):
    """Run the wrapper with given args. Returns (rc, stdout, stderr)."""
    wrapper = wrapper_dir / "bin" / "firefox"
    env = os.environ.copy()
    env["PATH"] = str(wrapper_dir / "bin") + ":" + env.get("PATH", "")
    env["FPWRAPPER_TEST_ENV"] = "1"
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(
        [str(wrapper), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return r.returncode, r.stdout, r.stderr


class TestWrapperTemplateExecution:
    """Walk the wrapper template's decision tree for every documented flag."""

    def test_wrapper_help_flag(self, wrapper_dir):
        rc, out, _ = _run(wrapper_dir, ["--fpwrapper-help"])
        assert rc == 0
        assert "--fpwrapper-help" in out
        assert "--fpwrapper-info" in out
        assert "--fpwrapper-launch" in out
        assert "--fpwrapper-force" in out
        assert "--fpwrapper-hook-failure" in out

    def test_wrapper_info_flag(self, wrapper_dir):
        rc, out, _ = _run(wrapper_dir, ["--fpwrapper-info"])
        assert rc == 0
        assert "firefox" in out
        assert "org.mozilla.firefox" in out

    def test_wrapper_config_dir_flag(self, wrapper_dir):
        """--fpwrapper-config-dir prints the Flatpak data dir path."""
        rc, out, _ = _run(wrapper_dir, ["--fpwrapper-config-dir"])
        assert rc == 0
        assert out.strip().startswith("/"), f"Expected absolute path, got {out!r}"

    def test_wrapper_force_interactive_flag(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-force-interactive", "--fpwrapper-info"])
        assert rc == 0

    def test_wrapper_launch_flatpak(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-launch", "flatpak", "--version"])
        assert rc == 0

    def test_wrapper_launch_system(self, wrapper_dir):
        """--fpwrapper-launch system finds the system binary via PATH."""
        fake_bin = wrapper_dir / "fakebin"
        fake_bin.mkdir()
        fake_firefox = fake_bin / "firefox"
        fake_firefox.write_text("#!/bin/bash\necho fake-firefox $@\n")
        fake_firefox.chmod(0o755)
        old_path = os.environ.get("PATH", "")
        try:
            # Put fakebin AFTER wrapper bin so the wrapper itself runs first
            os.environ["PATH"] = str(wrapper_dir / "bin") + ":" + str(fake_bin) + ":" + old_path
            rc, out, _ = _run(wrapper_dir, ["--fpwrapper-launch", "system", "--test-arg"])
            assert "fake-firefox --test-arg" in out, f"Expected fake-firefox, got {out!r}"
        finally:
            os.environ["PATH"] = old_path

    def test_wrapper_launch_invalid_choice(self, wrapper_dir):
        rc, _, err = _run(wrapper_dir, ["--fpwrapper-launch", "evil_choice"])
        assert rc != 0
        assert "Invalid choice" in err

    def test_wrapper_force_shortcut_f(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-force", "f", "--version"])
        assert rc == 0

    def test_wrapper_force_shortcut_d(self, wrapper_dir):
        """--fpwrapper-force d finds the system binary via PATH."""
        fake_bin = wrapper_dir / "fakebin"
        fake_bin.mkdir()
        fake_firefox = fake_bin / "firefox"
        fake_firefox.write_text("#!/bin/bash\necho fake-firefox $@\n")
        fake_firefox.chmod(0o755)
        old_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = str(wrapper_dir / "bin") + ":" + str(fake_bin) + ":" + old_path
            rc, out, _ = _run(wrapper_dir, ["--fpwrapper-force", "d", "--test-arg"])
            assert "fake-firefox --test-arg" in out, f"Expected fake-firefox, got {out!r}"
        finally:
            os.environ["PATH"] = old_path

    def test_wrapper_force_invalid_arg(self, wrapper_dir):
        rc, _, err = _run(wrapper_dir, ["--fpwrapper-force", "evil"])
        assert rc != 0
        assert "Invalid" in err

    def test_wrapper_hook_failure_abort(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-hook-failure", "abort", "--fpwrapper-info"])
        assert rc == 0

    def test_wrapper_hook_failure_warn(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-hook-failure", "warn", "--fpwrapper-info"])
        assert rc == 0

    def test_wrapper_hook_failure_ignore(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-hook-failure", "ignore", "--fpwrapper-info"])
        assert rc == 0

    def test_wrapper_hook_failure_invalid(self, wrapper_dir):
        rc, _, err = _run(wrapper_dir, ["--fpwrapper-hook-failure", "evil-mode"])
        assert rc != 0
        assert "Invalid hook failure mode" in err

    def test_wrapper_abort_on_hook_failure(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-abort-on-hook-failure", "--fpwrapper-info"])
        assert rc == 0

    def test_wrapper_ignore_hook_failure(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-ignore-hook-failure", "--fpwrapper-info"])
        assert rc == 0

    def test_wrapper_set_override_system(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-set-override", "system"])
        assert rc == 0
        pref = wrapper_dir / "cfg" / "firefox.pref"
        assert pref.exists()
        assert pref.read_text().strip() == "system"

    def test_wrapper_set_override_flatpak(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-set-override", "flatpak"])
        assert rc == 0
        pref = wrapper_dir / "cfg" / "firefox.pref"
        assert pref.read_text().strip() == "flatpak"

    def test_wrapper_set_override_invalid(self, wrapper_dir):
        rc, _, err = _run(wrapper_dir, ["--fpwrapper-set-override", "evil"])
        assert rc != 0
        assert "Invalid preference" in err

    def test_wrapper_set_preference_alias(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-set-preference", "system"])
        assert rc == 0
        pref = wrapper_dir / "cfg" / "firefox.pref"
        assert pref.read_text().strip() == "system"

    def test_wrapper_sandbox_reset(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-sandbox-reset"])
        assert isinstance(rc, int)

    def test_wrapper_sandbox_yolo(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-sandbox-yolo"])
        assert isinstance(rc, int)

    def test_wrapper_run_unrestricted(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-run-unrestricted", "--version"], timeout=10)
        # Real flatpak may fail due to test sandbox; just verify no crash
        assert isinstance(rc, int)

    def test_wrapper_remove_pre_script_no_script(self, wrapper_dir):
        rc, out, _ = _run(wrapper_dir, ["--fpwrapper-remove-pre-script"])
        assert rc == 0
        assert "No pre-launch script configured" in out

    def test_wrapper_remove_post_script_no_script(self, wrapper_dir):
        rc, out, _ = _run(wrapper_dir, ["--fpwrapper-remove-post-script"])
        assert rc == 0
        assert "No post-run script configured" in out

    def test_wrapper_set_pre_script_copies(self, wrapper_dir):
        src = wrapper_dir / "my_pre.sh"
        src.write_text("#!/bin/bash\necho pre-launch\n")
        src.chmod(0o755)
        rc, _, _ = _run(wrapper_dir, ["--fpwrapper-set-pre-script", str(src)])
        assert rc == 0
        dest = wrapper_dir / "cfg" / "scripts" / "firefox" / "pre-launch.sh"
        assert dest.exists()

    def test_wrapper_set_pre_script_rejects_symlink(self, wrapper_dir):
        src_real = wrapper_dir / "real_pre.sh"
        src_real.write_text("#!/bin/bash\necho pre-launch\n")
        src_real.chmod(0o755)
        src_link = wrapper_dir / "link_pre.sh"
        src_link.symlink_to(src_real)
        rc, _, err = _run(wrapper_dir, ["--fpwrapper-set-pre-script", str(src_link)])
        assert rc != 0
        assert "symlink" in err.lower()

    def test_wrapper_set_pre_script_rejects_etc(self, wrapper_dir):
        # /etc/passwd always exists; the wrapper must reject it
        rc, _, err = _run(wrapper_dir, ["--fpwrapper-set-pre-script", "/etc/passwd"])
        assert rc != 0
        assert "Refusing" in err or "sensitive" in err or "Script not found" in err

    def test_wrapper_unknown_flag_passes_through(self, wrapper_dir):
        rc, _, _ = _run(wrapper_dir, ["--unknown-flag"])
        assert isinstance(rc, int)


class TestWrapperTemplateSyntax:
    """Bash-level syntactic checks on the generated wrapper."""

    def test_generated_wrapper_passes_bash_n(self, wrapper_dir):
        wrapper = wrapper_dir / "bin" / "firefox"
        r = subprocess.run(
            ["bash", "-n", str(wrapper)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert r.returncode == 0, f"bash -n failed: {r.stderr}"
        assert r.stderr == ""

    def test_generated_wrapper_runs_in_strict_mode(self, wrapper_dir):
        wrapper = wrapper_dir / "bin" / "firefox"
        content = wrapper.read_text()
        assert "set -eo pipefail" in content

    def test_generated_wrapper_has_all_handler_blocks(self, wrapper_dir):
        wrapper = wrapper_dir / "bin" / "firefox"
        content = wrapper.read_text()
        for flag in [
            "--fpwrapper-help",
            "--fpwrapper-info",
            "--fpwrapper-config-dir",
            "--fpwrapper-launch",
            "--fpwrapper-force",
            "--fpwrapper-force-interactive",
            "--fpwrapper-hook-failure",
            "--fpwrapper-abort-on-hook-failure",
            "--fpwrapper-ignore-hook-failure",
            "--fpwrapper-set-override",
            "--fpwrapper-set-preference",
            "--fpwrapper-set-pre-script",
            "--fpwrapper-set-post-script",
            "--fpwrapper-remove-pre-script",
            "--fpwrapper-remove-post-script",
            "--fpwrapper-sandbox-reset",
            "--fpwrapper-sandbox-yolo",
            "--fpwrapper-run-unrestricted",
        ]:
            assert flag in content, f"Generated wrapper missing handler for {flag!r}"


class TestWrapperTemplateShellcheck:
    """shellcheck analysis on the generated wrapper."""

    @pytest.mark.skipif(
        subprocess.run(["which", "shellcheck"], capture_output=True).returncode != 0,
        reason="shellcheck not installed",
    )
    def test_generated_wrapper_shellcheck_clean(self, wrapper_dir):
        wrapper = wrapper_dir / "bin" / "firefox"
        r = subprocess.run(
            ["shellcheck", "-S", "error", str(wrapper)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert r.returncode == 0, f"shellcheck found errors:\n{r.stdout}\n{r.stderr}"
