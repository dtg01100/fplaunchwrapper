# Quick Start Guide

Get started with fplaunchwrapper in under 5 minutes!

## Installation

### Option 1: Package Manager (Recommended)

**Debian/Ubuntu:**
```bash
# Download from GitHub Releases
wget https://github.com/dtg01100/fplaunchwrapper/releases/latest/download/fplaunchwrapper_1.1.0_all.deb
sudo dpkg -i fplaunchwrapper_1.1.0_all.deb
sudo apt-get install -f

# IMPORTANT: Run per-user setup (required)
bash /usr/lib/fplaunchwrapper/install.sh
# You'll be prompted whether to enable automatic updates
```

**Fedora/RHEL:**
```bash
# Download from GitHub Releases  
wget https://github.com/dtg01100/fplaunchwrapper/releases/latest/download/fplaunchwrapper-1.1.0-1.noarch.rpm
sudo dnf install fplaunchwrapper-1.1.0-1.noarch.rpm

# IMPORTANT: Run per-user setup (required)
bash /usr/lib/fplaunchwrapper/install.sh
# You'll be prompted whether to enable automatic updates
```

**Note**: The package installation only installs files system-wide. Each user must run the `install.sh` script to:
- Generate wrapper scripts in their `~/.local/bin`
- Optionally enable automatic wrapper updates (via systemd or crontab)

### Option 2: From Source

```bash
git clone https://github.com/dtg01100/fplaunchwrapper.git
cd fplaunchwrapper
bash install.sh
```

## First Steps

1. **Verify installation:**
   ```bash
   fplaunch-manage --help
   ```

2. **List your wrappers:**
   ```bash
   fplaunch-manage list
   ```

3. **Search for apps:**
   ```bash
   fplaunch-manage search browser
   fplaunch-manage search office
   ```

4. **Launch an app:**
   ```bash
   # If you have Firefox as a Flatpak:
   firefox
   # Or any other Flatpak app by its wrapper name
   ```

## Common Tasks

### Find and Launch Apps

```bash
# Search for video apps
fplaunch-manage search video

# Launch VLC (if installed)
vlc
```

### Manage Preferences

```bash
# If both system and Flatpak versions exist, set a preference
fplaunch-manage set-pref firefox flatpak

# Remove preference to be prompted again
fplaunch-manage remove-pref firefox
```

### View App Information

```bash
# Get detailed info about a wrapper
fplaunch-manage info firefox

# See Flatpak manifest
fplaunch-manage manifest firefox
```

### Install New Flatpak Apps

```bash
# Install and automatically create wrapper
fplaunch-manage install org.gimp.GIMP

# Now you can run it
gimp
```

## Wrapper Features

Every wrapper supports these flags:

```bash
# Get help
chrome --fpwrapper-help

# See app info
chrome --fpwrapper-info

# Open config directory
cd "$(chrome --fpwrapper-config-dir)"

# View sandbox permissions
chrome --fpwrapper-sandbox-info

# Edit sandbox permissions interactively
chrome --fpwrapper-edit-sandbox
```

## Advanced Features

### Environment Variables

```bash
# Set environment variable for a specific app
fplaunch-manage set-env firefox MOZ_ENABLE_WAYLAND 1

# List environment variables
fplaunch-manage list-env firefox

# Remove environment variable
fplaunch-manage remove-env firefox MOZ_ENABLE_WAYLAND
```

### Aliases

```bash
# Create an alias
fplaunch-manage set-alias firefox browser

# Now you can use both:
firefox
browser

# Remove alias
fplaunch-manage remove-alias browser
```

### Pre-launch Scripts

```bash
# Create a script
cat > ~/chrome-setup.sh << 'EOF'
#!/bin/bash
echo "Starting Chrome..."
export CHROME_FLAGS="--enable-features=VaapiVideoDecoder"
EOF

chmod +x ~/chrome-setup.sh

# Set it for a wrapper
fplaunch-manage set-script chrome ~/chrome-setup.sh

# Remove it
fplaunch-manage remove-script chrome
```

### Block Unwanted Apps

```bash
# Block an app from having a wrapper
fplaunch-manage block org.example.UnwantedApp

# List blocked apps
fplaunch-manage list-blocked

# Unblock
fplaunch-manage unblock org.example.UnwantedApp
```

### Backup and Restore

```bash
# Export preferences and blocklist
fplaunch-manage export-prefs ~/my-prefs.tar.gz

# Export everything (preferences, env vars, aliases, scripts)
fplaunch-manage export-config ~/my-full-config.tar.gz

# Import on another machine or after reinstall
fplaunch-manage import-config ~/my-full-config.tar.gz
```

## Troubleshooting

**Wrappers not in PATH:**
```bash
# Add to ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"
```

**Bash completion not working:**
```bash
# Source the completion file
source ~/.bashrc.d/fplaunch_completion.bash
# Or restart your shell
```

**Need to regenerate all wrappers:**
```bash
fplaunch-manage regenerate
```

**Check auto-update status:**
```bash
systemctl --user status flatpak-wrappers.path
systemctl --user status flatpak-wrappers.timer
```

## Getting Help

- **Documentation**: See [README.md](README.md)
- **Examples**: Check [examples/](examples/) directory
- **Issues**: Report bugs at https://github.com/dtg01100/fplaunchwrapper/issues
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## Uninstallation

```bash
# From source install:
fplaunch-manage uninstall

# From package (after user uninstall):
sudo apt remove fplaunchwrapper    # Debian/Ubuntu
sudo dnf remove fplaunchwrapper    # Fedora/RHEL
```

---

**Enjoy simplified Flatpak launching!** 🚀
