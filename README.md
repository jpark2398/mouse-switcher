# 🖱️ Mouse Profile Switcher

A dynamic, window-aware mouse profile auto-switcher for Linux. Built on top of `input-remapper`, this tool runs a lightweight background daemon that monitors your active window (Wayland or X11) and instantly injects custom mouse macros and keybinds based on the game or application you are currently playing.

Includes a fully-featured, dark-mode GUI for mapping keys, visualizing your mouse grid, and managing the background service.

## ✨ Features
* **Auto-Switching Daemon:** Automatically detects the active window and swaps profiles in milliseconds.
* **Smart Fallback:** Returns to your `Default` profile the moment you alt-tab back to your desktop.
* **Visual Macro Editor:** A completely visual 3x4 grid interface for mapping hardware codes to keystrokes and macros.
* **Manual Overrides:** Temporarily force a specific profile to test your macros without launching the game.
* **Native Desktop Integration:** Installs as a standard Linux desktop application with a custom icon and launcher.

---

## 📦 Prerequisites

Before installing the switcher, ensure your system has the required dependencies.

### 1. `input-remapper`
This tool relies on `input-remapper` to handle the low-level `evdev` device injection.
* **Ubuntu/Debian:** `sudo apt install input-remapper`
* **Arch Linux (AUR):** `yay -S input-remapper-git`
* **Fedora:** `sudo dnf copr enable sezanzeb/input-remapper && sudo dnf install input-remapper`

Once installed, ensure the root service is enabled and running:
```bash
sudo systemctl enable --now input-remapper
```

### 2. Python & System Tools
You need Python 3, Tkinter (for the GUI window), the `venv` module, and Git.
* **Ubuntu/Debian:** `sudo apt install python3 python3-tk python3-venv git`
* **Arch Linux:** `sudo pacman -S python tk git`
* **Fedora:** `sudo dnf install python3 python3-tkinter git`

---

## 🚀 Installation

Clone this repository and run the included installation script. This will safely place the scripts in your path, move the configs to your `~/.config` folder, build an isolated Python environment for the UI theme, and generate a native desktop shortcut.

```bash
git clone [https://github.com/yourusername/mouse-switcher.git](https://github.com/yourusername/mouse-switcher.git)
cd mouse-switcher
chmod +x install.sh
./install.sh
```

---

## 🎨 Using the GUI

The easiest way to manage your profiles is through the graphical interface. Open your Linux app launcher (Super/Windows key) and search for **Mouse Switcher**.

The application is split into four main tabs:
1. **Mappings:** Link your installed Linux applications/games to a specific Profile Name (e.g., mapping `steam_app_1808500` to the `Arc` profile).
2. **Devices:** Select which physical hardware devices (mice/keypads) belong to the sync swarm.
3. **Profile Editor:** The visual configurator. Select a profile from the dropdown, click a tile on the visual grid, and type your desired key or macro (e.g., `CTRL+C`). Mapped keys will glow green, selected keys glow blue.
4. **Daemon Status:** Monitor the live logs of the background auto-switcher, and manually start/stop the service.

**Manual Overrides:**
If you want to test a profile without launching the game, select it in the Profile Editor and click **🚀 Apply Now**. The daemon will temporarily pause auto-switching. To resume automatic switching, click **❌ Remove Override** in the global header.

---

## 💻 CLI & Advanced Usage

If you prefer the terminal or are running a headless setup, you can interact with the core scripts directly. The `install.sh` script places these commands globally in your `~/.local/bin/`.

### `mouse-switcher` (The Daemon)
This is the core background service. While the GUI normally manages this in the background, you can run it directly in your terminal to monitor your window hooks and profile injection in real-time.

```bash
$ mouse-switcher
=== Mouse Switcher Started at 14:02:05 ===
Waiting for window changes...

Profile update event (Arc): steam_app_1808500
Applying profile 'Arc' via input-remapper...
Successfully injected profile into 1 device(s).

Profile update event (Default): gnome-terminal-server
Applying profile 'Default' via input-remapper...
Successfully injected profile into 1 device(s).
```

### `mouse-map` (Hardware Debugger)
A CLI utility for directly interacting with hardware codes without needing the GUI. This is incredibly useful if you plug in a new device and need to find its exact `evdev` name, or want to trace the hardware code of a specific button press.

**Example 1: Finding your device name**
```bash
$ mouse-map --list
Scanning /dev/input/...
Available Input Devices:
- Razer Naga Trinity (Event 14)
- Logitech G Pro X Superlight (Event 9)
- AT Translated Set 2 keyboard (Event 3)
```

**Example 2: Sniffing raw hardware codes**
```bash
$ mouse-map --listen "Razer Naga Trinity"
Listening to 'Razer Naga Trinity'... Press keys to see their hardware codes (Ctrl+C to exit).

[Event] KEY_LEFTSHIFT (Code: 42)
[Event] BTN_MOUSE_5 (Code: 279)
[Event] KEY_SPACE (Code: 57)
```

---

## 📁 File Structure

Once installed, your configuration files are safely separated from the application binaries. This means you can update the code later without losing your game mappings!

* **Binaries:** `~/.local/bin/` (`mouse-switcher`, `mouse-switcher-gui.py`, `mouse-map`)
* **Configs:** `~/.config/mouse-switcher/`
  * `profiles.conf` (Your game-to-profile mappings & device swarm)
  * `active.state` (The live tracking file used by the GUI badge)
  * `icon.png` (The application desktop icon)
  * `venv/` (Isolated Python environment for UI themes)
* **Logs:** `~/.mouse-switcher.log` (Rotates automatically to prevent bloat)