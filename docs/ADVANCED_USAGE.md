# Advanced Wrapper Usage

## Configuration Profiles

Profiles allow you to manage multiple wrapper configurations for different contexts (work, home, gaming, etc.).

### Profile Management Commands
```bash
# List all available profiles
fplaunch profiles list

# Create a new profile
fplaunch profiles create work
fplaunch profiles create gaming --copy-from default

# Switch to a profile
fplaunch profiles switch work

# Get current active profile
fplaunch profiles current

# Export/Import profiles
fplaunch profiles export work      # Saves to work.toml
fplaunch profiles import work.toml # Imports from file
```

### Profile Storage
```
~/.config/fplaunchwrapper/
  ├── config.toml              # Default/main configuration
  └── profiles/
      ├── work.toml           # Work profile
      ├── gaming.toml         # Gaming profile
      └── custom.toml         # Custom profile
```

### Use Cases
- Different wrapper preferences for work/home/gaming
- Backup and share configurations
- Per-machine configuration profiles
- A/B testing different wrapper configurations

## Permission Presets

Permission presets allow you to define and reuse common Flatpak sandbox permission configurations.

### Preset Management Commands
```bash
# List all permission presets
fplaunch presets list

# Get a specific preset's permissions
fplaunch presets get development

# Add/create a new preset
fplaunch presets add gaming --permissions "--device=dri" "--socket=pulseaudio"
fplaunch presets add work --permissions "--filesystem=home" "--share=ipc"

# Remove a preset
fplaunch presets remove gaming
```

### Preset Storage
```toml
[permission_presets.development]
permissions = ["--filesystem=home", "--device=dri"]

[permission_presets.media]
permissions = ["--device=dri", "--socket=pulseaudio"]
```

### Use Cases
- Quick permission templates for common use cases
- Sandbox editing in wrapper script integration
- Consistent permission sets across multiple wrappers
- Easy sharing of sandbox configurations

## Interactive Mode Control

### Environment Variable: `FPWRAPPER_FORCE`

The `FPWRAPPER_FORCE` environment variable controls wrapper behavior in non-interactive contexts:

```bash
# Force interactive mode
FPWRAPPER_FORCE=interactive firefox --help

# Force desktop/non-interactive mode (default behavior)
FPWRAPPER_FORCE=desktop firefox --help
```

### Command Flag: `--fpwrapper-force-interactive`

Alternative method to force interactive mode:

```bash
# Force interactive mode using flag
firefox --fpwrapper-force-interactive --fpwrapper-info
```

## Practical Examples

### 1. Script with Wrapper Features

```bash
#!/bin/bash
# backup-firefox-settings.sh

echo "Backing up Firefox settings..."

# Force interactive mode to access wrapper features
FPWRAPPER_FORCE=interactive firefox --fpwrapper-info > firefox-info.txt
FPWRAPPER_FORCE=interactive firefox --fpwrapper-config-dir > config-dir.txt

echo "Firefox info saved to firefox-info.txt"
echo "Config directory: $(cat config-dir.txt)"
```

### 2. Custom Desktop Entry with Wrapper Features

Create a custom `.desktop` file that uses wrapper features:

```ini
[Desktop Entry]
Name=Firefox with Wrapper Info
Exec=firefox --fpwrapper-force-interactive --fpwrapper-info
Icon=firefox
Type=Application
Categories=Network;WebBrowser;
```

### 3. Testing Wrapper Functionality

```bash
#!/bin/bash
# test-wrapper.sh

app_name="$1"

echo "Testing wrapper for: $app_name"

# Test help
echo "=== Help ==="
FPWRAPPER_FORCE=interactive "$app_name" --fpwrapper-help

echo ""
echo "=== Info ==="
FPWRAPPER_FORCE=interactive "$app_name" --fpwrapper-info

echo ""
echo "=== Config Dir ==="
FPWRAPPER_FORCE=interactive "$app_name" --fpwrapper-config-dir
```

### 4. Batch Operations

```bash
#!/bin/bash
# batch-wrapper-info.sh

# Get info for all wrapped apps
for wrapper in ~/.local/bin/*; do
    if [ -x "$wrapper" ]; then
        app_name=$(basename "$wrapper")
        echo "=== $app_name ==="
        FPWRAPPER_FORCE=interactive "$app_name" --fpwrapper-info 2>/dev/null || echo "Not a wrapper"
        echo ""
    fi
done
```

### 5. IDE Integration

Configure your IDE to use wrapper features:

```bash
# VS Code task to run Firefox with wrapper info
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Firefox Info",
            "type": "shell",
            "command": "firefox",
            "args": ["--fpwrapper-force-interactive", "--fpwrapper-info"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        }
    ]
}
```

## Detection Logic

Wrappers use these checks to determine interactivity:

```bash
is_interactive() {
    # Check if stdin is a terminal
    [ -t 0 ] && 
    # Check if stdout is a terminal  
    [ -t 1 ] && 
    # Check if not forced to desktop mode
    [ "${FPWRAPPER_FORCE:-}" != "desktop" ]
}
```

### What Makes a Session "Interactive"?

- **Terminal**: Running in a physical or virtual terminal
- **SSH**: Remote shell sessions
- **TTY**: Direct terminal access
- **Force Flag**: Using `--fpwrapper-force-interactive` or `FPWRAPPER_FORCE=interactive`

### What Makes a Session "Non-Interactive"?

- **.desktop files**: GUI application launchers
- **Shell scripts**: Non-interactive script execution
- **IDE execution**: Code editors running commands
- **System services**: Background processes
- **Force Desktop**: Using `FPWRAPPER_FORCE=desktop`

## Use Case Scenarios

### Development & Testing

```bash
# Test wrapper behavior in CI/CD
FPWRAPPER_FORCE=interactive firefox --fpwrapper-info

# Ensure wrapper works in scripts
if FPWRAPPER_FORCE=interactive firefox --fpwrapper-help >/dev/null 2>&1; then
    echo "Wrapper is functional"
else
    echo "Wrapper has issues"
fi
```

### System Administration

```bash
# Audit all wrapper configurations
for app in firefox chrome thunderbird; do
    echo "=== $app Configuration ==="
    FPWRAPPER_FORCE=interactive "$app" --fpwrapper-info
    echo ""
done
```

### User Customization

```bash
# Create a custom launcher script
#!/bin/bash
# smart-firefox.sh

# Check if we want wrapper features today
if [ "$1" = "--with-wrapper" ]; then
    shift
    FPWRAPPER_FORCE=interactive firefox "$@"
else
    # Use normal bypass behavior
    firefox "$@"
fi
```

## Troubleshooting

### Wrapper Not Responding

```bash
# Force interactive mode to debug
FPWRAPPER_FORCE=interactive firefox --fpwrapper-info

# Check if wrapper exists
which firefox
file ~/.local/bin/firefox

# Test bypass behavior
FPWRAPPER_FORCE=desktop firefox --version
```

### Environment Issues

```bash
# Check current environment
echo "FPWRAPPER_FORCE: ${FPWRAPPER_FORCE:-unset}"
echo "Terminal: $([ -t 0 ] && echo YES || echo NO)"
echo "Interactive: $([[ $- == *i* ]] && echo YES || echo NO)"

# Test wrapper detection
firefox --fpwrapper-force-interactive --help
```

## Best Practices

1. **Use in Scripts**: Add `FPWRAPPER_FORCE=interactive` when you need wrapper features
2. **Testing**: Use `--fpwrapper-force-interactive` for one-off commands
3. **Fallback**: Always provide fallback behavior for non-interactive contexts
4. **Documentation**: Document why you're forcing interactive mode in scripts
5. **Security**: Be aware that forcing interactive mode may expose prompts in unexpected contexts

## Security Considerations

- **Desktop Files**: Default behavior bypasses wrappers for security
- **Scripts**: Force interactive mode only when needed
- **Automation**: Consider if wrapper features are appropriate for automated tasks
- **User Input**: Interactive mode may prompt for user input in scripts

## Related Commands

- `fplaunch`: Main management utility with commands: list, search, remove, remove-pref, set-pref, set-env, remove-env, list-env, set-pref-all, set-script, set-post-script, remove-script, remove-post-script, set-alias, remove-alias, export-prefs, import-prefs, export-config, import-config, block, unblock, list-blocked, install, launch, regenerate, info, manifest, files, uninstall
- `fplaunch profiles`: Manage configuration profiles
- `fplaunch presets`: Manage permission presets
- `fplaunch systemd`: Manage systemd timer
- `fplaunch generate`: Regenerate all wrappers
- `fplaunch cleanup`: Remove all wrappers and configuration