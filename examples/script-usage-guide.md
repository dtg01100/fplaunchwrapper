# Practical Script Setup Examples

This guide shows how to set up and use pre-launch and post-run scripts with real-world examples.

## Quick Start: Chrome with Privacy Setup

### 1. Create a Pre-launch Script
```bash
#!/bin/bash
# ~/scripts/chrome-private.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"

echo "🔒 Setting up private browsing for $WRAPPER_NAME..."

# Create isolated temporary directories
SESSION_ID="$$"
TEMP_HOME="/tmp/chrome-private-$SESSION_ID"
mkdir -p "$TEMP_HOME"/{cache,config,data,downloads}

# Set up private environment
export XDG_CACHE_HOME="$TEMP_HOME/cache"
export XDG_CONFIG_HOME="$TEMP_HOME/config" 
export XDG_DATA_HOME="$TEMP_HOME/data"
export CHROME_DOWNLOAD_DIR="$TEMP_HOME/downloads"

# Disable telemetry and tracking
export GOOGLE_UPDATE_DISABLED=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1

# Log the private session start
echo "$(date '+%Y-%m-%d %H:%M:%S') | Private session started: $SESSION_ID" >> "$HOME/.logs/chrome-private.log"

# Store session info for cleanup
echo "$SESSION_ID" > "/tmp/chrome-session-id"
echo "$TEMP_HOME" > "/tmp/chrome-temp-home"

echo "✅ Private environment ready"
```

### 2. Create a Post-run Script
```bash
#!/bin/bash
# ~/scripts/chrome-private-cleanup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"
EXIT_CODE="$4"

echo "🧹 Cleaning up private session for $WRAPPER_NAME..."

# Get session info
SESSION_ID=$(cat /tmp/chrome-session-id 2>/dev/null || echo "$$")
TEMP_HOME=$(cat /tmp/chrome-temp-home 2>/dev/null || echo "/tmp/chrome-private-$SESSION_ID")

# Securely remove all private data
if [ -d "$TEMP_HOME" ]; then
    echo "🔒 Securely removing private data..."
    find "$TEMP_HOME" -type f -exec shred -u {} \; 2>/dev/null || true
    rm -rf "$TEMP_HOME" 2>/dev/null || true
    echo "✅ Private data completely removed"
fi

# Log the cleanup
LOG_FILE="$HOME/.logs/chrome-private.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') | Private session ended: $SESSION_ID | Exit: $EXIT_CODE" >> "$LOG_FILE"

# Remove temporary files
rm -f "/tmp/chrome-session-id" "/tmp/chrome-temp-home"

# Clear clipboard for privacy
if command -v xsel &> /dev/null; then
    echo -n "" | xsel --clipboard --input
    echo -n "" | xsel --primary --input
fi

echo "✅ Privacy cleanup complete"
```

### 3. Set Up the Scripts
```bash
# Make scripts executable
chmod +x ~/scripts/chrome-private.sh
chmod +x ~/scripts/chrome-private-cleanup.sh

# Set up the wrapper (assuming chrome wrapper exists)
fplaunch set-script chrome ~/scripts/chrome-private.sh
fplaunch set-post-script chrome ~/scripts/chrome-private-cleanup.sh

# Or using wrapper commands
chrome --fpwrapper-set-pre-script ~/scripts/chrome-private.sh
chrome --fpwrapper-set-post-script ~/scripts/chrome-private-cleanup.sh
```

## Example: Development Environment with VS Code

### Pre-launch Script for VS Code
```bash
#!/bin/bash
# ~/scripts/vscode-dev-setup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"

echo "🔧 Setting up development environment..."

# Source development environment
if [ -f "$HOME/.dev-env" ]; then
    source "$HOME/.dev-env"
    echo "✅ Loaded development environment"
fi

# Set up SSH agent for Git operations
if [ -z "$SSH_AUTH_SOCK" ]; then
    eval $(ssh-agent -s)
    ssh-add ~/.ssh/id_rsa 2>/dev/null || true
    echo "🔐 SSH agent configured"
fi

# Set up Python virtual environment if in a Python project
if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "Pipfile" ]; then
    if [ -d "venv" ]; then
        export VIRTUAL_ENV="$PWD/venv"
        export PATH="$VIRTUAL_ENV/bin:$PATH"
        echo "🐍 Python virtual environment activated"
    elif [ -f "poetry.lock" ]; then
        export POETRY_ACTIVE=1
        echo "📦 Poetry environment detected"
    fi
fi

# Set up Node.js environment if in a Node project
if [ -f "package.json" ]; then
    if [ -d "node_modules" ]; then
        export NODE_PATH="$PWD/node_modules:$NODE_PATH"
        echo "📦 Node.js environment configured"
    fi
fi

# Create development log entry
echo "$(date '+%Y-%m-%d %H:%M:%S') | Starting VS Code session" >> "$HOME/.logs/dev-sessions.log"

echo "✅ Development environment ready"
```

### Post-run Script for VS Code
```bash
#!/bin/bash
# ~/scripts/vscode-dev-cleanup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"
EXIT_CODE="$4"

echo "🧹 Cleaning up development environment..."

# Stop SSH agent if we started one
if [ -n "$SSH_AUTH_SOCK" ] && [[ "$SSH_AUTH_SOCK" == */tmp/ssh-* ]]; then
    ssh-agent -k 2>/dev/null || true
    echo "🔐 Stopped SSH agent"
fi

# Log development session
LOG_FILE="$HOME/.logs/dev-sessions.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') | VS Code session ended | Exit: $EXIT_CODE" >> "$LOG_FILE"

# Update project statistics
if [ -n "$VIRTUAL_ENV" ] && [ -d "$VIRTUAL_ENV" ]; then
    STATS_FILE="$VIRTUAL_ENV/.dev-stats"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | Python development | Duration: unknown" >> "$STATS_FILE"
fi

# Clean up temporary development files
find /tmp -name "vscode-*" -type d -mtime +1 -exec rm -rf {} \; 2>/dev/null || true

echo "✅ Development cleanup complete"
```

## Example: Gaming Setup with Performance Optimization

### Pre-launch Script for Steam
```bash
#!/bin/bash
# ~/scripts/steam-performance.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"

echo "🎮 Optimizing system for gaming..."

# Store original settings
echo "$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo 'ondemand')" > "/tmp/steam-gov-backup"

# Set performance governor
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true
echo "⚡ CPU performance mode enabled"

# Disable screen blanking
xset s off -dpms 2>/dev/null || true
echo "🖥️  Screen blanking disabled"

# Set up game-specific environment
export __GL_THREADED_OPTIMIZATIONS=1
export __GL_SYNC_TO_VBLANK=0
export vblank_mode=0

# Log game session start
echo "$(date '+%Y-%m-%d %H:%M:%S') | Gaming session started" >> "$HOME/.logs/gaming.log"

echo "✅ Gaming environment optimized"
```

### Post-run Script for Steam
```bash
#!/bin/bash
# ~/scripts/steam-performance-cleanup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"
EXIT_CODE="$4"

echo "🧹 Restoring system settings..."

# Restore original CPU governor
if [ -f "/tmp/steam-gov-backup" ]; then
    ORIGINAL_GOV=$(cat "/tmp/steam-gov-backup")
    echo "$ORIGINAL_GOV" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true
    rm -f "/tmp/steam-gov-backup"
    echo "🔧 CPU governor restored to: $ORIGINAL_GOV"
fi

# Re-enable screen blanking
xset s on +dpms 2>/dev/null || true
echo "🖥️  Screen blanking re-enabled"

# Log gaming session
LOG_FILE="$HOME/.logs/gaming.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') | Gaming session ended | Exit: $EXIT_CODE" >> "$LOG_FILE"

# Clean up any temporary files
find /tmp -name "steam-*" -type f -delete 2>/dev/null || true

echo "✅ System settings restored"
```

## Usage Examples

### Setting up scripts via management command:
```bash
# Set pre-launch script
fplaunch set-script chrome ~/scripts/chrome-private.sh

# Set post-run script  
fplaunch set-post-script chrome ~/scripts/chrome-private-cleanup.sh

# View current scripts
ls ~/.config/fplaunchwrapper/scripts/chrome/

# Remove scripts
fplaunch remove-script chrome
fplaunch remove-post-script chrome
```

### Setting up scripts via wrapper commands:
```bash
# Set scripts using wrapper
chrome --fpwrapper-set-pre-script ~/scripts/chrome-private.sh
chrome --fpwrapper-set-post-script ~/scripts/chrome-private-cleanup.sh

# Remove scripts using wrapper
chrome --fpwrapper-remove-pre-script
chrome --fpwrapper-remove-post-script
```

### Testing scripts:
```bash
# Test pre-launch script manually
~/scripts/chrome-private.sh chrome com.google.Chrome flatpak

# Test post-run script manually  
~/scripts/chrome-private-cleanup.sh chrome com.google.Chrome flatpak 0

# Check logs
tail -f ~/.logs/chrome-private.log
```

## Best Practices

### Pre-launch Scripts:
1. **Keep them fast** - Don't add significant startup delay
2. **Handle errors gracefully** - Allow user to continue or abort
3. **Use temporary directories** - Clean up after yourself
4. **Log important actions** - For debugging and tracking
5. **Check dependencies** - Verify required tools are available

### Post-run Scripts:
1. **Always clean up** - Remove temporary files and directories
2. **Handle all exit codes** - Clean up regardless of how app exited
3. **Log sessions** - Track usage and performance
4. **Reset system changes** - Restore original settings
5. **Be robust** - Handle missing files and directories gracefully

### Security Considerations:
1. **Validate script paths** - Don't execute arbitrary commands
2. **Use absolute paths** - Avoid path traversal issues
3. **Secure temporary files** - Use appropriate permissions
4. **Sanitize environment** - Don't leak sensitive data
5. **Audit script content** - Review what scripts do