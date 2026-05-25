#!/bin/bash

echo "🗑️  Uninstalling Mouse Profile Switcher..."

# Define target directories
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/mouse-switcher"
APP_DIR="$HOME/.local/share/applications"
LOG_FILE="$HOME/.mouse-switcher.log"

# 1. Stop any running instances
echo "🛑 Stopping background services..."
pkill -f 'bin/mouse-switcher' 2>/dev/null
sleep 0.5

# 2. Remove Executables
echo "🧹 Removing core scripts..."
rm -f "$BIN_DIR/mouse-switcher"
rm -f "$BIN_DIR/mouse-map"
rm -f "$BIN_DIR/mouse-switcher-gui"

# 3. Remove Desktop Shortcut
echo "🚀 Removing desktop integration..."
rm -f "$APP_DIR/mouse-switcher.desktop"

# Refresh the application menu so the icon disappears immediately
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$APP_DIR"
fi

# 4. Handle Configuration & Logs
echo ""
read -p "❓ Do you want to delete your saved profiles and configuration files? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔥 Wiping configuration and Python environment..."
    rm -rf "$CONFIG_DIR"
    rm -f "$LOG_FILE"
    echo "   -> Configs and logs removed."
else
    echo "🛡️  Preserving configuration folder: $CONFIG_DIR"
fi

echo ""
echo "✅ Uninstallation Complete!"
echo "Note: The system dependency 'input-remapper' was not removed. You can remove it via your package manager if you no longer need it."