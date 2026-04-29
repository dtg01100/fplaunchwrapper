#!/usr/bin/env python3
"""Focused edge case tests for project-specific python utilities."""
import pytest

try:
    from lib.python_utils import (
        sanitize_id_to_name,
        sanitize_string,
    )

    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="python_utils not available")
class TestPythonUtilsInputValidation:
    """Test input validation edge cases using python_utils directly."""

    def test_empty_and_none_inputs(self) -> None:
        """Test handling of empty and None inputs."""
        result = sanitize_string("")
        assert result == ""

        result = sanitize_string(None)
        assert result == ""

        result = sanitize_id_to_name("")
        assert result.startswith("app-")

    def test_sanitize_id_to_name_caps_long_names(self) -> None:
        """Test generated names are capped to a safe length."""
        flatpak_id = f"org.example.{'A' * 150}"

        result = sanitize_id_to_name(flatpak_id)

        assert len(result) <= 100
        assert result
        assert all(char.islower() or char.isdigit() or char in "-_" for char in result)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
