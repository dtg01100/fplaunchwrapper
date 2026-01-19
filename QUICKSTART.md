# Quick Start

Install and use fplaunchwrapper in under 2 minutes.

## Installation

```bash
# Install with uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install fplaunchwrapper

# Or with pip
pip install fplaunchwrapper
```

## First Steps

```bash
# Verify installation
fplaunch --help

# Generate wrappers for Flatpak apps
fplaunch generate ~/bin

# List wrappers
fplaunch list

# Launch
firefox  # Uses saved preference
```

## Common Tasks

### Generate and List

```bash
# Generate in custom directory
fplaunch generate ~/my-wrappers

# Generate with verbose output
fplaunch generate --verbose ~/bin

# List wrappers
fplaunch list
```

### Manage Preferences

```bash
# Set Firefox to use Flatpak
fplaunch set-pref firefox flatpak

# Set Chrome to use system package
fplaunch set-pref chrome system

# Remove wrapper
fplaunch remove vlc
```

### Safe Testing with Emit Mode

Preview changes without executing:

```bash
# Preview wrapper generation
fplaunch generate --emit ~/bin

# Preview with file contents
fplaunch generate --emit --emit-verbose ~/bin

# Preview preference changes
fplaunch set-pref firefox flatpak --emit

# Test systemd setup
fplaunch systemd enable --emit
```

### Wrapper Commands

```bash
# Get help
firefox --fpwrapper-help

# Show app info
firefox --fpwrapper-info

# Show config directory
firefox --fpwrapper-config-dir

# Force launch method
firefox --fpwrapper-launch flatpak
firefox --fpwrapper-launch system

# Set preference
firefox --fpwrapper-set-override flatpak
```

## Automatic Updates

```bash
# Set up systemd monitoring (recommended)
fplaunch systemd enable

# Monitor manually
fplaunch monitor
```

## Configuration

Edit `~/.config/fplaunchwrapper/config.toml`:

```toml
[global_preferences]
launch_method = "auto"
env_vars = { "LANG" = "en_US.UTF-8" }

[app_preferences.firefox]
launch_method = "flatpak"
custom_args = ["--new-window"]
```

## Troubleshooting

**Command not found:**
```bash
export PATH="$HOME/.local/bin:$PATH"
uv tool install --force fplaunchwrapper
```

**No Flatpak apps:**
```bash
flatpak install flathub org.mozilla.firefox
fplaunch generate ~/bin
```

**Permission errors:**
```bash
chmod 755 ~/bin
# Or use different directory
fplaunch generate ~/my-wrappers
```

**Monitoring issues:**
```bash
uv pip install watchdog
fplaunch systemd enable
```

## Resources

- [README.md](README.md) - Full documentation
- [docs/ADVANCED_USAGE.md](docs/ADVANCED_USAGE.md) - Advanced features
- [docs/FPWRAPPER_FORCE.md](docs/FPWRAPPER_FORCE.md) - Interactive mode control
- [GitHub Issues](https://github.com/dtg01100/fplaunchwrapper/issues)
