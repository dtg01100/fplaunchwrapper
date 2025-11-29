# FPWRAPPER_FORCE Environment Variable - Complete Guide

## Overview

The `FPWRAPPER_FORCE` environment variable controls whether wrappers use their full functionality or bypass themselves in non-interactive contexts.

## Values

### `FPWRAPPER_FORCE=desktop` (Default)
- **Behavior**: Bypass wrapper, search PATH for next executable
- **Use Case**: .desktop files, system services, background processes
- **Result**: Clean, predictable execution without wrapper interference

### `FPWRAPPER_FORCE=interactive` 
- **Behavior**: Force full wrapper functionality
- **Use Case**: Scripts, testing, debugging, custom launchers
- **Result**: All wrapper features available (prompts, preferences, etc.)

### Unset (Auto-detect)
- **Behavior**: Detect interactivity automatically
- **Interactive**: Full wrapper functionality
- **Non-interactive**: Bypass wrapper

## Usage Examples

### 1. Script with Wrapper Features

```bash
#!/bin/bash
# Get Firefox wrapper information
FPWRAPPER_FORCE=interactive firefox --fpwrapper-info > firefox-info.txt

# Get configuration directory
config_dir=$(FPWRAPPER_FORCE=interactive firefox --fpwrapper-config-dir)
echo "Firefox config: $config_dir"
```

### 2. Testing Wrapper Functionality

```bash
#!/bin/bash
# Test if wrapper is working
if FPWRAPPER_FORCE=interactive firefox --fpwrapper-help >/dev/null 2>&1; then
    echo "✅ Firefox wrapper is functional"
else
    echo "❌ Firefox wrapper has issues"
fi
```

### 3. Custom Desktop Entry

```ini
[Desktop Entry]
Name=Firefox with Info
Exec=sh -c "firefox --fpwrapper-force-interactive --fpwrapper-info > /tmp/firefox-info.txt; firefox %U"
Icon=firefox
Type=Application
```

### 4. Batch Operations

```bash
#!/bin/bash
# Get info for all wrapped apps
for app in firefox chrome thunderbird; do
    echo "=== $app ==="
    FPWRAPPER_FORCE=interactive "$app" --fpwrapper-info 2>/dev/null || echo "Not a wrapper"
done
```

### 5. IDE Integration

```bash
# VS Code task
{
    "label": "Firefox Debug Info",
    "type": "shell", 
    "command": "firefox",
    "args": ["--fpwrapper-force-interactive", "--fpwrapper-info"]
}
```

## Command Equivalents

```bash
# Environment variable method
FPWRAPPER_FORCE=interactive firefox --help

# Command flag method  
firefox --fpwrapper-force-interactive --help

# Both achieve the same result
```

## Detection Logic

Wrappers determine interactivity using:

```bash
is_interactive() {
    # stdin is terminal AND stdout is terminal AND not forced to desktop
    [ -t 0 ] && [ -t 1 ] && [ "${FPWRAPPER_FORCE:-}" != "desktop" ]
}
```

### Interactive Detection
- `[ -t 0 ]`: Check if stdin is a terminal
- `[ -t 1 ]`: Check if stdout is a terminal  
- `[[ $- == *i* ]]`: Check if shell has interactive flag
- `PS1` set: Interactive shells have prompt set

### Force Override
- `FPWRAPPER_FORCE=interactive`: Always interactive
- `FPWRAPPER_FORCE=desktop`: Always non-interactive
- `--fpwrapper-force-interactive`: Force for single command

## Practical Scenarios

### Development Scripts
```bash
#!/bin/bash
# development-setup.sh

echo "Setting up development environment..."

# Force wrapper features to configure apps
FPWRAPPER_FORCE=interactive firefox --fpwrapper-set-override system
FPWRAPPER_FORCE=interactive chrome --fpwrapper-set-pre-script ~/scripts/dev-setup.sh

echo "Development configuration complete"
```

### System Administration
```bash
#!/bin/bash
# audit-wrappers.sh

echo "Auditing wrapper configurations..."

for wrapper in ~/.local/bin/*; do
    if [ -x "$wrapper" ]; then
        app=$(basename "$wrapper")
        echo "=== $app ==="
        FPWRAPPER_FORCE=interactive "$app" --fpwrapper-info 2>/dev/null
    fi
done
```

### Backup Scripts
```bash
#!/bin/bash
# backup-app-configs.sh

backup_dir="$HOME/app-config-backups/$(date +%Y%m%d)"
mkdir -p "$backup_dir"

for app in firefox chrome thunderbird; do
    echo "Backing up $app..."
    
    # Get config directory
    config_dir=$(FPWRAPPER_FORCE=interactive "$app" --fpwrapper-config-dir 2>/dev/null)
    
    if [ -n "$config_dir" ] && [ -d "$config_dir" ]; then
        cp -r "$config_dir" "$backup_dir/$app-config"
        echo "✅ Backed up $app configuration"
    fi
done

echo "Backup complete: $backup_dir"
```

### Troubleshooting Scripts
```bash
#!/bin/bash
# debug-wrapper.sh

app="$1"
if [ -z "$app" ]; then
    echo "Usage: $0 <app-name>"
    exit 1
fi

echo "Debugging wrapper for: $app"
echo ""

echo "1. Testing bypass behavior:"
FPWRAPPER_FORCE=desktop "$app" --version 2>/dev/null && echo "   ✅ Bypass works" || echo "   ❌ Bypass failed"

echo ""
echo "2. Testing interactive behavior:"
FPWRAPPER_FORCE=interactive "$app" --fpwrapper-info >/dev/null 2>&1 && echo "   ✅ Interactive works" || echo "   ❌ Interactive failed"

echo ""
echo "3. Environment info:"
echo "   Wrapper location: $(which "$app")"
echo "   System command: $(command -v "$app" 2>/dev/null || echo "Not found")"
echo "   FPWRAPPER_FORCE: ${FPWRAPPER_FORCE:-unset}"
```

## Best Practices

### 1. Use Judiciously
- Only force interactive mode when you actually need wrapper features
- Default bypass behavior is usually what you want for automation

### 2. Document Usage
- Comment why you're forcing interactive mode in scripts
- Provide fallback behavior for when wrappers aren't available

### 3. Error Handling
- Always check if wrapper commands succeed
- Provide meaningful error messages

### 4. Security Considerations
- Interactive mode may prompt for user input
- Be careful using in unattended scripts

### 5. Testing
- Test both interactive and non-interactive behavior
- Verify scripts work in different contexts

## Troubleshooting

### Wrapper Not Responding
```bash
# Check if wrapper exists
which firefox

# Test with force flag
FPWRAPPER_FORCE=interactive firefox --help

# Check environment
echo "FPWRAPPER_FORCE: ${FPWRAPPER_FORCE:-unset}"
```

### Unexpected Prompts
```bash
# Ensure desktop mode for automation
FPWRAPPER_FORCE=desktop firefox --arg

# Or unset to use auto-detection
unset FPWRAPPER_FORCE
firefox --arg
```

### PATH Issues
```bash
# Check what wrapper will find
FPWRAPPER_FORCE=interactive firefox --fpwrapper-info 2>&1 | grep "System package"

# Verify PATH order
echo "$PATH" | tr ':' '\n'
```

## Related Files

- `docs/ADVANCED_USAGE.md` - Comprehensive examples and use cases
- `README.md` - Basic usage and installation
- `manage_wrappers.sh` - Wrapper management commands
- Individual wrapper scripts - Generated by `fplaunch-generate`

## Summary

The `FPWRAPPER_FORCE` environment variable provides fine-grained control over wrapper behavior:

- **Default**: Smart auto-detection works for most cases
- **Force Interactive**: Access wrapper features in scripts
- **Force Desktop**: Ensure bypass behavior when needed

This flexibility makes fplaunchwrapper suitable for both interactive use and automated scenarios while maintaining clean behavior in desktop environments.