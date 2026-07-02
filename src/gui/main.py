import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sv_ttk
import os
import subprocess
import time
import threading
import tempfile
import json

CONFIG_DIR = os.path.expanduser("~/.config/mouse-switcher")
CONFIG_FILE = os.path.join(CONFIG_DIR, "profiles.json")
LOG_FILE = os.path.expanduser("~/.mouse-switcher.log")

class MouseSwitcherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mouse Profile Switcher")
        self.geometry("900x650")
        sv_ttk.set_theme("dark")

        icon_path = os.path.expanduser("~/.config/mouse-switcher/icon.png")
        if os.path.exists(icon_path):
            try:
                icon = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, icon)
            except Exception as e:
                print(f"Failed to load icon: {e}")

        self.config = {}
        self.group_var = tk.StringVar()

        self.load_config()
        self.create_widgets()
        
        # Initialize the global state
        self.update_group_dropdown()

    def load_config(self):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        
        # Initialize default JSON structure if missing or corrupt
        if not os.path.exists(CONFIG_FILE):
            self.config = {
                "sync_groups": {
                    "Desktop Gaming": {
                        "devices": {},
                        "mappings": {"Default": ["default"]}
                    }
                }
            }
            self.save_config()
        else:
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                    
                # Schema Migration (legacy check)
                needs_save = False
                for group_name, group_data in self.config.get("sync_groups", {}).items():
                    mappings = group_data.get("mappings", {})
                    new_mappings = {}
                    for k, v in mappings.items():
                        if isinstance(v, str):  # Old Format
                            needs_save = True
                            if v not in new_mappings:
                                new_mappings[v] = []
                            new_mappings[v].append(k)
                        elif isinstance(v, list): # New Format
                            new_mappings[k] = v
                    if needs_save:
                        group_data["mappings"] = new_mappings
                        
                if needs_save:
                    self.save_config()
                    
            except json.JSONDecodeError:
                messagebox.showerror("Error", "profiles.json is corrupt. Backing up and resetting.")
                os.rename(CONFIG_FILE, CONFIG_FILE + ".bak")
                self.load_config()

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def create_widgets(self):
        # 1. Header (Top)
        header_frame = ttk.Frame(self)
        header_frame.pack(side="top", fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(header_frame, text="🖱️ Mouse Switcher", font=("Segoe UI Variable Display", 18, "bold")).pack(side="left")
        
        # Global Sync Group Selector (Pushed to the right)
        sync_frame = ttk.Frame(header_frame)
        sync_frame.pack(side="right")
        ttk.Label(sync_frame, text="Active Sync Group:").pack(side="left", padx=(0, 5))
        
        self.group_combo = ttk.Combobox(sync_frame, textvariable=self.group_var, state="readonly", width=20)
        self.group_combo.pack(side="left")
        self.group_combo.bind("<<ComboboxSelected>>", self.on_group_changed)

        # 2. Footer (Status Bar at the Bottom)
        footer_frame = ttk.Frame(self)
        footer_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 15))

        # Bottom Left: Active Profile
        self.active_badge = ttk.Label(footer_frame, text="🎯 Active: Scanning...", font=("", 12, "bold"), foreground="#0078d4")
        self.active_badge.pack(side="left")

        self.remove_override_btn = ttk.Button(footer_frame, text="❌ Remove Override", command=self.remove_override)

        # Bottom Right: Service Status
        self.status_btn = ttk.Button(footer_frame, text="🟢 Service Running")
        self.status_btn.pack(side="right")

        # 3. Main Notebook (Tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 15))

        # 4. Build Tabs (Now merged down to 3 tabs)
        self.build_editor_tab()
        self.build_devices_tab()
        self.build_logs_tab()

    def update_group_dropdown(self):
        groups = list(self.config.get("sync_groups", {}).keys())
        self.group_combo['values'] = groups
        
        if groups:
            if self.group_var.get() not in groups:
                self.group_var.set(groups[0])
        else:
            self.group_var.set("")
            
        self.on_group_changed()

    def on_group_changed(self, event=None):
        """Fired when the global Sync Group is changed."""
        self.refresh_devices_list()
        self.refresh_editor_dropdown()

    # --- TAB 1: PROFILE EDITOR & MAPPINGS ---
    def build_editor_tab(self):
        frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(frame, text=" 🎮 Profile Editor ")

        self.current_preset_data = []
        self.current_json_path = ""
        self.selected_hw_id = ""
        self.selected_btn_name = ""
        self.NAGA_MAP = {str(i): i+1 for i in range(1, 13)}

        # TOP ROW: Preset Selector & Global Controls
        preset_row = ttk.Frame(frame)
        preset_row.pack(fill="x", pady=(0, 20))

        ttk.Label(preset_row, text="Target Profile:", font=("", 10, "bold")).pack(side="left", padx=(0, 10))
        
        self.preset_combo = ttk.Combobox(preset_row, state="readonly", width=25)
        self.preset_combo.pack(side="left", padx=(0, 10))
        self.preset_combo.bind("<<ComboboxSelected>>", self.load_preset_json)

        ttk.Button(preset_row, text="➕ New Profile", command=self.create_new_preset).pack(side="left")
        ttk.Button(preset_row, text="🗑️ Delete Profile", command=self.delete_profile).pack(side="left", padx=(10, 0))
        ttk.Button(preset_row, text="🚀 Apply Now", command=self.manual_apply_profile).pack(side="right")

        # MAIN CONTENT SPLIT (3 Columns)
        split_frame = ttk.Frame(frame)
        split_frame.pack(fill="both", expand=True)

        # 1. Left Column: MMO Grid
        grid_frame = ttk.LabelFrame(split_frame, text=" MMO Side Panel ", padding=15)
        grid_frame.pack(side="left", fill="y", padx=(0, 15))

        self.grid_buttons = {}
        btn_count = 1
        for row in range(4):
            for col in range(3):
                btn_name = str(btn_count)
                hw_id = self.NAGA_MAP.get(btn_name)
                
                btn = tk.Button(
                    grid_frame, text=btn_name, width=6, height=2, relief="flat", bd=0, highlightthickness=2, justify="center", font=("", 10, "bold"), cursor="hand2"
                )
                btn.config(command=lambda n=btn_name, h=hw_id: self.select_grid_button(n, h))
                btn.grid(row=row, column=col, padx=4, pady=4)
                
                self.grid_buttons[btn_name] = btn
                btn_count += 1

        # 2. Middle Column: Keybind Configurator
        config_frame = ttk.Frame(split_frame)
        config_frame.pack(side="left", fill="both", expand=True, padx=(0, 15))

        self.btn_label = ttk.Label(config_frame, text="Select a button on the grid...", font=("", 11, "bold"))
        self.btn_label.pack(anchor="w", pady=(0, 15))

        ttk.Label(config_frame, text="Output Action:").pack(anchor="w")
        self.action_entry = ttk.Entry(config_frame)
        self.action_entry.pack(fill="x", pady=(0, 5))
        
        self.listen_btn = ttk.Button(config_frame, text="🟢 Listen for Keystroke", style="Accent.TButton", command=self.start_listen)
        self.listen_btn.pack(anchor="w", pady=(0, 15))

        ttk.Button(config_frame, text="💾 Save to JSON", command=self.save_preset_json).pack(anchor="w")

        # 3. Right Column: Linked Windows Array
        win_frame = ttk.LabelFrame(split_frame, text=" Windows Linked to Profile ", padding=15)
        win_frame.pack(side="left", fill="both", expand=True)

        self.win_tree = ttk.Treeview(win_frame, columns=("Class",), show="headings", height=8)
        self.win_tree.heading("Class", text="Window Class")
        self.win_tree.pack(fill="both", expand=True, pady=(0, 10))

        controls = ttk.Frame(win_frame)
        controls.pack(fill="x")
        
        self.capture_btn = ttk.Button(controls, text="🎯 Capture", command=self.capture_window_to_selected)
        self.capture_btn.pack(side="left", padx=(0, 5))
        ttk.Button(controls, text="➕ Add", command=self.add_window_manual).pack(side="left", padx=(0, 5))
        ttk.Button(controls, text="🗑️ Remove", command=self.delete_window).pack(side="right")

    def refresh_editor_dropdown(self):
        active_group = self.group_var.get()
        if not active_group: return
        
        mappings = self.config["sync_groups"].get(active_group, {}).get("mappings", {})
        presets = sorted(list(mappings.keys()))
        
        self.preset_combo['values'] = presets
        
        current = self.preset_combo.get()
        if current in presets:
            self.preset_combo.set(current)
        elif presets:
            self.preset_combo.set(presets[0])
        else:
            self.preset_combo.set("")
            self.current_preset_data = []
            self.refresh_grid_visuals()
            self.refresh_linked_windows()
            return
            
        self.load_preset_json()

    def create_new_preset(self):
        active_group = self.group_var.get()
        if not active_group:
            messagebox.showwarning("No Group", "Please select a Sync Group first.")
            return

        preset = simpledialog.askstring("New Profile", "Enter the input-remapper profile name:")
        if preset:
            preset = preset.strip()
            if not preset: return
            
            mappings = self.config["sync_groups"][active_group]["mappings"]
            if preset not in mappings:
                mappings[preset] = []
                self.save_config()
                self.refresh_editor_dropdown()
                self.preset_combo.set(preset)
                self.load_preset_json()
            else:
                messagebox.showinfo("Info", "A profile with this name already exists in this group.")

    def delete_profile(self):
        preset = self.preset_combo.get()
        if not preset: return
        
        if preset.lower() == 'default':
            messagebox.showwarning("Warning", "You cannot delete the Default fallback profile.")
            return
            
        if messagebox.askyesno("Confirm", f"Remove the profile '{preset}' and unbind all its windows from this Sync Group?"):
            active_group = self.group_var.get()
            mappings = self.config["sync_groups"][active_group]["mappings"]
            
            if preset in mappings:
                del mappings[preset]
                self.save_config()
                self.refresh_editor_dropdown()

    def refresh_linked_windows(self):
        for item in self.win_tree.get_children():
            self.win_tree.delete(item)
            
        active_group = self.group_var.get()
        preset = self.preset_combo.get()
        if not active_group or not preset: return
        
        mappings = self.config["sync_groups"].get(active_group, {}).get("mappings", {})
        windows = mappings.get(preset, [])
        
        for win_class in windows:
            self.win_tree.insert("", tk.END, values=(win_class,))

    def capture_window_to_selected(self):
        preset = self.preset_combo.get()
        if not preset:
            messagebox.showwarning("Selection Required", "Please select a target profile first.")
            return

        if not self.group_var.get():
            messagebox.showwarning("No Group", "Please select a Sync Group first.")
            return

        self.capture_btn.config(text="Capturing in 3...", state="disabled")
        
        def capture_thread():
            time.sleep(1)
            self.capture_btn.config(text="Capturing in 2...")
            time.sleep(1)
            self.capture_btn.config(text="Capturing in 1...")
            time.sleep(1)
            self.capture_btn.config(text="Capturing!")
            
            try:
                cmd = "kdotool getactivewindow getwindowclassname" if "wayland" in os.environ.get("WAYLAND_DISPLAY", "").lower() or subprocess.run("command -v kdotool", shell=True, capture_output=True).returncode == 0 else "xdotool getactivewindow getwindowclassname"
                win_class = subprocess.check_output(cmd, shell=True, text=True).strip()
                self.after(0, self.apply_captured_window, preset, win_class)
            except Exception as e:
                self.after(0, messagebox.showerror, "Capture Failed", f"Could not detect window.\n{e}")
            finally:
                self.after(0, lambda: self.capture_btn.config(text="🎯 Capture", state="normal"))

        threading.Thread(target=capture_thread, daemon=True).start()

    def apply_captured_window(self, preset, win_class):
        if not win_class: return
        
        active_group = self.group_var.get()
        mappings = self.config["sync_groups"][active_group]["mappings"]
        
        # Safely remove this window from any other presets to avoid conflicts
        for p_name, windows in list(mappings.items()):
            if win_class in windows:
                windows.remove(win_class)

        if preset not in mappings:
            mappings[preset] = []
        if win_class not in mappings[preset]:
            mappings[preset].append(win_class)
            
        self.save_config()
        self.refresh_linked_windows()
        messagebox.showinfo("Success", f"Linked window '{win_class}' to profile '{preset}'.")

    def add_window_manual(self):
        preset = self.preset_combo.get()
        if not preset:
            messagebox.showwarning("Selection Required", "Please select a target profile first.")
            return
            
        win_class = simpledialog.askstring("Add Window", f"Enter the Window Class to add to '{preset}':")
        if win_class:
            win_class = win_class.strip()
            if not win_class: return
            self.apply_captured_window(preset, win_class)

    def delete_window(self):
        preset = self.preset_combo.get()
        if not preset: return
        
        selected = self.win_tree.selection()
        if not selected: return
        
        item = self.win_tree.item(selected[0])
        win_class = str(item['values'][0])
        
        if preset.lower() == 'default' and win_class.lower() == 'default':
            messagebox.showwarning("Warning", "You shouldn't delete the default fallback window!")
            return

        active_group = self.group_var.get()
        mappings = self.config["sync_groups"][active_group]["mappings"]
        
        if preset in mappings and win_class in mappings[preset]:
            mappings[preset].remove(win_class)
                
        self.save_config()
        self.refresh_linked_windows()

    # --- INPUT-REMAPPER JSON LOGIC ---
    def load_preset_json(self, event=None):
        preset_name = self.preset_combo.get()
        active_group = self.group_var.get()
        
        # Always refresh the windows tree immediately
        self.refresh_linked_windows()
        
        if not preset_name or not active_group: return

        devices = self.config["sync_groups"][active_group].get("devices", {})
        if not devices: return
        
        first_vid = list(devices.keys())[0]
        target_device = devices[first_vid].get("dev_name", "")
        
        # We extract the hash out of the dictionary now
        self.current_origin_hash = devices[first_vid].get("hash", "")
        self.current_json_path = os.path.expanduser(f"~/.config/input-remapper-2/presets/{target_device}/{preset_name}.json")

        if os.path.exists(self.current_json_path):
            with open(self.current_json_path, 'r') as f:
                data = json.load(f)
                self.current_preset_data = data if isinstance(data, list) else []
        else:
            self.current_preset_data = []

        if self.selected_hw_id:
            self.select_grid_button(self.selected_btn_name, self.selected_hw_id)
        self.refresh_grid_visuals()

    def format_key_label(self, action_string):
        clean = action_string
        # Clean up the new Tkinter keysym names for the visual grid
        replacements = {
            "Control_L": "CTRL", "Control_R": "CTRL",
            "Shift_L": "SHIFT", "Shift_R": "SHIFT",
            "Alt_L": "ALT", "Alt_R": "ALT",
            "space": "SPC", "Return": "ENT", "Escape": "ESC"
        }
        for old, new in replacements.items(): 
            clean = clean.replace(old, new)
        return clean

    def refresh_grid_visuals(self):
        mapped_codes = {}
        for mapping in self.current_preset_data:
            for combo in mapping.get("input_combination", []):
                if combo.get("type") == 1:
                    mapped_codes[combo.get("code")] = mapping.get("output_symbol", "Mapped")

        for btn_name, btn in self.grid_buttons.items():
            hw_id = self.NAGA_MAP.get(btn_name)
            is_selected = getattr(self, 'selected_btn_name', "") == btn_name
            outline_color = "#0078d4" if is_selected else ("#1e5c2b" if hw_id in mapped_codes else "#2b2b2b")

            if hw_id in mapped_codes:
                display_action = self.format_key_label(mapped_codes[hw_id])[:7]
                btn.config(text=f"{btn_name}\n[{display_action}]", bg="#2b2b2b", fg="#ffffff", highlightbackground=outline_color, highlightcolor=outline_color)
            else:
                btn.config(text=f"{btn_name}\n ", bg="#2b2b2b", fg="#666666", highlightbackground=outline_color, highlightcolor=outline_color)

    def select_grid_button(self, btn_name, hw_id):
        self.selected_btn_name = btn_name
        self.selected_hw_id = hw_id
        self.btn_label.config(text=f"Button {btn_name} (Hardware Code: {hw_id})")
        self.action_entry.delete(0, tk.END)
        self.refresh_grid_visuals()
        
        for mapping in self.current_preset_data:
            for combo in mapping.get("input_combination", []):
                if combo.get("type") == 1 and combo.get("code") == hw_id:
                    self.action_entry.insert(0, mapping.get("output_symbol", ""))
                    return

    def start_listen(self):
        self.listen_btn.config(text="Press any key...", state="disabled")
        self.bind("<KeyPress>", self.capture_key)

    def capture_key(self, event):
        self.unbind("<KeyPress>")
        
        # event.keysym grabs the exact, case-sensitive key name (e.g., 'Control_L', 'M', 'space')
        key_sym = event.keysym
        
        self.action_entry.delete(0, tk.END)
        self.action_entry.insert(0, key_sym)
        self.listen_btn.config(text="🟢 Listen for Keystroke", state="normal")

    def save_preset_json(self):
        if not self.selected_hw_id or not self.current_json_path: return messagebox.showwarning("Error", "Select a preset and a button.")
        new_action = self.action_entry.get().strip()
        
        for i in range(len(self.current_preset_data) - 1, -1, -1):
            mapping = self.current_preset_data[i]
            new_combos = [c for c in mapping.get("input_combination", []) if not (c.get("type") == 1 and c.get("code") == self.selected_hw_id)]
            if not new_combos: del self.current_preset_data[i]
            else: mapping["input_combination"] = new_combos

        if new_action:
            self.current_preset_data.append({
                "input_combination": [{"type": 1, "code": self.selected_hw_id, "origin_hash": getattr(self, 'current_origin_hash', "")}],
                "target_uinput": "keyboard,mouse",
                "output_symbol": new_action,
                "mapping_type": "key_macro",
                "name": f"Button {self.selected_btn_name}"
            })

        os.makedirs(os.path.dirname(self.current_json_path), exist_ok=True)
        with open(self.current_json_path, 'w') as f: json.dump(self.current_preset_data, f, indent=4)
        self.refresh_grid_visuals()
        messagebox.showinfo("Saved", f"Profile '{self.preset_combo.get()}' updated!")

    def manual_apply_profile(self):
        preset = self.preset_combo.get()
        active_group = self.group_var.get()
        if not preset or not active_group: return
        
        devices = self.config["sync_groups"][active_group].get("devices", {})
        if not devices: 
            return messagebox.showwarning("No Devices", "No devices in this Sync Group.")

        def apply_thread():
            connected_vid_pids = set()
            
            # 1. Bulletproof check for connected hardware via /proc (No root required)
            try:
                with open("/proc/bus/input/devices", "r") as f:
                    for line in f:
                        if line.startswith("I:"):
                            # Example line: I: Bus=0003 Vendor=1532 Product=00b9 Version=0111
                            parts = line.split()
                            vendor = "0000"
                            product = "0000"
                            for part in parts:
                                if part.startswith("Vendor="):
                                    vendor = part.split("=")[1].lower()
                                elif part.startswith("Product="):
                                    product = part.split("=")[1].lower()
                            connected_vid_pids.add(f"{vendor}:{product}")
            except Exception as e:
                print(f"Error reading input devices: {e}")

            print(f"\n[DEBUG] Physically plugged in VID:PIDs: {connected_vid_pids}")

            success = False
            
            # 2. Iterate over our saved devices in the group
            for vid_pid, dev_info in devices.items():
                print(f"[DEBUG] Checking your saved device: {vid_pid}...")
                
                # Skip if the device is not physically plugged in right now
                if vid_pid not in connected_vid_pids:
                    print(f"[DEBUG] --> {vid_pid} is NOT plugged in right now. Skipping.")
                    continue

                print(f"[DEBUG] --> {vid_pid} IS plugged in! Injecting and applying...")
                dev_name = dev_info.get("dev_name", "")
                dev_hash = dev_info.get("hash", "")
                
                preset_path = os.path.expanduser(f"~/.config/input-remapper-2/presets/{dev_name}/{preset}.json")
                
                # 3. Inject the hash into the input-remapper preset JSON
                if os.path.exists(preset_path):
                    try:
                        with open(preset_path, 'r') as f:
                            preset_data = json.load(f)
                        
                        if isinstance(preset_data, list):
                            for mapping in preset_data:
                                if "input_combination" in mapping:
                                    # Drill down into the combination list
                                    for combination in mapping["input_combination"]:
                                        combination["origin_hash"] = dev_hash
                            
                        with open(preset_path, 'w') as f:
                            json.dump(preset_data, f, indent=4)

                    except Exception as e:
                        print(f"Failed to inject hash into {preset_path}: {e}")

                # 4. Apply the preset using input-remapper-control
                try:
                    result = subprocess.run(
                        ["input-remapper-control", "--command", "start", "--device", dev_name, "--preset", preset], 
                        check=True, 
                        capture_output=True,
                        text=True
                    )
                    print(f"[DEBUG] Successfully applied profile to {dev_name}")
                    success = True
                except subprocess.CalledProcessError as e: 
                    print(f"[DEBUG] input-remapper failed to apply: {e.stderr}")
            
            # 5. UI Updates
            if success:
                with open(os.path.expanduser("~/.config/mouse-switcher/active.state"), "w") as sf:
                    sf.write(f"{preset} (Manual)")
                self.after(0, messagebox.showinfo, "Success", f"Profile '{preset}' injected and applied!")
            else:
                self.after(0, messagebox.showerror, "Error", "Failed to apply profile. Are the devices plugged in?")

        threading.Thread(target=apply_thread, daemon=True).start()


    # --- TAB 2: DEVICES & SYNC ---
    def build_devices_tab(self):
        frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(frame, text=" Devices & Sync ")

        # Create multiple columns for the new data structure
        self.dev_tree = ttk.Treeview(frame, columns=("DevName", "VidPid", "Hash"), show="tree headings", height=10)
        
        self.dev_tree.heading("#0", text="Sync Group / Friendly Name")
        self.dev_tree.heading("DevName", text="System Name")
        self.dev_tree.heading("VidPid", text="VID:PID")
        self.dev_tree.heading("Hash", text="MD5 Hash")
        
        self.dev_tree.column("#0", width=250)
        self.dev_tree.column("DevName", width=250)
        self.dev_tree.column("VidPid", width=100, anchor="center")
        self.dev_tree.column("Hash", width=250)
        
        self.dev_tree.pack(fill="both", expand=True, pady=(0, 15))

        controls = ttk.Frame(frame)
        controls.pack(fill="x")
        
        ttk.Button(controls, text="➕ New Sync Group", command=self.create_sync_group).pack(side="left", padx=(0, 10))
        ttk.Button(controls, text="✏️ Rename Group", command=self.rename_sync_group).pack(side="left", padx=(0, 10))
        ttk.Button(controls, text="✏️ Rename Device", command=self.rename_device).pack(side="left", padx=(0, 10))
        
        self.scan_btn = ttk.Button(controls, text="🔍 Add Device to Active Group", style="Accent.TButton", command=self.scan_devices)
        self.scan_btn.pack(side="left", padx=(0, 10))
        
        ttk.Button(controls, text="🗑️ Delete Selected", command=self.delete_device_or_group).pack(side="right")

    def refresh_devices_list(self):
        for item in self.dev_tree.get_children():
            self.dev_tree.delete(item)
            
        active_group_name = self.group_var.get()
            
        for group_name, group_data in self.config.get("sync_groups", {}).items():
            is_active = (group_name == active_group_name)
            display_text = f"📂 {group_name} (Active)" if is_active else f"📂 {group_name}"
            
            group_id = self.dev_tree.insert("", "end", text=display_text, open=True, tags=("group", group_name))
            
            # Now iterating over vid_pid
            for vid_pid, dev_data in group_data.get("devices", {}).items():
                friendly = dev_data.get("friendly_name", dev_data.get("dev_name", "Unknown"))
                dev_name = dev_data.get("dev_name", "Unknown")
                dev_hash = dev_data.get("hash", "unknown")
                
                self.dev_tree.insert(
                    group_id, "end", text=f"🖱️ {friendly}", 
                    values=(dev_name, vid_pid, dev_hash), 
                    tags=("device", group_name, vid_pid) # Pass vid_pid as the tag
                )
                
    def create_sync_group(self):
        name = simpledialog.askstring("New Group", "Enter a name for the new Sync Group:")
        if name:
            if name in self.config["sync_groups"]:
                messagebox.showerror("Error", "Group already exists.")
                return
                
            self.config["sync_groups"][name] = {"devices": {}, "mappings": {"Default": ["default"]}}
            self.save_config()
            self.update_group_dropdown()
            self.group_var.set(name)
            self.on_group_changed()

    def rename_sync_group(self):
        selected = self.dev_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a Sync Group to rename.")
            return

        item_tags = self.dev_tree.item(selected[0], "tags")
        if not item_tags or item_tags[0] != "group":
            messagebox.showwarning("Invalid Selection", "Please select a Sync Group folder, not a device.")
            return

        old_name = item_tags[1]
        new_name = simpledialog.askstring("Rename Group", f"Enter a new name for '{old_name}':", initialvalue=old_name)
        
        if new_name and new_name != old_name:
            if new_name in self.config["sync_groups"]:
                messagebox.showerror("Error", "A group with this name already exists.")
                return
            
            new_groups = {}
            for k, v in self.config["sync_groups"].items():
                if k == old_name:
                    new_groups[new_name] = v
                else:
                    new_groups[k] = v
            self.config["sync_groups"] = new_groups
            self.save_config()
            
            if self.group_var.get() == old_name:
                self.group_var.set(new_name)
                
            self.update_group_dropdown()
            self.refresh_devices_list()

    def rename_device(self):
        selected = self.dev_tree.selection()
        if not selected: return
        
        item_tags = self.dev_tree.item(selected[0], "tags")
        if not item_tags or item_tags[0] != "device":
            return messagebox.showwarning("Selection", "Select a device to rename.")
            
        group_name, dev_hash = item_tags[1], item_tags[2]
        current_data = self.config["sync_groups"][group_name]["devices"][dev_hash]
        current_name = current_data.get("friendly_name", "")
        
        new_name = simpledialog.askstring("Rename Device", "Enter a friendly name:", initialvalue=current_name)
        if new_name is not None:
            new_name = new_name.strip()
            self.config["sync_groups"][group_name]["devices"][dev_hash]["friendly_name"] = new_name if new_name else current_data["dev_name"]
            self.save_config()
            self.refresh_devices_list()

    def delete_device_or_group(self):
        selected = self.dev_tree.selection()
        if not selected: return
        
        item_tags = self.dev_tree.item(selected[0], "tags")
        if not item_tags: return
        
        if item_tags[0] == "group":
            group_name = item_tags[1]
            if len(self.config["sync_groups"]) == 1:
                messagebox.showwarning("Warning", "You must have at least one Sync Group.")
                return
            if messagebox.askyesno("Confirm", f"Delete Sync Group '{group_name}' and all its mappings?"):
                del self.config["sync_groups"][group_name]
                self.save_config()
                self.update_group_dropdown()
                
        elif item_tags[0] == "device":
            group_name, vid_pid = item_tags[1], item_tags[2]
            del self.config["sync_groups"][group_name]["devices"][vid_pid]
            self.save_config()
            self.refresh_devices_list()

    def scan_devices(self):
        active_group = self.group_var.get()
        if not active_group:
            messagebox.showwarning("No Group", "Please select or create a Sync Group first.")
            return

        self.scan_btn.config(state="disabled")
        
        self.wait_popup = tk.Toplevel(self)
        self.wait_popup.title("Listening for Device...")
        self.wait_popup.geometry("350x150")
        self.wait_popup.transient(self)
        self.wait_popup.grab_set()
        
        ttk.Label(self.wait_popup, text="🎮 Press any side button on your mouse now...", font=("", 10, "bold")).pack(expand=True)
        ttk.Label(self.wait_popup, text="(Waiting up to 15 seconds)").pack(pady=(0, 10))
        ttk.Button(self.wait_popup, text="Cancel", command=self.close_wait_popup_with_error).pack(pady=(0, 10))

        payload = """import sys, json, hashlib, select, time
try:
    import evdev
except ImportError:
    sys.exit(1)

# Grab all physical devices, explicitly ignoring input-remapper virtual devices
devices = {}
for path in evdev.list_devices():
    try:
        dev = evdev.InputDevice(path)
        if "input-remapper" not in dev.name.lower():
            devices[dev.fd] = dev
    except Exception:
        pass

start = time.time()

try:
    while time.time() - start < 15:
        r, w, x = select.select(devices.keys(), [], [], 1.0)
        for fd in r:
            dev = devices[fd]
            for event in dev.read():
                if event.type == evdev.ecodes.EV_KEY and event.value == 1:
                    s = str(dev.capabilities(absinfo=False)) + dev.name
                    dev_hash = hashlib.md5(s.encode('utf-8')).hexdigest().lower()
                    
                    vid_pid = f"{dev.info.vendor:04x}:{dev.info.product:04x}"
                    
                    data = {
                        vid_pid: {
                            "dev_name": dev.name,
                            "friendly_name": dev.name,
                            "hash": dev_hash
                        }
                    }
                    print(json.dumps(data))
                    sys.exit(0)
except Exception:
    pass
sys.exit(1)
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(payload)
            temp_path = f.name

        def execute_scan():
            try:
                # Force input-remapper to drop its exclusive hardware locks
                subprocess.run(["input-remapper-control", "--command", "stop-all"], capture_output=True)
                
                # Run the scanner payload now that the hardware is free
                result = subprocess.run(["pkexec", "python3", temp_path], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    self.after(0, self.confirm_device_selection, json.loads(result.stdout))
                else:
                    self.after(0, self.close_wait_popup_with_error)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                # 1. Restore standard input-remapper autoload profiles (e.g., your main keyboard)
                subprocess.run(["input-remapper-control", "--command", "autoload"], capture_output=True)
                
                self.after(0, lambda: self.scan_btn.config(state="normal"))

        threading.Thread(target=execute_scan, daemon=True).start()

    def confirm_device_selection(self, device_data):
        if hasattr(self, 'wait_popup') and self.wait_popup.winfo_exists():
            self.wait_popup.destroy()
            
        vid_pid = list(device_data.keys())[0]
        dev_info = device_data[vid_pid]
        new_dev_name = dev_info["dev_name"]
        new_hash = dev_info["hash"]
        
        if messagebox.askyesno("Device Detected", f"Detected input from:\n\n{new_dev_name}\n\nAdd this device to '{self.group_var.get()}'?"):
            active_group = self.group_var.get()
            existing_devices = self.config["sync_groups"][active_group].get("devices", {})
            
            # 1. Find an existing device in the group to act as the source template
            source_dev_name = None
            for existing_vid, existing_data in existing_devices.items():
                if existing_vid != vid_pid:  # Don't copy from itself
                    source_dev_name = existing_data.get("dev_name")
                    break

            # 2. Add the new device to our config
            self.config["sync_groups"][active_group]["devices"][vid_pid] = dev_info
            self.save_config()
            self.refresh_devices_list()
            
            # 3. Perform the One-Time Profile Sync
            if source_dev_name:
                source_dir = os.path.expanduser(f"~/.config/input-remapper-2/presets/{source_dev_name}")
                dest_dir = os.path.expanduser(f"~/.config/input-remapper-2/presets/{new_dev_name}")
                
                if os.path.exists(source_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                    synced_count = 0
                    
                    for filename in os.listdir(source_dir):
                        if filename.endswith(".json"):
                            src_file = os.path.join(source_dir, filename)
                            dest_file = os.path.join(dest_dir, filename)
                            
                            try:
                                with open(src_file, 'r') as f:
                                    preset_data = json.load(f)
                                
                                # Inject the newly scanned hash into the copied preset
                                if isinstance(preset_data, list):
                                    for mapping in preset_data:
                                        if "input_combination" in mapping:
                                            # Drill down into the combination list
                                            for combination in mapping["input_combination"]:
                                                combination["origin_hash"] = new_hash
                                    
                                with open(dest_file, 'w') as f:
                                    json.dump(preset_data, f, indent=4)
                                    
                                synced_count += 1
                            except Exception as e:
                                print(f"Failed to sync {filename}: {e}")
                                
                    if synced_count > 0:
                        print(f"Synced {synced_count} profiles from {source_dev_name} to {new_dev_name}")

            # 4. Automatically remove overrides and restart daemon
            if self.preset_combo.get():
                self.remove_override()

    def close_wait_popup_with_error(self):
        if hasattr(self, 'wait_popup') and self.wait_popup.winfo_exists():
            self.wait_popup.destroy()
            messagebox.showwarning("Scan Finished", "No button press detected or authentication was cancelled.")

    # --- TAB 3: DAEMON & LOGS ---
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
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f: logs = f.read()
            self.log_text.config(state="normal")
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, logs)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")

        is_running = (subprocess.run(["pgrep", "-f", "bin/mouse-switcher$"], capture_output=True).returncode == 0)

        if is_running:
            self.status_btn.config(text="🟢 Service Running")
            state_file = os.path.expanduser("~/.config/mouse-switcher/active.state")
            if os.path.exists(state_file):
                with open(state_file, "r") as sf: active_preset = sf.read().strip()
                self.active_badge.config(text=f"🎯 Active: {active_preset}")
                
                if "(Manual)" in active_preset and not self.remove_override_btn.winfo_ismapped():
                    self.remove_override_btn.pack(side="left", padx=(15, 0))
                elif "(Manual)" not in active_preset and self.remove_override_btn.winfo_ismapped():
                    self.remove_override_btn.pack_forget()
        else:
            self.status_btn.config(text="🔴 Service Stopped")
            self.active_badge.config(text="🎯 Active: Offline")
            if self.remove_override_btn.winfo_ismapped(): self.remove_override_btn.pack_forget()
        
        self.after(2000, self.update_logs)

    def restart_daemon(self):
        script_path = os.path.expanduser("~/.local/bin/mouse-switcher")
        subprocess.run(["pkill", "-f", "bin/mouse-switcher$"])
        time.sleep(0.5)
        subprocess.Popen(["bash", script_path], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        messagebox.showinfo("Restarted", "The background daemon has been restarted!")

    def stop_daemon(self):
        subprocess.run(["pkill", "-f", "bin/mouse-switcher$"])
        messagebox.showinfo("Stopped", "The background daemon has been stopped.")

    def remove_override(self):
        with open(os.path.expanduser("~/.config/mouse-switcher/active.state"), "w") as sf:
            sf.write("Resuming Auto-Switch")
        self.restart_daemon()

if __name__ == "__main__":
    app = MouseSwitcherApp()
    app.mainloop()
