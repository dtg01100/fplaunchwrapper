# Flatpak Launch Wrappers

A utility to create small wrapper scripts for Flatpak applications, allowing you to launch them by their simplified name (e.g., `chrome` instead of `flatpak run com.google.Chrome`). It handles conflicts with system packages, remembers user preferences, and provides management tools.

## Features

- Generates wrappers for user and system Flatpak apps
- Automatic updates via systemd (user changes trigger immediately, system changes daily)
- Conflict resolution: Choose between system package or Flatpak app, with preference memory
- Aliases: Create custom names for wrappers
- Help and info: `--help` and `--fpwrapper-info` flags on wrappers
- Backup/restore: Export/import preferences and blocklists
- Management script: Interactive menu (with dialog GUI fallback) or CLI for configuring wrappers
- Block/unblock specific apps
- Customizable wrapper directory
- Environment variables: Set per-wrapper environment variables
- Pre-launch scripts: Run custom scripts before launching apps
- Post-run scripts: Execute cleanup or logging scripts after apps exit

## Wrapper Features

Each generated wrapper provides these additional options:


- `--fpwrapper-help` - Show detailed help with all available options
- `--fpwrapper-info` - Show wrapper and Flatpak app information
- `--fpwrapper-config-dir` - Show the Flatpak app's configuration directory
- `--fpwrapper-sandbox-info` - Show Flatpak sandbox details and permissions
- `--fpwrapper-edit-sandbox` - Interactive sandbox permission editor
- `--fpwrapper-sandbox-yolo` - Grant all permissions (use with extreme caution)
- `--fpwrapper-set-override [system|flatpak]` - Force preference for this wrapper
- `--fpwrapper-set-pre-script <script>` - Set a pre-launch script
- `--fpwrapper-set-post-script <script>` - Set a post-run script
- `--fpwrapper-remove-pre-script` - Remove pre-launch script
- `--fpwrapper-remove-post-script` - Remove post-run script

**Script Arguments:** Pre-launch and post-run scripts receive: wrapper name, Flatpak ID, target application, and any additional arguments.

## Installation

1. Clone or download the scripts.
2. Run `bash install.sh [optional_bin_dir]` to install (default bin dir: `~/.local/bin`). You'll be prompted to enable automatic updates.
3. Ensure `~/.local/bin` (or your chosen dir) is in your PATH.

**Installation Notes:**
- The installer will check for Flatpak, systemd, and crontab availability
- Automatic updates can use systemd (preferred) or fall back to crontab
- Bash completion is automatically installed to `~/.bashrc.d/` if available, or copied to your bin directory
- The installer generates initial wrappers for all installed Flatpak apps

## Usage

- Launch apps: `chrome`, `firefox`, etc.
- Get info: `chrome --fpwrapper-info` or `chrome --fpwrapper-help` for detailed options.
- Config dir: `cd "$(chrome --fpwrapper-config-dir)"` to access app data.
- Sandbox info: `chrome --fpwrapper-sandbox-info` to show Flatpak details.
- Edit sandbox: `chrome --fpwrapper-edit-sandbox` for interactive permission editing.
- YOLO mode: `chrome --fpwrapper-sandbox-yolo` to grant all permissions (use with caution).
- Set override: `chrome --fpwrapper-set-override [system|flatpak]` to force preference (prompts if not specified).
- Env vars: Set transient env vars via `fplaunch-manage set-env` (for permanent, use `flatpak override <app> --env=VAR=value`).
- Manage: `fplaunch-manage` for interactive menu (uses dialog if available), or CLI commands like `fplaunch-manage list`, `fplaunch-manage info <name>`, `fplaunch-manage manifest <name>`.
- Install: `fplaunch-manage install <app>` to install a Flatpak and create wrapper.
- Launch: `fplaunch-manage launch <name>` to launch a wrapper.
  - Examples:
   - `fplaunch-manage set-alias chrome browser`
   - `fplaunch-manage export-prefs prefs.tar.gz`
   - `fplaunch-manage export-config full_backup.tar.gz` to export complete configuration
   - `fplaunch-manage info chrome` to show detailed app info and manifest
   - `fplaunch-manage manifest chrome local > manifest.ini` to save local manifest
   - `fplaunch-manage set-env chrome MOZ_ENABLE_WAYLAND 1` to set environment variables
   - `fplaunch-manage set-script chrome ~/scripts/chrome-prelaunch.sh` to set pre-launch script
   - `fplaunch-manage set-post-script chrome ~/scripts/chrome-postrun.sh` to set post-run script
   - `fplaunch-manage remove-script chrome` to remove pre-launch script
   - `fplaunch-manage remove-post-script chrome` to remove post-run script
   - `bash manage_wrappers.sh block com.example.App`

## Scripts

- `install.sh`: Sets up wrappers and systemd units (accepts optional bin directory).
- `uninstall.sh`: Removes wrappers, preferences, and systemd units.
- `fplaunch-generate`: Generates/updates wrappers.
- `fplaunch-setup-systemd`: Configures systemd for auto-updates.
- `manage_wrappers.sh`: Management utility (installed as `fplaunch-manage`) with commands: list, remove, remove-pref, set-pref, set-env, remove-env, list-env, set-pref-all, set-script, set-post-script, remove-script, remove-post-script, set-alias, remove-alias, export-prefs, import-prefs, export-config, import-config, block, unblock, list-blocked, install, launch, regenerate, info, manifest, files, uninstall.
- `fplaunch_completion.bash`: Bash completion support.

**Note:** The main management script is called `manage_wrappers.sh` in the source but installed as `fplaunch-manage` for easier access.

## Requirements

- **Required:** Bash, Flatpak
- **Optional for auto-updates:** Systemd (user session) or crontab
- **Optional for management UI:** dialog package (falls back to CLI if not available)
- **Optional for bash completion:** Standard bash completion setup

## Script Execution

### Pre-launch Scripts
Pre-launch scripts run before the Flatpak application starts. They are useful for:
- Setting up environment variables or temporary files
- Checking system requirements
- Starting dependent services
- Displaying warnings or messages

### Post-run Scripts  
Post-run scripts execute after the Flatpak application exits. They can:
- Clean up temporary files created by pre-launch scripts
- Log application usage or exit codes
- Restart services that were modified
- Display completion messages

### Script Arguments
Both pre-launch and post-run scripts receive these arguments:
1. `$1` - Wrapper name (e.g., "chrome")
2. `$2` - Flatpak ID (e.g., "com.google.Chrome")  
3. `$3` - Target application ("flatpak" or system command name)
4. `$@` - All original arguments passed to the wrapper

### Error Handling
- Pre-launch script failures prompt user to continue or abort
- Post-run scripts execute regardless of application exit status
- Scripts must be executable files with proper permissions

## License

MIT

## Troubleshooting

**Common Issues:**
- If wrappers don't launch, ensure your bin directory is in PATH
- If auto-updates don't work, check that systemd user session is running or crontab is available
- If bash completion doesn't work, source the completion file manually: `source ~/.bashrc.d/fplaunch_completion.bash`

**Debugging:**
- Use `fplaunch-manage files` to see all generated files
- Use `fplaunch-manage info <wrapper>` to debug wrapper configuration
- Check systemd status with `systemctl --user status flatpak-wrappers.*`

**Configuration Directory:** `~/.config/flatpak-wrappers/`
**Generated Wrappers:** Default to `~/.local/bin/` (configurable during installation)