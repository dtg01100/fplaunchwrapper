# fplaunchwrapper

Python utility for creating wrapper scripts that launch Flatpak applications by simplified names (e.g., `firefox` instead of `flatpak run org.mozilla.firefox`).

## What It Does

Creates wrapper scripts that intelligently choose between:
- System packages (native applications)
- Flatpak applications (sandboxed)
- User-defined preferences

## Installation

```bash
# Install with uv (recommended)
uv tool install fplaunchwrapper

# Or with pip
pip install fplaunchwrapper
```

## Quick Start

```bash
# Generate wrappers for all Flatpak apps
fplaunch generate ~/bin

# List wrappers
fplaunch list

# Set preference
fplaunch set-pref firefox flatpak

# Launch
firefox  # Uses your saved preference
```

## Commands

### Core

```bash
fplaunch generate [DIR]         # Generate wrappers
fplaunch list                   # List all wrappers
fplaunch set-pref APP PREF     # Set launch method (system/flatpak)
fplaunch remove APP            # Remove wrapper
fplaunch launch APP            # Launch application
fplaunch monitor               # Start monitoring daemon
fplaunch config                # Show configuration
fplaunch systemd enable        # Set up automatic updates
```

All commands support `--emit` for dry-run mode.

### Profiles & Presets

```bash
fplaunch profiles list              # List profiles
fplaunch profiles create work       # Create profile
fplaunch profiles switch work       # Switch profile
fplaunch presets list              # List permission presets
fplaunch presets add gaming --permissions "--device=dri" "--socket=pulseaudio"
```

### Systemd

```bash
fplaunch systemd enable            # Enable automatic updates
fplaunch systemd disable           # Disable
fplaunch systemd status            # Check status
```

## Wrapper Features

Each wrapper supports:

```bash
firefox --fpwrapper-help           # Help
firefox --fpwrapper-info          # App info
firefox --fpwrapper-config-dir    # Config directory
firefox --fpwrapper-sandbox-info  # Sandbox details
firefox --fpwrapper-launch flatpak # Force method
firefox --fpwrapper-set-override flatpak  # Set preference
```

### Interactive vs Non-Interactive

**Terminal**: Full functionality with prompts and menus
**Desktop files/scripts**: Auto-bypass to system command, silent execution

Force interactive mode:
```bash
FPWRAPPER_FORCE=interactive firefox --fpwrapper-help
firefox --fpwrapper-force-interactive --help
```

## Configuration

Edit `~/.config/fplaunchwrapper/config.toml`:

```toml
bin_dir = "/home/user/bin"
log_level = "INFO"

[global_preferences]
launch_method = "auto"

[app_preferences.firefox]
launch_method = "flatpak"
custom_args = ["--new-window"]
```

## Emit Mode (Dry Run)

Test commands without making changes:

```bash
fplaunch generate --emit ~/bin
fplaunch set-pref firefox flatpak --emit
fplaunch systemd enable --emit
```

Add `--emit-verbose` to see file contents.

## Development

```bash
git clone https://github.com/dtg01100/fplaunchwrapper.git
cd fplaunchwrapper
./setup-dev.sh

# Run tests
uv run pytest tests/python/ -v

# Format code
uv run black lib/ tests/python/

# Lint
uv run flake8 lib/ tests/python/
```

### Project Structure

```
fplaunchwrapper/
├── fplaunch/                     # Python package
├── lib/                          # Backward compatibility
├── tests/                        # Test suite
├── docs/                         # Documentation
├── examples/                      # Usage examples
└── pyproject.toml               # Package config
```

## System Requirements

- Python 3.8+
- Flatpak 1.0+
- Linux: systemd or cron support

## License

MIT
