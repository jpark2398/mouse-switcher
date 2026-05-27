# 🖱️ Mouse Profile Switcher

A dynamic, window-aware mouse profile auto-switcher for Linux. Built on top of `input-remapper`, this tool runs a lightweight background daemon that monitors your active window (Wayland or X11) and instantly injects custom mouse macros and keybinds based on the game or application you are currently playing.

Includes a fully-featured, dark-mode GUI for mapping keys, visualizing your mouse grid, managing your hardware, and linking multiple game windows to a single profile.

## ✨ Features
* **Auto-Switching Daemon:** Automatically detects the active window and swaps profiles in milliseconds utilizing native desktop hooks and fast `jq` parsing.
* **Sync Groups:** Group multiple input devices (e.g., a desktop mouse, a travel mouse, and a keypad) into distinct profiles. Context switches happen seamlessly across all devices in the active group.
* **Smart Fallback:** Returns to your `Default` profile the moment you alt-tab back to your desktop.
* **Unified Profile Editor:** A clean 3-column interface to edit macros visually on an MMO grid, save to JSON, and link multiple game window classes to a single unified profile.
* **Manual Overrides:** Temporarily force a specific profile to test your macros without launching the game.
* **Native Desktop Integration:** Installs as a standard Linux desktop application with a custom icon and launcher.

---

## 📦 Prerequisites

Before installing the switcher, ensure your system has the required dependencies.

### 1. `input-remapper`
This tool relies on `input-remapper` to handle the low-level `evdev` device injection.
* **Ubuntu/Debian:** `sudo apt install input-remapper`
* **Arch Linux / CachyOS:** `paru -S input-remapper-git`
* **Fedora:** `sudo dnf copr enable sezanzeb/input-remapper && sudo dnf install input-remapper`

Once installed, ensure the root service is enabled and running:
```bash
sudo systemctl enable --now input-remapper
```

### 2. Python & System Tools
You need Python 3, Tkinter (for the GUI window), the `venv` module, Git, and `jq` (for blazing-fast JSON parsing in the background daemon).
* **Ubuntu/Debian:** `sudo apt install python3 python3-tk python3-venv git jq`
* **Arch Linux / CachyOS:** `sudo pacman -S python tk git jq`
* **Fedora:** `sudo dnf install python3 python3-tkinter git jq`

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

The easiest way to manage your profiles is through the graphical interface. Open your Linux app launcher and search for **Mouse Switcher**.

**The Global Layout:**
* **Top Bar:** Contains the **Active Sync Group** dropdown. Changing this context updates all the tabs below it to only show mappings and hardware for that specific group.
* **Bottom Footer:** Displays the live status of the daemon, the active profile, and a button to quickly kill manual overrides.

**The Tabs:**
1. **Profile Editor:** The core configurator. 
   * **Left:** Click tiles on the visual grid to select hardware buttons. 
   * **Middle:** Bind keys/macros and save them to your active profile. 
   * **Right:** Manage the array of "Linked Windows". Click "Capture" to instantly grab the window class of your active game and tie it to the currently selected profile.
2. **Devices & Sync:** A collapsible folder view to add, rename, and manage physical hardware devices in your Sync Groups.
3. **Daemon Status:** Monitor the live logs of the background auto-switcher, and manually restart/stop the service.

**Manual Overrides:**
If you want to test a profile without launching the game, select it in the Profile Editor and click **🚀 Apply Now**. The daemon will temporarily pause auto-switching. To resume automatic switching, click **❌ Remove Override** in the bottom-left footer.

---

## 💻 CLI & Advanced Usage

If you prefer the terminal or are running a headless setup, you can interact with the core scripts directly. The `install.sh` script places these commands globally in your `~/.local/bin/`.

### `mouse-switcher` (The Daemon)
This is the core background service. While the GUI normally manages this in the background, you can run it directly in your terminal to monitor your window hooks and profile injection in real-time.

### `mouse-map` (Hardware Debugger)
A CLI utility that safely injects window classes into your `profiles.json` arrays via inline Python without needing the GUI. 

---

## 📁 File Structure

Once installed, your configuration files are safely separated from the application binaries. This means you can update the code later without losing your game mappings!

* **Binaries:** `~/.local/bin/` (`mouse-switcher`, `mouse-switcher-gui`, `mouse-map`)
* **Configs:** `~/.config/mouse-switcher/`
  * `profiles.json` (Your multi-window game mappings & device swarm)
  * `active.state` (The live tracking file used by the GUI badge)
  * `icon.png` (The application desktop icon)
  * `venv/` (Isolated Python environment for UI themes)
* **Logs:** `~/.mouse-switcher.log` (Rotates automatically to prevent bloat)