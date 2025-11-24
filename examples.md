# Pre-launch and Post-run Script Examples

These examples show the basic functionality for Linux users who want to customize their Flatpak application launches.

## Basic Pre-launch Script

```bash
#!/bin/bash
# ~/scripts/simple-setup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"

echo "🚀 Starting $WRAPPER_NAME..."

# Set a custom download directory
mkdir -p "$HOME/Downloads/$WRAPPER_NAME"
export CHROME_DOWNLOAD_DIR="$HOME/Downloads/$WRAPPER_NAME"

# Enable Wayland if available
if command -v weston &> /dev/null; then
    export MOZ_ENABLE_WAYLAND=1
fi

echo "✅ Environment ready"
```

## Basic Post-run Script

```bash
#!/bin/bash
# ~/scripts/simple-cleanup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"
EXIT_CODE="$4"

echo "🧹 $WRAPPER_NAME exited with code: $EXIT_CODE"

# Log the session
echo "$(date): $WRAPPER_NAME exited with $EXIT_CODE" >> "$HOME/.app-logs"

# Simple cleanup
rm -rf "/tmp/${WRAPPER_NAME}-temp" 2>/dev/null || true

echo "✅ Cleanup complete"
```

## Quick Setup

```bash
# Make scripts executable
chmod +x ~/scripts/simple-setup.sh
chmod +x ~/scripts/simple-cleanup.sh

# Set up the wrapper
chrome --fpwrapper-set-pre-script ~/scripts/simple-setup.sh
chrome --fpwrapper-set-post-script ~/scripts/simple-cleanup.sh
```

## Minimal Examples

### Very Simple Pre Script
```bash
#!/bin/bash
echo "Starting $1..."
```

### Very Simple Post Script  
```bash
#!/bin/bash
echo "$1 exited with code $4"
```

These basic examples cover the core functionality for users who want to customize their application launches.