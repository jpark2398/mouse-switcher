#!/bin/bash

echo "🖱️ Installing Mouse Profile Switcher..."

# Define target directories
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/mouse-switcher"
APP_DIR="$HOME/.local/share/applications"

# 1. Create necessary directories
echo "📁 Setting up directories..."
mkdir -p "$BIN_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$APP_DIR"

# 2. Install Executables
echo "⚙️ Installing core scripts..."
cp mouse-switcher "$BIN_DIR/"
cp mouse-map "$BIN_DIR/"
cp mouse-switcher-gui.py "$BIN_DIR/"

# Ensure they are executable
chmod +x "$BIN_DIR/mouse-switcher"
chmod +x "$BIN_DIR/mouse-map"
chmod +x "$BIN_DIR/mouse-switcher-gui.py"

# 3. Install Config & Assets
echo "🎨 Installing configuration and assets..."

# Safely copy profiles.conf ONLY if it doesn't exist yet
if [ ! -f "$CONFIG_DIR/profiles.conf" ]; then
    cp profiles.conf "$CONFIG_DIR/"
    echo "   -> Copied default profiles.conf"
else
    echo "   -> Existing profiles.conf found, skipping to preserve settings."
fi

# Copy the hidden .icon.png and rename it to standard icon.png 
if [ -f ".icon.png" ]; then
    cp .icon.png "$CONFIG_DIR/icon.png"
    echo "   -> Installed application icon"
fi

# 4. Setup Python Virtual Environment
echo "🐍 Setting up isolated Python environment..."
# Create the venv silently
python3 -m venv "$CONFIG_DIR/venv"
# Install the UI theme into the venv safely
"$CONFIG_DIR/venv/bin/pip" install --quiet sv-ttk
echo "   -> UI theme installed successfully"

# 5. Create the Desktop Launcher
echo "🚀 Creating desktop shortcut..."
cat <<EOF > "$APP_DIR/mouse-switcher.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Mouse Switcher
Comment=Auto-switch mouse profiles based on active window
Exec=$CONFIG_DIR/venv/bin/python $BIN_DIR/mouse-switcher-gui.py
Icon=$CONFIG_DIR/icon.png
Terminal=false
Categories=Utility;Settings;HardwareSettings;
EOF

# Update the desktop database so your app launcher sees it immediately
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$APP_DIR"
fi

echo ""
echo "✅ Installation Complete!"
echo "You can now launch 'Mouse Switcher' directly from your application menu."