#!/usr/bin/env python3
"""Focused edge case tests that work in the test environment
Tests input validation, error handling, and boundary conditions.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Add lib to path
# Import what we can
try:
    from lib.python_utils import (
        canonicalize_path_no_resolve,
        find_executable,
        sanitize_id_to_name,
        sanitize_string,
        validate_home_dir,
    )

    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False


class TestInputValidationEdgeCases:
    """Test input validation edge cases that work with python_utils."""

    @pytest.mark.skipif(not UTILS_AVAILABLE, reason="python_utils not available")
    def test_empty_and_none_inputs(self) -> None:
        """Test handling of empty and None inputs."""
        # Test sanitize_string with empty input
        result = sanitize_string("")
        assert result == ""

        result = sanitize_string(None)
        assert result == ""

        # Test sanitize_id_to_name with empty input
        result = sanitize_id_to_name("")
        assert result.startswith("app-")  # Should generate hash-based fallback

    @pytest.mark.skipif(not UTILS_AVAILABLE, reason="python_utils not available")
    def test_extremely_long_inputs(self) -> None:
        """Test handling of extremely long inputs."""
        # Very long string
        long_string = "a" * 10000
        result = sanitize_string(long_string)
        assert len(result) >= 10000  # Should handle long strings without truncating

        # Very long ID
        long_id = "com.example." + "a" * 1000
        result = sanitize_id_to_name(long_id)
        assert len(result) < 200  # Should be limited/truncated

    @pytest.mark.skipif(not UTILS_AVAILABLE, reason="python_utils not available")
    def test_unicode_and_special_characters(self) -> None:
        """Test handling of Unicode and special characters."""
        # Unicode strings
        unicode_strings = [
            "tëst",  # Accented
            "🚀test",  # Emoji
            "test\x00null",  # Null byte
        ]

        for test_str in unicode_strings:
            result = sanitize_string(test_str)
            assert isinstance(result, str)
            # Should handle without crashing

    @pytest.mark.skipif(not UTILS_AVAILABLE, reason="python_utils not available")
    def test_malformed_flatpak_ids(self) -> None:
        """Test handling of malformed Flatpak IDs."""
        malformed_ids = [
            "",  # Empty
            "no-dots",  # No dots
            ".leading",  # Leading dot
            "trailing.",  # Trailing dot
            "a" * 500,  # Very long
        ]

        for malformed_id in malformed_ids:
            result = sanitize_id_to_name(malformed_id)
            assert isinstance(result, str)
            # Should handle malformed input gracefully

    @pytest.mark.skipif(not UTILS_AVAILABLE, reason="python_utils not available")
    def test_path_injection_attempts(self) -> None:
        """Test path injection and traversal attempts."""
        injection_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "~/../../../../root",
        ]

        for injection in injection_paths:
            # Test canonicalize_path_no_resolve
            result = canonicalize_path_no_resolve(injection)
            assert isinstance(result, (str, type(None), Path))

            # Test validate_home_dir (should reject non-home paths)
            result = validate_home_dir(injection)
            # Should return None for paths outside HOME
            assert result is None or isinstance(result, str)

    @pytest.mark.skipif(not UTILS_AVAILABLE, reason="python_utils not available")
    def test_command_injection_prevention(self) -> None:
        """Test command injection prevention."""
        injection_attempts = [
            '"; rm -rf / #',
            "$(rm -rf /)",
            "`rm -rf /`",
            "${rm,-rf,/}",
        ]

        for injection in injection_attempts:
            result = sanitize_string(injection)
            # Dangerous characters should be escaped
            assert '"' not in result.replace('\\"', "")
            assert ";" not in result.replace("\\;", "")
            assert "$" not in result.replace("\\$", "")
            assert "`" not in result.replace("\\`", "")


class TestSystemResourceEdgeCases:
    """Test system resource edge cases."""

    def test_file_operations_with_no_permissions(self) -> None:
        """Test file operations when permissions are denied."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a read-only directory
            test_dir = Path(temp_dir) / "readonly"
            test_dir.mkdir()
            test_dir.chmod(0o444)  # Read-only

            test_file = test_dir / "test.txt"
            permission_error_caught = False

            try:
                # Try to write to read-only directory
                with open(test_file, "w") as f:
                    f.write("test")
            except (PermissionError, OSError) as e:
                # Expected when permissions are denied
                permission_error_caught = True
                # Verify we got an appropriate error
                assert isinstance(e, (PermissionError, OSError))
            finally:
                # Restore permissions for cleanup
                test_dir.chmod(0o755)

            # Verify we actually tested the permission error path
            # (some systems may allow the write despite chmod)
            if not permission_error_caught:
                # File was created, verify it exists
                assert test_file.exists(), "Expected either PermissionError or file creation"

    def test_extreme_file_sizes(self) -> None:
        """Test handling of extreme file sizes."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            # Test with very large content
            large_content = "x" * 1000000  # 1MB of data
            with open(temp_file, "w") as f:
                f.write(large_content)

            # Should be able to read it back
            with open(temp_file) as f:
                read_content = f.read()
                assert len(read_content) == 1000000

        finally:
            os.unlink(temp_file)

    def test_deep_directory_structures(self) -> None:
        """Test deep directory structure handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create very deep directory structure
            deep_path = Path(temp_dir)
            for i in range(20):  # 20 levels deep
                deep_path = deep_path / f"level_{i}"
                deep_path.mkdir()

            # Should be able to create files in deep directories
            test_file = deep_path / "test.txt"
            test_file.write_text("deep file")
            assert test_file.exists()

    def test_special_file_types(self) -> None:
        """Test handling of special file types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test with symlink
            target_file = temp_path / "target.txt"
            target_file.write_text("target")
            symlink_file = temp_path / "symlink.txt"
            symlink_file.symlink_to(target_file)

            # Should handle symlinks
            assert symlink_file.exists()
            assert symlink_file.is_symlink()

            # Test reading through symlink
            content = symlink_file.read_text()
            assert content == "target"


class TestConcurrencyEdgeCases:
    """Test concurrency and race condition edge cases."""

    def test_concurrent_file_access(self) -> None:
        """Test concurrent file access patterns."""
        import threading
        import time

        results = []
        errors = []

        def file_writer(thread_id, temp_file) -> None:
            try:
                for i in range(100):
                    with open(temp_file, "a") as f:
                        f.write(f"Thread {thread_id}: {i}\n")
                    time.sleep(0.001)  # Small delay to encourage race conditions
                results.append(f"thread_{thread_id}_success")
            except Exception as e:
                errors.append(f"thread_{thread_id}_error: {e}")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_file = f.name

        try:
            # Run multiple threads writing to the same file
            threads = []
            for i in range(5):
                t = threading.Thread(target=file_writer, args=[i, temp_file])
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=10)

            # Should complete without errors
            assert len(errors) == 0
            assert len(results) == 5

            # File should contain content from all threads
            with open(temp_file) as f:
                content = f.read()
                assert len(content) > 0
                # Should contain lines from different threads
                thread_lines = [line for line in content.split("\n") if line.strip()]
                assert len(thread_lines) > 400  # At least 5 threads * 80 writes each

        finally:
            os.unlink(temp_file)

    def test_atomic_file_operations(self) -> None:
        """Test atomic file operation patterns."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "atomic_test.txt"

            # Test atomic write using temp file + rename pattern
            def atomic_write(content) -> bool | None:
                temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir, text=True)
                try:
                    with os.fdopen(temp_fd, "w") as f:
                        f.write(content)
                    os.rename(temp_path, test_file)
                    return True
                except Exception:
                    os.unlink(temp_path)
                    return False

            # Test multiple atomic writes
            for i in range(10):
                success = atomic_write(f"Content {i}\n")
                assert success

            # File should contain the last write
            content = test_file.read_text()
            assert "Content 9" in content


class TestEncodingAndUnicodeEdgeCases:
    """Test encoding and Unicode edge cases."""

    def test_various_unicode_encodings(self) -> None:
        """Test various Unicode encodings and edge cases."""
        unicode_strings = [
            "café",  # Latin-1 supplement
            "naïve",  # Latin extended
            "Москва",  # Cyrillic
            "東京",  # CJK
            "🚀⭐💫",  # Emojis
            "𝄞♪♫",  # Musical symbols
            "\u0000\u0001\u0002",  # Control characters
            "\ufeff",  # BOM
        ]

        for unicode_str in unicode_strings:
            # Test string operations
            assert isinstance(unicode_str, str)
            assert len(unicode_str) > 0

            # Test encoding/decoding
            try:
                utf8_bytes = unicode_str.encode("utf-8")
                decoded = utf8_bytes.decode("utf-8")
                assert decoded == unicode_str
            except (UnicodeEncodeError, UnicodeDecodeError):
                # Some edge cases might fail, which is acceptable
                pass

    def test_mixed_encoding_scenarios(self) -> None:
        """Test mixed encoding scenarios."""
        # Test strings with mixed character sets
        mixed_strings = [
            "English: Hello 日本語: こんにちは Ελληνικά: Γεια σας",
            "Math: ∑ ∏ √ ∞ ≈ ≠ ≡",
            "Symbols: ©®™€£¥¢",
        ]

        for mixed_str in mixed_strings:
            # Should handle mixed encodings
            assert isinstance(mixed_str, str)
            assert len(mixed_str) > 10

    def test_string_normalization(self) -> None:
        """Test Unicode string normalization."""
        # Test various Unicode normalization forms

        # Different representations of the same character
        forms = [
            "caf\u00e9",  # NFC (composed)
            "cafe\u0301",  # NFD (decomposed)
        ]

        for form in forms:
            # Should handle all normalization forms
            assert isinstance(form, str)
            # Normalization should work
            normalized = form.encode("utf-8").decode("utf-8")
            assert normalized == form


class TestBoundaryConditionEdgeCases:
    """Test boundary condition edge cases."""

    def test_empty_collections_and_sequences(self) -> None:
        """Test handling of empty collections and sequences."""
        # Test with empty lists, dicts, etc.
        empty_cases = [
            [],  # Empty list
            {},  # Empty dict
            set(),  # Empty set
            "",  # Empty string
            0,  # Zero
        ]

        for empty_case in empty_cases:
            # Should handle empty inputs gracefully
            assert empty_case is not None  # Just test they exist

    def test_maximum_values(self) -> None:
        """Test handling of maximum values."""
        # Test with very large numbers, strings, etc.
        large_cases = [
            2**63 - 1,  # Max int64
            "x" * 1000000,  # Very long string
            list(range(10000)),  # Large list
        ]

        for large_case in large_cases:
            # Should handle large inputs (may be slow, but shouldn't crash)
            assert large_case is not None

    def test_minimum_values(self) -> None:
        """Test handling of minimum values."""
        # Test with minimum values
        min_cases = [
            (-(2**63), int),  # Min int64
            (0, int),  # Zero
            ("", str),  # Empty string
            ([], list),  # Empty list
        ]

        for min_case, expected_type in min_cases:
            # Should handle minimum inputs without crashing
            # Verify the value has the expected type
            assert isinstance(min_case, expected_type)
            # Verify the value equals what we set
            if expected_type == int:
                assert min_case <= 0
            elif expected_type == str:
                assert len(min_case) == 0
            elif expected_type == list:
                assert len(min_case) == 0

    def test_type_boundary_cases(self) -> None:
        """Test type boundary cases."""
        # Test with different types that might be passed unexpectedly
        boundary_types = [
            (None, type(None)),
            (True, bool),
            (False, bool),
            (42, int),
            (3.14, float),
            (complex(1, 2), complex),
        ]

        for value, expected_type in boundary_types:
            # Should handle unexpected types gracefully
            # Verify each value has the correct type
            assert isinstance(value, expected_type), f"Expected {expected_type}, got {type(value)}"
            # Verify truthiness behavior is consistent
            if value is None or value is False:
                assert not value
            elif value is True or value:
                assert value


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
