"""Phase 7: Equivalence partitioning tests.

Boundary tests verify behavior at partition edges. Each validation function
partitions inputs into "valid" and "invalid"; we test that:
- All inputs just inside the boundary are accepted
- All inputs just outside the boundary are rejected
- The boundary itself is in the correct partition

For length limits: name of exactly N chars must validate, name of N+1 must not.
"""
from __future__ import annotations

import string

import pytest
from hypothesis import given, settings, strategies as st

from lib.exceptions import ForbiddenNameError
from lib.python_utils import sanitize_id_to_name
from lib.validation import (
    MAX_WRAPPER_NAME_LENGTH,
    validate_app_id,
    validate_wrapper_name,
)


class TestWrapperNameLengthBoundary:
    """Boundary at MAX_WRAPPER_NAME_LENGTH (255)."""

    @pytest.mark.parametrize("length", [0, 1, 100, 254, 255, 256, 257, 1000, 10000])
    def test_length_boundary(self, length):
        name = "a" * length
        ok, err = validate_wrapper_name(name)
        if length < 1:
            assert not ok
        elif length <= MAX_WRAPPER_NAME_LENGTH:
            assert ok, f"Length {length} should be accepted: {err!r}"
        else:
            assert not ok, f"Length {length} should be rejected"
            assert "too long" in err.lower() or "length" in err.lower()

    def test_max_length_just_at_boundary_accepted(self):
        name = "a" * MAX_WRAPPER_NAME_LENGTH
        ok, err = validate_wrapper_name(name)
        assert ok, f"255 chars should be accepted: {err!r}"

    def test_max_length_plus_one_rejected(self):
        name = "a" * (MAX_WRAPPER_NAME_LENGTH + 1)
        ok, err = validate_wrapper_name(name)
        assert not ok
        assert "too long" in err.lower() or "length" in err.lower()

    def test_max_length_minus_one_accepted(self):
        name = "a" * (MAX_WRAPPER_NAME_LENGTH - 1)
        ok, err = validate_wrapper_name(name)
        assert ok, f"254 chars should be accepted: {err!r}"


class TestWrapperNameCharBoundary:
    """Boundary tests for individual characters."""

    @pytest.mark.parametrize("char", list("/\\"))
    def test_path_separator_rejected_anywhere(self, char):
        for pos in [0, 1, 5, 100, 254]:
            name = ("a" * pos) + char + ("a" * (10 - pos))
            ok, _ = validate_wrapper_name(name)
            assert not ok, f"{char!r} at position {pos} accepted"

    @pytest.mark.parametrize("char", ["\x00", "\n", "\r"])
    def test_control_chars_rejected(self, char):
        for pos in [0, 5, 100]:
            name = ("a" * pos) + char + ("a" * (10 - pos))
            ok, _ = validate_wrapper_name(name)
            assert not ok, f"Control char {char!r} at position {pos} accepted"

    def test_leading_hyphen_rejected(self):
        for length in [1, 5, 100, 255]:
            name = "-" + "a" * (length - 1)
            ok, _ = validate_wrapper_name(name)
            assert not ok, f"Leading hyphen with length {length} accepted"

    def test_internal_hyphen_accepted(self):
        for name in ["a-b", "foo-bar", "x" * 100 + "-tail"]:
            ok, _ = validate_wrapper_name(name)
            assert ok, f"Internal hyphen in {name!r} rejected"
    def test_double_dot_rejected(self):
        """`..` is rejected by validate_wrapper_name itself.

        Consecutive dots collide with path-traversal semantics (``..`` is
        the parent-directory reference) and should never be a wrapper
        name. The validator owns this rejection; downstream path-traversal
        checks are a second line of defense, not the first.
        """
        ok, err = validate_wrapper_name("..")
        assert not ok, f"`..` should be rejected: {err!r}"
        # Internal `..` is also rejected
        ok2, _ = validate_wrapper_name("foo..bar")
        assert not ok2, "Internal `..` should be rejected"


    @pytest.mark.parametrize("char", list(string.ascii_letters + string.digits + "_."))
    def test_all_safe_chars_accepted_alone(self, char):
        """Each individually-safe char (excluding leading hyphen) accepted as 1-char name."""
        ok, err = validate_wrapper_name(char)
        assert ok, f"Safe char {char!r} rejected as name: {err!r}"


class TestAppIdBoundary:
    """Boundary tests for validate_app_id."""

    @pytest.mark.parametrize("app_id", [
        "a.b", "ab.cd", "a1.b2", "a-b.c-d", "a_b.c_d",
    ])
    def test_minimal_valid_app_ids(self, app_id):
        ok, err = validate_app_id(app_id)
        assert ok, f"{app_id!r} should validate: {err!r}"

    @pytest.mark.parametrize("app_id", [
        ".ab", "ab.", "ab", "ab.cd/", "ab/cd", "1ab.cd", "-ab.cd",
    ])
    def test_invalid_boundary_cases(self, app_id):
        ok, _ = validate_app_id(app_id)
        assert not ok, f"{app_id!r} should be rejected"

    def test_double_slash_platform_version_accepted(self):
        ok, err = validate_app_id("org.freedesktop.Platform//21.08")
        assert ok, f"Platform version should validate: {err!r}"

    def test_triple_slash_rejected(self):
        ok, _ = validate_app_id("org.foo///21.08")
        assert not ok, "Triple slash should be rejected"

    def test_consecutive_dots_rejected(self):
        ok, _ = validate_app_id("ab..cd")
        assert not ok, "Consecutive dots should be rejected"

    def test_trailing_slash_with_platform_version_rejected(self):
        ok, _ = validate_app_id("org.foo.Platform//21.08/")
        assert not ok


class TestSanitizeEquivalenceClasses:
    """Inputs in the same equivalence class must produce the same output."""

    @pytest.mark.parametrize("id_pair", [
        ("org.mozilla.firefox", "Org.Mozilla.Firefox"),
        ("com.example.MyApp", "com.example.myapp"),
        ("io.github.user.repo", "io.github.user.repo-"),
    ])
    def test_equivalent_inputs_same_output(self, id_pair):
        a, b = id_pair
        out_a = sanitize_id_to_name(a)
        out_b = sanitize_id_to_name(b)
        assert out_a == out_b, (
            f"Equivalent inputs {a!r} and {b!r} produced different outputs: "
            f"{out_a!r} vs {out_b!r}"
        )

    @pytest.mark.parametrize("char_class,chars", [
        ("uppercase", list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
        ("lowercase", list("abcdefghijklmnopqrstuvwxyz")),
        ("digits", list("0123456789")),
        ("hyphen", ["-"]),
        ("underscore", ["_"]),
        ("dot", ["."]),
    ])
    def test_all_chars_in_class_produce_safe_output(self, char_class, chars):
        for c in chars:
            out = sanitize_id_to_name(c)
            assert out, f"Empty output for {c!r} in class {char_class}"
            assert "/" not in out
            assert "\\" not in out
            assert out != ".."
            assert out == out.lower()


class TestForbiddenNameEquivalenceClasses:
    """Forbidden names form a partition: each name is forbidden or not."""

    def test_partition_complete(self):
        for name in ["bash", "firefox", "rm", "chrome", "python", "myapp"]:
            result = ForbiddenNameError.is_forbidden(name)
            assert isinstance(result, bool)

    def test_partition_contains_expected_classes(self):
        assert ForbiddenNameError.is_forbidden("bash")
        assert ForbiddenNameError.is_forbidden("pip")
        assert ForbiddenNameError.is_forbidden("sudo")
        assert ForbiddenNameError.is_forbidden("rm")

    def test_non_forbidden_safe_apps_partition(self):
        safe_apps = ["firefox", "chrome", "thunderbird", "myapp",
                     "ranger", "alacritty", "kitty", "weechat"]
        for app in safe_apps:
            assert not ForbiddenNameError.is_forbidden(app), (
                f"{app!r} incorrectly in forbidden set"
            )


class TestHypothesisBoundaries:
    """Hypothesis finds boundary cases by exploring input space."""

    @given(st.text(min_size=0, max_size=10, alphabet="/"))
    @settings(max_examples=20, deadline=None)
    def test_only_slashes_always_rejected(self, s):
        ok, _ = validate_wrapper_name(s)
        if s:
            assert not ok

    @given(st.text(min_size=1, max_size=5, alphabet="-"))
    @settings(max_examples=20, deadline=None)
    def test_only_hyphens_rejected(self, s):
        ok, _ = validate_wrapper_name(s)
        assert not ok

    @given(st.text(min_size=1, max_size=100, alphabet=string.ascii_lowercase))
    @settings(max_examples=50, deadline=None)
    def test_lowercase_alpha_names_accepted(self, s):
        ok, err = validate_wrapper_name(s)
        assert ok, f"Lowercase name {s!r} rejected: {err!r}"

    @given(st.text(min_size=1, max_size=100, alphabet=string.ascii_lowercase + "."))
    @settings(max_examples=50, deadline=None)
    def test_lowercase_with_dots(self, s):
        if s and not s.startswith(".") and not s.endswith(".") and ".." not in s:
            ok, _ = validate_wrapper_name(s)
            assert ok


class TestCustomLengthBoundary:
    """The max_total_length parameter changes the boundary."""

    @pytest.mark.parametrize("max_len,test_len", [
        (10, 10), (10, 11), (10, 9), (1, 1), (1, 2), (1000, 1000),
    ])
    def test_custom_length_boundary(self, max_len, test_len):
        name = "a" * test_len
        ok, err = validate_wrapper_name(name, max_total_length=max_len)
        if test_len <= max_len and test_len >= 1:
            assert ok, f"Length {test_len} (max {max_len}) should be accepted"
        elif test_len > max_len:
            assert not ok, f"Length {test_len} (max {max_len}) should be rejected"
