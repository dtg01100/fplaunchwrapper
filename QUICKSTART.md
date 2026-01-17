# Quick Start Guide

Get started with fplaunchwrapper in under 2 minutes.

## Installation

### Python Installation

**Using uv:**
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install fplaunchwrapper
uv tool install fplaunchwrapper

# Verify installation
fplaunch --help
```

**Using pip:**
```bash
# Install globally
pip install fplaunchwrapper

# Or for current user
pip install --user fplaunchwrapper
```

### Traditional Package Installation

**Debian/Ubuntu (.deb):**
```bash
# Download from GitHub Releases
wget https://github.com/dtg01100/fplaunchwrapper/releases/latest/download/fplaunchwrapper_*.deb
sudo dpkg -i fplaunchwrapper_*.deb
sudo apt-get install -f
```

**Fedora/RHEL (.rpm):**
```bash
# Download from GitHub Releases
wget https://github.com/dtg01100/fplaunchwrapper/releases/latest/download/fplaunchwrapper-*.rpm
sudo dnf install fplaunchwrapper-*.rpm
```

### Development Installation

```bash
git clone https://github.com/dtg01100/fplaunchwrapper.git
cd fplaunchwrapper

# Set up complete development environment
./setup-dev.sh
```

## 🎯 First Steps

1. **Verify installation:**
    ```bash
    fplaunch --help
    ```

2. **Generate wrappers for your Flatpak apps:**
    ```bash
    fplaunch generate ~/bin
    ```

3. **List your wrappers:**
    ```bash
    fplaunch list
    ```

4. **Launch an app:**
    ```bash
    # Now you can launch any Flatpak app by name!
    firefox
    vlc
    gimp
    # And so on...
    ```

## 🎨 Common Tasks

### Generate and List Wrappers

```bash
# Generate wrappers in custom directory
fplaunch generate ~/my-wrappers

# Generate with verbose output
fplaunch generate --verbose ~/bin

# List all wrappers with beautiful formatting
fplaunch list
```

### Manage Launch Preferences

```bash
# Set Firefox to use Flatpak version
fplaunch set-pref firefox flatpak

# Set Chrome to use system version
fplaunch set-pref chrome system

# Remove a wrapper completely
fplaunch remove vlc
```

### 🧪 Safe Testing with Emit Mode

**Preview changes before making them:**

```bash
# See what wrappers would be generated
fplaunch generate --emit ~/bin

# Preview with full file contents
fplaunch generate --emit --emit-verbose ~/bin

# Preview preference changes
fplaunch set-pref firefox flatpak --emit

# Preview with preference file content
fplaunch set-pref firefox flatpak --emit --emit-verbose

# Test systemd setup safely
fplaunch setup-systemd --emit

# Test with complete systemd unit files
fplaunch setup-systemd --emit --emit-verbose

# Use global emit flag for any command
fplaunch --emit set-pref chrome system
fplaunch --emit-verbose set-pref chrome system
```

**Benefits:**
- ✅ **Risk-free testing** - No system changes
- ✅ **Detailed preview** - See exact operations and file contents
- ✅ **Script validation** - Test automation safely
- ✅ **Content inspection** - Verify generated files before creation

### Get Wrapper Information

```bash
# Show detailed info about a wrapper
fplaunch info firefox

# Show current configuration
fplaunch config
```

### Launch Applications

```bash
# Normal launch (uses your saved preference)
firefox

# Force specific launch method for one time
firefox --fpwrapper-launch flatpak
firefox --fpwrapper-launch system

# Get help with wrapper options
firefox --fpwrapper-help
```

## 🔧 Wrapper Features

Every generated wrapper provides intelligent behavior and these commands:

```bash
# Get comprehensive help
firefox --fpwrapper-help

# Show app and wrapper information
firefox --fpwrapper-info

# Show Flatpak configuration directory
firefox --fpwrapper-config-dir

# Display sandbox permissions and details
firefox --fpwrapper-sandbox-info

# Force launch method (one-time)
firefox --fpwrapper-launch flatpak
firefox --fpwrapper-launch system

# Set persistent launch preference
firefox --fpwrapper-set-override flatpak
```

## ⚙️ Advanced Configuration

### Automatic Updates

**Set up systemd monitoring (recommended):**
```bash
fplaunch systemd enable
```
- Monitors for Flatpak app changes
- Automatically regenerates wrappers
- Runs daily maintenance tasks

**Monitor manually:**
```bash
fplaunch monitor  # Start real-time monitoring
```

### Custom Configuration

**Edit TOML configuration:**
```bash
# Edit configuration file
$EDITOR ~/.config/fplaunchwrapper/config.toml

# View current configuration
fplaunch config
```

**Example configuration:**
```toml
# Global preferences
[global_preferences]
launch_method = "auto"
env_vars = { "LANG" = "en_US.UTF-8" }

# App-specific preferences
[app_preferences.firefox]
launch_method = "flatpak"
custom_args = ["--new-window"]

[app_preferences.chrome]
launch_method = "system"
```

### Scripting Integration

**Pre-launch and post-run scripts:**
```bash
# Set pre-launch script
firefox --fpwrapper-set-pre-script ~/scripts/pre-launch.sh

# Set post-run script
firefox --fpwrapper-set-post-script ~/scripts/post-run.sh
```

**Environment variable control:**
```bash
# Force interactive mode in scripts
FPWRAPPER_FORCE=interactive firefox --fpwrapper-help
```

## 🔧 Troubleshooting

### Common Issues

**Command not found after installation:**
```bash
# Ensure PATH includes uv tools
export PATH="$HOME/.local/bin:$PATH"

# Reinstall if needed
uv tool install --force fplaunchwrapper
```

**No Flatpak apps found:**
```bash
# Check if Flatpak is installed
flatpak --version

# Install some apps
flatpak install flathub org.mozilla.firefox
flatpak install flathub org.videolan.VLC

# Regenerate wrappers
fplaunch generate ~/bin
```

**Permission errors:**
```bash
# Make bin directory writable
chmod 755 ~/bin

# Or use a different directory
fplaunch generate ~/my-wrappers
```

**Monitoring not working:**
```bash
# Ensure watchdog is installed
uv pip install watchdog

# Try systemd setup
fplaunch systemd enable
```

**PATH issues:**
```bash
# Add to your shell profile
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Getting Help

```bash
# CLI help
fplaunch --help

# Wrapper help
firefox --fpwrapper-help

# Documentation
man fplaunchwrapper  # If installed
```

## 🧹 Cleanup & Uninstallation

### Safe Cleanup
```bash
# Preview what will be removed
fplaunch cleanup --dry-run

# Remove everything (with confirmation)
fplaunch cleanup --yes

# Remove from specific directory
fplaunch cleanup --bin-dir ~/my-wrappers
```

### Complete Uninstallation
```bash
# Remove user data
fplaunch cleanup --yes

# Remove systemd units
systemctl --user disable flatpak-wrappers.path flatpak-wrappers.timer
systemctl --user stop flatpak-wrappers.path flatpak-wrappers.timer

# Uninstall package
uv tool uninstall fplaunchwrapper
# OR
pip uninstall fplaunchwrapper
```

## 📚 Resources

- **Full Documentation**: [README.md](README.md)
- **Advanced Usage**: [docs/ADVANCED_USAGE.md](docs/ADVANCED_USAGE.md)
- **Configuration Guide**: [docs/FPWRAPPER_FORCE.md](docs/FPWRAPPER_FORCE.md)
- **Examples**: [examples/](examples/) directory
- **Issues**: [GitHub Issues](https://github.com/dtg01100/fplaunchwrapper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dtg01100/fplaunchwrapper/discussions)

---

## 🎉 Enjoy Simplified Flatpak Launching!

**fplaunchwrapper** makes Flatpak apps feel like native system applications. Launch any Flatpak app by name, manage preferences intelligently, and enjoy automatic updates!

**Next steps:**
- Install more Flatpak apps: `flatpak install flathub <app-id>`
- Regenerate wrappers: `fplaunch generate ~/bin`
- Set up monitoring: `fplaunch systemd enable`

**Happy Flatpaking!** 🚀
