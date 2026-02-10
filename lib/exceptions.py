#!/usr/bin/env python3
"""Exception hierarchy for fplaunchwrapper.

This module defines all custom exceptions used throughout the project,
providing a consistent error handling interface.

Hierarchy:
    FplaunchError (base)
    ├── ConfigError
    │   ├── ConfigFileNotFoundError
    │   ├── ConfigParseError
    │   ├── ConfigValidationError
    │   ├── ConfigMigrationError
    │   └── ConfigPermissionError
    ├── WrapperError
    │   ├── WrapperExistsError
    │   ├── WrapperNotFoundError
    │   └── WrapperGenerationError
    ├── LaunchError
    │   ├── AppNotFoundError
    │   └── LaunchBlockedError
    └── SafetyError
        ├── ForbiddenNameError
        └── PathTraversalError
"""

from __future__ import annotations

from typing import Any


class FplaunchError(Exception):
    """Base exception for all fplaunchwrapper errors.

    All custom exceptions in the project inherit from this class,
    allowing callers to catch all fplaunchwrapper-specific errors
    with a single except clause.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


# ============================================================================
# Configuration Errors
# ============================================================================


class ConfigError(FplaunchError):
    """Base exception for configuration-related errors."""

    pass


class ConfigFileNotFoundError(ConfigError):
    """Raised when a configuration file cannot be found."""

    pass


class ConfigParseError(ConfigError):
    """Raised when configuration parsing fails."""

    pass


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""

    pass


class ConfigMigrationError(ConfigError):
    """Raised when configuration migration fails."""

    pass


class ConfigPermissionError(ConfigError):
    """Raised when configuration file permissions are incorrect."""

    pass


# ============================================================================
# Wrapper Errors
# ============================================================================


class WrapperError(FplaunchError):
    """Base exception for wrapper-related errors."""

    pass


class WrapperExistsError(WrapperError):
    """Raised when attempting to create a wrapper that already exists."""

    def __init__(self, wrapper_name: str, wrapper_path: str | None = None) -> None:
        message = f"Wrapper already exists: {wrapper_name}"
        details = {"wrapper_name": wrapper_name}
        if wrapper_path:
            details["wrapper_path"] = wrapper_path
        super().__init__(message, details)
        self.wrapper_name = wrapper_name
        self.wrapper_path = wrapper_path


class WrapperNotFoundError(WrapperError):
    """Raised when a requested wrapper cannot be found."""

    def __init__(
        self, wrapper_name: str, searched_paths: list[str] | None = None
    ) -> None:
        message = f"Wrapper not found: {wrapper_name}"
        details: dict[str, Any] = {"wrapper_name": wrapper_name}
        if searched_paths:
            details["searched_paths"] = searched_paths
        super().__init__(message, details)
        self.wrapper_name = wrapper_name
        self.searched_paths = searched_paths


class WrapperGenerationError(WrapperError):
    """Raised when wrapper generation fails."""

    def __init__(
        self, app_id: str, reason: str, details: dict[str, Any] | None = None
    ) -> None:
        message = f"Failed to generate wrapper for {app_id}: {reason}"
        full_details = {"app_id": app_id, "reason": reason}
        if details:
            full_details.update(details)
        super().__init__(message, full_details)
        self.app_id = app_id
        self.reason = reason


# ============================================================================
# Launch Errors
# ============================================================================


class LaunchError(FplaunchError):
    """Base exception for application launch errors."""

    pass


class AppNotFoundError(LaunchError):
    """Raised when an application cannot be found (neither system nor Flatpak)."""

    def __init__(self, app_name: str) -> None:
        message = f"Application not found: {app_name}"
        super().__init__(message, {"app_name": app_name})
        self.app_name = app_name


class LaunchBlockedError(LaunchError):
    """Raised when a launch is blocked by safety checks."""

    def __init__(
        self, app_name: str, reason: str, details: dict[str, Any] | None = None
    ) -> None:
        message = f"Launch blocked for {app_name}: {reason}"
        full_details = {"app_name": app_name, "reason": reason}
        if details:
            full_details.update(details)
        super().__init__(message, full_details)
        self.app_name = app_name
        self.reason = reason


# ============================================================================
# Safety Errors
# ============================================================================


class SafetyError(FplaunchError):
    """Base exception for safety-related errors."""

    pass


class ForbiddenNameError(SafetyError):
    """Raised when a wrapper name is forbidden (conflicts with system commands)."""

    FORBIDDEN_NAMES = frozenset(
        [
            "bash",
            "sh",
            "zsh",
            "fish",
            "csh",
            "tcsh",
            "ksh",
            "dash",
            "ash",
            "ssh",
            "scp",
            "sftp",
            "rsync",
            "wget",
            "curl",
            "git",
            "hg",
            "svn",
            "make",
            "gcc",
            "g++",
            "clang",
            "python",
            "python3",
            "pip",
            "pip3",
            "node",
            "npm",
            "yarn",
            "java",
            "javac",
            "ruby",
            "gem",
            "perl",
            "php",
            "go",
            "cargo",
            "rustc",
            "docker",
            "podman",
            "flatpak",
            "systemctl",
            "journalctl",
            "dmesg",
            "ls",
            "cat",
            "grep",
            "find",
            "ps",
            "top",
            "htop",
            "kill",
            "killall",
            "pkill",
            "pgrep",
            "mkdir",
            "rmdir",
            "rm",
            "cp",
            "mv",
            "ln",
            "chmod",
            "chown",
            "chgrp",
            "df",
            "du",
            "free",
            "uptime",
            "uname",
            "whoami",
            "id",
            "passwd",
            "su",
            "sudo",
            "visudo",
            "useradd",
            "userdel",
            "groupadd",
            "groupdel",
            "mount",
            "umount",
            "fdisk",
            "mkfs",
            "fsck",
            "dd",
            "tar",
            "gzip",
            "gunzip",
            "bzip2",
            "xz",
            "zip",
            "unzip",
            "7z",
            "rar",
            "unrar",
            "less",
            "more",
            "head",
            "tail",
            "sort",
            "uniq",
            "wc",
            "cut",
            "paste",
            "tr",
            "sed",
            "awk",
            "vim",
            "vi",
            "nano",
            "emacs",
            "joe",
            "screen",
            "tmux",
            "sshd",
            "httpd",
            "nginx",
            "apache2",
            "mysql",
            "postgresql",
            "redis",
            "mongodb",
            "sqlite3",
            "ftp",
            "telnet",
            "ping",
            "traceroute",
            "nslookup",
            "dig",
            "host",
            "whois",
            "ifconfig",
            "ip",
            "route",
            "netstat",
            "ss",
            "iptables",
            "firewall-cmd",
            "ufw",
            "nmap",
            "tcpdump",
            "wireshark",
            "strace",
            "ltrace",
            "gdb",
            "valgrind",
            "perf",
            "sar",
            "iostat",
            "vmstat",
            "mpstat",
            "atop",
            "iotop",
            "glances",
            "nc",
            "socat",
            "openssl",
            "gpg",
            "ssh-keygen",
        ]
    )

    def __init__(self, name: str, is_builtin: bool = True) -> None:
        if is_builtin:
            message = f"Forbidden wrapper name '{name}': conflicts with system command"
        else:
            message = f"Forbidden wrapper name '{name}': blocked by user blocklist"
        super().__init__(message, {"name": name, "is_builtin": is_builtin})
        self.name = name
        self.is_builtin = is_builtin

    @classmethod
    def is_forbidden(cls, name: str) -> bool:
        """Check if a name is in the forbidden list."""
        return name.lower() in cls.FORBIDDEN_NAMES


class PathTraversalError(SafetyError):
    """Raised when a path traversal attempt is detected."""

    def __init__(self, path: str, base_dir: str | None = None) -> None:
        message = f"Path traversal detected: '{path}'"
        details: dict[str, Any] = {"path": path}
        if base_dir:
            message += f" escapes base directory '{base_dir}'"
            details["base_dir"] = base_dir
        super().__init__(message, details)
        self.path = path
        self.base_dir = base_dir


class InvalidFlatpakIdError(SafetyError):
    """Raised when a Flatpak ID is invalid."""

    def __init__(self, app_id: str, reason: str | None = None) -> None:
        message = f"Invalid Flatpak ID: '{app_id}'"
        if reason:
            message += f" - {reason}"
        super().__init__(message, {"app_id": app_id, "reason": reason})
        self.app_id = app_id
        self.reason = reason
