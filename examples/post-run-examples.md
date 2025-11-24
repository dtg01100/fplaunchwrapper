# Post-run Script Examples

Post-run scripts execute after the Flatpak application exits and receive these arguments:
- `$1` - Wrapper name (e.g., "chrome")
- `$2` - Flatpak ID (e.g., "com.google.Chrome")
- `$3` - Target application ("flatpak" or system command)
- `$4` - Exit code of the application
- `$@` - All original arguments passed to the wrapper

## Example 1: Chrome Cleanup and Logging
```bash
#!/bin/bash
# ~/scripts/chrome-cleanup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"
EXIT_CODE="$4"

echo "🧹 Cleaning up after $WRAPPER_NAME (exit code: $EXIT_CODE)..."

# Remove temporary profile directory
TEMP_PROFILE="/tmp/chrome-profile-$$"
if [ -d "$TEMP_PROFILE" ]; then
    rm -rf "$TEMP_PROFILE"
    echo "✅ Removed temporary profile"
fi

# Clean up download directory if it was created
CUSTOM_DOWNLOADS="$HOME/Downloads/Chrome"
if [ -d "$CUSTOM_DOWNLOADS" ] && [ "$(ls -A $CUSTOM_DOWNLOADS)" ]; then
    echo "📁 Downloads saved to: $CUSTOM_DOWNLOADS"
else
    # Remove empty directory if we created it
    rmdir "$CUSTOM_DOWNLOADS" 2>/dev/null || true
fi

# Log usage statistics
LOG_FILE="$HOME/.logs/chrome-usage.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "$(date '+%Y-%m-%d %H:%M:%S') | $WRAPPER_NAME | Exit: $EXIT_CODE | Duration: $(ps -o etime= -p $$ 2>/dev/null || echo 'unknown')" >> "$LOG_FILE"

# Handle crash scenarios
if [ "$EXIT_CODE" -ne 0 ]; then
    echo "⚠️  $WRAPPER_NAME exited with code $EXIT_CODE"
    
    # Create crash report
    CRASH_DIR="$HOME/.crash-reports"
    mkdir -p "$CRASH_DIR"
    CRASH_FILE="$CRASH_DIR/chrome-crash-$(date +%Y%m%d-%H%M%S).log"
    
    echo "=== Chrome Crash Report ===" > "$CRASH_FILE"
    echo "Timestamp: $(date)" >> "$CRASH_FILE"
    echo "Exit Code: $EXIT_CODE" >> "$CRASH_FILE"
    echo "Wrapper: $WRAPPER_NAME" >> "$CRASH_FILE"
    echo "Flatpak ID: $FLATPAK_ID" >> "$CRASH_FILE"
    echo "System Info:" >> "$CRASH_FILE"
    uname -a >> "$CRASH_FILE" 2>/dev/null || echo "N/A" >> "$CRASH_FILE"
    echo "" >> "$CRASH_FILE"
    
    # Check for common issues
    if command -v dmesg &> /dev/null; then
        echo "Recent kernel messages:" >> "$CRASH_FILE"
        dmesg | tail -10 >> "$CRASH_FILE" 2>/dev/null || echo "Cannot access dmesg" >> "$CRASH_FILE"
    fi
    
    echo "Crash report saved to: $CRASH_FILE"
fi
```

## Example 2: Development Environment Cleanup
```bash
#!/bin/bash
# ~/scripts/ide-cleanup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"
EXIT_CODE="$4"

echo "🧹 Cleaning up development environment for $WRAPPER_NAME..."

# Stop SSH agent if we started one
if [ -n "$SSH_AUTH_SOCK" ] && [[ "$SSH_AUTH_SOCK" == */tmp/ssh-* ]]; then
    ssh-agent -k 2>/dev/null || true
    echo "🔐 Stopped temporary SSH agent"
fi

# Clean up temporary files
TEMP_DIRS=(
    "/tmp/${WRAPPER_NAME}-cache-$$"
    "/tmp/${WRAPPER_NAME}-config-$$"
    "/tmp/${WRAPPER_NAME}-data-$$"
)

for temp_dir in "${TEMP_DIRS[@]}"; do
    if [ -d "$temp_dir" ]; then
        rm -rf "$temp_dir"
        echo "✅ Removed $temp_dir"
    fi
done

# Update project statistics
if [ -n "$WORKSPACE_DIR" ] && [ -d "$WORKSPACE_DIR" ]; then
    STATS_FILE="$WORKSPACE_DIR/.development-stats"
    
    # Update daily coding time
    CURRENT_DATE=$(date '+%Y-%m-%d')
    if [ -f "$STATS_FILE" ]; then
        # Check if we have an entry for today
        if grep -q "^$CURRENT_DATE" "$STATS_FILE"; then
            # Update existing entry
            sed -i "s/^$CURRENT_DATE.*/$CURRENT_DATE:$(($(date +%s) - $(stat -c %Y "$STATS_FILE" 2>/dev/null || echo $(date +%s)))):$(($(grep "^$CURRENT_DATE" "$STATS_FILE" | cut -d: -f2 || echo 0) + 1))/" "$STATS_FILE"
        else
            # Add new entry
            echo "$CURRENT_DATE:0:1" >> "$STATS_FILE"
        fi
    else
        echo "$CURRENT_DATE:0:1" > "$STATS_FILE"
    fi
fi

# Log IDE session
LOG_FILE="$HOME/.logs/ide-sessions.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "$(date '+%Y-%m-%d %H:%M:%S') | $WRAPPER_NAME | Exit: $EXIT_CODE | Workspace: ${WORKSPACE_DIR:-default}" >> "$LOG_FILE"

# Handle specific IDE cleanup
case "$WRAPPER_NAME" in
    "code")
        # Clean up VS Code specific files
        find "$HOME/.vscode" -name "*.lock" -delete 2>/dev/null || true
        ;;
    "pycharm")
        # Clean up PyCharm specific files
        find "$HOME/.cache/JetBrains" -name "*.lock" -delete 2>/dev/null || true
        ;;
    "eclipse")
        # Clean up Eclipse specific files
        find "$WORKSPACE_DIR" -name "*.lock" -delete 2>/dev/null || true
        ;;
esac
```

## Example 3: Game Session Statistics
```bash
#!/bin/bash
# ~/scripts/game-cleanup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"
EXIT_CODE="$4"

echo "📊 Processing game session for $WRAPPER_NAME..."

# Restore system settings
echo "🔧 Restoring system settings..."
if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    echo powersave | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true
fi

# Re-enable screen blanking
xset s on +dpms 2>/dev/null || true

# Calculate session duration
SESSION_START_FILE="/tmp/${WRAPPER_NAME}-session-start"
if [ -f "$SESSION_START_FILE" ]; then
    SESSION_START=$(cat "$SESSION_START_FILE")
    SESSION_END=$(date +%s)
    SESSION_DURATION=$((SESSION_END - SESSION_START))
    rm -f "$SESSION_START_FILE"
else
    SESSION_DURATION=0
fi

# Log game session
LOG_DIR="$HOME/.logs/games"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${WRAPPER_NAME}.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') | Duration: ${SESSION_DURATION}s | Exit: $EXIT_CODE | Score: ${GAME_SCORE:-unknown}" >> "$LOG_FILE"

# Update game statistics
STATS_FILE="$LOG_DIR/${WRAPPER_NAME}-stats.json"
if [ ! -f "$STATS_FILE" ]; then
    echo '{"sessions": 0, "total_time": 0, "wins": 0, "losses": 0}' > "$STATS_FILE"
fi

# Update JSON statistics (simple implementation)
TOTAL_SESSIONS=$(jq '.sessions' "$STATS_FILE" 2>/dev/null || echo 0)
TOTAL_TIME=$(jq '.total_time' "$STATS_FILE" 2>/dev/null || echo 0)
NEW_TOTAL_SESSIONS=$((TOTAL_SESSIONS + 1))
NEW_TOTAL_TIME=$((TOTAL_TIME + SESSION_DURATION))

# Create temporary stats file
TEMP_STATS="/tmp/game-stats-$$.json"
cat > "$TEMP_STATS" << EOF
{
    "sessions": $NEW_TOTAL_SESSIONS,
    "total_time": $NEW_TOTAL_TIME,
    "average_session": $((NEW_TOTAL_TIME / NEW_TOTAL_SESSIONS)),
    "last_played": "$(date '+%Y-%m-%d %H:%M:%S')",
    "exit_codes": {
        "normal": $(jq '.exit_codes.normal // 0' "$STATS_FILE" 2>/dev/null || echo 0)$([ "$EXIT_CODE" -eq 0 ] && echo ", \"$EXIT_CODE\": $(($(jq ".exit_codes[\"$EXIT_CODE\"] // 0" "$STATS_FILE" 2>/dev/null || echo 0) + 1))" || echo "")
    }
}
EOF

mv "$TEMP_STATS" "$STATS_FILE"
rm -f "$TEMP_STATS"

echo "📊 Session logged: ${SESSION_DURATION}s (total: ${NEW_TOTAL_TIME}s, sessions: $NEW_TOTAL_SESSIONS)"
```

## Example 4: Privacy and Security Cleanup
```bash
#!/bin/bash
# ~/scripts/privacy-cleanup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"
EXIT_CODE="$4"

echo "🔒 Cleaning up privacy environment for $WRAPPER_NAME..."

# Remove isolated environment directories
TEMP_DIRS=(
    "/tmp/${WRAPPER_NAME}-cache-$$"
    "/tmp/${WRAPPER_NAME}-config-$$" 
    "/tmp/${WRAPPER_NAME}-data-$$"
    "/tmp/${WRAPPER_NAME}-$$"
)

for temp_dir in "${TEMP_DIRS[@]}"; do
    if [ -d "$temp_dir" ]; then
        echo "🧹 Securely removing: $temp_dir"
        # Use shred if available for sensitive data
        if command -v shred &> /dev/null; then
            find "$temp_dir" -type f -exec shred -u {} \; 2>/dev/null || true
            rmdir "$temp_dir" 2>/dev/null || true
        else
            rm -rf "$temp_dir"
        fi
        echo "✅ Removed $temp_dir"
    fi
done

# Clear browser cache and cookies if this was a browser
case "$FLATPAK_ID" in
    "org.mozilla.firefox"|"com.google.Chrome"|"org.chromium.Chromium"|"microsoft.edgedev")
        echo "🍪 Clearing browser traces..."
        # Clear system clipboard
        if command -v xsel &> /dev/null; then
            echo -n "" | xsel --clipboard --input
            echo -n "" | xsel --primary --input
        elif command -v xclip &> /dev/null; then
            echo -n "" | xclip -selection clipboard
            echo -n "" | xclip -selection primary
        fi
        ;;
esac

# Log privacy session
LOG_FILE="$HOME/.logs/privacy-sessions.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "$(date '+%Y-%m-%d %H:%M:%S') | $WRAPPER_NAME | Exit: $EXIT_CODE | Privacy mode: true" >> "$LOG_FILE"

# Check for potential security issues
if [ "$EXIT_CODE" -ne 0 ]; then
    echo "⚠️  Security alert: $WRAPPER_NAME exited abnormally (code: $EXIT_CODE)"
    
    # Log security incident
    SECURITY_LOG="$HOME/.logs/security-incidents.log"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $WRAPPER_NAME | Abnormal exit: $EXIT_CODE | Action: logged" >> "$SECURITY_LOG"
    
    # Optional: Send notification
    if command -v notify-send &> /dev/null; then
        notify-send "Privacy Alert" "$WRAPPER_NAME exited abnormally" -u critical
    fi
fi

# Reset environment variables
unset XDG_CACHE_HOME
unset XDG_CONFIG_HOME  
unset XDG_DATA_HOME
unset DOTNET_CLI_TELEMETRY_OPTOUT
unset VSCODE_CLI_TELEMETRY_OPTOUT

echo "🔒 Privacy cleanup complete for $WRAPPER_NAME"
```

## Example 5: Network and Proxy Cleanup
```bash
#!/bin/bash
# ~/scripts/network-cleanup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"
EXIT_CODE="$4"

echo "🌐 Cleaning up network settings for $WRAPPER_NAME..."

# Log network session
LOG_FILE="$HOME/.logs/network-sessions.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Get network interface statistics before cleanup
if command -v ip &> /dev/null; then
    INTERFACE=$(ip route | grep default | awk '{print $5}' | head -1)
    if [ -n "$INTERFACE" ]; then
        RX_BYTES_BEFORE=$(cat /sys/class/net/$INTERFACE/statistics/rx_bytes 2>/dev/null || echo 0)
        TX_BYTES_BEFORE=$(cat /sys/class/net/$INTERFACE/statistics/tx_bytes 2>/dev/null || echo 0)
        echo "$(date '+%Y-%m-%d %H:%M:%S') | $WRAPPER_NAME | Interface: $INTERFACE | RX: $RX_BYTES_BEFORE | TX: $TX_BYTES_BEFORE | Exit: $EXIT_CODE" >> "$LOG_FILE"
    fi
fi

# Reset MTU if we modified it
if [[ "$INTERFACE" == tun* ]] || [[ "$INTERFACE" == vpn* ]]; then
    if command -v ip &> /dev/null; then
        ip link set dev "$INTERFACE" mtu 1500
        echo "🔧 Reset MTU to 1500 for interface $INTERFACE"
    fi
fi

# Clear proxy settings if we set them
if [ -n "$http_proxy" ]; then
    unset http_proxy https_proxy no_proxy
    echo "🌐 Cleared proxy settings"
fi

# Check for network issues
if [ "$EXIT_CODE" -ne 0 ]; then
    echo "⚠️  Network application $WRAPPER_NAME exited with code $EXIT_CODE"
    
    # Test current network connectivity
    if ping -c 1 8.8.8.8 &> /dev/null; then
        echo "✅ Network connectivity is OK"
    else
        echo "❌ Network connectivity issues detected"
        
        # Log network problem
        NETWORK_LOG="$HOME/.logs/network-issues.log"
        echo "$(date '+%Y-%m-%d %H:%M:%S') | $WRAPPER_NAME | Network issue detected | Exit: $EXIT_CODE" >> "$NETWORK_LOG"
    fi
fi

# Reset DNS settings if needed
if [ "$SYSTEMD_RESOLVED" = "true" ]; then
    # Reset any custom DNS settings
    if command -v resolvectl &> /dev/null; then
        resolvectl flush-caches 2>/dev/null || true
        echo "🔄 Flushed DNS cache"
    fi
fi

echo "🌐 Network cleanup complete for $WRAPPER_NAME"
```

## Example 6: Universal Template
```bash
#!/bin/bash
# ~/scripts/universal-cleanup.sh
WRAPPER_NAME="$1"
FLATPAK_ID="$2"
TARGET_APP="$3"
EXIT_CODE="$4"
shift 4  # Remove first 4 args

# Universal cleanup script that works with any application

echo "🧹 Universal cleanup for $WRAPPER_NAME (exit: $EXIT_CODE)"

# Common cleanup tasks
CLEANUP_DIRS=(
    "/tmp/${WRAPPER_NAME}-$$"
    "/tmp/${WRAPPER_NAME}-cache-$$"
    "/tmp/${WRAPPER_NAME}-temp-$$"
)

for dir in "${CLEANUP_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        rm -rf "$dir"
        echo "✅ Removed $dir"
    fi
done

# Log all sessions
LOG_DIR="$HOME/.logs/sessions"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/all-sessions.log"

# Get session duration if we have a start time
SESSION_START_FILE="/tmp/${WRAPPER_NAME}-session-start"
if [ -f "$SESSION_START_FILE" ]; then
    SESSION_START=$(cat "$SESSION_START_FILE")
    SESSION_END=$(date +%s)
    SESSION_DURATION=$((SESSION_END - SESSION_START))
    rm -f "$SESSION_START_FILE"
else
    SESSION_DURATION=0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') | $WRAPPER_NAME | $FLATPAK_ID | $EXIT_CODE | ${SESSION_DURATION}s | $TARGET_APP" >> "$LOG_FILE"

# Handle different exit codes
case "$EXIT_CODE" in
    0)
        echo "✅ $WRAPPER_NAME completed successfully"
        ;;
    1)
        echo "⚠️  $WRAPPER_NAME exited with general error"
        ;;
    2)
        echo "⚠️  $WRAPPER_NAME exited with misuse of shell builtins"
        ;;
    130)
        echo "⚠️  $WRAPPER_NAME was terminated by Ctrl+C"
        ;;
    143)
        echo "⚠️  $WRAPPER_NAME was terminated by SIGTERM"
        ;;
    *)
        echo "❌ $WRAPPER_NAME exited with code $EXIT_CODE"
        ;;
esac

# Create summary
echo "📊 Session Summary:"
echo "  Application: $WRAPPER_NAME ($FLATPAK_ID)"
echo "  Duration: ${SESSION_DURATION}s"
echo "  Exit Code: $EXIT_CODE"
echo "  Target: $TARGET_APP"

echo "🧹 Universal cleanup complete"
```