# Web OS v5.0 Ultimate — Complete Installation Guide

## Overview

Web OS is a standalone operating system based on Debian Linux. It auto-starts the Web OS web interface on boot. Can be installed as the only OS or alongside Windows/Linux (dual-boot).

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 GHz dual-core | 2 GHz quad-core |
| RAM | 512 MB | 2 GB+ |
| Storage | 4 GB | 16 GB+ (SSD) |
| USB Drive | 8 GB | 16 GB |
| Network | Ethernet/WiFi | Gigabit Ethernet |

## Method 1: Build ISO via WSL (from Windows)

This is the recommended method for Windows users. It uses WSL to build the ISO.

### Prerequisites

- Windows 10/11 with WSL installed
- At least 10 GB free disk space

### Step 1: Install WSL (if not already installed)

Open PowerShell as Administrator and run:

```powershell
wsl --install -d Ubuntu
```

Restart your PC when prompted. After restart, Ubuntu will launch and ask you to create a Linux username/password.

### Step 2: Build the ISO

```cmd
cd web-os\iso-builder
build-with-wsl.bat
```

The script will:
1. Check WSL is installed
2. Install build dependencies in WSL
3. Copy Web OS source to WSL
4. Build the full ISO (10-30 minutes)
5. Copy the ISO back to your Desktop

The final ISO will be at: `C:\Users\<you>\Desktop\web-os-5.0-x86_64.iso`

## Method 2: Build ISO on Linux

```bash
cd web-os

# Install build dependencies
sudo apt update
sudo apt install -y debootstrap grub-pc-bin grub-efi-amd64-bin xorriso squashfs-tools cpio

# Build the bootable ISO
sudo bash iso-builder/build-iso.sh
```

ISO output: `web-os/dist/web-os-5.0-x86_64.iso`

## Method 3: Docker Build (No Linux needed)

```bash
cd web-os

# Build and run the ISO builder inside Docker
docker build -t webos-iso-builder -f iso-builder/Dockerfile .
docker run --rm -v "$(pwd)/dist:/build/web-os/dist" webos-iso-builder

# ISO will be in ./dist/
```

## Write ISO to USB

### On Windows (Rufus)

1. Download [Rufus](https://rufus.ie/) (portable version works)
2. Open Rufus
3. Select your USB drive from "Device" dropdown
4. Click "SELECT" and choose `web-os-5.0-x86_64.iso`
5. Leave all settings as default:
   - Partition scheme: MBR (or GPT for modern UEFI PCs)
   - Target system: BIOS or UEFI
   - File system: Large FAT32
6. Click **START**
7. If asked "Write in DD Image mode?", click **Yes**
8. Wait for write to complete

### On Linux

```bash
# Find USB device (be careful!)
lsblk

# Write ISO (replace /dev/sdX with your USB)
sudo dd if=web-os-5.0-x86_64.iso of=/dev/sdX bs=4M status=progress
sync
```

## Boot from USB

1. Insert USB into the target PC
2. Restart and enter Boot Menu (usually **F12**, **F2**, **Del**, or **Esc**)
3. Select the USB drive
4. You'll see the GRUB boot menu:

```
  Web OS v5.0 Ultimate - Boot Live
  Web OS v5.0 Ultimate - Boot Live (Safe Mode)
  Web OS v5.0 Ultimate - Boot Live (Verbose)
  Web OS v5.0 Ultimate - Install to Hard Drive
  Advanced Options >
```

**Options:**
- **Boot Live** — Try Web OS without installing (runs from RAM)
- **Safe Mode** — Boot with minimal drivers (for problem hardware)
- **Verbose** — Boot with full debug output
- **Install to Hard Drive** — Permanent installation
- **Advanced >** — Memtest, Boot from HDD, Reboot, Shutdown

## Install to Hard Drive

### Boot the Installer

1. From GRUB, choose **"Install to Hard Drive"**
2. Wait for the system to boot into installer mode

### Choose Install Mode

```
  Install Mode:
  --------------------------------------------
  1) Auto — Entire disk (destroys all data)
  2) Manual — Partition with cfdisk
  3) Dual-boot — Alongside existing OS
  4) LUKS — Encrypted entire disk
  --------------------------------------------
```

- **Auto** — Wipes the entire disk, creates EFI (512MB) + ext4 root. Good for dedicated PC.
- **Manual** — Opens `cfdisk` for custom partitions. Advanced users only.
- **Dual-boot** — Detects existing OS, shrink partition to make room. Keep Windows/Linux.
- **LUKS** — Full disk encryption. Enter passphrase at every boot.

### Complete Installation

1. Select target disk (e.g., `sda`, `nvme0n1`)
2. Confirm by typing `YES`
3. Wait 5-15 minutes for file copy
4. When done, reboot and remove USB

## First Boot

1. PC boots directly into Web OS (Plymouth boot splash animation)
2. Console shows the system dashboard with:
   - IP address
   - CPU/RAM/Disk usage
   - Web OS status
   - Access URL

### Access Web OS

Connect from any device on the same network:

```
http://<ip-address>:8080
http://webos:8080
http://localhost:8080
```

**Login:** `admin` / `admin`

### Configure WiFi

If using WiFi:
```bash
# Run NetworkManager TUI
nmtui

# Select "Activate a connection"
# Choose your WiFi network
# Enter password
```

Or edit `/etc/netplan/01-netcfg.yaml` and run `netplan apply`.

## Built-in Commands

Once logged into the system console:

| Command | Description |
|---------|-------------|
| `webos-dashboard` | Show system dashboard |
| `webos-logs` | View Web OS logs (live) |
| `webos-restart` | Restart Web OS service |
| `webos-config` | Configuration utility menu |
| `nmtui` | WiFi/Network configuration |
| `htop` | Interactive process viewer |
| `ip addr` | Network information |
| `systemctl status webos` | Check service status |
| `journalctl -u webos -f` | View Web OS logs |

## Web OS Features

### 40+ Built-in Apps
- Code Editor, Terminal, File Manager, Music Player, Video Player
- Image Viewer, PDF Viewer, Calculator, Calendar, Clock
- Weather, Notes, Whiteboard, Drawing Pad, Todo, Kanban
- Settings, System Monitor, Downloads, Notifications
- + Many more

### 6 AI Agents
- AI Assistant (ChatGPT-style)
- Code Generator
- Image Analyzer
- Data Analyzer
- Language Translator
- Math Solver

### 3 Games
- Snake
- Tetris
- Minesweeper

### Desktop Features
- Full desktop environment via browser
- Wallpaper gallery (10 themes)
- Lock screen (Ctrl+L)
- Task Manager (Ctrl+Shift+Esc)
- Right-click context menu
- Power menu (Shutdown, Restart, Logout)

## Updating Web OS

```bash
# SSH into the installed system or use Web OS Terminal
# Replace files
cp -r /path/to/new/web-os/* /opt/web-os/

# Restart
systemctl restart webos
```

## Uninstalling Web OS

### If installed as sole OS:
- Boot from any Linux live USB
- Repartition the disk (or reinstall Windows)

### If dual-boot:
- Boot into your other OS
- Delete the Web OS partitions using Disk Management (Windows) or GParted

## Troubleshooting

**Q: Can't access Web OS from browser**
- Check service: `systemctl status webos`
- Check IP: `ip addr` or `hostname -I`
- Ensure port 8080 is not blocked by firewall

**Q: Installation fails on UEFI systems**
- Disable **Secure Boot** in BIOS
- Try enabling CSM/Legacy boot mode

**Q: WiFi not working**
- Run `nmtui` to configure wireless
- Check if firmware is loaded: `dmesg | grep firmware`
- Install additional firmware: `apt install firmware-iwlwifi firmware-realtek`

**Q: Black screen on boot**
- Boot in **Safe Mode** from GRUB (nomodeset)
- After install, edit GRUB: add `nomodeset` to kernel params

**Q: Web OS doesn't auto-start**
- Check: `systemctl is-enabled webos`
- Enable: `systemctl enable webos`
- View logs: `journalctl -u webos -f`

**Q: How to change password**
- SSH into the system and run: `passwd admin`
- Or use Web OS Terminal app

**Q: ISO build fails in WSL**
- Run `wsl --update` in PowerShell (Admin)
- Make sure you have 10 GB free in WSL: `wsl df -h`
- Restart WSL: `wsl --shutdown` then relaunch

**Q: Rufus writes in DD mode but USB doesn't boot**
- Try **GPT partition scheme** instead of MBR
- Try a different USB port (USB 2.0 sometimes works better)
- Check if Secure Boot is disabled
- Try **BalenaEtcher** instead of Rufus

## Build Summary

| File | Path | Purpose |
|------|------|---------|
| `build-iso.sh` | `iso-builder/build-iso.sh` | Creates bootable ISO from Debian |
| `build-with-wsl.bat` | `iso-builder/build-with-wsl.bat` | Windows WSL-based ISO builder |
| `install-to-hdd.sh` | `iso-builder/install-to-hdd.sh` | Hard drive installer (4 modes) |
| `Dockerfile` | `iso-builder/Dockerfile` | Docker-based ISO builder |
| `webos.service` | Generated in ISO | Systemd service for auto-start |
| Output ISO | `dist/web-os-5.0-x86_64.iso` | Bootable OS image (~1-2 GB) |

---

Web OS v5.0 Ultimate — Built with Python, Flask, and JavaScript
