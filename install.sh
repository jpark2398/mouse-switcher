#!/bin/bash

echo "🖱️ Installing Mouse Profile Switcher..."

# Dependency Check
if ! command -v jq &> /dev/null; then
    echo "❌ Error: 'jq' is not installed. Please install it via your package manager (e.g., sudo pacman -S jq) and try again."
    exit 1
fi

# Define target directories
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/mouse-switcher"
APP_DIR="$HOME/.local/share/applications"

# 1. Create necessary directories
echo "📁 Setting up directories..."
mkdir -p "$BIN_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$APP_DIR"

# 2. Install Executables (Pulling from src/)
echo "⚙️ Installing core scripts..."
cp src/daemon/mouse-switcher "$BIN_DIR/"
cp src/daemon/mouse-map "$BIN_DIR/"
cp src/gui/main.py "$BIN_DIR/mouse-switcher-gui"

chmod +x "$BIN_DIR/mouse-switcher"
chmod +x "$BIN_DIR/mouse-map"
chmod +x "$BIN_DIR/mouse-switcher-gui"

# 3. Install Config & Assets
echo "🎨 Installing configuration and assets..."

if [ ! -f "$CONFIG_DIR/profiles.json" ]; then
    cp config/profiles.json "$CONFIG_DIR/"
    echo "   -> Copied default profiles.json"
else
    echo "   -> Existing profiles.json found, skipping to preserve settings."
fi

cp assets/icon.png "$CONFIG_DIR/icon.png"
echo "   -> Installed application icon"

# 4. Setup Python Virtual Environment
echo "🐍 Setting up isolated Python environment..."
python3 -m venv "$CONFIG_DIR/venv"
"$CONFIG_DIR/venv/bin/pip" install --quiet sv-ttk
echo "   -> UI theme installed successfully"

# 5. Create the Desktop Launcher
echo "🚀 Creating desktop shortcut..."
cat assets/mouse-switcher.desktop \
    | sed "s|{{PYTHON_EXEC}}|$CONFIG_DIR/venv/bin/python|g" \
    | sed "s|{{GUI_EXEC}}|$BIN_DIR/mouse-switcher-gui|g" \
    | sed "s|{{ICON_PATH}}|$CONFIG_DIR/icon.png|g" \
    > "$APP_DIR/mouse-switcher.desktop"

if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$APP_DIR"
fi

echo ""
echo "✅ Installation Complete! You can now launch 'Mouse Switcher' from your application menu."