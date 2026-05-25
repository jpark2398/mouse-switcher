#!/bin/bash

BIN_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
CONFIG_DIR="$HOME/.config/mouse-switcher"
CONFIG_FILE="$CONFIG_DIR/profiles.conf"
PRESET_DIR="$HOME/.config/input-remapper-2/presets"

echo "Installing Mouse Profile Switcher..."
mkdir -p "$BIN_DIR" "$AUTOSTART_DIR" "$CONFIG_DIR"

get_device_hash() {
    local dev_name="$1"
    local json_file=$(ls "$PRESET_DIR/$dev_name"/*.json 2>/dev/null | head -n 1)
    if [ -n "$json_file" ]; then
        grep -Eo '\b[a-f0-9]{32}\b' "$json_file" | head -n 1
    fi
}

echo ""
echo "Scanning Input Remapper preset folders for known devices..."
if [ ! -d "$PRESET_DIR" ]; then
    echo "❌ Error: Could not find $PRESET_DIR."
    exit 1
fi

mapfile -t devices < <(find "$PRESET_DIR" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)

if [ ${#devices[@]} -eq 0 ]; then
    echo "❌ Error: No device folders found in input-remapper!"
    exit 1
fi

echo "Configured Devices:"
for i in "${!devices[@]}"; do
    echo "$((i+1)). ${devices[$i]}"
done
echo ""

read -p "Enter the numbers of the devices you want synced and managed (comma-separated, e.g. 1,2): " selections

declare -A new_devices
IFS=',' read -r -a sel_array <<< "$selections"

for num in "${sel_array[@]}"; do
    num=$(echo "$num" | xargs) # trim whitespace
    if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -le "${#devices[@]}" ] && [ "$num" -ge 1 ]; then
        dev_name="${devices[$((num-1))]}"
        dev_hash=$(get_device_hash "$dev_name")
        if [ -n "$dev_hash" ]; then
            new_devices["$dev_name"]="$dev_hash"
        else
            echo "⚠️  Warning: Could not find a hash for '$dev_name' (needs at least 1 json file). Skipping."
        fi
    fi
done

if [ ${#new_devices[@]} -eq 0 ]; then
    echo "❌ Error: No valid devices selected. Aborting."
    exit 1
fi

# Extract existing mappings (if any) to preserve them
EXISTING_MAPPINGS="default=Default"
if [ -f "$CONFIG_FILE" ]; then
    extracted=$(sed -n '/^\[Mappings\]/,$p' "$CONFIG_FILE" | grep -v "^\[Mappings\]" | grep -v "^$")
    if [ -n "$extracted" ]; then
        EXISTING_MAPPINGS="$extracted"
    fi
fi

# Write the clean INI configuration
tmp=$(mktemp)
echo "[Devices]" > "$tmp"
for dev in "${!new_devices[@]}"; do
    echo "$dev=${new_devices[$dev]}" >> "$tmp"
done
echo "" >> "$tmp"
echo "[Mappings]" >> "$tmp"
echo "$EXISTING_MAPPINGS" >> "$tmp"

mv "$tmp" "$CONFIG_FILE"
echo ""
echo "✅ Devices and Mappings successfully written to $CONFIG_FILE"

# Install files
cp ./mouse-switcher "$BIN_DIR/"
cp ./mouse-map "$BIN_DIR/"
chmod +x "$BIN_DIR/mouse-switcher"
chmod +x "$BIN_DIR/mouse-map"

cat <<EOF > "$AUTOSTART_DIR/mouse-switcher.desktop"
[Desktop Entry]
Type=Application
Exec=$BIN_DIR/mouse-switcher
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Mouse Profile Switcher
Comment=Automatically switch input-remapper profiles based on active window
EOF

echo "✅ Installation complete!"
echo "To restart the background service, run: pkill -f mouse-switcher; $BIN_DIR/mouse-switcher &"
