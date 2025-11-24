#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_SCRIPT="$SCRIPT_DIR/generate_flatpak_wrappers.sh"
UNIT_DIR="$HOME/.config/systemd/user"
FLATPAK_BIN_DIR="$HOME/.local/share/flatpak/exports/bin"

# Check prerequisites
if ! command -v systemctl &> /dev/null; then
    echo "Error: systemctl not available."
    exit 1
fi

if ! command -v flatpak &> /dev/null; then
    echo "Error: Flatpak not installed."
    exit 1
fi

if [ ! -f "$WRAPPER_SCRIPT" ]; then
    echo "Error: Wrapper script not found at $WRAPPER_SCRIPT"
    exit 1
fi

mkdir -p "$UNIT_DIR"

# Create service unit
cat > "$UNIT_DIR/flatpak-wrappers.service" << EOF
[Unit]
Description=Generate Flatpak wrapper scripts

[Service]
Type=oneshot
ExecStart=$WRAPPER_SCRIPT
EOF

# Create path unit for automatic triggering
cat > "$UNIT_DIR/flatpak-wrappers.path" << EOF
[Unit]
Description=Watch for Flatpak app changes

[Path]
PathChanged=$FLATPAK_BIN_DIR
Unit=flatpak-wrappers.service

[Install]
WantedBy=default.target
EOF

# Create timer unit for periodic run
cat > "$UNIT_DIR/flatpak-wrappers.timer" << EOF
[Unit]
Description=Timer for Flatpak wrapper generation

[Timer]
OnCalendar=daily
OnBootSec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable flatpak-wrappers.path
systemctl --user start flatpak-wrappers.path
systemctl --user enable flatpak-wrappers.timer
systemctl --user start flatpak-wrappers.timer

echo "Systemd units installed and started. Wrappers will update automatically on user Flatpak changes and daily (system Flatpak changes require manual run or wait for timer)."