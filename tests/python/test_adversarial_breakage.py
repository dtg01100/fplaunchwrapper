#!/usr/bin/env python3
"""Adversarial break tests - tests edge cases with real assertions."""

from pathlib import Path

import pytest


# ── DesktopEntry edge cases ─────────────────────────────────────────────────

class TestDesktopEntryEdgeCases:
    """Edge cases for DesktopEntry constructor and properties."""

    def test_non_existent_file_falls_back_to_stem(self, tmp_path):
        """A non-existent .desktop file path should yield an entry whose name falls back to stem."""
        from lib.desktop_parser import DesktopEntry

        missing = tmp_path / "missing.desktop"
        entry = DesktopEntry(missing)
        assert entry.name == "missing"
        assert entry.exec_command is None
        assert entry.categories == []
        assert entry.terminal_required is False

    def test_multiple_sections(self, tmp_path):
        """Multiple sections should be parsed independently."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "multi.desktop"
        d.write_text(
            "[Desktop Entry]\n"
            "Name=Main\n"
            "Exec=/bin/true\n"
            "[Action Menu]\n"
            "Name=Action\n"
            "Exec=/bin/false\n"
        )
        entry = DesktopEntry(d)
        assert entry.name == "Main"
        assert entry.exec_command == "/bin/true"
        assert entry.get("Name", section="Action Menu") == "Action"

    def test_duplicate_key_last_wins(self, tmp_path):
        """Duplicate keys - last value wins."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "dup.desktop"
        d.write_text(
            "[Desktop Entry]\n"
            "Name=First\n"
            "Name=Second\n"
            "Exec=true\n"
        )
        entry = DesktopEntry(d)
        assert entry.name == "Second"

    def test_terminal_true_variants(self, tmp_path):
        """Terminal should accept both 'true' and '1' as true."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "term.desktop"
        d.write_text("[Desktop Entry]\nName=Test\nExec=true\nTerminal=true\n")
        entry = DesktopEntry(d)
        assert entry.terminal_required is True

        # '1' should also work as true (pragmatic .desktop compatibility)
        d2 = tmp_path / "term2.desktop"
        d2.write_text("[Desktop Entry]\nName=Test\nExec=true\nTerminal=1\n")
        entry2 = DesktopEntry(d2)
        assert entry2.terminal_required is True

    def test_categories_filter_empty(self, tmp_path):
        """Categories should filter empty segments from double semicolons."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "cat.desktop"
        d.write_text(
            "[Desktop Entry]\nName=Test\nExec=true\n"
            "Categories=Game;;Network;\n"
        )
        entry = DesktopEntry(d)
        assert entry.categories == ["Game", "Network"]

    def test_unknown_locale_falls_back(self, tmp_path):
        """Unknown locale should fall back to non-localized Name."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "locale.desktop"
        d.write_text("[Desktop Entry]\nName=BaseName\nExec=true\n")
        entry = DesktopEntry(d)
        assert entry.get_localized("Name", locale="xx_XX") == "BaseName"

    def test_comment_lines_ignored(self, tmp_path):
        """Lines starting with # should be ignored during parsing."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "comment.desktop"
        d.write_text(
            "# This is a comment\n"
            "[Desktop Entry]\n"
            "# Another comment\n"
            "Name=TestApp\n"
            "Exec=app\n"
        )
        entry = DesktopEntry(d)
        assert entry.name == "TestApp"

    def test_leading_trailing_whitespace_in_values(self, tmp_path):
        """Values should be stripped of leading/trailing whitespace."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "spaces.desktop"
        d.write_text("[Desktop Entry]\nName =   Test App   \nExec =   /bin/true  \n")
        entry = DesktopEntry(d)
        assert entry.name == "Test App"
        assert entry.exec_command == "/bin/true"

    def test_hidden_and_nodisplay(self, tmp_path):
        """Hidden/NoDisplay should match case-insensitively and accept '1'."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "hidden.desktop"
        d.write_text(
            "[Desktop Entry]\nName=HiddenApp\nExec=true\n"
            "Hidden=true\nNoDisplay=TRUE\n"
        )
        entry = DesktopEntry(d)
        assert entry.is_hidden is True
        assert entry.no_display is True

        # Also accept '1'
        d2 = tmp_path / "hidden2.desktop"
        d2.write_text(
            "[Desktop Entry]\nName=H2\nExec=true\n"
            "Hidden=1\nNoDisplay=1\n"
        )
        entry2 = DesktopEntry(d2)
        assert entry2.is_hidden is True
        assert entry2.no_display is True

    def test_no_section_header(self, tmp_path):
        """Orphan lines before first section header should be ignored."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "nosection.desktop"
        d.write_text("Orphan=value\n[Desktop Entry]\nName=Test\nExec=true\n")
        entry = DesktopEntry(d)
        assert entry.name == "Test"

    def test_malformed_section_header(self, tmp_path):
        """Section header without closing bracket is treated as unknown line."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "badsect.desktop"
        d.write_text("[Desktop Entry\nName=Test\nExec=true\n")
        entry = DesktopEntry(d)
        assert entry.name == "badsect"

    def test_empty_file(self, tmp_path):
        """Empty file should not crash, name falls back to stem."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "empty.desktop"
        d.write_text("")
        entry = DesktopEntry(d)
        assert entry.name == "empty"
        assert entry.categories == []

    def test_whitespace_file(self, tmp_path):
        """File with only whitespace should not crash."""
        from lib.desktop_parser import DesktopEntry

        d = tmp_path / "ws.desktop"
        d.write_text("   \n\n  \t  \n")
        entry = DesktopEntry(d)
        assert entry.name == "ws"

    def test_null_bytes_in_content(self, tmp_path):
        """Null bytes should be handled via errors=replace."""
        from lib.desktop_parser import DesktopEntry

        path = tmp_path / "null.desktop"
        path.write_bytes(b"[Desktop Entry]\nName=Test\x00App\nExec=true\n")
        entry = DesktopEntry(path)
        assert entry.name is not None

    def test_binary_file_no_crash(self, tmp_path):
        """Binary/random bytes should not crash parser."""
        from lib.desktop_parser import DesktopEntry

        path = tmp_path / "binary.desktop"
        path.write_bytes(bytes(range(256)))
        entry = DesktopEntry(path)
        assert entry.name is not None

    def test_unicode_name_preserved(self, tmp_path):
        """Unicode names should be preserved."""
        from lib.desktop_parser import DesktopEntry

        path = tmp_path / "unicode.desktop"
        path.write_text("[Desktop Entry]\nName=Café\nExec=true\n")
        entry = DesktopEntry(path)
        assert entry.name == "Café"


# ── Validation edge cases ────────────────────────────────────────────────────

class TestValidateAppIdEdgeCases:
    """Edge cases for validate_app_id."""

    def test_platform_version_format(self):
        """// format for platform/runtime versions should be valid."""
        from lib.validation import validate_app_id

        valid, msg = validate_app_id("org.freedesktop.Platform//21.08")
        assert valid is True, msg

    def test_single_slash_rejected(self):
        """Single / without // should be rejected."""
        from lib.validation import validate_app_id

        valid, _ = validate_app_id("org.test/foo")
        assert valid is False

    def test_null_byte_rejected(self):
        """Null byte should be rejected."""
        from lib.validation import validate_app_id

        valid, _ = validate_app_id("org.example\x00bad")
        assert valid is False

    def test_starts_with_digit(self):
        """IDs starting with a digit should be rejected."""
        from lib.validation import validate_app_id

        valid, _ = validate_app_id("123.test")
        assert valid is False

    def test_starts_with_underscore(self):
        """IDs starting with underscore should be rejected."""
        from lib.validation import validate_app_id

        valid, _ = validate_app_id("_test.App")
        assert valid is False

    def test_double_dot_allowed(self):
        """Double dots are technically allowed by the regex."""
        from lib.validation import validate_app_id

        valid, msg = validate_app_id("org..test")
        assert valid is True, msg

    def test_no_dot_rejected(self):
        """IDs without a dot should be rejected."""
        from lib.validation import validate_app_id

        valid, _ = validate_app_id("a")
        assert valid is False

    def test_ends_with_dot(self):
        """IDs ending with a dot should be rejected."""
        from lib.validation import validate_app_id

        valid, _ = validate_app_id("org.")
        assert valid is False

    def test_ends_with_slash(self):
        """IDs ending with a slash should be rejected."""
        from lib.validation import validate_app_id

        valid, _ = validate_app_id("org.test/")
        assert valid is False

    def test_very_long_id(self):
        """Very long IDs should not crash."""
        from lib.validation import validate_app_id

        valid, _ = validate_app_id("a." + "x" * 10000)
        assert valid is True

    def test_empty_string_rejected(self):
        """Empty string should be rejected."""
        from lib.validation import validate_app_id

        valid, _ = validate_app_id("")
        assert valid is False

    def test_spaces_rejected(self):
        """IDs with spaces should be rejected."""
        from lib.validation import validate_app_id

        valid, _ = validate_app_id("org.test App")
        assert valid is False

    def test_hyphen_allowed(self):
        """Hyphens should be allowed in IDs."""
        from lib.validation import validate_app_id

        valid, msg = validate_app_id("org.example.my-app")
        assert valid is True, msg


# ── validate_flatpak_id (safety.py) edge cases ───────────────────────────────

class TestValidateFlatpakIdEdgeCases:
    """Edge cases for validate_flatpak_id in safety.py."""

    def test_none_input(self):
        """None should return False."""
        from lib.safety import validate_flatpak_id

        assert validate_flatpak_id(None) is False

    def test_integer_input(self):
        """Non-string input should return False."""
        from lib.safety import validate_flatpak_id

        assert validate_flatpak_id(123) is False

    def test_only_dots(self):
        """Only dots should return False (starts with '.')."""
        from lib.safety import validate_flatpak_id

        assert validate_flatpak_id("...") is False

    def test_valid_minus(self):
        """Valid ID with hyphens should pass."""
        from lib.safety import validate_flatpak_id

        assert validate_flatpak_id("org.example.my-app") is True

    def test_no_dot(self):
        """No dot should return False."""
        from lib.safety import validate_flatpak_id

        assert validate_flatpak_id("invalid") is False

    def test_starts_with_hyphen(self):
        """Starting with hyphen should return False."""
        from lib.safety import validate_flatpak_id

        assert validate_flatpak_id("-org.example") is False

    def test_ends_with_dot(self):
        """Ending with dot should return False."""
        from lib.safety import validate_flatpak_id

        assert validate_flatpak_id("org.example.") is False


# ── sanitize_id_to_name edge cases ───────────────────────────────────────────

class TestSanitizeIdToNameEdgeCases:
    """Edge cases for sanitize_id_to_name."""

    def test_empty_string(self):
        """Empty string should fall back to hash-based name."""
        from lib.python_utils import sanitize_id_to_name

        result = sanitize_id_to_name("")
        assert result.startswith("app-")

    def test_none_input(self):
        """None should fall back to hash-based name."""
        from lib.python_utils import sanitize_id_to_name

        result = sanitize_id_to_name(None)
        assert result.startswith("app-")

    def test_last_segment_extraction(self):
        """Should extract the last segment after the last dot."""
        from lib.python_utils import sanitize_id_to_name

        assert sanitize_id_to_name("org.mozilla.Firefox") == "firefox"
        assert sanitize_id_to_name("com.company.App123") == "app123"

    def test_unicode_combining_chars(self):
        """Unicode NFKD normalization should handle combining chars."""
        from lib.python_utils import sanitize_id_to_name

        result = sanitize_id_to_name("org.example.café")
        assert "é" not in result
        assert result == "cafe"

    def test_non_ascii_only(self):
        """Non-ASCII only should fall back to hash."""
        from lib.python_utils import sanitize_id_to_name

        result = sanitize_id_to_name("org.example.日本語")
        assert result.startswith("app-")

    def test_very_long_id_truncated(self):
        """Very long sanitized name should be truncated to 100 chars."""
        from lib.python_utils import sanitize_id_to_name

        result = sanitize_id_to_name("org.example." + "x" * 200)
        assert len(result) <= 100

    def test_only_special_chars(self):
        """Only special chars should fall back to hash."""
        from lib.python_utils import sanitize_id_to_name

        result = sanitize_id_to_name("org.example.!@#$%")
        assert result.startswith("app-")

    def test_leading_trailing_hyphens_stripped(self):
        """Leading and trailing hyphens in the segment should be stripped."""
        from lib.python_utils import sanitize_id_to_name

        result = sanitize_id_to_name("org.example.-test-")
        assert result == "test"
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_multiple_hyphens_collapsed(self):
        """Multiple consecutive hyphens should be collapsed to one."""
        from lib.python_utils import sanitize_id_to_name

        result = sanitize_id_to_name("org.example.test---app")
        assert "---" not in result
        assert result == "test-app"


# ── validate_home_dir edge cases ─────────────────────────────────────────────

class TestValidateHomeDirEdgeCases:
    """Edge cases for validate_home_dir."""

    def test_none_input_returns_none(self):
        """None input should return None without crashing."""
        from lib.python_utils import validate_home_dir

        result = validate_home_dir(None)
        assert result is None

    def test_tilde_expansion(self):
        """~ should be expanded to HOME."""
        from lib.python_utils import validate_home_dir

        result = validate_home_dir("~")
        assert result == str(Path.home())

    def test_outside_home_returns_none(self, tmp_path):
        """Path outside HOME should return None."""
        from lib.python_utils import validate_home_dir

        if str(tmp_path) == str(Path.home()):
            pytest.skip("tmp_path equals HOME")
        assert validate_home_dir(tmp_path) is None


# ── check_path_traversal edge cases ──────────────────────────────────────────

class TestCheckPathTraversalEdgeCases:
    """Edge cases for check_path_traversal."""

    def test_subdir_within_base(self, tmp_path):
        """Valid subdirectory within base should be safe."""
        from lib.validation import check_path_traversal

        base = tmp_path / "base"
        base.mkdir()
        subdir = base / "subdir"
        subdir.mkdir()

        safe, msg = check_path_traversal(subdir, base)
        assert safe is True, msg

    def test_sibling_dir_outside_base(self, tmp_path):
        """Sibling directory should be blocked."""
        from lib.validation import check_path_traversal

        base = tmp_path / "base"
        base.mkdir()
        sibling = tmp_path / "sibling"
        sibling.mkdir()

        safe, _ = check_path_traversal(sibling, base)
        assert safe is False

    def test_parent_ref_resolves_to_base(self, tmp_path):
        """base/subdir/.. resolves to base which IS within base, so safe."""
        from lib.validation import check_path_traversal

        base = tmp_path / "base"
        base.mkdir()
        subdir = base / "subdir"
        subdir.mkdir()

        safe, msg = check_path_traversal(subdir / "..", base)
        assert safe is True, msg

    def test_double_parent_ref_escape(self, tmp_path):
        """base/subdir/../../outside should escape base."""
        from lib.validation import check_path_traversal

        base = tmp_path / "base"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        subdir = base / "subdir"
        subdir.mkdir()

        safe, _ = check_path_traversal(subdir / ".." / ".." / "outside", base)
        assert safe is False

    def test_absolute_path_outside(self, tmp_path):
        """Absolute path outside base should be blocked."""
        from lib.validation import check_path_traversal

        base = tmp_path / "base"
        base.mkdir()

        safe, _ = check_path_traversal("/etc/passwd", base)
        assert safe is False

    def test_non_existent_subpath_of_base(self, tmp_path):
        """Non-existent path within base should still be safe."""
        from lib.validation import check_path_traversal

        base = tmp_path / "base"
        base.mkdir()
        new_path = base / "not-yet-created" / "subdir"

        safe, msg = check_path_traversal(new_path, base)
        assert safe is True, msg

    def test_dot_path(self, tmp_path):
        """'.' should resolve to base and be safe."""
        from lib.validation import check_path_traversal

        base = tmp_path / "base"
        base.mkdir()

        safe, msg = check_path_traversal(base / ".", base)
        assert safe is True, msg


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])