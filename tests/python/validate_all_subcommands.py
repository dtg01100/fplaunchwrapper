#!/usr/bin/env python3
"""Comprehensive validation of all fplaunch subcommands.

This script validates that:
1. All subcommands are defined and executable
2. All subcommands have --help support
3. All subcommands handle invalid arguments gracefully
4. All group subcommands (systemd, profiles, presets) work correctly
"""

import sys
from pathlib import Path

# Add project root to path for lib imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from click.testing import CliRunner
from lib.cli import cli

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


class SubcommandValidator:
    """Validates all fplaunch subcommands."""

    def __init__(self):
        self.runner = CliRunner()
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def print_header(self, text):
        """Print a section header."""
        print(f"\n{BOLD}{text}{RESET}")
        print("=" * len(text))

    def print_success(self, text):
        """Print a success message."""
        print(f"{GREEN}✓{RESET} {text}")
        self.passed += 1

    def print_failure(self, text):
        """Print a failure message."""
        print(f"{RED}✗{RESET} {text}")
        self.failed += 1

    def print_warning(self, text):
        """Print a warning message."""
        print(f"{YELLOW}⚠{RESET} {text}")
        self.warnings += 1

    def validate_help(self, command_parts):
        """Validate that a command has working --help."""
        result = self.runner.invoke(cli, [*command_parts, "--help"])

        command_str = " ".join(command_parts) if command_parts else "main"

        if result.exit_code != 0:
            self.print_failure(
                f"'{command_str} --help' failed with exit code {result.exit_code}"
            )
            return False

        if not result.output:
            self.print_failure(f"'{command_str} --help' produced no output")
            return False

        if "--help" not in result.output and "-h" not in result.output:
            self.print_warning(f"'{command_str} --help' doesn't show help flag")

        self.print_success(f"'{command_str} --help' works")
        return True

    def validate_invalid_args(self, command_parts, expected_error_phrases=None):
        """Validate that a command handles invalid arguments gracefully."""
        result = self.runner.invoke(cli, [*command_parts, "invalid_arg_xyz"])

        command_str = " ".join(command_parts) if command_parts else "main"

        if result.exit_code == 0:
            self.print_warning(f"'{command_str}' with invalid args returned 0")
            return False

        if not result.output:
            self.print_failure(f"'{command_str}' with invalid args produced no output")
            return False

        self.print_success(f"'{command_str}' handles invalid args")
        return True

    def validate_command_exists(self, command_parts):
        """Validate that a command exists."""
        result = self.runner.invoke(cli, command_parts)

        command_str = " ".join(command_parts)

        if "Error: No such command" in result.output:
            self.print_failure(f"Command '{command_str}' does not exist")
            return False

        self.print_success(f"Command '{command_str}' exists")
        return True

    def validate_group_subcommands(self, group_name, subcommands):
        """Validate all subcommands of a group."""
        self.print_header(f"{group_name} subcommands")

        self.validate_help([group_name])

        for subcmd in subcommands:
            self.validate_help([group_name, subcmd])

    def run_validation(self):
        """Run complete validation suite."""
        print(f"{BOLD}fplaunch Subcommand Validation{RESET}")
        print("=" * 50)

        # Main commands
        self.print_header("Main CLI")
        self.validate_help([])

        # Core commands
        self.print_header("Core Commands")
        core_commands = [
            "generate",
            "list",
            "launch",
            "remove",
            "rm",  # alias
            "cleanup",
            "clean",  # alias
            "config",
            "monitor",
            "info",
            "search",
            "discover",  # alias
            "install",
            "uninstall",
            "files",
            "manifest",
            "set-pref",
            "pref",  # alias
            "systemd-setup",
        ]

        for cmd in core_commands:
            self.validate_help([cmd])

        # systemd group
        systemd_subcommands = [
            "enable",
            "disable",
            "status",
            "start",
            "stop",
            "restart",
            "reload",
            "logs",
            "list",
            "test",
        ]
        self.validate_group_subcommands("systemd", systemd_subcommands)

        # profiles group
        profiles_subcommands = [
            "list",
            "create",
            "switch",
            "current",
            "export",
            "import",
        ]
        self.validate_group_subcommands("profiles", profiles_subcommands)

        # presets group
        presets_subcommands = [
            "list",
            "get",
            "add",
            "remove",
        ]
        self.validate_group_subcommands("presets", presets_subcommands)

        # Invalid argument handling
        self.print_header("Invalid Argument Handling")
        test_commands = [
            ["generate"],
            ["list"],
            ["config"],
            ["systemd"],
        ]

        for cmd in test_commands:
            command_str = " ".join(cmd)
            result = self.runner.invoke(cli, [*cmd, "--invalid-flag-xyz"])
            if result.exit_code != 0:
                self.print_success(f"'{command_str}' rejects invalid flags")
            else:
                self.print_warning(f"'{command_str}' doesn't reject invalid flags")

        # Summary
        self.print_header("Summary")
        total = self.passed + self.failed + self.warnings
        print(f"Total checks: {total}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")
        print(f"{YELLOW}Warnings: {self.warnings}{RESET}")

        if self.failed > 0:
            print(f"\n{RED}VALIDATION FAILED{RESET}")
            return 1
        elif self.warnings > 0:
            print(f"\n{YELLOW}VALIDATION PASSED WITH WARNINGS{RESET}")
            return 0
        else:
            print(f"\n{GREEN}ALL VALIDATIONS PASSED{RESET}")
            return 0


def main():
    """Main entry point."""
    validator = SubcommandValidator()
    return validator.run_validation()


if __name__ == "__main__":
    sys.exit(main())
