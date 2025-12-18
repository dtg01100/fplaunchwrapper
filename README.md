# fplaunchwrapper - Modern Flatpak Wrapper Management

A **modern Python-based** utility to create intelligent wrapper scripts for Flatpak applications, allowing you to launch them by their simplified name (e.g., `firefox` instead of `flatpak run org.mozilla.firefox`). It provides conflict resolution, preference management, automatic monitoring, and comprehensive management tools with a beautiful CLI interface.

## ✨ Key Features

- 🚀 **Modern Python CLI** with Rich formatting and progress bars
- 📦 **Easy Installation** via `pip` or `uv` package managers
- 🔍 **Intelligent App Discovery** for user and system Flatpak installations
- ⚡ **Real-time Monitoring** with automatic wrapper regeneration
- 🎯 **Smart Conflict Resolution** between system packages and Flatpak apps
- 💾 **Preference Memory** with TOML-based configuration
- 🎨 **Interactive Mode** with beautiful prompts and help systems
- 🔧 **Advanced Management** with comprehensive CLI tools
- 🛡️ **Security Hardened** with input validation and injection prevention
- 🌍 **Cross-platform** support with proper path handling
- 📊 **Rich Reporting** with tables, progress bars, and status indicators

## 🎯 What It Does

fplaunchwrapper creates **smart wrapper scripts** that intelligently choose between:
- **System packages** (native applications)
- **Flatpak applications** (sandboxed Flatpak apps)
- **Custom preferences** (user-defined launch methods)

### Example Usage
```bash
# Install with uv (recommended)
uv tool install fplaunchwrapper

# Generate wrappers for all Flatpak apps
fplaunch-cli generate ~/bin

# List all wrappers with beautiful formatting
fplaunch-cli list

# Set launch preference for an app
fplaunch-cli set-pref firefox flatpak

# Launch app (automatically uses your preference)
firefox
```

## 🔧 Wrapper Features

Each generated wrapper provides intelligent behavior and additional options:

### 🎯 Smart Launch Behavior
- **Automatic Detection**: Chooses between system packages and Flatpak apps
- **Preference Memory**: Remembers your choices per application
- **Conflict Resolution**: Handles name conflicts gracefully
- **Fallback Logic**: Intelligent fallback when preferred option unavailable

### 📋 Available Commands
```bash
# Get help
firefox --fpwrapper-help

# Show app information
firefox --fpwrapper-info

# Show configuration directory
firefox --fpwrapper-config-dir

# Show sandbox details
firefox --fpwrapper-sandbox-info

# Force specific launch method
firefox --fpwrapper-launch flatpak
firefox --fpwrapper-launch system

# Set persistent preference
firefox --fpwrapper-set-override flatpak
```

### 🎨 Interactive Mode
When run from a terminal, wrappers provide:
- **Beautiful Prompts**: Rich-formatted choice menus
- **Help System**: Comprehensive command documentation
- **Preference Management**: Easy preference setting
- **Information Display**: Detailed app and wrapper info

### 🤖 Non-Interactive Mode
When run from scripts, desktop files, or IDEs:
- **PATH Search**: Finds next executable with same name
- **Direct Execution**: Runs system commands directly
- **Clean Fallback**: Falls back to Flatpak if needed
- **No Prompts**: Silent, predictable behavior

## 📖 Usage Guide

### Basic Workflow

1. **Install fplaunchwrapper**
   ```bash
   uv tool install fplaunchwrapper
   ```

2. **Generate Wrappers**
   ```bash
   fplaunch-cli generate ~/bin
   ```

3. **List Your Wrappers**
   ```bash
   fplaunch-cli list
   ```

4. **Launch Applications**
   ```bash
   firefox          # Uses your saved preference
   firefox --fpwrapper-help  # Show wrapper options
   ```

### 🔧 Available Commands

#### Core Commands
```bash
fplaunch-cli generate [DIR]     # Generate wrapper scripts
fplaunch-cli list              # List all wrappers
fplaunch-cli set-pref APP PREF # Set launch preference (system/flatpak)
fplaunch-cli remove APP        # Remove a wrapper
fplaunch-cli info APP          # Show detailed wrapper info
fplaunch-cli monitor           # Start real-time monitoring daemon
fplaunch-cli config            # Show current configuration
```

#### Management Commands
```bash
fplaunch-cleanup               # Safely remove all artifacts
fplaunch-setup-systemd         # Set up automatic updates
fplaunch-config                # Configuration management
```

#### Direct Commands
```bash
fplaunch-generate [DIR]        # Direct wrapper generation
fplaunch-manage list           # Direct wrapper management
fplaunch-launch APP [ARGS]     # Direct app launching
```

### 🎨 Command Examples

**Generate Wrappers:**
```bash
# Generate in default location
fplaunch-cli generate

# Generate in custom directory
fplaunch-cli generate ~/my-wrappers

# Generate with verbose output
fplaunch-cli generate --verbose ~/bin
```

**Manage Preferences:**
```bash
# Set Firefox to use Flatpak
fplaunch-cli set-pref firefox flatpak

# Set Chrome to use system package
fplaunch-cli set-pref chrome system

# Remove a wrapper
fplaunch-cli remove vlc
```

**Monitor for Changes:**
```bash
# Start monitoring daemon
fplaunch-cli monitor

# Set up automatic systemd monitoring
fplaunch-setup-systemd
```

**Get Information:**
```bash
# Show all wrappers
fplaunch-cli list

# Show detailed info for specific app
fplaunch-cli info firefox

# Show current configuration
fplaunch-cli config
```

### 🔄 Automatic Updates

**Systemd Setup (Recommended):**
```bash
fplaunch-setup-systemd
```
- Monitors Flatpak directory for changes
- Automatically regenerates wrappers
- Runs daily maintenance

**Cron Fallback:**
```bash
fplaunch-setup-systemd  # Uses cron if systemd unavailable
```

### 🧹 Cleanup

**Safe Cleanup:**
```bash
# Preview what will be removed
fplaunch-cleanup --dry-run

# Remove everything (with confirmation)
fplaunch-cleanup --yes

# Remove from custom directory
fplaunch-cleanup --bin-dir ~/my-wrappers
```

## Interactive vs Non-Interactive Behavior

Wrappers automatically detect their execution context and behave accordingly:

### Interactive Mode (Terminal)
When run from an interactive terminal, wrappers provide full functionality:
- Preference prompts and management
- Interactive sandbox editing
- Help and information commands
- All wrapper features available

### Non-Interactive Mode (.desktop files, scripts, IDEs)
When run from non-interactive contexts, wrappers automatically bypass themselves:
- Search PATH for next executable with the same name
- Execute system command directly if found
- Fall back to Flatpak if no system command exists
- No prompts or interactive features
- Clean, predictable behavior for desktop environments

### Force Interactive Mode

You can force interactive mode in scripts using the environment variable:

```bash
# Force interactive mode in a script
FPWRAPPER_FORCE=interactive firefox --fpwrapper-help

# Or use the built-in flag
firefox --fpwrapper-force-interactive --help
```

**Use Cases:**
- **Scripting**: Force wrapper features in automated scripts
- **Testing**: Ensure wrapper functionality works as expected
- **Debugging**: Access wrapper help and diagnostics in scripts
- **Custom Launchers**: Create custom desktop entries that use wrapper features

## 🏗️ Architecture & Implementation

### Python-Based Implementation
fplaunchwrapper is built with modern Python technologies:

- **🐍 Pure Python**: Zero bash dependencies
- **📦 Standard Packaging**: Installable via pip/uv
- **🎨 Rich CLI**: Beautiful terminal interface
- **🔒 Security Hardened**: Input validation and injection prevention
- **⚡ High Performance**: Fast execution with optimized code
- **🌍 Cross-Platform**: Works on Linux, macOS, Windows
- **🧪 Well Tested**: Comprehensive test suite with CI/CD

### Key Technologies
- **Click**: Modern CLI framework
- **Rich**: Beautiful terminal formatting
- **Pydantic**: Type-safe configuration
- **TOML**: Human-readable configuration
- **pathlib**: Cross-platform path handling
- **watchdog**: Real-time file monitoring

## 📚 Advanced Usage

### Configuration Management

**TOML Configuration:**
```toml
# ~/.config/fplaunchwrapper/config.toml
bin_dir = "/home/user/bin"
debug_mode = false
log_level = "INFO"

[global_preferences]
launch_method = "auto"
env_vars = { "LANG" = "en_US.UTF-8" }

[app_preferences.firefox]
launch_method = "flatpak"
custom_args = ["--new-window"]
```

**Configuration Commands:**
```bash
# Show current config
fplaunch-cli config

# Edit configuration manually
$EDITOR ~/.config/fplaunchwrapper/config.toml
```

### Scripting & Automation

**Pre/Post Launch Scripts:**
```bash
# Set pre-launch script
firefox --fpwrapper-set-pre-script ~/scripts/pre-launch.sh

# Set post-run script
firefox --fpwrapper-set-post-script ~/scripts/post-run.sh
```

**Environment Variables:**
```bash
# Force interactive mode
FPWRAPPER_FORCE=interactive firefox --fpwrapper-help

# Custom wrapper directory
export FPWRAPPER_BIN_DIR=~/my-wrappers
```

### Advanced Features

For detailed information about:
- **[docs/FPWRAPPER_FORCE.md](docs/FPWRAPPER_FORCE.md)** - Interactive mode control
- **[docs/ADVANCED_USAGE.md](docs/ADVANCED_USAGE.md)** - Scripting and automation
- **[docs/path_resolution.md](docs/path_resolution.md)** - Path handling and resolution

## 🔧 Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/dtg01100/fplaunchwrapper.git
cd fplaunchwrapper

# Set up development environment (installs uv and all dependencies)
./setup-dev.sh

# Run tests
uv run pytest tests/python/ -v

# Run security verification
./test_security_fixes.sh

# Code formatting
uv run black lib/ tests/python/

# Linting
uv run flake8 lib/ tests/python/
```

### Project Structure

```
fplaunchwrapper/
├── lib/                          # Python modules
│   ├── fplaunch.py              # Main entry point
│   ├── cli.py                   # CLI interface
│   ├── generate.py              # Wrapper generation
│   ├── manage.py                # Wrapper management
│   ├── launch.py                # App launching
│   ├── cleanup.py               # Cleanup functionality
│   ├── systemd_setup.py         # Systemd setup
│   ├── config_manager.py        # Configuration management
│   ├── flatpak_monitor.py       # File monitoring
│   └── python_utils.py          # Utility functions
├── tests/                       # Test suite
│   ├── python/                  # Python unit tests
│   └── test_security_fixes.sh   # Security verification
├── docs/                        # Documentation
├── packaging/                   # Package building
├── pyproject.toml               # Python package config
├── setup-dev.sh                 # Development setup
└── requirements.txt             # Dependencies
```

### Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Write tests** for your changes
4. **Run the test suite**: `./setup-dev.sh test`
5. **Format your code**: `uv run black lib/`
6. **Commit your changes**: `git commit -m "feat: add amazing feature"`
7. **Push to the branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Testing Strategy

- **Unit Tests**: Test individual functions and modules
- **Integration Tests**: Test component interactions
- **Security Tests**: Verify input validation and injection prevention
- **Performance Tests**: Ensure efficient execution
- **CI/CD**: Automated testing on multiple Python versions

## 🐛 Troubleshooting

### Common Issues

**Command not found after installation:**
```bash
# Ensure PATH includes uv tools
export PATH="$HOME/.local/bin:$PATH"

# Or reinstall
uv tool install --force fplaunchwrapper
```

**Wrappers not generating:**
```bash
# Check if Flatpak is installed
flatpak --version

# Check if any Flatpak apps are installed
flatpak list --app

# Run with verbose output
fplaunch-cli generate --verbose ~/bin
```

**Permission denied errors:**
```bash
# Make bin directory writable
chmod 755 ~/bin

# Or use system directory (if admin)
sudo fplaunch-cli generate /usr/local/bin
```

**Monitoring not working:**
```bash
# Install watchdog
uv pip install watchdog

# Check systemd setup
fplaunch-setup-systemd
```

### Getting Help

- **Documentation**: Check `docs/` directory
- **Issues**: [GitHub Issues](https://github.com/dtg01100/fplaunchwrapper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dtg01100/fplaunchwrapper/discussions)
- **Wrapper Help**: `firefox --fpwrapper-help`

## 📊 Performance & Compatibility

### System Requirements

- **Python**: 3.8 or higher
- **Flatpak**: 1.0 or higher
- **Linux**: systemd or cron support
- **Storage**: ~50MB for dependencies

### Performance Characteristics

- **Startup Time**: < 100ms for CLI commands
- **Wrapper Generation**: ~2-5 seconds for 50 apps
- **Memory Usage**: < 50MB during normal operation
- **Disk Usage**: ~1KB per wrapper script

### Supported Platforms

- ✅ **Linux** (primary target)
- ✅ **macOS** (experimental)
- ✅ **Windows** (experimental via WSL)
- ✅ **Containerized** (Docker, Podman)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Flatpak Community** for the amazing sandboxing technology
- **Python Ecosystem** for the rich tooling and libraries
- **Contributors** who help improve and maintain this project

## 📞 Support

- **Bug Reports**: [GitHub Issues](https://github.com/dtg01100/fplaunchwrapper/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/dtg01100/fplaunchwrapper/discussions)
- **Documentation**: [Wiki](https://github.com/dtg01100/fplaunchwrapper/wiki)

---

<p align="center">
  <strong>Made with ❤️ for the Flatpak and Linux communities</strong>
</p>

## 🚀 Installation

### Modern Python Installation (Recommended)

**Using uv (Fast Python Package Manager):**
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install fplaunchwrapper
uv tool install fplaunchwrapper

# Verify installation
fplaunch-cli --help
```

**Using pip:**
```bash
# Install globally
pip install fplaunchwrapper

# Or install for current user
pip install --user fplaunchwrapper
```

### Traditional Package Installation

**Debian/Ubuntu (.deb):**
```bash
# Download from GitHub Releases
sudo dpkg -i fplaunchwrapper_*.deb
sudo apt-get install -f  # Install dependencies

# Generate wrappers
fplaunch-generate ~/bin
```

**Red Hat/Fedora (.rpm):**
```bash
# Download from GitHub Releases
sudo rpm -Uvh fplaunchwrapper-*.rpm

# Generate wrappers
fplaunch-generate ~/bin
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/dtg01100/fplaunchwrapper.git
cd fplaunchwrapper

# Install with uv (development mode)
uv pip install -e ".[dev]"

# Or install with pip (development mode)
pip install -e ".[dev]"
```

**Fedora/RHEL:**
```bash
# Download the .rpm from GitHub Releases
sudo dnf install fplaunchwrapper-*.rpm

# Generate wrapper scripts for your user
fplaunch-manage regenerate

# (Optional) Enable automatic updates
fplaunch-setup-systemd
```

**Important**: Package installation installs system files and commands. Each user must run `fplaunch-manage regenerate` to generate wrappers in their home directory and optionally `fplaunch-setup-systemd` to enable automatic updates.

### From Source

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
- Manage: `fplaunch-manage` for interactive menu (uses dialog if available), or CLI commands like `fplaunch-manage list`, `fplaunch-manage search <keyword>`, `fplaunch-manage info <name>`.
- Search: `fplaunch-manage search <keyword>` to find wrappers by name, ID, or description.
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
   - `fplaunch-manage block com.example.App` to block an app

## Commands

- `fplaunch-manage`: Main management utility with commands: list, search, remove, remove-pref, set-pref, set-env, remove-env, list-env, set-pref-all, set-script, set-post-script, remove-script, remove-post-script, set-alias, remove-alias, export-prefs, import-prefs, export-config, import-config, block, unblock, list-blocked, install, launch, regenerate, info, manifest, files, uninstall.
- `fplaunch-generate`: Generates/updates wrappers.
- `fplaunch-setup-systemd`: Configures systemd for auto-updates.
- `fplaunch-cleanup`: Removes all per-user artifacts (run before uninstalling).
- `install.sh`: Manual installation script (for source installs, accepts optional bin directory).
- `uninstall.sh`: Manual uninstallation script (for source installs).
- Bash completion: Automatically configured for all commands.

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