# fplaunchwrapper Design Document

## Overview

**fplaunchwrapper** is a Python utility that creates wrapper scripts for Flatpak applications, enabling users to launch them by simplified names (e.g., `firefox` instead of `flatpak run org.mozilla.firefox`) while intelligently choosing between system packages, Flatpak applications, and user-defined preferences.

| Property | Value |
|----------|-------|
| Version | 1.3.0 |
| License | MIT |
| Python | 3.8+ |
| Status | Production/Stable |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Layer (cli.py)                      │
│           Click-based command dispatching                    │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   generate.py │   │   manage.py   │   │   launch.py   │
│ Wrapper Gen   │   │ CRUD Ops      │   │ App Launcher  │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              config_manager.py (EnhancedConfigManager)       │
│         TOML config, profiles, presets, validation          │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│flatpak_monitor│   │ systemd_setup │   │   cleanup.py  │
│ Watchdog FS   │   │ Cron/Systemd  │   │ Obsolete Wraps│
└───────────────┘   └───────────────┘   └───────────────┘
```

---

## Core Components

| Module | Class | Responsibility |
|--------|-------|----------------|
| `cli.py` | Click group | CLI interface, command routing |
| `generate.py` | `WrapperGenerator` | Discovers Flatpaks, generates wrapper scripts from template |
| `manage.py` | `WrapperManager` | Lists, removes, sets preferences, manages aliases |
| `launch.py` | `AppLauncher` | Launches apps with preference handling, hooks |
| `config_manager.py` | `EnhancedConfigManager` | TOML config with Pydantic validation, profiles/presets |
| `systemd_setup.py` | `SystemdSetup` | Creates systemd user units or cron jobs |
| `flatpak_monitor.py` | `FlatpakEventHandler` | Watchdog-based monitoring daemon |
| `cleanup.py` | `WrapperCleanup` | Removes obsolete wrappers |
| `exceptions.py` | Exception hierarchy | Custom exceptions for all error types |
| `python_utils.py` | Utility functions | Path normalization, lock management, temp file creation, executable finding |
| `safety.py` | Security boundaries | Input validation, path traversal prevention, wrapper validation, forbidden names, test environment detection |
| `notifications.py` | Desktop notifications | libnotify integration for user feedback |

---

## Wrapper Script Design

Each generated wrapper is a self-contained bash script created from `templates/wrapper.template.sh` that:

1. **Detects context**: Interactive terminal vs desktop/non-interactive
2. **Discovers system binary**: Checks if native package exists in PATH
3. **Respects preferences**: Reads `~/.config/fplaunchwrapper/<app>.pref`
4. **Provides CLI options**: `--fpwrapper-*` flags for info, sandbox editing, preferences
5. **Supports hooks**: Pre-launch and post-run scripts with environment variables
6. **Handles non-interactive**: Auto-bypasses to system command when not in terminal

### Wrapper Options

```
--fpwrapper-help              Show detailed help
--fpwrapper-info              Show wrapper info
--fpwrapper-config-dir        Show Flatpak data directory
--fpwrapper-sandbox-info      Show Flatpak sandbox details
--fpwrapper-edit-sandbox      Interactive sandbox permission editor
--fpwrapper-sandbox-yolo      Grant all permissions (dangerous)
--fpwrapper-sandbox-reset     Reset sandbox to defaults
--fpwrapper-set-override      Set launch preference (system/flatpak)
--fpwrapper-launch            One-shot launch method override
--fpwrapper-force-interactive Force interactive mode
--fpwrapper-set-pre-script    Set pre-launch hook script
--fpwrapper-set-post-script   Set post-run hook script
```

#### Additional Wrapper Options

| Option | Description |
|--------|-------------|
| `--fpwrapper-run-unrestricted` | Run Flatpak with `--no-sandbox` flag |
| `--fpwrapper-remove-pre-script` | Remove pre-launch script for this invocation |
| `--fpwrapper-remove-post-script` | Remove post-run script for this invocation |

### Interactive Detection

A wrapper is considered interactive when:
- `FPWRAPPER_FORCE=interactive` is set, OR
- stdin AND stdout are both TTY AND `FPWRAPPER_FORCE != "desktop"`

Non-interactive mode (desktop files, scripts) automatically bypasses prompts.

---

## Configuration System

### Main Configuration

**Location:** `~/.config/fplaunchwrapper/config.toml`

```toml
schema_version = 1
bin_dir = "/home/user/bin"
log_level = "INFO"
enable_notifications = true

[global_preferences]
launch_method = "auto"

[app_preferences.firefox]
launch_method = "flatpak"
custom_args = ["--new-window"]
pre_launch_script = "/path/to/script.sh"
post_launch_script = "/path/to/script.sh"
```

### Auxiliary Files

| File | Purpose |
|------|---------|
| `<app>.pref` | Per-app launch preference (single word: system/flatpak) |
| `<app>.env` | Per-app environment variables (sourced before launch) |
| `aliases` | Alias mappings (name → flatpak ID) |
| `blocklist` | User-blocked app IDs (won't generate wrappers) |
| `profiles/*.toml` | Named configuration profiles (aspirational) |
| `presets/*.toml` | Sandbox permission presets |

### Schema Migration

When `schema_version` doesn't match the current version, migration functions upgrade the config file automatically while preserving user settings.

#### Additional Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `cron_interval` | integer | 6 | Cron interval in hours for cleanup |
| `enable_notifications` | boolean | true | Enable desktop notifications |

---

## Profiles & Presets

### Profiles

Profiles allow switching between different configuration sets (e.g., "work", "personal"):
- Stored as separate files in `profiles/` directory
- CLI commands: `fplaunch profiles list|create|switch|current|export|import`
- Switching updates the active profile in config

### Presets

Sandbox permission presets are stored as separate TOML files:

```
~/.config/fplaunchwrapper/presets/
├── gaming.toml
├── development.toml
└── media.toml
```

Preset file format:
```toml
name = "gaming"
description = "Graphics, input, audio, network access"
permissions = [
    "--device=dri",
    "--device=input",
    "--socket=pulseaudio",
    "--socket=wayland",
    "--socket=x11",
    "--share=ipc",
    "--share=network",
    "--filesystem=~/Games"
]
```

Built-in presets: Development, Media, Network, Minimal, Gaming, Offline

---

## Hook System

### Pre-Launch Hooks

Executed before the application starts. Receives:
- `$1` - Wrapper name
- `$2` - Flatpak ID
- `$3` - Launch source (system/flatpak)
- `$@` - All user arguments

### Post-Run Hooks

Executed after the application exits. Receives:
- `$1` - Wrapper name
- `$2` - Flatpak ID
- `$3` - Launch source (system/flatpak)
- `$4` - Exit code
- `FPWRAPPER_EXIT_CODE` - Exit code (env var)
- `FPWRAPPER_SOURCE` - Launch source (env var)
- `FPWRAPPER_WRAPPER_NAME` - Wrapper name (env var)
- `FPWRAPPER_APP_ID` - Flatpak ID (env var)

### Hook Failure Behavior

Currently hooks always continue with warning on failure. Planned:
- User configurable per-hook behavior
- Option to abort launch entirely on pre-launch failure

---

## Security Model

### Forbidden Names

Wrappers cannot be generated for shell-critical commands. Centralized in `exceptions.py`:
- **Built-in list**: `ForbiddenNameError.FORBIDDEN_NAMES` (159 system commands)
- **User blocklist**: `~/.config/fplaunchwrapper/blocklist`
- **Check method**: `ForbiddenNameError.is_forbidden(name)`

### Security Model (`safety.py`)

All security boundaries are consolidated in `safety.py`:

- **Input validation**: Flatpak ID format validation, shell metacharacter filtering
- **Path operations**: Path traversal prevention, HOME directory validation
- **Wrapper validation**: Binary content detection, file size limits (100KB), shebang validation
- **Forbidden names**: Built-in list + user blocklist for wrapper names
- **Test environment detection**: Prevents accidental browser launches during pytest

### Path Restrictions

- Wrapper generation restricted to directories within HOME
- Validation prevents `..` traversal
- Symlink resolution before path checks

---

## Monitoring & Auto-Update

### Flatpak Monitor

Uses watchdog filesystem events to monitor Flatpak installation directories:
- Triggers automatic wrapper regeneration on app install/uninstall
- Can run as daemon or via systemd/cron scheduling

### Systemd Integration

`systemd_setup.py` creates:
- User systemd service unit for monitoring
- User systemd timer for periodic regeneration
- Falls back to cron if systemd unavailable

---

## File Locking

Per-user lock prevents concurrent wrapper generation:
- Lock location: XDG_RUNTIME_DIR or config directory
- Uses directory creation for atomic lock acquisition
- Automatically released on process exit

---

## Error Handling

Custom exception hierarchy for consistent error handling:

```
FplaunchError (base)
├── ConfigError
│   ├── ConfigParseError
│   └── ConfigMigrationError
├── WrapperError
│   ├── WrapperExistsError
│   └── WrapperNotFoundError
├── LaunchError
│   └── AppNotFoundError
└── SafetyError
    ├── ForbiddenNameError
    └── PathTraversalError
```

#### Additional Exception Types

| Exception | Description |
|-----------|-------------|
| `ConfigFileNotFoundError` | Configuration file not found |
| `ConfigPermissionError` | Permission denied accessing config |
| `InvalidFlatpakIdError` | Invalid Flatpak identifier format |

---

## Notifications

Desktop-only notifications via libnotify:
- Wrapper generation completion
- Error alerts
- Status updates from daemon

---

## Testing

Comprehensive test suite organized in `tests/python/`:

| Category | Description |
|----------|-------------|
| Unit | Individual function/class tests with mocked subprocess |
| Integration | Tests that run actual flatpak commands |
| Security | Adversarial tests for input validation, path traversal |
| Slow | Long-running tests (marked, selectable) |

Test markers: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.security`

---

## Dependencies

### Core (Always Installed)

| Package | Purpose |
|---------|---------|
| click >= 8.1.0 | CLI framework |
| rich >= 13.0.0 | Enhanced terminal output |
| platformdirs >= 3.0.0 | XDG directory handling |
| watchdog >= 3.0.0 | Filesystem monitoring |

### Optional

| Extra | Packages | Purpose |
|-------|----------|---------|
| robustness | pydantic, tomli, tomli-w, psutil | Config validation, process utilities |
| advanced | structlog, validators | Structured logging, input validation |
| dev | pytest, ruff, black, flake8, pylint | Development tools |
| security | cryptography, bandit | Security scanning |
| integration | dbus-python, xvfbwrapper | GUI/DBus testing |

---

## Entry Points

```
fplaunch               Main CLI
fplaunch-cli           CLI alternate entry
fplaunch-generate      Wrapper generation
fplaunch-manage        Wrapper management
fplaunch-launch        App launching
fplaunch-cleanup       Cleanup obsolete wrappers
fplaunch-setup-systemd Systemd/cron setup
fplaunch-config        Configuration management
fplaunch-monitor       Monitoring daemon
```

### CLI Commands

#### Core Commands
| Command | Description |
|---------|-------------|
| `generate` | Generate wrapper script for a Flatpak app |
| `launch` | Launch a Flatpak with wrapper options |
| `manage` | Manage generated wrappers (list, remove, etc.) |
| `cleanup` | Clean up stale wrappers and configurations |

#### Systemd Command Group
| Command | Description |
|---------|-------------|
| `systemd enable` | Enable systemd service for auto-start |
| `systemd disable` | Disable systemd service |
| `systemd status` | Show service status |
| `systemd start` | Start the service |
| `systemd stop` | Stop the service |
| `systemd restart` | Restart the service |
| `systemd reload` | Reload service configuration |
| `systemd logs` | View service logs |
| `systemd list` | List managed services |
| `systemd test` | Test systemd configuration |

#### Profile/Preset Commands
| Command | Description |
|---------|-------------|
| `profiles` | Manage configuration profiles |
| `presets` | Manage configuration presets |

#### Utility Commands
| Command | Description |
|---------|-------------|
| `files` | Display managed files with filtering options |
| `manifest` | Show Flatpak manifest information |
| `install` | Install Flatpak and generate wrapper |
| `uninstall` | Uninstall Flatpak and remove wrapper |
| `search` / `discover` | Search for available wrappers |
| `config` | Configuration management (show, init, cron-interval) |

---

## Directory Structure

```
fplaunchwrapper/
├── lib/                      Python package (installed as 'fplaunch')
│   ├── __init__.py
│   ├── fplaunch.py          Main entry point
│   ├── cli.py               Click CLI interface
│   ├── generate.py          Wrapper generation
│   ├── manage.py            Wrapper management
│   ├── launch.py            App launching
│   ├── config_manager.py    Configuration handling
│   ├── systemd_setup.py     Systemd/cron integration
│   ├── flatpak_monitor.py   Filesystem monitoring
│   ├── cleanup.py           Obsolete wrapper removal
│   ├── exceptions.py        Exception hierarchy
│   ├── python_utils.py      Utility functions (path normalization, locking, temp files)
│   ├── safety.py            Security boundaries (input validation, path safety, forbidden names)
│   └── notifications.py     Desktop notifications
├── templates/
│   └── wrapper.template.sh  Bash wrapper template
├── tests/
│   └── python/              Pytest test suite
├── docs/
│   ├── man/                 Man pages
│   └── info/                Info pages
├── examples/                Usage examples
├── packaging/               Debian packaging
├── pyproject.toml           Project configuration
└── README.md
```

---

### Hook Failure Modes

The hook failure modes system controls how the wrapper handles failures in pre-launch and post-run scripts.

#### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `hook_failure_mode_default` | `ignore` | Default mode for all hooks |
| `pre_launch_failure_mode_default` | (inherits) | Default for pre-launch hooks |
| `post_launch_failure_mode_default` | (inherits) | Default for post-run hooks |

#### Failure Modes

| Mode | Behavior |
|------|----------|
| `ignore` | Log the failure, continue execution |
| `warn` | Show warning notification, continue |
| `abort` | Stop execution, don't launch app |

#### CLI Options

| Option | Description |
|--------|-------------|
| `--hook-failure MODE` | Set failure mode for this invocation |
| `--abort-on-hook-failure` | Shorthand for `--hook-failure abort` |
| `--ignore-hook-failure` | Shorthand for `--hook-failure ignore` |

#### Wrapper Options

| Option | Description |
|--------|-------------|
| `--fpwrapper-hook-failure MODE` | Set failure mode at runtime |
| `--fpwrapper-abort-on-hook-failure` | Abort on hook failure |
| `--fpwrapper-ignore-hook-failure` | Ignore hook failures |

#### Environment Variables

| Variable | Description |
|----------|-------------|
| `FPWRAPPER_HOOK_FAILURE` | Runtime hook failure mode override |
| `FPWRAPPER_HOOK_FAILURE_MODE` | Exported to hook scripts (read-only) |

See [`plans/hook-failure-modes-design.md`](plans/hook-failure-modes-design.md) for the full design specification.

---

### Future Enhancements

See [`docs/DEFERRED_FEATURES_IMPLEMENTATION.md`](docs/DEFERRED_FEATURES_IMPLEMENTATION.md) for planned features and enhancement roadmap.

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [`COMMAND_REFERENCE.md`](COMMAND_REFERENCE.md) | Full command documentation |
| [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) | Feature completion status |
| [`docs/ADVANCED_USAGE.md`](docs/ADVANCED_USAGE.md) | Advanced usage examples |
| [`plans/hook-failure-modes-design.md`](plans/hook-failure-modes-design.md) | Hook failure modes design spec |
| [`QUICKSTART.md`](QUICKSTART.md) | Quick start guide |
| [`examples/`](examples/) | Example scripts and configurations |
