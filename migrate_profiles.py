import os
import json
import shutil

CONFIG_FILE = os.path.expanduser("~/.config/mouse-switcher/profiles.json")
BACKUP_FILE = os.path.expanduser("~/.config/mouse-switcher/profiles.json.bak")

def migrate():
    if not os.path.exists(CONFIG_FILE):
        print("❌ Error: profiles.json not found. Nothing to migrate.")
        return

    # 1. Create a backup
    shutil.copy2(CONFIG_FILE, BACKUP_FILE)
    print(f"✅ Created backup at: {BACKUP_FILE}")

    # 2. Load the data
    with open(CONFIG_FILE, 'r') as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            print("❌ Error: profiles.json is corrupt and cannot be read.")
            return

    needs_save = False

    # 3. Perform the migration
    for group_name, group_data in config.get("sync_groups", {}).items():
        
        # --- A. Migrate Mappings (String -> List) ---
        mappings = group_data.get("mappings", {})
        new_mappings = {}
        for k, v in mappings.items():
            if isinstance(v, str):
                needs_save = True
                if v not in new_mappings:
                    new_mappings[v] = []
                new_mappings[v].append(k)
            elif isinstance(v, list):
                new_mappings[k] = v
        group_data["mappings"] = new_mappings
        
        # --- B. Migrate Devices (Name:Hash OR Hash:Dict -> VID:PID:Dict) ---
        devices = group_data.get("devices", {})
        new_devices = {}
        
        for key, value in devices.items():
            needs_save = True
            
            # Scenario 1: Oldest Format (DevName : Hash)
            if isinstance(value, str):
                new_devices["unknown_vid_pid"] = {
                    "dev_name": key,
                    "friendly_name": key,
                    "hash": value
                }
            
            # Scenario 2: Intermediate Format (Hash : {Data})
            elif isinstance(value, dict):
                if "vendor_product" in value:
                    vid_pid = value.get("vendor_product", "unknown_vid_pid")
                    new_devices[vid_pid] = {
                        "dev_name": value.get("dev_name", key),
                        "friendly_name": value.get("friendly_name", value.get("dev_name", key)),
                        "hash": key
                    }
                else:
                    # Scenario 3: Already correct format
                    new_devices[key] = value
                    needs_save = False 
                    
        group_data["devices"] = new_devices

    # 4. Save the updated config
    if needs_save:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print("🎉 Migration complete! Your profiles.json is now updated to the final schema.")
    else:
        print("ℹ️ No migration needed. The file is already using the new schema.")

if __name__ == "__main__":
    print("Mouse Switcher Schema Migration Tool")
    print("-" * 36)
    migrate()