"""Phase 4: Property-based testing with Hypothesis.

Property tests verify that invariants hold for arbitrary inputs generated
by the Hypothesis library, not just for hand-picked cases. This catches
edge cases that explicit parametrization misses.
"""
from __future__ import annotations

import string
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from lib.exceptions import ForbiddenNameError
from lib.python_utils import sanitize_id_to_name
from lib.validation import (
    check_path_traversal,
    validate_app_id,
    validate_wrapper_name,
)


# Strategies

# A "valid" app_id has at least one dot, starts with letter, contains only safe chars.
# Bug #8 fix: validator rejects consecutive dots (..).
_valid_app_id_chars = string.ascii_letters + string.digits + "._-"
_app_id_strategy = st.text(
    alphabet=_valid_app_id_chars, min_size=1, max_size=100
).filter(
    lambda s: "." in s
    and s[0].isalpha()
    and not s.endswith(".")
    and not s.startswith(".")
    and ".." not in s
)

# Arbitrary text — may contain anything
_arbitrary_text = st.text(min_size=0, max_size=200)


# ---- validate_app_id properties ------------------------------------------

class TestValidateAppIdProperties:
    """Properties that must hold for validate_app_id over all inputs."""

    @given(_arbitrary_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_no_crash_on_any_input(self, s):
        """validate_app_id must never raise on any string input."""
        try:
            ok, err = validate_app_id(s)
            assert isinstance(ok, bool)
            assert isinstance(err, str)
            if ok:
                assert err == ""
        except Exception as e:
            pytest.fail(f"validate_app_id raised {type(e).__name__} on {s!r}: {e}")

    @given(_app_id_strategy)
    @settings(
        max_examples=200,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def test_valid_inputs_accepted(self, s):
        """Inputs matching the spec format must be accepted."""
        ok, err = validate_app_id(s)
        assert ok, f"Valid-looking app_id {s!r} rejected: {err!r}"

    def test_empty_string_always_rejected(self):
        ok, err = validate_app_id("")
        assert not ok
        assert err

    @given(st.text(min_size=1, max_size=10, alphabet="."))
    def test_only_dots_rejected(self, s):
        ok, _ = validate_app_id(s)
        assert not ok

    @given(st.integers(min_value=1, max_value=10000))
    def test_long_input_handled(self, length):
        s = "a" * length + ".b"
        ok, err = validate_app_id(s)
        assert ok, f"ID of length {length} rejected: {err}"


# ---- validate_wrapper_name properties ------------------------------------

class TestValidateWrapperNameProperties:
    """Properties for validate_wrapper_name."""

    @given(_arbitrary_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_no_crash_on_any_input(self, s):
        try:
            ok, err = validate_wrapper_name(s)
            assert isinstance(ok, bool)
            assert isinstance(err, str)
            if ok:
                assert err == ""
        except Exception as e:
            pytest.fail(f"validate_wrapper_name raised {type(e).__name__} on {s!r}: {e}")

    @given(st.text(alphabet="abc-_.", min_size=1, max_size=200).filter(lambda s: ".." not in s))
    @settings(max_examples=100)
    def test_safe_chars_accepted_within_length(self, s):
        if not s.startswith("-") and len(s) <= 255:
            ok, err = validate_wrapper_name(s)
            assert ok, f"Safe name {s!r} rejected: {err!r}"

    @given(st.text(alphabet="/\\\0", min_size=1, max_size=10))
    def test_path_separators_rejected(self, s):
        ok, _ = validate_wrapper_name(s)
        assert not ok

    @given(st.text(min_size=1, max_size=10, alphabet="-"))
    def test_leading_hyphen_rejected(self, s):
        ok, _ = validate_wrapper_name(s)
        assert not ok

    @given(st.integers(min_value=256, max_value=1000))
    def test_overlong_names_rejected(self, length):
        s = "a" * length
        ok, err = validate_wrapper_name(s)
        assert not ok, f"Length {length} should be rejected"
        assert "too long" in err.lower() or "length" in err.lower()

    def test_empty_string_rejected(self):
        ok, _ = validate_wrapper_name("")
        assert not ok


# ---- check_path_traversal properties ------------------------------------

class TestCheckPathTraversalProperties:
    """Properties for check_path_traversal."""

    def test_absolute_outside_path_always_rejected(self, tmp_path):
        for path in ["/etc/passwd", "/root/.ssh/id_rsa", "/usr/bin/sudo"]:
            ok, _ = check_path_traversal(path, tmp_path)
            assert not ok, f"{path!r} should be rejected"

    def test_path_equal_to_base_accepted(self, tmp_path):
        ok, _ = check_path_traversal(tmp_path, tmp_path)
        assert ok

    @given(st.text(alphabet=string.ascii_letters + "_-", min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_safe_subpath_accepted(self, subpath):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            ok, _ = check_path_traversal(subpath, base)
            assert ok, f"Safe subpath {subpath!r} rejected"


# ---- sanitize_id_to_name properties --------------------------------------

class TestSanitizeIdProperties:
    """Properties for sanitize_id_to_name."""

    @given(_arbitrary_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_no_crash_on_any_input(self, s):
        try:
            result = sanitize_id_to_name(s)
            assert isinstance(result, str)
            assert len(result) <= 100
        except Exception as e:
            pytest.fail(f"sanitize_id_to_name raised {type(e).__name__} on {s!r}: {e}")

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_no_path_separators_in_output(self, s):
        result = sanitize_id_to_name(s)
        assert "/" not in result
        assert "\\" not in result

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_no_dotdot_in_output(self, s):
        result = sanitize_id_to_name(s)
        assert result != ".."

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_lowercase_output(self, s):
        result = sanitize_id_to_name(s)
        assert result == result.lower()

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_ascii_output(self, s):
        result = sanitize_id_to_name(s)
        assert all(ord(c) < 128 for c in result)

    @given(st.text(min_size=1, max_size=1000, alphabet="a"))
    def test_handles_long_inputs(self, s):
        result = sanitize_id_to_name(s)
        assert len(result) <= 100

    def test_empty_string_returns_something(self):
        result = sanitize_id_to_name("")
        assert result and len(result) > 0


# ---- Forbidden name properties -------------------------------------------

class TestForbiddenNameProperties:
    """Properties for ForbiddenNameError.is_forbidden."""

    @given(_arbitrary_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_no_crash_on_any_input(self, s):
        try:
            result = ForbiddenNameError.is_forbidden(s)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"is_forbidden raised {type(e).__name__} on {s!r}: {e}")

    @given(st.sampled_from(list(ForbiddenNameError.FORBIDDEN_NAMES)))
    @settings(max_examples=50)
    def test_known_forbidden_always_detected(self, name):
        assert ForbiddenNameError.is_forbidden(name)
        assert ForbiddenNameError.is_forbidden(name.upper())
        assert ForbiddenNameError.is_forbidden(name.capitalize())

    def test_known_safe_names_not_forbidden(self):
        safe_names = ["firefox", "chrome", "thunderbird", "myapp", "weechat",
                      "ranger", "alacritty", "kitty"]
        for safe in safe_names:
            assert not ForbiddenNameError.is_forbidden(safe), (
                f"{safe!r} incorrectly classified as forbidden"
            )
