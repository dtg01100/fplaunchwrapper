# fplaunch Command Reference

Quick reference for all fplaunch commands and subcommands.

## Usage Pattern
```bash
fplaunch [OPTIONS] COMMAND [ARGS...]
```

## Global Options
- `--verbose, -v` - Enable verbose output
- `--emit` - Dry-run mode (show what would be done)
- `--emit-verbose` - Show detailed file contents in emit mode
- `--config-dir PATH` - Use custom configuration directory
- `--version` - Show version and exit (use with a command)
- `--help` - Show help message

## Core Commands

### Wrapper Management
```bash
fplaunch generate [DIR]              # Generate wrappers (default: ~/bin)
fplaunch list [APP_NAME]             # List all wrappers or show one
fplaunch info APP_NAME               # Show wrapper information
fplaunch remove NAME                 # Remove wrapper
fplaunch rm NAME                     # Alias for remove
fplaunch cleanup                     # Clean orphaned wrappers
fplaunch clean                       # Alias for cleanup
```

### Application Operations
```bash
fplaunch launch APP_NAME             # Launch application
fplaunch install APP_NAME            # Install Flatpak + generate wrapper
fplaunch uninstall APP_NAME          # Uninstall Flatpak + remove wrapper
fplaunch manifest APP_NAME           # Show Flatpak manifest
fplaunch search [QUERY]              # Search/discover wrappers
fplaunch discover [QUERY]            # Alias for search
```

### Configuration
```bash
fplaunch config [ACTION] [VALUE]     # Manage configuration
fplaunch config show                 # Show current config
fplaunch config init                 # Initialize config
fplaunch config cron-interval [HRS]  # Set/show cron interval
fplaunch set-pref APP PREF           # Set launch preference
fplaunch pref APP PREF               # Alias for set-pref
```

### Monitoring
```bash
fplaunch monitor [--daemon]          # Start monitoring daemon
```

### Utilities
```bash
fplaunch files                       # Files helper
fplaunch systemd-setup [DIR] [SCRIPT] # Install systemd units
```

## systemd Group
Manage systemd user units for automatic wrapper generation.

```bash
fplaunch systemd [OPTIONS] COMMAND
```

### Subcommands
```bash
fplaunch systemd enable              # Enable automatic updates
fplaunch systemd disable             # Disable automatic updates
fplaunch systemd status              # Show status
fplaunch systemd start               # Start units
fplaunch systemd stop                # Stop units
fplaunch systemd restart             # Restart units
fplaunch systemd reload              # Reload units
fplaunch systemd logs                # View logs
fplaunch systemd list                # List units
fplaunch systemd test                # Test configuration
```

## profiles Group
Manage configuration profiles.

```bash
fplaunch profiles [OPTIONS] COMMAND
```

### Subcommands
```bash
fplaunch profiles list               # List available profiles
fplaunch profiles create NAME        # Create new profile
fplaunch profiles switch NAME        # Switch to profile
fplaunch profiles current            # Show current profile
fplaunch profiles export NAME [FILE] # Export profile
fplaunch profiles import FILE [NAME] # Import profile
```

## presets Group
Manage permission presets for Flatpak applications.

```bash
fplaunch presets [OPTIONS] COMMAND
```

### Subcommands
```bash
fplaunch presets list                # List available presets
fplaunch presets get NAME            # Get preset details
fplaunch presets add NAME -p PERM    # Add new preset
fplaunch presets remove NAME         # Remove preset
```

### Example
```bash
fplaunch presets add gaming -p "--device=dri" -p "--socket=pulseaudio"
```

## Common Workflows

### First-time Setup
```bash
# Generate wrappers for all installed Flatpaks
fplaunch generate ~/bin

# Enable automatic wrapper generation
fplaunch systemd enable
```

### Installing Applications
```bash
# Install and create wrapper in one command
fplaunch install org.mozilla.firefox

# Or manually
flatpak install org.mozilla.firefox
fplaunch generate
```

### Managing Preferences
```bash
# Set preference to always use Flatpak version
fplaunch set-pref firefox flatpak

# Set preference to use system version
fplaunch set-pref firefox system

# Apply preference to all wrappers
fplaunch set-pref all flatpak
```

### Dry-run Testing
```bash
# Test what would be generated
fplaunch --emit generate ~/bin

# Test systemd setup
fplaunch --emit systemd enable

# Test any command without executing
fplaunch --emit <command>
```

### Cleanup
```bash
# Remove orphaned wrappers
fplaunch cleanup

# Remove specific wrapper
fplaunch remove firefox

# Uninstall app and wrapper
fplaunch uninstall org.mozilla.firefox
```

## Help for Any Command
```bash
# Main help
fplaunch --help

# Command help
fplaunch <command> --help

# Group help
fplaunch systemd --help
fplaunch profiles --help
fplaunch presets --help

# Subcommand help
fplaunch systemd enable --help
```

## Exit Codes
- `0` - Success
- `1` - Error (invalid arguments, operation failed)
- `2` - Click usage error (missing required arguments)

## Notes
- Commands that modify the system accept `--emit` for dry-run
- Most commands work with both app names and Flatpak IDs
- Wrapper names are sanitized from Flatpak IDs (e.g., `org.mozilla.firefox` → `firefox`)
- Preferences can be `system`, `flatpak`, or a specific Flatpak ID
