# Package Building

This directory contains the build scripts and configurations for creating distribution packages.

## Supported Formats

- **Debian/Ubuntu** (.deb)
- **Fedora/RHEL/openSUSE** (.rpm)

## Building Packages

### Prerequisites

**For Debian packages:**
```bash
sudo apt-get install build-essential devscripts debhelper
```

**For RPM packages:**
```bash
sudo dnf install rpm-build  # Fedora/RHEL
# or
sudo zypper install rpm-build  # openSUSE
```

### Build Commands

**Debian package:**
```bash
./packaging/build-deb.sh 1.1.0
```

**RPM package:**
```bash
./packaging/build-rpm.sh 1.1.0
```

Replace `1.1.0` with the desired version number.

## Package Installation

### Debian/Ubuntu

```bash
sudo dpkg -i fplaunchwrapper_1.1.0_all.deb
sudo apt-get install -f  # Install any missing dependencies
bash /usr/lib/fplaunchwrapper/install.sh
```

### Fedora/RHEL/openSUSE

```bash
sudo rpm -i fplaunchwrapper-1.1.0-1.noarch.rpm
# or
sudo dnf install fplaunchwrapper-1.1.0-1.noarch.rpm
bash /usr/lib/fplaunchwrapper/install.sh
```

## Package Contents

Both packages install to:
- `/usr/lib/fplaunchwrapper/` - Main scripts and libraries
- `/usr/share/doc/fplaunchwrapper/` - Documentation
- `/usr/share/bash-completion/completions/` - Bash completion

The user installation script (`install.sh`) must be run after package installation to:
- Generate wrapper scripts in `~/.local/bin`
- Set up systemd user units for automatic updates
- Configure user preferences

## Automated Releases

The GitHub Actions workflow automatically builds and releases packages when you push a tag:

```bash
git tag v1.2.0
git push origin v1.2.0
```

This will:
1. Build .deb and .rpm packages
2. Create a GitHub Release
3. Attach packages to the release
4. Include release notes from `RELEASE_v1.2.0.md` if available

## Directory Structure

```
packaging/
├── build-deb.sh           # Debian package build script
├── build-rpm.sh           # RPM package build script
├── fplaunchwrapper.spec   # RPM spec file
└── debian/                # Debian packaging files
    ├── control            # Package metadata and dependencies
    ├── changelog          # Debian changelog
    ├── compat             # Debhelper compatibility version
    ├── rules              # Build rules (Makefile)
    └── postinst           # Post-installation script
```
