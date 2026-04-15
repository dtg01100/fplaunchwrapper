#!/usr/bin/env python3
"""Unit tests for desktop_parser.py.

Tests desktop file parsing, localization support, and Flatpak metadata extraction.
Uses mocks for file I/O and external dependencies.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch



class TestDesktopEntry:
    """Tests for DesktopEntry class."""

    SAMPLE_DESKTOP_CONTENT = """[Desktop Entry]
Version=1.0
Type=Application
Name=Firefox Web Browser
Name[en_US]=Firefox
Name[fr_FR]=Firefox
Comment=Browse the World Wide Web
Comment[en_US]=Browse the World Wide Web
Icon=firefox
Exec=firefox %u
Terminal=false
Categories=Network;WebBrowser;
X-Flatpak=org.mozilla.firefox
Hidden=false
NoDisplay=false
"""

    MINIMAL_DESKTOP_CONTENT = """[Desktop Entry]
Type=Application
"""

    MALFORMED_CONTENT = """
# This is a comment
[Desktop Entry]
Name=Test App
# Another comment
Exec=test
NotAValidLine
"""

    EDGE_CASE_WITH_SPACES = """
[Desktop Entry]
Name=App With Spaces
Exec=command --option "with spaces" --another='quoted'
"""

    def _create_temp_desktop_file(self, content: str, suffix: str = ".desktop") -> Path:
        """Create a temporary desktop file with given content."""
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return Path(path)

    def teardown_method(self) -> None:
        """Clean up any temp files created during tests."""
        import shutil

        for attr in dir(self):
            if attr.startswith("_temp_"):
                path = getattr(self, attr)
                if isinstance(path, Path) and path.exists():
                    shutil.rmtree(path.parent, ignore_errors=True)

    # === Normal Parsing Tests ===

    def test_parse_basic_desktop_file(self) -> None:
        """Test parsing a basic valid desktop file."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.SAMPLE_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.file_path == path
        assert "Desktop Entry" in entry._entries
        assert entry.get("Name") == "Firefox Web Browser"
        assert entry.get("Exec") == "firefox %u"
        assert entry.get("Icon") == "firefox"

    def test_parse_stores_all_sections(self) -> None:
        """Test that multiple sections are properly stored."""
        from lib.desktop_parser import DesktopEntry

        content = """[Desktop Entry]
Name=App1

[Desktop Action browse]
Name=Browse Files

[Desktop Action edit]
Name=Edit File
"""
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert "Desktop Entry" in entry._entries
        assert "Desktop Action browse" in entry._entries
        assert "Desktop Action edit" in entry._entries
        assert entry.get("Name", section="Desktop Entry") == "App1"
        assert entry.get("Name", section="Desktop Action browse") == "Browse Files"

    def test_get_with_default_value(self) -> None:
        """Test get() returns default for missing keys."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.MINIMAL_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.get("NonExistent") is None
        assert entry.get("NonExistent", default="default") == "default"
        assert entry.get("NonExistent", section="Other") is None

    def test_get_with_custom_section(self) -> None:
        """Test get() with custom section specification."""
        from lib.desktop_parser import DesktopEntry

        content = """[Section A]
Key=valueA

[Section B]
Key=valueB
"""
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.get("Key", section="Section A") == "valueA"
        assert entry.get("Key", section="Section B") == "valueB"
        assert entry.get("Key", section="Section C") is None

    # === Property Tests ===

    def test_name_property(self) -> None:
        """Test name property returns localized name or stem."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.SAMPLE_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.name == "Firefox Web Browser"

    def test_name_property_fallback_to_stem(self) -> None:
        """Test name property falls back to file stem when Name is missing."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.MINIMAL_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.name == path.stem

    def test_comment_property(self) -> None:
        """Test comment property returns localized comment."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.SAMPLE_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.comment == "Browse the World Wide Web"

    def test_icon_property(self) -> None:
        """Test icon property."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.SAMPLE_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.icon == "firefox"

    def test_categories_property(self) -> None:
        """Test categories property parses semicolon-separated list."""
        from lib.desktop_parser import DesktopEntry

        content = """[Desktop Entry]
Type=Application
Name=Firefox
Categories=Network;WebBrowser;
"""
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.categories == ["Network", "WebBrowser"]

    def test_categories_handles_empty(self) -> None:
        """Test categories handles empty or missing Categories field."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.MINIMAL_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.categories == []

    def test_flatpak_id_property(self) -> None:
        """Test flatpak_id property returns X-Flatpak field."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.SAMPLE_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.flatpak_id == "org.mozilla.firefox"

    def test_flatpak_id_returns_none_when_missing(self) -> None:
        """Test flatpak_id returns None when X-Flatpak is not present."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.MINIMAL_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.flatpak_id is None

    def test_exec_command_property(self) -> None:
        """Test exec_command property."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.SAMPLE_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.exec_command == "firefox %u"

    def test_terminal_required_property_true(self) -> None:
        """Test terminal_required returns True when Terminal=true."""
        from lib.desktop_parser import DesktopEntry

        content = "[Desktop Entry]\nType=Application\nTerminal=true\n"
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.terminal_required is True

    def test_terminal_required_property_false(self) -> None:
        """Test terminal_required returns False for missing or false value."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.SAMPLE_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.terminal_required is False

    def test_is_hidden_property(self) -> None:
        """Test is_hidden property."""
        from lib.desktop_parser import DesktopEntry

        content = "[Desktop Entry]\nType=Application\nHidden=true\n"
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.is_hidden is True

    def test_no_display_property(self) -> None:
        """Test no_display property."""
        from lib.desktop_parser import DesktopEntry

        content = "[Desktop Entry]\nType=Application\nNoDisplay=true\n"
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.no_display is True

    # === Localization Tests ===

    @patch.dict(os.environ, {"LANG": "en_US"})
    def test_get_localized_returns_exact_locale_match(self) -> None:
        """Test get_localized returns exact locale match when available."""
        from lib.desktop_parser import DesktopEntry

        content = """[Desktop Entry]
Type=Application
Name[en.US]=Firefox
Name=Firefox Web Browser
"""
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.get_localized("Name") == "Firefox"

    @patch.dict(os.environ, {"LANG": "fr_FR"})
    def test_get_localized_returns_language_only_fallback(self) -> None:
        """Test get_localized falls back to language-only locale."""
        from lib.desktop_parser import DesktopEntry

        content = """[Desktop Entry]
Name[en]=Firefox English
Name[fr]=Firefox Francais
Name=Firefox Default
"""
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.get_localized("Name", locale="fr") == "Firefox Francais"

    @patch.dict(os.environ, {"LANG": "de_DE"})
    def test_get_localized_falls_back_to_non_localized(self) -> None:
        """Test get_localized falls back to non-localized key."""
        from lib.desktop_parser import DesktopEntry

        content = """[Desktop Entry]
Name=Firefox Default
"""
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.get_localized("Name") == "Firefox Default"

    @patch.dict(os.environ, {"LANG": "en_US"})
    def test_get_localized_with_explicit_locale(self) -> None:
        """Test get_localized respects explicit locale parameter."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.SAMPLE_DESKTOP_CONTENT)
        entry = DesktopEntry(path)

        assert entry.get_localized("Name", locale="fr_FR") == "Firefox"

    # === Error Handling Tests ===

    def test_handles_malformed_lines(self) -> None:
        """Test that malformed lines are handled gracefully."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file(self.MALFORMED_CONTENT)
        entry = DesktopEntry(path)

        assert entry.get("Name") == "Test App"
        assert entry.get("Exec") == "test"
        assert entry.get("NotAValidLine") is None

    def test_handles_comments(self) -> None:
        """Test that comment lines are ignored."""
        from lib.desktop_parser import DesktopEntry

        content = """# Full line comment
[Desktop Entry]
Name=App
# Inline style comment
Exec=command
"""
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.get("Name") == "App"
        assert entry.get("Exec") == "command"

    def test_handles_extra_whitespace(self) -> None:
        """Test that extra whitespace is stripped."""
        from lib.desktop_parser import DesktopEntry

        content = """
[Desktop Entry]
   Name  =    App With Spaces   
   Exec  =    command    
"""
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.get("Name") == "App With Spaces"
        assert entry.get("Exec") == "command"

    def test_handles_empty_file(self) -> None:
        """Test handling of empty file content."""
        from lib.desktop_parser import DesktopEntry

        path = self._create_temp_desktop_file("")
        entry = DesktopEntry(path)

        assert entry.get("Name") is None

    def test_handles_no_section(self) -> None:
        """Test handling of entries without a section header."""
        from lib.desktop_parser import DesktopEntry

        content = "Name=NoSection\nExec=command\n"
        path = self._create_temp_desktop_file(content)
        entry = DesktopEntry(path)

        assert entry.get("Name", section="Desktop Entry") is None

    def test_file_read_error_returns_empty_parse(self) -> None:
        """Test that file read errors are handled gracefully."""
        from lib.desktop_parser import DesktopEntry

        mock_path = MagicMock(spec=Path)
        mock_path.read_text.side_effect = OSError("Permission denied")
        mock_path.exists.return_value = True

        entry = DesktopEntry(mock_path)

        assert entry._entries == {}
        assert entry._raw_lines == []

    def test_nonexistent_file(self) -> None:
        """Test handling of non-existent file."""
        from lib.desktop_parser import DesktopEntry

        path = Path("/nonexistent/path/to/file.desktop")
        entry = DesktopEntry(path)

        assert entry._entries == {}
        assert entry._raw_lines == []


class TestFindDesktopFiles:
    """Tests for find_desktop_files function."""

    def test_returns_empty_for_nonexistent_directory(self) -> None:
        """Test find_desktop_files returns empty list for nonexistent dir."""
        from lib.desktop_parser import find_desktop_files

        result = find_desktop_files(Path("/nonexistent/directory"))
        assert result == []

    def test_returns_empty_for_non_directory(self) -> None:
        """Test find_desktop_files returns empty for non-directory path."""
        from lib.desktop_parser import find_desktop_files

        with tempfile.NamedTemporaryFile(suffix=".desktop") as f:
            result = find_desktop_files(Path(f.name))
            assert result == []

    def test_finds_desktop_files_non_recursive(self) -> None:
        """Test finding .desktop files in non-recursive mode."""
        from lib.desktop_parser import find_desktop_files

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            (tmppath / "app1.desktop").touch()
            (tmppath / "app2.desktop").touch()
            subdir = tmppath / "subdir"
            subdir.mkdir()
            (subdir / "app3.desktop").touch()

            result = find_desktop_files(tmppath, recursive=False)
            result_names = {p.name for p in result}

            assert "app1.desktop" in result_names
            assert "app2.desktop" in result_names
            assert "app3.desktop" not in result_names

    def test_finds_desktop_files_recursive(self) -> None:
        """Test finding .desktop files recursively."""
        from lib.desktop_parser import find_desktop_files

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            (tmppath / "app1.desktop").touch()
            subdir = tmppath / "subdir"
            subdir.mkdir()
            (subdir / "app2.desktop").touch()
            deeper = subdir / "deeper"
            deeper.mkdir()
            (deeper / "app3.desktop").touch()

            result = find_desktop_files(tmppath, recursive=True)
            result_names = {p.name for p in result}

            assert len(result) == 3
            assert "app1.desktop" in result_names
            assert "app2.desktop" in result_names
            assert "app3.desktop" in result_names

    def test_ignores_non_desktop_files(self) -> None:
        """Test that non-.desktop files are ignored."""
        from lib.desktop_parser import find_desktop_files

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            (tmppath / "app1.desktop").touch()
            (tmppath / "app2.txt").touch()
            (tmppath / "app3.conf").touch()

            result = find_desktop_files(tmppath, recursive=False)
            result_names = {p.name for p in result}

            assert len(result) == 1
            assert "app1.desktop" in result_names


class TestParseFlatpakDesktopFiles:
    """Tests for parse_flatpak_desktop_files function."""

    @patch("lib.desktop_parser.find_desktop_files")
    @patch("lib.desktop_parser.DesktopEntry")
    def test_parses_desktop_files_from_custom_dir(
        self, mock_entry_class, mock_find
    ) -> None:
        """Test parsing desktop files from a custom directory."""
        from lib.desktop_parser import parse_flatpak_desktop_files

        mock_find.return_value = [Path("/fake/app.desktop")]

        mock_entry = MagicMock()
        mock_entry.flatpak_id = "org.example.app"
        mock_entry.name = "Example App"
        mock_entry_class.return_value = mock_entry

        result = parse_flatpak_desktop_files(flatpak_dir=Path("/fake/flatpak"))

        assert "org.example.app" in result
        assert result["org.example.app"].name == "Example App"

    @patch("lib.desktop_parser.find_desktop_files")
    @patch("lib.desktop_parser.DesktopEntry")
    def test_uses_filename_stem_when_no_flatpak_id(
        self, mock_entry_class, mock_find
    ) -> None:
        """Test fallback to filename stem when X-Flatpak is missing."""
        from lib.desktop_parser import parse_flatpak_desktop_files

        mock_find.return_value = [Path("/fake/org.example.app.desktop")]

        mock_entry = MagicMock()
        mock_entry.flatpak_id = None
        mock_entry.name = "Example App"
        mock_entry_class.return_value = mock_entry

        result = parse_flatpak_desktop_files(flatpak_dir=Path("/fake/"))

        assert "org.example.app" in result

    @patch("lib.desktop_parser.find_desktop_files")
    @patch("lib.desktop_parser.Path")
    def test_searches_default_locations_when_no_flatpak_dir(
        self, mock_path, mock_find
    ) -> None:
        """Test default search locations when no flatpak_dir specified."""
        from lib.desktop_parser import parse_flatpak_desktop_files

        mock_home = MagicMock()
        mock_home.__truediv__ = lambda self, key: Path(f"/home/user/.local/share/{key}")
        mock_path.home.return_value = mock_home

        mock_find.return_value = []

        with patch.object(Path, "exists", return_value=False):
            parse_flatpak_desktop_files()

        mock_find.assert_called()


class TestGetAppMetadata:
    """Tests for get_app_metadata function."""

    def test_returns_metadata_from_existing_entry(self) -> None:
        """Test getting metadata from a pre-fetched desktop entry."""
        from lib.desktop_parser import DesktopEntry, get_app_metadata

        mock_entry = MagicMock(spec=DesktopEntry)
        mock_entry.name = "Test App"
        mock_entry.comment = "A test application"
        mock_entry.icon = "test-icon"
        mock_entry.categories = ["Utility", "Test"]
        mock_entry.terminal_required = False
        mock_entry.exec_command = "test-app"

        desktop_entries = {"org.test.app": mock_entry}

        result = get_app_metadata("org.test.app", desktop_entries)

        assert result["name"] == "Test App"
        assert result["comment"] == "A test application"
        assert result["icon"] == "test-icon"
        assert result["categories"] == ["Utility", "Test"]
        assert result["terminal"] is False
        assert result["exec"] == "test-app"

    def test_returns_fallback_when_entry_not_found(self) -> None:
        """Test fallback metadata construction when entry not found."""
        from lib.desktop_parser import get_app_metadata

        desktop_entries = {}

        result = get_app_metadata("org.example.my-app", desktop_entries)

        assert result["name"] == "My App"
        assert result["comment"] is None
        assert result["icon"] == "org.example.my-app"
        assert result["categories"] == []
        assert result["terminal"] is False
        assert result["exec"] is None

    def test_fallback_name_extraction(self) -> None:
        """Test that fallback name properly extracts from ID."""
        from lib.desktop_parser import get_app_metadata

        result = get_app_metadata("com.example.my-app", {})

        assert result["name"] == "My App"

    @patch("lib.desktop_parser.parse_flatpak_desktop_files")
    def test_fetches_entries_when_not_provided(self, mock_parse) -> None:
        """Test that entries are fetched when not provided."""
        from lib.desktop_parser import get_app_metadata

        mock_entry = MagicMock()
        mock_entry.name = "Fetched App"
        mock_entry.comment = None
        mock_entry.icon = "icon"
        mock_entry.categories = []
        mock_entry.terminal_required = False
        mock_entry.exec_command = None

        mock_parse.return_value = {"org.test.app": mock_entry}

        result = get_app_metadata("org.test.app")

        mock_parse.assert_called_once()
        assert result["name"] == "Fetched App"
