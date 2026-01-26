#!/usr/bin/env python3
"""Test suite for fplaunch.generate output behavior.

Validates that generate module shows output to inform users about progress
and errors, with appropriate stream routing (stdout for info/success,
stderr for errors/warnings).
"""
from __future__ import annotations

import tempfile


from lib.generate import WrapperGenerator


class TestGenerateOutput:
    """Test WrapperGenerator output behavior."""

    def test_log_info_to_stdout(self, capsys):
        """Test that info messages print to stdout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = WrapperGenerator(tmpdir, emit_mode=True)
            gen.log("Test info message")

            captured = capsys.readouterr()
            assert "Test info message" in captured.out
            assert "ERROR" not in captured.err
            assert "WARN" not in captured.err

    def test_log_success_to_stdout(self, capsys):
        """Test that success messages print to stdout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = WrapperGenerator(tmpdir, emit_mode=True)
            gen.log("Operation successful", "success")

            captured = capsys.readouterr()
            assert "Operation successful" in captured.out
            assert "✓" in captured.out

    def test_log_warning_to_stderr(self, capsys):
        """Test that warnings print to stderr."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = WrapperGenerator(tmpdir, emit_mode=True)
            gen.log("Test warning", "warning")

            captured = capsys.readouterr()
            assert "Test warning" in captured.err
            assert "WARN" in captured.err

    def test_log_error_to_stderr(self, capsys):
        """Test that errors print to stderr."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = WrapperGenerator(tmpdir, emit_mode=True)
            gen.log("Test error", "error")

            captured = capsys.readouterr()
            assert "Test error" in captured.err
            assert "ERROR" in captured.err

    def test_emit_mode_shows_messages(self, capsys):
        """Test that emit mode shows action messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = WrapperGenerator(tmpdir, emit_mode=True)
            gen.log("EMIT: Would create wrapper: firefox")

            captured = capsys.readouterr()
            assert "EMIT: Would create wrapper: firefox" in captured.out

    def test_generate_without_verbose_still_shows_output(self, capsys):
        """Test that output is shown even without verbose flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create generator with verbose=False (default)
            gen = WrapperGenerator(tmpdir, verbose=False, emit_mode=True)
            gen.log("Important message")

            captured = capsys.readouterr()
            # Should still show info messages even without verbose
            assert "Important message" in captured.out

    def test_errors_always_show(self, capsys):
        """Test that error messages always display regardless of verbose."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = WrapperGenerator(tmpdir, verbose=False, emit_mode=True)
            gen.log("Critical error occurred", "error")

            captured = capsys.readouterr()
            assert "Critical error occurred" in captured.err
            assert "ERROR" in captured.err

    def test_log_output_with_special_characters(self, capsys):
        """Test that output handles special characters in messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = WrapperGenerator(tmpdir, emit_mode=True)
            gen.log("Created wrapper: com.example.app")
            gen.log("⚠️ Warning about special chars", "warning")

            captured = capsys.readouterr()
            assert "com.example.app" in captured.out
            # Warning should be in stderr
            assert "special chars" in captured.err
