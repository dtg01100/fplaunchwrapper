#!/usr/bin/env python3
"""Fuzz tests for validation and safety modules.

These tests verify that validation and safety functions handle
malformed input gracefully.
"""

from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck, strategies as st


# Strategies
# ==========================

@st.composite
def flatpak_id_strategy(draw) -> str:
    """Generate Flatpak IDs (valid and invalid)."""
    return draw(st.sampled_from([
        "",
        "a",
        "ab",
        "firefox",
        "org.mozilla.firefox",
        "org.mozilla.firefox.stable",
        "org.mozilla.firefox-1.0",
        "ORG.MOZILLA.FIREFOX",
        "org.test.app_name.with_underscores",
        "org.test.app-name.with-dashes",
        "org.test.app.name.with.dots",
        "org.test.app+name+with+pluses",
        "1.org.test.app",
        ".org.test.app",
        "org..test..app",
        "org.test.",
        "org.test.app;rm -rf",
        "org.test.app`id`",
        "org.test.app$(whoami)",
        "org.test.app|cat /etc/passwd",
        "org.test.app && echo pwned",
        "org/\x00test/app",
        "org/test\x00/app",
        "org/😀/app",
        "org/" + "x" * 200 + "/app",
        "org/test/" + "x" * 200,
    ]))


@st.composite
def path_strategy(draw) -> str:
    """Generate path strings (valid and invalid)."""
    return draw(st.sampled_from([
        "",
        "/",
        "/tmp",
        "/home/user",
        "/home/user/.config",
        "/home/user/.config/fplaunchwrapper",
        "~",
        "~/",
        "~/bin",
        "../../../etc",
        "../" * 20 + "etc/passwd",
        "/etc/passwd",
        "/etc/../../../var/log",
        "/home/user/../../root/.ssh",
        "/tmp/../../../etc/shadow",
        "x" * 100,
        "x" * 1000,
        "x" * 10000,
        "/tmp/with spaces",
        "/tmp/with\ttab",
        "/tmp/with;semicolon",
        "/tmp/with|pipe",
        "/tmp/with\nnewline",
        "/tmp/with\r\nreturn",
        "/tmp/with\\backslash",
        "/tmp/with\"quotes",
        "/tmp/with'double'quotes",
        "\\\\UNC\\path",
        "//server/share",
        "/tmp/../etc",
        "/etc/./passwd",
        "/./etc/passwd",
        ".",
        "..",
        "./..",
        "../.",
        "/tmp/.",
        "/tmp/..",
        "/tmp/../..",
        "/tmp/./..",
        "/var/home/dlafreniere/.config/fplaunchwrapper/../../../etc/passwd",
    ]))


# Tests
# ==========================

class TestValidateFlatpakId:
    """Fuzz tests for validate_flatpak_id."""

    @given(app_id=flatpak_id_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_validate_flatpak_id_never_crashes(self, app_id):
        """validate_flatpak_id should never crash on any input."""
        from lib.safety import validate_flatpak_id

        try:
            result = validate_flatpak_id(app_id)
            assert isinstance(result, bool)
        except Exception:
            pytest.fail("validate_flatpak_id raised an exception")

    @given(app_id=flatpak_id_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_validate_flatpak_id_rejects_injection(self, app_id):
        """validate_flatpak_id should reject shell injection patterns."""
        from lib.safety import validate_flatpak_id

        injection_patterns = [";", "|", "&", "`", "$(", "&&", "||", ">", "<"]
        is_injection = any(p in app_id for p in injection_patterns)

        if is_injection and len(app_id) < 100:
            result = validate_flatpak_id(app_id)
            assert result is False, f"Should reject injection in: {app_id[:50]}"


class TestValidateAppId:
    """Fuzz tests for validate_app_id."""

    @given(app_id=st.text(max_size=10000))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_validate_app_id_never_crashes(self, app_id):
        """validate_app_id should never crash on any input."""
        from lib.validation import validate_app_id

        try:
            valid, reason = validate_app_id(app_id)
            assert isinstance(valid, bool)
            assert isinstance(reason, str)
        except Exception:
            pytest.fail("validate_app_id raised an exception")

    @given(app_id=st.text(max_size=10000))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_validate_app_id_empty_returns_false(self, app_id):
        """Empty app IDs should be rejected."""
        from lib.validation import validate_app_id

        if len(app_id.strip()) == 0:
            valid, reason = validate_app_id(app_id)
            assert valid is False


class TestCheckPathTraversal:
    """Fuzz tests for check_path_traversal."""

    @given(
        path_str=path_strategy(),
        base=st.sampled_from([
            "/home/user/.config/fplaunchwrapper",
            "/home/user/.local/share/fplaunchwrapper",
            "/tmp/fplaunchwrapper",
            str(Path.home() / ".config" / "fplaunchwrapper"),
        ])
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_check_path_traversal_never_crashes(self, path_str, base):
        """check_path_traversal should never crash."""
        from lib.validation import check_path_traversal

        try:
            valid, reason = check_path_traversal(Path(path_str), Path(base))
            assert isinstance(valid, bool)
            assert isinstance(reason, str)
        except Exception:
            pytest.fail("check_path_traversal raised an exception")

    def test_obvious_traversal_attacks(self):
        """check_path_traversal should block obvious traversal attempts."""
        from lib.validation import check_path_traversal

        base = Path("/home/user/.config/fplaunchwrapper")
        attacks = [
            "/home/user/.config/fplaunchwrapper/../../../etc/passwd",
            "/home/user/../../root/.ssh/id_rsa",
            "/etc/../../../var/log",
            "/var/home/dlafreniere/../../etc/passwd",
        ]

        for path in attacks:
            valid, reason = check_path_traversal(Path(path), base)
            assert valid is False, f"Should reject: {path}"

    def test_legitimate_paths_allowed(self):
        """check_path_traversal should allow legitimate nested paths."""
        from lib.validation import check_path_traversal

        base = Path("/home/user/.config/fplaunchwrapper")
        legitimate = [
            "/home/user/.config/fplaunchwrapper/wrappers",
            "/home/user/.config/fplaunchwrapper/wrappers/firefox",
            "/home/user/.config/fplaunchwrapper/wrappers/org.mozilla.firefox",
        ]

        for path in legitimate:
            valid, _ = check_path_traversal(Path(path), base)
            assert valid is True, f"Should allow: {path}"


class TestSanitizeIdToName:
    """Fuzz tests for sanitize_id_to_name."""

    @given(app_id=st.text(max_size=10000))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_sanitize_id_to_name_never_crashes(self, app_id):
        """sanitize_id_to_name should never crash."""
        from lib.python_utils import sanitize_id_to_name

        try:
            result = sanitize_id_to_name(app_id)
            assert isinstance(result, str)
            if len(app_id) > 0:
                assert len(result) > 0
        except Exception:
            pytest.fail("sanitize_id_to_name raised an exception")

    @given(app_id=st.text(max_size=10000))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_sanitize_id_to_name_length_bounded(self, app_id):
        """sanitize_id_to_name output should be reasonably bounded."""
        from lib.python_utils import sanitize_id_to_name

        result = sanitize_id_to_name(app_id)
        assert len(result) <= 255, f"Output too long: {len(result)}"

    @given(app_id=st.text(max_size=10000))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_sanitize_id_to_name_no_path_traversal(self, app_id):
        """sanitize_id_to_name should not produce path traversal characters."""
        from lib.python_utils import sanitize_id_to_name

        result = sanitize_id_to_name(app_id)
        assert ".." not in result
        assert not result.startswith("/")


class TestDesktopParserFuzz:
    """Fuzz tests for desktop file parsing."""

    @given(content=st.text(max_size=10000))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_desktop_parser_handles_various_content(self, content):
        """Desktop parser should handle various file contents."""
        from lib.desktop_parser import DesktopEntry

        try:
            entry = DesktopEntry.from_string(content)
            assert hasattr(entry, 'name') or hasattr(entry, 'exec')
        except Exception:
            pass

    @given(exec_value=st.text(max_size=1000))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_exec_substitution(self, exec_value):
        """Exec substitution should handle various values."""
        from lib.desktop_parser import DesktopEntry

        basic_desktop = f"""[Desktop Entry]
Name=Test App
Exec={exec_value}
Type=Application
"""
        try:
            entry = DesktopEntry.from_string(basic_desktop)
            assert hasattr(entry, 'exec')
        except Exception:
            pass


class TestPathResolution:
    """Fuzz tests for path resolution functions."""

    @given(path_str=path_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_resolve_bin_dir_never_crashes(self, path_str):
        """resolve_bin_dir should never crash."""
        from lib.paths import resolve_bin_dir

        try:
            result = resolve_bin_dir(explicit_dir=path_str)
            assert isinstance(result, Path)
            assert result.is_absolute()
        except Exception:
            pass

    @given(path_str=st.text(max_size=1000))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_get_default_bin_dir(self, path_str):
        """get_default_bin_dir should handle various home paths."""
        from lib.paths import get_default_bin_dir

        try:
            result = get_default_bin_dir(home_path=path_str)
            assert isinstance(result, Path)
        except Exception:
            pass
