import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sv_ttk
import configparser
import os
import subprocess
import time
import threading
import tempfile
import json

CONFIG_DIR = os.path.expanduser("~/.config/mouse-switcher")
CONFIG_FILE = os.path.join(CONFIG_DIR, "profiles.conf")
LOG_FILE = os.path.expanduser("~/.mouse-switcher.log")

class MouseSwitcherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mouse Profile Switcher")
        self.geometry("800x600")
        sv_ttk.set_theme("dark")

        icon_path = os.path.expanduser("~/.config/mouse-switcher/icon.png")
        if os.path.exists(icon_path):
            try:
                icon = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, icon)
            except Exception as e:
                print(f"Failed to load icon: {e}")

        # Load Config
        self.config = configparser.ConfigParser()
        self.config.optionxform = str # Preserve case sensitivity
        self.load_config()

        self.create_widgets()

    def load_config(self):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        if not os.path.exists(CONFIG_FILE):
            # Create default structure if missing
            self.config['Devices'] = {}
            self.config['Mappings'] = {'default': 'Default'}
            with open(CONFIG_FILE, 'w') as f:
                self.config.write(f)
        self.config.read(CONFIG_FILE)

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            self.config.write(f)

    def create_widgets(self):
        # 1. Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(header_frame, text="🖱️ Mouse Profile Switcher", font=("Segoe UI Variable Display", 18, "bold")).pack(side="left")
        
        # 2. Right-Aligned Header Controls
        header_right = ttk.Frame(header_frame)
        header_right.pack(side="right")

        self.active_badge = ttk.Label(header_right, text="🎯 Active: Scanning...", font=("", 12, "bold"), foreground="#0078d4")
        self.active_badge.pack(side="left", padx=(0, 20))

        # We create the button, but we DO NOT pack it yet!
        self.remove_override_btn = ttk.Button(header_right, text="❌ Remove Override", command=self.remove_override)

        self.status_btn = ttk.Button(header_right, text="🟢 Service Running")
        self.status_btn.pack(side="left")

        # 3. Main Notebook (Tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # 4. Build Tabs
        self.build_mappings_tab()
        self.build_devices_tab()
        self.build_editor_tab()
        self.build_logs_tab()

    # --- TAB 1: MAPPINGS ---
    def build_mappings_tab(self):
        frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(frame, text=" Game Mappings ")

        columns = ("Window Class", "Preset Name")
        self.map_tree = ttk.Treeview(frame, columns=columns, show="headings", height=10)
        self.map_tree.heading("Window Class", text="Window Class")
        self.map_tree.heading("Preset Name", text="Preset Name")
        self.map_tree.column("Window Class", width=350)
        self.map_tree.column("Preset Name", width=250)
        self.map_tree.pack(fill="both", expand=True, pady=(0, 15))

        self.refresh_mappings_list()

        controls = ttk.Frame(frame)
        controls.pack(fill="x")

        self.capture_btn = ttk.Button(controls, text="🎯 Capture Active Window (3s delay)", style="Accent.TButton", command=self.capture_window)
        self.capture_btn.pack(side="left", padx=(0, 10))
        
        ttk.Button(controls, text="🗑️ Delete Selected", command=self.delete_mapping).pack(side="right")

    def refresh_mappings_list(self):
        for item in self.map_tree.get_children():
            self.map_tree.delete(item)
        if 'Mappings' in self.config:
            for win_class, preset in self.config['Mappings'].items():
                self.map_tree.insert("", tk.END, values=(win_class, preset))

    def capture_window(self):
        self.capture_btn.config(text="Capturing in 3...", state="disabled")
        
        def capture_thread():
            time.sleep(1)
            self.capture_btn.config(text="Capturing in 2...")
            time.sleep(1)
            self.capture_btn.config(text="Capturing in 1...")
            time.sleep(1)
            self.capture_btn.config(text="Capturing!")
            
            try:
                # Try kdotool (Wayland) or xdotool (X11)
                cmd = "kdotool getactivewindow getwindowclassname" if "wayland" in os.environ.get("WAYLAND_DISPLAY", "").lower() or subprocess.run("command -v kdotool", shell=True, capture_output=True).returncode == 0 else "xdotool getactivewindow getwindowclassname"
                win_class = subprocess.check_output(cmd, shell=True, text=True).strip()
                
                # Ask user for preset name back on the main thread
                self.after(0, self.prompt_preset, win_class)
            except Exception as e:
                self.after(0, messagebox.showerror, "Capture Failed", f"Could not detect window.\n{e}")
            finally:
                self.after(0, lambda: self.capture_btn.config(text="🎯 Capture Active Window (3s delay)", state="normal"))

        threading.Thread(target=capture_thread, daemon=True).start()

    def prompt_preset(self, win_class):
        if not win_class:
            return
        preset = simpledialog.askstring("Preset Name", f"Detected Window: {win_class}\n\nEnter the exact Input Remapper preset name for this game:")
        if preset:
            if 'Mappings' not in self.config:
                self.config['Mappings'] = {}
            self.config['Mappings'][win_class] = preset
            self.save_config()
            self.refresh_mappings_list()
            self.refresh_editor_dropdown()

    def delete_mapping(self):
        selected = self.map_tree.selection()
        if not selected: return
        
        item = self.map_tree.item(selected[0])
        win_class = item['values'][0]
        
        if win_class == 'default':
            messagebox.showwarning("Warning", "You shouldn't delete the default fallback profile!")
            return

        del self.config['Mappings'][win_class]
        self.save_config()
        self.refresh_mappings_list()

    # --- TAB 2: DEVICES ---
    def build_devices_tab(self):
        frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(frame, text=" Devices & Sync ")

        ttk.Label(frame, text="Devices in this list automatically sync their presets with each other.", foreground="gray").pack(anchor="w", pady=(0, 10))

        columns = ("Device Name", "Hardware Hash")
        self.dev_tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        self.dev_tree.heading("Device Name", text="Device Name")
        self.dev_tree.heading("Hardware Hash", text="Hardware Hash (MD5)")
        self.dev_tree.column("Device Name", width=300)
        self.dev_tree.column("Hardware Hash", width=300)
        self.dev_tree.pack(fill="both", expand=True, pady=(0, 15))

        self.refresh_devices_list()

        controls = ttk.Frame(frame)
        controls.pack(fill="x")
        self.scan_btn = ttk.Button(controls, text="🔍 Scan Connected Devices", style="Accent.TButton", command=self.scan_devices)
        self.scan_btn.pack(side="left", padx=(0, 10))

    def refresh_devices_list(self):
        for item in self.dev_tree.get_children():
            self.dev_tree.delete(item)
        if 'Devices' in self.config:
            for dev_name, dev_hash in self.config['Devices'].items():
                self.dev_tree.insert("", tk.END, values=(dev_name, dev_hash))

    def scan_devices(self):
        # Change button state so the user knows it's working
        self.scan_btn.config(text="Waiting for Authentication...", state="disabled")
        self.update_idletasks()

        # 1. Generate the payload script
        payload = """import sys, json, hashlib
try:
    import evdev
except ImportError:
    print("ERROR: evdev not installed. Please run: sudo pacman -S python-evdev")
    sys.exit(1)

devices = {}
for path in evdev.list_devices():
    try:
        dev = evdev.InputDevice(path)
        phys_path = dev.phys.split("/")[0] if dev.phys else "-"
        hardware_key = f"{dev.info.bustype}_{dev.info.vendor}_{dev.info.product}_{phys_path}"
        hash_md5 = hashlib.md5(hardware_key.encode('utf-8')).hexdigest()
        
        # Filter out random motherboard sensors; keep likely mice/keyboards
        if "Razer" in dev.name or "Keyboard" in dev.name or "Mouse" in dev.name:
            devices[dev.name] = hash_md5
    except Exception:
        pass
print(json.dumps(devices))
"""
        # 2. Save it to a secure temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(payload)
            temp_path = f.name

        def execute_scan():
            try:
                # 3. Execute via PolicyKit
                result = subprocess.run(["pkexec", "python3", temp_path], capture_output=True, text=True)
                
                if result.returncode == 0:
                    scanned_devices = json.loads(result.stdout)
                    self.after(0, self.prompt_device_selection, scanned_devices)
                else:
                    if "ERROR" in result.stdout:
                        self.after(0, messagebox.showerror, "Dependency Missing", result.stdout)
                    else:
                        self.after(0, messagebox.showerror, "Scan Failed", "Authentication cancelled or failed.")
            finally:
                # 4. Clean up the temp file and restore button
                os.remove(temp_path)
                self.after(0, lambda: self.scan_btn.config(text="🔍 Scan Connected Devices", state="normal"))

        # Run the pkexec block in a thread so it doesn't freeze the GUI while waiting for the password!
        threading.Thread(target=execute_scan, daemon=True).start()

    def prompt_device_selection(self, devices):
        if not devices:
            messagebox.showinfo("No Devices", "No supported input devices found.")
            return

        # Create a popup window
        popup = tk.Toplevel(self)
        popup.title("Select Hardware")
        popup.geometry("400x300")
        popup.transient(self) # Keep on top of main window
        popup.grab_set()      # Block main window interactions

        ttk.Label(popup, text="Select a device to add to your Sync Swarm:", font=("", 10, "bold")).pack(pady=10)

        # Build a Listbox with the scanned devices
        listbox = tk.Listbox(popup, bg="#2b2b2b", fg="#ffffff", selectbackground="#0078d4", font=("", 10))
        listbox.pack(fill="both", expand=True, padx=10, pady=5)

        device_names = list(devices.keys())
        for name in device_names:
            listbox.insert(tk.END, name)

        def on_add():
            selected_idx = listbox.curselection()
            if not selected_idx: return
            
            dev_name = device_names[selected_idx[0]]
            dev_hash = devices[dev_name]

            # Save to configuration
            if 'Devices' not in self.config:
                self.config['Devices'] = {}
            
            self.config['Devices'][dev_name] = dev_hash
            self.save_config()
            self.refresh_devices_list()
            popup.destroy()

        controls = ttk.Frame(popup)
        controls.pack(fill="x", pady=10)
        ttk.Button(controls, text="Add to Swarm", style="Accent.TButton", command=on_add).pack(side="right", padx=10)
        ttk.Button(controls, text="Cancel", command=popup.destroy).pack(side="right")

    # --- TAB 3: PROFILE EDITOR (3x4 MMO GRID) ---
    def build_editor_tab(self):
        frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(frame, text=" 🎮 Profile Editor ")

        # --- Data State ---
        self.current_preset_data = {}
        self.current_json_path = ""
        self.selected_hw_id = ""
        self.selected_btn_name = ""

        # Map the 12 side buttons to their evdev hardware IDs
        # (Update these if input-remapper shows different IDs for your specific Naga)
        self.NAGA_MAP = {
            "1": 2,   # KEY_1
            "2": 3,   # KEY_2
            "3": 4,   # KEY_3
            "4": 5,   # KEY_4
            "5": 6,   # KEY_5
            "6": 7,   # KEY_6
            "7": 8,   # KEY_7
            "8": 9,   # KEY_8
            "9": 10,  # KEY_9
            "10": 11, # KEY_0
            "11": 12, # KEY_MINUS (-)
            "12": 13  # KEY_EQUAL (=)
        }

        # Left side: The Grid
        grid_frame = ttk.LabelFrame(frame, text=" MMO Side Panel ", padding=20)
        grid_frame.pack(side="left", fill="y", padx=(0, 20))

        self.grid_buttons = {}
        btn_count = 1
        self.grid_buttons = {}
        btn_count = 1
        for row in range(4):
            for col in range(3):
                btn_name = str(btn_count)
                hw_id = self.NAGA_MAP.get(btn_name)
                
                # Switch to a standard tk.Button for strict color and alignment control
                btn = tk.Button(
                    grid_frame, 
                    text=btn_name,
                    width=8, height=3,           # Fixed tile size
                    relief="flat", bd=0,         # Remove standard 3D borders
                    highlightthickness=2,        # Enable the custom color ring
                    justify="center",            # Centers multi-line text perfectly
                    font=("", 10, "bold"),
                    cursor="hand2"
                )
                
                btn.config(command=lambda n=btn_name, h=hw_id: self.select_grid_button(n, h))
                btn.grid(row=row, column=col, padx=4, pady=4)
                
                self.grid_buttons[btn_name] = btn
                btn_count += 1

        # Right side: Configurator
        config_frame = ttk.Frame(frame)
        config_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(config_frame, text="Target Preset:", foreground="gray").pack(anchor="w")
        
        # We will populate this combobox dynamically based on your Mappings
        preset_row = ttk.Frame(config_frame)
        preset_row.pack(fill="x", pady=(0, 20))

        self.preset_combo = ttk.Combobox(preset_row, state="readonly")
        self.preset_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.preset_combo.bind("<<ComboboxSelected>>", self.load_preset_json)

        # Pack these to the right. (The first one packed goes furthest right)
        ttk.Button(preset_row, text="🚀 Apply Now", command=self.manual_apply_profile).pack(side="right")

        self.btn_label = ttk.Label(config_frame, text="Select a button on the grid...", font=("", 12, "bold"))
        self.btn_label.pack(anchor="w", pady=(0, 20))

        ttk.Label(config_frame, text="Output Action:").pack(anchor="w")
        self.action_entry = ttk.Entry(config_frame)
        self.action_entry.pack(fill="x", pady=(0, 5))
        
        self.listen_btn = ttk.Button(config_frame, text="🟢 Listen for Keystroke", style="Accent.TButton", command=self.start_listen)
        self.listen_btn.pack(anchor="w", pady=(0, 20))

        ttk.Button(config_frame, text="💾 Save to JSON", command=self.save_preset_json).pack(side="bottom", anchor="e")

        # Initialize the dropdown with presets from the config
        self.refresh_editor_dropdown()

    def refresh_editor_dropdown(self):
        """Pulls the unique preset names from the Mappings config and sorts them."""
        if 'Mappings' in self.config:
            # We added sorted() here to alphabetize the list!
            presets = sorted(list(set(self.config['Mappings'].values())))
            
            self.preset_combo['values'] = presets
            if presets:
                self.preset_combo.set(presets[0])
                self.load_preset_json()

    def format_key_label(self, action_string):
        """Translates 'key(KEY_LEFTCTRL)' or 'macro(KEY_LEFTCTRL, KEY_C)' into 'CTRL+C'"""
        # Strip out the wrapper functions
        clean = action_string.replace("key(", "").replace("macro(", "").replace(")", "")
        
        # Strip out the KEY_ prefix
        clean = clean.replace("KEY_", "")
        
        # Replace complex kernel names with clean keyboard names
        replacements = {
            "LEFTCTRL": "CTRL", "RIGHTCTRL": "CTRL",
            "LEFTSHIFT": "SHIFT", "RIGHTSHIFT": "SHIFT",
            "Alt_L": "ALT", "Alt_R": "ALT",
            "LEFTMETA": "WIN", "RIGHTMETA": "WIN",
            "SPACE": "SPC", "ENTER": "ENT", "RETURN": "ENT",
            "ESCAPE": "ESC", "SEMICOLON": ";", "COMMA": ",", "period": ".", "MINUS": "-", "EQUAL": "=",
            ", ": "+"  # This connects macros like "CTRL, C" into "CTRL+C"
        }
        
        for old, new in replacements.items():
            clean = clean.replace(old, new)
            
        return clean

    def refresh_grid_visuals(self):
        """Updates the colors and text of the 3x4 grid based on current mappings."""
        mapped_codes = {}
        for mapping in self.current_preset_data:
            combos = mapping.get("input_combination", [])
            for combo in combos:
                if combo.get("type") == 1:
                    mapped_codes[combo.get("code")] = mapping.get("output_symbol", "Mapped")

        for btn_name, btn in self.grid_buttons.items():
            hw_id = self.NAGA_MAP.get(btn_name)
            
            # --- NEW: Determine the outline color based on selection state ---
            is_selected = getattr(self, 'selected_btn_name', "") == btn_name
            
            if is_selected:
                outline_color = "#0078d4"      # Bright Blue (Active Selection)
            elif hw_id in mapped_codes:
                outline_color = "#1e5c2b"      # Dark Green (Mapped, but not selected)
            else:
                outline_color = "#2b2b2b"      # Invisible (Empty, not selected)

            # Apply the text and the dynamic outline color
            if hw_id in mapped_codes:
                raw_action = mapped_codes[hw_id]
                display_action = self.format_key_label(raw_action)
                
                if len(display_action) > 9:
                    display_action = display_action[:7] + ".." 
                    
                btn.config(
                    text=f"{btn_name}\n[{display_action}]", 
                    bg="#2b2b2b",                  
                    fg="#ffffff",                  
                    activebackground="#3b3b3b",    
                    highlightbackground=outline_color, 
                    highlightcolor=outline_color       
                )
            else:
                btn.config(
                    text=f"{btn_name}\n ", 
                    bg="#2b2b2b",                  
                    fg="#666666",                  
                    activebackground="#3b3b3b",    
                    highlightbackground=outline_color, 
                    highlightcolor=outline_color
                )

    def load_preset_json(self, event=None):
        """Loads the JSON file for the selected preset."""
        preset_name = self.preset_combo.get()
        if not preset_name or 'Devices' not in self.config: 
            return

        # Grab the first managed device to use as the source folder
        devices = list(self.config['Devices'].keys())
        if not devices: return
        target_device = devices[0]

        # Save the origin hash for mapping creation later
        self.current_origin_hash = self.config['Devices'][target_device]
        
        self.current_json_path = os.path.expanduser(f"~/.config/input-remapper-2/presets/{target_device}/{preset_name}.json")

        if os.path.exists(self.current_json_path):
            import json
            with open(self.current_json_path, 'r') as f:
                data = json.load(f)
                # input-remapper v2 saves presets as a LIST of mapping objects
                self.current_preset_data = data if isinstance(data, list) else []
        else:
            self.current_preset_data = []

        # Refresh the UI if a button is already selected
        if self.selected_hw_id:
            self.select_grid_button(self.selected_btn_name, self.selected_hw_id)

        self.refresh_grid_visuals()

    def select_grid_button(self, btn_name, hw_id):
        """Updates the configurator panel when a grid button is clicked."""
        self.selected_btn_name = btn_name
        self.selected_hw_id = hw_id
        
        self.btn_label.config(text=f"Button {btn_name} (Hardware Code: {hw_id})")
        
        # Look up the existing mapping in the loaded JSON list
        self.action_entry.delete(0, tk.END)

        self.refresh_grid_visuals()
        
        for mapping in self.current_preset_data:
            combos = mapping.get("input_combination", [])
            for combo in combos:
                # Type 1 is EV_KEY. We check if the code matches our hardware ID.
                if combo.get("type") == 1 and combo.get("code") == hw_id:
                    self.action_entry.insert(0, mapping.get("output_symbol", ""))
                    return

    def start_listen(self):
        """Captures the next physical key press on the keyboard."""
        self.listen_btn.config(text="Press any key...", state="disabled")
        
        # Bind a global key press event to the whole window
        self.bind("<KeyPress>", self.capture_key)

    def capture_key(self, event):
        """Translates the tk key event into an input-remapper string."""
        self.unbind("<KeyPress>") # Stop listening immediately
        
        # Convert standard Tkinter key names to Linux KEY_ names
        key_sym = event.keysym.upper()
        special_keys = {
            "SPACE": "KEY_SPACE", "RETURN": "KEY_ENTER", 
            "ESCAPE": "KEY_ESC", "MINUS": "KEY_MINUS",
            "EQUAL": "KEY_EQUAL", "SHIFT_L": "KEY_LEFTSHIFT",
            "CONTROL_L": "KEY_LEFTCTRL", "ALT_L": "KEY_LEFTALT"
        }
        
        out_key = special_keys.get(key_sym, f"KEY_{key_sym}")
        
        self.action_entry.delete(0, tk.END)
        self.action_entry.insert(0, f"key({out_key})")
        
        self.listen_btn.config(text="🟢 Listen for Keystroke", state="normal")

    def save_preset_json(self):
        """Writes the updated mapping back to the JSON list."""
        if not self.selected_hw_id or not self.current_json_path:
            messagebox.showwarning("Error", "Please select a preset and a button first.")
            return

        new_action = self.action_entry.get().strip()
        
        # First, safely remove any existing mapping for this specific code
        # We iterate backward so we can safely delete from the list without skipping elements
        for i in range(len(self.current_preset_data) - 1, -1, -1):
            mapping = self.current_preset_data[i]
            combos = mapping.get("input_combination", [])
            
            # Keep only the inputs that ARE NOT our selected button
            new_combos = [c for c in combos if not (c.get("type") == 1 and c.get("code") == self.selected_hw_id)]
            
            if not new_combos:
                # If removing our button leaves this mapping with no triggers, delete it completely
                del self.current_preset_data[i]
            else:
                mapping["input_combination"] = new_combos

        # If the user typed an action, create a new V2 mapping block
        if new_action:
            new_mapping = {
                "input_combination": [
                    {
                        "type": 1,
                        "code": self.selected_hw_id,
                        "origin_hash": getattr(self, 'current_origin_hash', "")
                    }
                ],
                "target_uinput": "keyboard",
                "output_symbol": new_action,
                "mapping_type": "key_macro",
                "name": f"Button {self.selected_btn_name}"
            }
            self.current_preset_data.append(new_mapping)

        import json
        os.makedirs(os.path.dirname(self.current_json_path), exist_ok=True)
        
        with open(self.current_json_path, 'w') as f:
            json.dump(self.current_preset_data, f, indent=4)

        self.refresh_grid_visuals()
            
        messagebox.showinfo("Saved", f"Profile '{self.preset_combo.get()}' updated!")

    def manual_apply_profile(self):
        """Forces input-remapper to apply the currently selected preset."""
        preset = self.preset_combo.get()
        if not preset: return
        
        if 'Devices' not in self.config or not self.config['Devices']:
            messagebox.showwarning("No Devices", "You haven't added any devices to the Sync Swarm yet.")
            return

        def apply_thread():
            success = False
            # Loop through your managed swarm and try to apply it
            for dev in self.config['Devices'].keys():
                cmd = ["input-remapper-control", "--command", "start", "--device", dev, "--preset", preset]
                try:
                    # Run the command and suppress the chatty terminal output
                    subprocess.run(cmd, check=True, capture_output=True)
                    success = True
                except subprocess.CalledProcessError:
                    pass # Fails cleanly if that specific device is currently unplugged
            
            if success:
                # Update the tiny state file so your GUI's active badge updates immediately!
                state_file = os.path.expanduser("~/.config/mouse-switcher/active.state")
                with open(state_file, "w") as sf:
                    sf.write(f"{preset} (Manual)")
                    
                self.after(0, messagebox.showinfo, "Success", f"Profile '{preset}' injected into active devices!")
            else:
                self.after(0, messagebox.showerror, "Error", "Failed to apply profile. Are your devices plugged in?")

        # Run in a thread so the GUI doesn't freeze while talking to D-Bus
        threading.Thread(target=apply_thread, daemon=True).start()

    def remove_override(self):
        """Removes the manual override and hands control back to the auto-switcher."""
        state_file = os.path.expanduser("~/.config/mouse-switcher/active.state")
        with open(state_file, "w") as sf:
            sf.write("Resuming Auto-Switch...")
            
        script_path = os.path.expanduser("~/.local/bin/mouse-switcher")
        
        # Kill, wait, and spawn cleanly
        subprocess.run(["pkill", "-f", "bin/mouse-switcher"])
        time.sleep(0.5)
        subprocess.Popen(["bash", script_path], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # --- TAB 4: DAEMON & LOGS ---
    def build_logs_tab(self):
        frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(frame, text=" Daemon Status ")

        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(0, 10))

        ttk.Button(controls, text="🔄 Restart Background Service", style="Accent.TButton", command=self.restart_daemon).pack(side="left", padx=(0, 10))
        ttk.Button(controls, text="⏹️ Stop Service", command=self.stop_daemon).pack(side="left")

        self.log_text = tk.Text(frame, height=15, bg="#1e1e1e", fg="#cccccc", font=("Consolas", 10), borderwidth=0)
        self.log_text.pack(fill="both", expand=True)
        
        self.update_logs()

    def update_logs(self):
        # 1. Update the log text box
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                logs = f.read()
                
            self.log_text.config(state="normal")
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, logs)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")

        # --- NEW: Check if the background bash script is actually running ---
        # pgrep returns 0 if a matching process is found, 1 if it is dead.
        check_proc = subprocess.run(["pgrep", "-f", "bin/mouse-switcher"], capture_output=True)
        is_running = (check_proc.returncode == 0)

        if is_running:
            # Service is Alive
            self.status_btn.config(text="🟢 Service Running")
            
            # 2. Update the Active Badge
            state_file = os.path.expanduser("~/.config/mouse-switcher/active.state")
            if os.path.exists(state_file):
                with open(state_file, "r") as sf:
                    active_preset = sf.read().strip()
                self.active_badge.config(text=f"🎯 Active: {active_preset}")

                # Dynamic Override Button Logic
                if "(Manual)" in active_preset and not self.remove_override_btn.winfo_ismapped():
                    self.remove_override_btn.pack(side="left", padx=(0, 10), before=self.status_btn)
                elif "(Manual)" not in active_preset and self.remove_override_btn.winfo_ismapped():
                    self.remove_override_btn.pack_forget()
        else:
            # Service is Dead
            self.status_btn.config(text="🔴 Service Stopped")
            self.active_badge.config(text="🎯 Active: Offline")
            
            # Hide the override button if the service isn't running to accept it
            if self.remove_override_btn.winfo_ismapped():
                self.remove_override_btn.pack_forget()
        
        self.after(2000, self.update_logs)

    def restart_daemon(self):
        script_path = os.path.expanduser("~/.local/bin/mouse-switcher")
        
        # 1. Send the kill signal
        subprocess.run(["pkill", "-f", "bin/mouse-switcher"])
        
        # 2. Wait exactly half a second for Linux to clear the process
        time.sleep(0.5)
        
        # 3. Explicitly use 'bash' to run it, bypassing any permission errors
        subprocess.Popen(["bash", script_path], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        messagebox.showinfo("Restarted", "The background daemon has been restarted!")

    def stop_daemon(self):
        subprocess.run(["pkill", "-f", "bin/mouse-switcher"])
        messagebox.showinfo("Stopped", "The background daemon has been stopped.")

if __name__ == "__main__":
    app = MouseSwitcherApp()
    app.mainloop()