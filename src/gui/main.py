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
        self.geometry("850x650")
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
                        "mappings": {"default": "Default"}
                    }
                }
            }
            self.save_config()
        else:
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
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
        # Pack this BEFORE the notebook so it sticks to the absolute bottom
        footer_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 15))

        # Bottom Left: Active Profile
        self.active_badge = ttk.Label(footer_frame, text="🎯 Active: Scanning...", font=("", 12, "bold"), foreground="#0078d4")
        self.active_badge.pack(side="left")

        # We create the override button, but don't pack it until it's needed
        self.remove_override_btn = ttk.Button(footer_frame, text="❌ Remove Override", command=self.remove_override)

        # Bottom Right: Service Status
        self.status_btn = ttk.Button(footer_frame, text="🟢 Service Running")
        self.status_btn.pack(side="right")

        # 3. Main Notebook (Tabs)
        self.notebook = ttk.Notebook(self)
        # Now the notebook expands to fill the space between header and footer
        self.notebook.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 15))

        # 4. Build Tabs
        self.build_mappings_tab()
        self.build_devices_tab()
        self.build_editor_tab()
        self.build_logs_tab()

    def update_group_dropdown(self):
        groups = list(self.config.get("sync_groups", {}).keys())
        self.group_combo['values'] = groups
        
        if groups:
            # Set to current or fallback to first
            if self.group_var.get() not in groups:
                self.group_var.set(groups[0])
        else:
            self.group_var.set("")
            
        self.on_group_changed()

    def on_group_changed(self, event=None):
        """Fired when the global Sync Group is changed."""
        self.refresh_mappings_list()
        self.refresh_devices_list()
        self.refresh_editor_dropdown()

    # --- TAB 1: MAPPINGS ---
    def build_mappings_tab(self):
        frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(frame, text=" Game Mappings ")

        ttk.Label(frame, text="Mappings listed here apply ONLY to the globally selected Sync Group.", foreground="gray").pack(anchor="w", pady=(0, 10))

        columns = ("Window Class", "Preset Name")
        self.map_tree = ttk.Treeview(frame, columns=columns, show="headings", height=10)
        self.map_tree.heading("Window Class", text="Window Class")
        self.map_tree.heading("Preset Name", text="Preset Name")
        self.map_tree.column("Window Class", width=350)
        self.map_tree.column("Preset Name", width=250)
        self.map_tree.pack(fill="both", expand=True, pady=(0, 15))

        controls = ttk.Frame(frame)
        controls.pack(fill="x")

        self.capture_btn = ttk.Button(controls, text="🎯 Capture Active Window", style="Accent.TButton", command=self.capture_window)
        self.capture_btn.pack(side="left", padx=(0, 10))
        
        ttk.Button(controls, text="🗑️ Delete Selected", command=self.delete_mapping).pack(side="right")

    def refresh_mappings_list(self):
        for item in self.map_tree.get_children():
            self.map_tree.delete(item)
            
        active_group = self.group_var.get()
        if not active_group: return
        
        mappings = self.config["sync_groups"].get(active_group, {}).get("mappings", {})
        for win_class, preset in mappings.items():
            self.map_tree.insert("", tk.END, values=(win_class, preset))

    def capture_window(self):
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
                self.after(0, self.prompt_preset, win_class)
            except Exception as e:
                self.after(0, messagebox.showerror, "Capture Failed", f"Could not detect window.\n{e}")
            finally:
                self.after(0, lambda: self.capture_btn.config(text="🎯 Capture Active Window", state="normal"))

        threading.Thread(target=capture_thread, daemon=True).start()

    def prompt_preset(self, win_class):
        if not win_class: return
        
        preset = simpledialog.askstring("Preset Name", f"Detected Window: {win_class}\n\nEnter the input-remapper preset name:")
        if preset:
            active_group = self.group_var.get()
            self.config["sync_groups"][active_group]["mappings"][win_class] = preset
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

        active_group = self.group_var.get()
        del self.config["sync_groups"][active_group]["mappings"][win_class]
        self.save_config()
        self.refresh_mappings_list()

    # --- TAB 2: DEVICES ---
    def build_devices_tab(self):
        frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(frame, text=" Devices & Sync ")

        # Create Treeview to act as Folders
        self.dev_tree = ttk.Treeview(frame, columns=("Hash",), show="tree headings", height=10)
        self.dev_tree.heading("#0", text="Sync Group / Device Name")
        self.dev_tree.heading("Hash", text="Hardware Hash (MD5)")
        self.dev_tree.column("#0", width=400)
        self.dev_tree.column("Hash", width=300)
        self.dev_tree.pack(fill="both", expand=True, pady=(0, 15))

        controls = ttk.Frame(frame)
        controls.pack(fill="x")
        
        ttk.Button(controls, text="➕ New Sync Group", command=self.create_sync_group).pack(side="left", padx=(0, 10))
        self.scan_btn = ttk.Button(controls, text="🔍 Add Device to Active Group", style="Accent.TButton", command=self.scan_devices)
        self.scan_btn.pack(side="left", padx=(0, 10))
        
        ttk.Button(controls, text="🗑️ Delete Selected", command=self.delete_device_or_group).pack(side="right")

    def refresh_devices_list(self):
        for item in self.dev_tree.get_children():
            self.dev_tree.delete(item)
            
        for group_name, group_data in self.config.get("sync_groups", {}).items():
            # Insert Folder
            group_id = self.dev_tree.insert("", "end", text=f"📂 {group_name}", open=True, tags=("group", group_name))
            
            # Insert Devices
            for dev_name, dev_hash in group_data.get("devices", {}).items():
                self.dev_tree.insert(group_id, "end", text=dev_name, values=(dev_hash,), tags=("device", group_name, dev_name))

    def create_sync_group(self):
        name = simpledialog.askstring("New Group", "Enter a name for the new Sync Group:")
        if name:
            if name in self.config["sync_groups"]:
                messagebox.showerror("Error", "Group already exists.")
                return
                
            self.config["sync_groups"][name] = {"devices": {}, "mappings": {"default": "Default"}}
            self.save_config()
            self.update_group_dropdown()
            self.group_var.set(name)
            self.on_group_changed()

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
            group_name, dev_name = item_tags[1], item_tags[2]
            del self.config["sync_groups"][group_name]["devices"][dev_name]
            self.save_config()
            self.refresh_devices_list()

    def scan_devices(self):
        active_group = self.group_var.get()
        if not active_group:
            messagebox.showwarning("No Group", "Please select or create a Sync Group first.")
            return

        self.scan_btn.config(text="Waiting for Auth...", state="disabled")
        self.update_idletasks()

        payload = """import sys, json, hashlib
try:
    import evdev
except ImportError:
    sys.exit(1)

devices = {}
for path in evdev.list_devices():
    try:
        dev = evdev.InputDevice(path)
        phys = dev.phys.split("/")[0] if dev.phys else "-"
        key = f"{dev.info.bustype}_{dev.info.vendor}_{dev.info.product}_{phys}"
        devices[dev.name] = hashlib.md5(key.encode('utf-8')).hexdigest()
    except: pass
print(json.dumps(devices))
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(payload)
            temp_path = f.name

        def execute_scan():
            try:
                result = subprocess.run(["pkexec", "python3", temp_path], capture_output=True, text=True)
                if result.returncode == 0:
                    self.after(0, self.prompt_device_selection, json.loads(result.stdout))
                else:
                    self.after(0, messagebox.showerror, "Scan Failed", "Authentication cancelled or failed.")
            finally:
                os.remove(temp_path)
                self.after(0, lambda: self.scan_btn.config(text="🔍 Add Device to Active Group", state="normal"))

        threading.Thread(target=execute_scan, daemon=True).start()

    def prompt_device_selection(self, devices):
        if not devices: return messagebox.showinfo("No Devices", "No supported input devices found.")

        popup = tk.Toplevel(self)
        popup.title("Select Hardware")
        popup.geometry("400x300")
        popup.transient(self)
        popup.grab_set()

        ttk.Label(popup, text=f"Adding to: {self.group_var.get()}", font=("", 10, "bold")).pack(pady=10)
        listbox = tk.Listbox(popup, bg="#2b2b2b", fg="#ffffff", selectbackground="#0078d4", font=("", 10))
        listbox.pack(fill="both", expand=True, padx=10, pady=5)

        device_names = list(devices.keys())
        for name in device_names: listbox.insert(tk.END, name)

        def on_add():
            idx = listbox.curselection()
            if not idx: return
            dev_name = device_names[idx[0]]
            dev_hash = devices[dev_name]

            active_group = self.group_var.get()
            self.config["sync_groups"][active_group]["devices"][dev_name] = dev_hash
            self.save_config()
            self.refresh_devices_list()
            popup.destroy()

        controls = ttk.Frame(popup)
        controls.pack(fill="x", pady=10)
        ttk.Button(controls, text="Add Device", style="Accent.TButton", command=on_add).pack(side="right", padx=10)
        ttk.Button(controls, text="Cancel", command=popup.destroy).pack(side="right")

    # --- TAB 3: PROFILE EDITOR (3x4 MMO GRID) ---
    def build_editor_tab(self):
        frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(frame, text=" 🎮 Profile Editor ")

        self.current_preset_data = []
        self.current_json_path = ""
        self.selected_hw_id = ""
        self.selected_btn_name = ""

        self.NAGA_MAP = {str(i): i+1 for i in range(1, 13)}

        # Grid
        grid_frame = ttk.LabelFrame(frame, text=" MMO Side Panel ", padding=20)
        grid_frame.pack(side="left", fill="y", padx=(0, 20))

        self.grid_buttons = {}
        btn_count = 1
        for row in range(4):
            for col in range(3):
                btn_name = str(btn_count)
                hw_id = self.NAGA_MAP.get(btn_name)
                
                btn = tk.Button(
                    grid_frame, text=btn_name, width=8, height=3, relief="flat", bd=0, highlightthickness=2, justify="center", font=("", 10, "bold"), cursor="hand2"
                )
                btn.config(command=lambda n=btn_name, h=hw_id: self.select_grid_button(n, h))
                btn.grid(row=row, column=col, padx=4, pady=4)
                
                self.grid_buttons[btn_name] = btn
                btn_count += 1

        # Configurator
        config_frame = ttk.Frame(frame)
        config_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(config_frame, text="Target Preset:", foreground="gray").pack(anchor="w")
        preset_row = ttk.Frame(config_frame)
        preset_row.pack(fill="x", pady=(0, 20))

        self.preset_combo = ttk.Combobox(preset_row, state="readonly")
        self.preset_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.preset_combo.bind("<<ComboboxSelected>>", self.load_preset_json)

        ttk.Button(preset_row, text="🚀 Apply Now", command=self.manual_apply_profile).pack(side="right")

        self.btn_label = ttk.Label(config_frame, text="Select a button on the grid...", font=("", 12, "bold"))
        self.btn_label.pack(anchor="w", pady=(0, 20))

        ttk.Label(config_frame, text="Output Action:").pack(anchor="w")
        self.action_entry = ttk.Entry(config_frame)
        self.action_entry.pack(fill="x", pady=(0, 5))
        
        self.listen_btn = ttk.Button(config_frame, text="🟢 Listen for Keystroke", style="Accent.TButton", command=self.start_listen)
        self.listen_btn.pack(anchor="w", pady=(0, 20))

        ttk.Button(config_frame, text="💾 Save to JSON", command=self.save_preset_json).pack(side="bottom", anchor="e")

    def refresh_editor_dropdown(self):
        active_group = self.group_var.get()
        if not active_group: return
        
        mappings = self.config["sync_groups"].get(active_group, {}).get("mappings", {})
        presets = sorted(list(set(mappings.values())))
        
        self.preset_combo['values'] = presets
        if presets:
            self.preset_combo.set(presets[0])
            self.load_preset_json()
        else:
            self.preset_combo.set("")
            self.current_preset_data = []
            self.refresh_grid_visuals()

    def format_key_label(self, action_string):
        clean = action_string.replace("key(", "").replace("macro(", "").replace(")", "").replace("KEY_", "")
        replacements = {"LEFTCTRL": "CTRL", "LEFTSHIFT": "SHIFT", "LEFTMETA": "WIN", "SPACE": "SPC", "ENTER": "ENT", ", ": "+"}
        for old, new in replacements.items(): clean = clean.replace(old, new)
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

    def load_preset_json(self, event=None):
        preset_name = self.preset_combo.get()
        active_group = self.group_var.get()
        
        if not preset_name or not active_group: return

        devices = self.config["sync_groups"][active_group].get("devices", {})
        if not devices: return
        
        target_device = list(devices.keys())[0]
        self.current_origin_hash = devices[target_device]
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
        key_sym = event.keysym.upper()
        special_keys = {"SPACE": "KEY_SPACE", "RETURN": "KEY_ENTER", "ESCAPE": "KEY_ESC"}
        out_key = special_keys.get(key_sym, f"KEY_{key_sym}")
        
        self.action_entry.delete(0, tk.END)
        self.action_entry.insert(0, f"key({out_key})")
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
                "target_uinput": "keyboard",
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
        if not devices: return messagebox.showwarning("No Devices", "No devices in this Sync Group.")

        def apply_thread():
            success = False
            for dev in devices.keys():
                try:
                    subprocess.run(["input-remapper-control", "--command", "start", "--device", dev, "--preset", preset], check=True, capture_output=True)
                    success = True
                except subprocess.CalledProcessError: pass
            
            if success:
                with open(os.path.expanduser("~/.config/mouse-switcher/active.state"), "w") as sf:
                    sf.write(f"{preset} (Manual)")
                self.after(0, messagebox.showinfo, "Success", f"Profile '{preset}' injected!")
            else:
                self.after(0, messagebox.showerror, "Error", "Failed to apply profile. Are devices plugged in?")

        threading.Thread(target=apply_thread, daemon=True).start()

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
                
                # Pop the override button next to the active badge on the bottom left
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
            sf.write("Resuming Auto-Switch...")
        self.restart_daemon()

if __name__ == "__main__":
    app = MouseSwitcherApp()
    app.mainloop()