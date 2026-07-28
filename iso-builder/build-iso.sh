#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# Web OS v1.0 Ultimate — Complete Bootable ISO Builder
# Creates a full standalone Linux ISO that boots directly
# on PC hardware and auto-starts Web OS
# ═══════════════════════════════════════════════════════
set -euo pipefail

VERSION="1.0"
ISO_NAME="web-os-${VERSION}-x86_64.iso"
WORK_DIR="/tmp/webos-iso-build"
OUTPUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/dist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEBOS_SRC="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

unmount_virtual_fs() {
    local rootfs="${1:-$WORK_DIR/rootfs}"
    if [[ -d "$rootfs" ]]; then
        sudo umount -f -l "$rootfs/dev/pts" 2>/dev/null || true
        sudo umount -f -l "$rootfs/dev" 2>/dev/null || true
        sudo umount -f -l "$rootfs/sys" 2>/dev/null || true
        sudo umount -f -l "$rootfs/proc" 2>/dev/null || true
    fi
}

cleanup() {
    info "Cleaning up..."
    unmount_virtual_fs "$WORK_DIR/rootfs"
    if [[ ! -c /dev/null ]]; then
        sudo mknod -m 666 /dev/null c 1 3 2>/dev/null || true
    fi
    sudo rm -rf "$WORK_DIR" 2>/dev/null || true
}
trap cleanup EXIT

check_deps() {
    local deps=("debootstrap" "grub-mkrescue" "xorriso" "mksquashfs" "cpio")
    local missing=()
    for d in "${deps[@]}"; do
        if ! command -v "$d" &>/dev/null; then
            missing+=("$d")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        err "Missing required tools: ${missing[*]}"
        echo "  Install them:"
        echo "  sudo apt update"
        echo "  sudo apt install -y debootstrap grub-pc-bin grub-efi-amd64-bin xorriso squashfs-tools cpio"
        exit 1
    fi
    ok "All build dependencies found"
}

create_rootfs() {
    local rootfs="$1"
    info "Creating Debian root filesystem (clean minimal base)..."

    sudo debootstrap --arch=amd64 --components=main,contrib,non-free,non-free-firmware --include="\
        ca-certificates,locales,sudo,wget,curl,gpg,systemd,systemd-sysv\
    " bookworm "$rootfs" http://deb.debian.org/debian

    # Ensure /dev/null exists in host
    if [[ ! -c /dev/null ]]; then
        sudo mknod -m 666 /dev/null c 1 3 2>/dev/null || true
    fi

    # Copy host DNS configuration for chroot internet access
    sudo cp -L /etc/resolv.conf "$rootfs/etc/resolv.conf" 2>/dev/null || true

    info "Mounting virtual filesystems in chroot..."
    sudo mount -t proc proc "$rootfs/proc" 2>/dev/null || true
    sudo mount -t sysfs sysfs "$rootfs/sys" 2>/dev/null || true
    sudo mount -t devtmpfs devtmpfs "$rootfs/dev" 2>/dev/null || true
    sudo mkdir -p "$rootfs/dev/pts"
    sudo mount -t devpts devpts "$rootfs/dev/pts" 2>/dev/null || true

    if [[ ! -c "$rootfs/dev/null" ]]; then
        sudo mknod -m 666 "$rootfs/dev/null" c 1 3 2>/dev/null || true
    fi

    info "Configuring Apt repositories..."
    sudo tee "$rootfs/etc/apt/sources.list" > /dev/null << 'SOURCES'
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://deb.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm-updates main contrib non-free non-free-firmware
SOURCES

    info "Installing kernel, system, network, and GUI packages inside chroot..."
    sudo chroot "$rootfs" env DEBIAN_FRONTEND=noninteractive apt-get update
    sudo chroot "$rootfs" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        linux-image-amd64 grub-pc-bin grub-efi-amd64-bin grub-efi-amd64-signed \
        dbus polkitd network-manager wireless-tools firmware-linux firmware-realtek firmware-iwlwifi \
        python3 python3-pip python3-venv python3-dev \
        nano vim htop iotop iftop lsof net-tools iproute2 tmux screen \
        zip unzip gzip xz-utils bzip2 dosfstools rsync ntfs-3g \
        plymouth plymouth-themes cryptsetup lvm2 parted gdisk man-db less \
        firefox-esr xdg-utils xorg openbox chromium xserver-xorg xinit x11-utils \
        mesa-utils fonts-dejavu-core fonts-liberation pulseaudio alsa-utils

    sudo mkdir -p "$rootfs/opt/web-os"
    sudo cp -r "$WEBOS_SRC"/* "$rootfs/opt/web-os/"
    sudo rm -rf "$rootfs/opt/web-os/iso-builder" "$rootfs/opt/web-os/dist" 2>/dev/null || true
    ok "Base system created with all tools"
}

install_python_packages() {
    local rootfs="$1"
    info "Installing Python packages..."
    sudo chroot "$rootfs" bash -c '
        pip3 install flask flask-cors wsgidav cheroot requests psutil pillow \
            watchdog cryptography mutagen paramiko --break-system-packages 2>/dev/null || \
        pip3 install flask flask-cors wsgidav cheroot requests psutil pillow \
            watchdog cryptography mutagen paramiko
    ' 2>&1 | tail -5
    ok "Python packages installed"
}

create_plymouth_theme() {
    local rootfs="$1"
    info "Creating Plymouth boot splash theme..."
    local theme_dir="$rootfs/usr/share/plymouth/themes/webos"
    sudo mkdir -p "$theme_dir"

    sudo tee "$theme_dir/webos.plymouth" > /dev/null << 'PLYMOUTH'
[Plymouth Theme]
Name=Web OS 6.0
Description=Web OS Ultimate Edition Boot Splash
ModuleName=script
PLYMOUTH

    sudo tee "$theme_dir/webos.script" > /dev/null << 'SCRIPT'
wallpaper = Image("wallpaper.png");
water_circle = Image("circle.png");

fun refresh (){
    wal = wallpaper.Scale(screen_width, screen_height).Wrapped(0,0);
    wal.SetOpacity(0.3);
    circle = water_circle.Scale(150,150).Wrapped(screen_width/2 - 75, screen_height/2 - 75);
    circle.SetOpacity(0.8);
    wal.Compose(circle);
    text = Text("Web OS v1.0").SetFont("DejaVu Bold", 28).SetColor(0.49, 0.42, 1.0, 1.0);
    text.SetX(screen_width / 2 - text.GetWidth() / 2);
    text.SetY(screen_height / 2 + 60);
    wal.Compose(text);
    text2 = Text("Loading...").SetFont("DejaVu", 14).SetColor(0.5, 0.5, 0.7, 0.8);
    text2.SetX(screen_width / 2 - text2.GetWidth() / 2);
    text2.SetY(screen_height / 2 + 100);
    wal.Compose(text2);
    wal.Activate();
}
SCRIPT

    # Create simple wallpaper image using python
    sudo chroot "$rootfs" bash -c '
        python3 -c "
from PIL import Image, ImageDraw, ImageFont
w, h = 1920, 1080
img = Image.new(\"RGBA\", (w, h), (10, 10, 26, 255))
draw = ImageDraw.Draw(img)
for i in range(0, w, 4):
    c = int(10 + (i/w) * 20)
    draw.line([(i,0),(i,h)], fill=(c, c-5, c+10, 255))
draw.ellipse([w//2-80, h//2-80, w//2+80, h//2+80], fill=(124, 107, 255, 60))
draw.ellipse([w//2-60, h//2-60, w//2+60, h//2+60], fill=(51, 199, 72, 40))
img.save(\"/usr/share/plymouth/themes/webos/wallpaper.png\")
img2 = Image.new(\"RGBA\", (200,200), (0,0,0,0))
d2 = ImageDraw.Draw(img2)
d2.ellipse([10,10,190,190], outline=(124,107,255,100), width=3)
d2.ellipse([30,30,170,170], outline=(51,199,72,80), width=2)
img2.save(\"/usr/share/plymouth/themes/webos/circle.png\")
        "
    ' 2>/dev/null || true
    sudo chroot "$rootfs" plymouth-set-default-theme webos 2>/dev/null || true
    ok "Plymouth boot splash configured"
}

configure_system() {
    local rootfs="$1"
    info "Configuring system..."

    # Hostname
    echo "webos" | sudo tee "$rootfs/etc/hostname" > /dev/null
    sudo tee "$rootfs/etc/hosts" > /dev/null << 'HOSTS'
127.0.0.1   localhost
127.0.1.1   webos
::1         localhost ip6-localhost ip6-loopback
HOSTS

    # Network - DHCP + WiFi
    sudo mkdir -p "$rootfs/etc/netplan"
    sudo tee "$rootfs/etc/netplan/01-netcfg.yaml" > /dev/null << 'NETPLAN'
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0: { dhcp4: true }
    en*: { dhcp4: true }
    wl*: { dhcp4: true }
NETPLAN

    # Web OS systemd service
    sudo mkdir -p "$rootfs/etc/systemd/system"
    sudo tee "$rootfs/etc/systemd/system/webos.service" > /dev/null << 'SERVICE'
[Unit]
Description=Web OS v1.0 Ultimate - Web-Based Operating System
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/web-os
ExecStart=/usr/bin/python3 /opt/web-os/main.py
Restart=always
RestartSec=2
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

    # Auto-login on tty1
    sudo mkdir -p "$rootfs/etc/systemd/system/getty@tty1.service.d"
    sudo tee "$rootfs/etc/systemd/system/getty@tty1.service.d/override.conf" > /dev/null << 'GETTY'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear %I 38400 linux
GETTY

    # Issue banner
    sudo tee "$rootfs/etc/issue" > /dev/null << 'BANNER'
###################################################
#                                                 #
#     Web OS v1.0 Ultimate - Standalone OS        #
#                                                 #
#     Access from any browser:                    #
#     http://localhost:8080                       #
#     http://webos:8080                           #
#                                                 #
#     Login: admin / admin                        #
#                                                 #
#     Commands: systemctl status webos            #
#               journalctl -u webos -f            #
#               nmtui (WiFi setup)                #
#               webos-config (settings)           #
#                                                 #
###################################################
BANNER

    # /root/.bashrc with Web OS dashboard
    sudo tee "$rootfs/root/.bashrc" > /dev/null << 'BASHRC'
export PS1='\[\e[1;34m\]\u@webos\[\e[0m\]:\[\e[1;33m\]\w\[\e[0m\]\$ '

webos_dashboard() {
    clear
    local ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    local cpu=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}') 
    local mem=$(free -m | awk '/Mem:/ {print $3 "MB / " $2 "MB"}')
    local disk=$(df -h / | awk 'NR==2 {print $3 " / " $2 " (" $5 ")"}')
    local webos_status=$(systemctl is-active webos.service 2>/dev/null)
    local uptime_info=$(uptime -p | sed 's/up //')
    echo ""
    echo "  ================================================"
    echo "      Web OS v1.0 Ultimate - System Dashboard"
    echo "  ================================================"
    echo ""
    echo "  Hostname    : $(hostname)"
    echo "  IP Address  : ${ip:-Not connected}"
    echo "  Kernel      : $(uname -r)"
    echo "  Uptime      : $uptime_info"
    echo "  Web OS      : ${webos_status:-unknown}"
    echo ""
    echo "  CPU         : $cpu%"
    echo "  Memory      : $mem"
    echo "  Disk        : $disk"
    echo ""
    echo "  -------------------------------------------------"
    echo ""
    echo "  Web UI      : http://${ip:-localhost}:8080"
    echo "  Desktop     : http://${ip:-localhost}:8080/desktop"
    echo "  Login       : admin / admin"
    echo ""
    echo "  Commands:"
    echo "    webos-dashboard  - Show this dashboard"
    echo "    webos-logs       - Show Web OS logs"
    echo "    webos-restart    - Restart Web OS"
    echo "    nmtui            - Configure WiFi/Network"
    echo "    htop             - Process viewer"
    echo "    mc               - File manager (if installed)"
    echo ""
    echo "  ================================================"
    echo ""
}
alias webos-logs='journalctl -u webos -f --no-hostname'
alias webos-restart='systemctl restart webos && echo "[OK] Web OS restarted"'
alias ll='ls -la'
alias la='ls -A'
alias ..='cd ..'
alias ip='ip -c'

# Show dashboard on login
clear
echo "  Booting Web OS v1.0 Ultimate..."
sleep 1
webos_dashboard
echo "  [Press ENTER for terminal]"
BASHRC

    # Enable services
    sudo chroot "$rootfs" systemctl enable webos.service
    sudo chroot "$rootfs" systemctl enable systemd-networkd
    sudo chroot "$rootfs" systemctl enable NetworkManager
    sudo chroot "$rootfs" systemctl enable plymouth-start 2>/dev/null || true

    # Set timezone to UTC (configurable)
    sudo chroot "$rootfs" ln -sf /usr/share/zoneinfo/UTC /etc/localtime

    # Create webos-config utility
    sudo mkdir -p "$rootfs/usr/local/bin"
    sudo tee "$rootfs/usr/local/bin/webos-config" > /dev/null << 'CONF'
#!/bin/bash
WEBOS_DIR="/opt/web-os"
echo ""
echo "  Web OS Configuration Utility"
echo "  ============================"
echo ""
echo "  1) View Web OS status"
echo "  2) Restart Web OS"
echo "  3) View Web OS logs (follow)"
echo "  4) Change Web OS port (default: 8080)"
echo "  5) Reset admin password"
echo "  6) Update Web OS from source"
echo "  7) Open Web OS dashboard"
echo "  8) Exit"
echo ""
read -rp "  Select option [1-8]: " opt
case $opt in
    1) systemctl status webos --no-pager ;;
    2) systemctl restart webos && echo "  [OK] Web OS restarted" ;;
    3) journalctl -u webos -f --no-hostname ;;
    4) read -rp "  New port (e.g., 9090): " port; sed -i "s/HTTP_PORT = .*/HTTP_PORT = $port/" "$WEBOS_DIR/config.py"; echo "  [OK] Port changed. Restart Web OS." ;;
    5) python3 "$WEBOS_DIR/server/database.py" && echo "  Reset done. Login with admin/admin" ;;
    6) echo "  To update, replace /opt/web-os with new version" ;;
    7) webos-dashboard ;;
    8) exit 0 ;;
esac
CONF
    sudo chmod +x "$rootfs/usr/local/bin/webos-config"

    ok "System fully configured with dashboard, aliases, and utilities"
}

configure_display() {
    local rootfs="$1"
    info "Configuring graphical display (Xorg + Openbox + Chromium kiosk)..."

    # Create X11 config
    sudo mkdir -p "$rootfs/etc/X11/xinit"
    sudo tee "$rootfs/etc/X11/xinit/xinitrc" > /dev/null << 'XINITRC'
#!/bin/bash
# Web OS Kiosk Desktop — Auto-starts Chromium in fullscreen

# Set up display
export DISPLAY=:0
export XAUTHORITY=/root/.Xauthority

# Wait for X server to be ready
sleep 1

# Start Openbox window manager
openbox --config-file /etc/xdg/openbox/rc.xml --startup /usr/share/webos/kiosk-start.sh &

# Start Chromium in kiosk mode pointing to Web OS
chromium \
    --kiosk \
    --no-first-run \
    --disable-features=TranslateUI \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --noerrdialogs \
    --disable-component-update \
    --disable-background-networking \
    --disable-sync \
    --disable-default-apps \
    --disable-extensions \
    --disable-translate \
    --disable-features=ChromeWhatsNewUI \
    --disable-features=PrivacySandboxSettings \
    --disable-features=MediaRouter \
    --no-default-browser-check \
    --check-for-update-interval=31536000 \
    --user-data-dir=/root/.webos-chromium \
    http://localhost:8080/desktop &
XINITRC
    sudo chmod +x "$rootfs/etc/X11/xinit/xinitrc"

    # Create kiosk startup script
    sudo mkdir -p "$rootfs/usr/share/webos"
    sudo tee "$rootfs/usr/share/webos/kiosk-start.sh" > /dev/null << 'KIOSK'
#!/bin/bash
# Kiosk post-startup tweaks
xset s off -dpms
xset s noblank
while true; do
    # Attempt to keep Chromium focused and alive
    wmctrl -a "Web OS" 2>/dev/null || true
    sleep 30
done
KIOSK
    sudo chmod +x "$rootfs/usr/share/webos/kiosk-start.sh"

    # Create Openbox config for kiosk
    sudo mkdir -p "$rootfs/etc/xdg/openbox"
    sudo tee "$rootfs/etc/xdg/openbox/rc.xml" > /dev/null << 'OPENBOX'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <desktops>
    <number>1</number>
    <names><name>Desktop</name></names>
  </desktops>
  <resistance><strength>0</strength></resistance>
  <mouse><drag>Disable</drag></mouse>
  <focus><focusNew>yes</focusNew></focus>
  <placement><policy>UnderMouse</policy></placement>
  <theme>
    <name>Clearlooks</name>
    <titleLayout>NL</titleLayout>
    <keepBorder>no</keepBorder>
    <cornerRadius>0</cornerRadius>
  </theme>
  <applications>
    <application class="Chromium">
      <desktop>1</desktop>
      <fullscreen>yes</fullscreen>
      <maximized>yes</maximized>
      <focus>yes</focus>
    </application>
  </applications>
</openbox_config>
OPENBOX

    # Add startx to root's bash profile for auto-start on tty1
    sudo tee "$rootfs/root/.bash_profile" > /dev/null << 'BASHPROFILE'
#!/bin/bash
# Auto-start X11 desktop on tty1
if [[ -z "$DISPLAY" && "$(tty)" =~ /dev/tty1 ]]; then
    clear
    echo ""
    echo "  Starting Web OS Desktop..."
    echo "  (Press Ctrl+Alt+F2 for console)"
    sleep 1
    startx &>/dev/null &
    exit 0
fi
BASHPROFILE

    # Create a desktop entry for Chromium shortcut
    sudo mkdir -p "$rootfs/usr/share/applications"
    sudo tee "$rootfs/usr/share/applications/webos-kiosk.desktop" > /dev/null << 'DESKTOP'
[Desktop Entry]
Name=Web OS
Comment=Web OS Desktop Environment
Exec=chromium --kiosk http://localhost:8080/desktop
Terminal=false
Type=Application
Categories=Network;WebBrowser;
DESKTOP

    # Enable display manager auto-start (just use xinit on tty1)
    # This is already handled by .bash_profile + getty autologin

    ok "Graphical display configured (Xorg + Openbox + Chromium kiosk)"
}

create_grub_config() {
    local iso_dir="$1"
    info "Creating GRUB configuration with multiple boot options..."

    sudo mkdir -p "$iso_dir/boot/grub"

    # GRUB theme
    sudo mkdir -p "$iso_dir/boot/grub/themes/webos"
    sudo tee "$iso_dir/boot/grub/themes/webos/theme.txt" > /dev/null << 'THEME'
title-text: "Web OS v1.0 Ultimate"
title-color: "#7c6bff"
title-font: "DejaVu Sans Bold 18"
desktop-image: "background.png"
desktop-color: "#0a0a1a"
terminal-font: "DejaVu Sans Mono 12"
+ boot_menu {
    left = 25%
    top = 20%
    width = 50%
    height = 60%
    item_color = "#8888aa"
    selected_item_color = "#7c6bff"
    item_height = 32
    item_padding = 8
    item_spacing = 4
    scrollbar = true
}
+ progress_bar {
    id = "progress"
    x = 25%
    y = 85%
    width = 50%
    height = 6
    bar_color = "#7c6bff"
}
THEME

    # Background image for GRUB
    sudo python3 -c "
from PIL import Image, ImageDraw, ImageFont
w, h = 1920, 1080
img = Image.new('RGBA', (w, h), (10, 10, 26, 255))
draw = ImageDraw.Draw(img)
# Gradient
for i in range(h):
    c = int(10 + (i/h) * 15)
    draw.line([(0,i),(w,i)], fill=(c, c-5, c+5, 255))
# Glow
for x_off, y_off, r, col in [(w//2, h//3, 300, (124,107,255,30)), (w//3, 2*h//3, 200, (51,199,72,20)), (2*w//3, 2*h//3, 200, (105,180,255,20))]:
    for i in range(r, 0, -1):
        alpha = int(col[3] * (1 - i/r))
        c = (col[0], col[1], col[2], alpha)
        draw.ellipse([x_off-i, y_off-i, x_off+i, y_off+i], fill=c)
img.save('$iso_dir/boot/grub/themes/webos/background.png')
" 2>/dev/null || true

    # Main GRUB config
    sudo tee "$iso_dir/boot/grub/grub.cfg" > /dev/null << 'GRUB'
set default="0"
set timeout=10

if loadfont unicode ; then
    set gfxmode=1920x1080x32,auto
    set gfxpayload=keep
    terminal_output gfxterm
fi

set theme=/boot/grub/themes/webos/theme.txt
insmod all_video
insmod gfxterm
insmod png
insmod part_gpt
insmod ext2
insmod ntfs
insmod chain

# Submenu: Boot Web OS
menuentry "Web OS v1.0 Ultimate - Boot Live" --class os {
    echo "Starting Web OS v1.0 Ultimate..."
    linux /live/vmlinuz boot=live components quiet splash plymouth.theme=webos
    initrd /live/initrd
}

menuentry "Web OS v1.0 Ultimate - Boot Live (Safe Mode)" --class os {
    echo "Starting Web OS in safe mode..."
    linux /live/vmlinuz boot=live components nomodeset acpi=off noapic nolapic
    initrd /live/initrd
}

menuentry "Web OS v1.0 Ultimate - Boot Live (Verbose)" --class os {
    echo "Starting Web OS in verbose mode..."
    linux /live/vmlinuz boot=live components debug nosplash
    initrd /live/initrd
}

menuentry "Web OS v1.0 Ultimate - Install to Hard Drive" --class install {
    echo "Starting Web OS installer..."
    linux /live/vmlinuz boot=live components webos-install console=tty0
    initrd /live/initrd
}

# Submenu: Advanced
submenu "Advanced Options" --class tools {
    menuentry "Test Memory (Memtest86+)" --class memtest {
        linux /boot/memtest86+.bin
    }

    menuentry "Boot from First Hard Drive" --class hdd {
        insmod chain
        set root=(hd0)
        chainloader +1
    }

    menuentry "Boot from First Hard Drive (UEFI)" --class hdd {
        insmod chain
        insmod fat
        insmod ext2
        search --set=root --file /EFI/BOOT/BOOTX64.EFI
        chainloader /EFI/BOOT/BOOTX64.EFI
    }

    menuentry "Reboot" --class reboot {
        reboot
    }

    menuentry "Shutdown" --class shutdown {
        halt
    }
}
GRUB
    ok "GRUB configuration created with 8 boot options"
}

create_iso_image() {
    local rootfs="$1"
    local iso_out="$2"
    local iso_dir="$WORK_DIR/iso"

    info "Creating ISO structure..."
    mkdir -p "$iso_dir/live" "$iso_dir/boot/grub"

    # Unmount virtual filesystems before squashfs creation
    sudo umount -l "$rootfs/dev/pts" 2>/dev/null || true
    sudo umount -l "$rootfs/dev" 2>/dev/null || true
    sudo umount -l "$rootfs/sys" 2>/dev/null || true
    sudo umount -l "$rootfs/proc" 2>/dev/null || true

    # Create squashfs
    info "Creating compressed filesystem (this will take several minutes)..."
    sudo mksquashfs "$rootfs" "$iso_dir/live/filesystem.squashfs" -comp xz -b 1M -Xbcj x86 -e boot
    ok "Filesystem compressed"

    # Copy kernel and initrd
    cp "$rootfs/boot/vmlinuz-"* "$iso_dir/live/vmlinuz" 2>/dev/null
    cp "$rootfs/boot/initrd.img-"* "$iso_dir/live/initrd" 2>/dev/null
    ok "Kernel and initramfs copied"

    # Create GRUB and ISO
    create_grub_config "$iso_dir"

    # Copy memtest
    cp "$iso_dir/../memtest86plus.bin" "$iso_dir/boot/memtest86+.bin" 2>/dev/null || true

    info "Building final bootable ISO (UEFI + BIOS)..."
    sudo grub-mkrescue -o "$iso_out" "$iso_dir" --verbose 2>&1 | tail -5
    ok "ISO created successfully"
}

download_memtest() {
    local dest="$1"
    info "Downloading Memtest86+..."
    wget -q "https://memtest.org/download/7.00/memtest86+-7.00.iso.gz" -O /tmp/memtest.iso.gz 2>/dev/null || return 0
    gunzip -f /tmp/memtest.iso.gz 2>/dev/null || return 0
    mkdir -p /tmp/memtest-mount
    mount -o loop /tmp/memtest.iso /tmp/memtest-mount 2>/dev/null || return 0
    cp /tmp/memtest-mount/memtest86+-* "$dest" 2>/dev/null || true
    umount /tmp/memtest-mount 2>/dev/null || true
}

main() {
    echo ""
    echo "================================================"
    echo "  Web OS v${VERSION} Ultimate - Full OS ISO Builder"
    echo "  Creates a standalone bootable PC operating system"
    echo "================================================"
    echo ""

    if [[ $EUID -ne 0 ]]; then
        err "Must run as root: sudo bash build-iso.sh"
        exit 1
    fi

    check_deps

    rm -rf "$WORK_DIR"
    mkdir -p "$WORK_DIR" "$OUTPUT_DIR"

    local rootfs="$WORK_DIR/rootfs"

    create_rootfs "$rootfs"
    install_python_packages "$rootfs"
    configure_system "$rootfs"
    configure_display "$rootfs"
    create_plymouth_theme "$rootfs"
    unmount_virtual_fs "$rootfs"

    download_memtest "$WORK_DIR"
    create_iso_image "$rootfs" "$OUTPUT_DIR/$ISO_NAME"

    local size=$(du -h "$OUTPUT_DIR/$ISO_NAME" | cut -f1)
    echo ""
    echo "================================================"
    echo "  ISO Built Successfully!"
    echo "================================================"
    echo ""
    echo "  File    : $OUTPUT_DIR/$ISO_NAME"
    echo "  Size    : $size"
    echo "  Type    : Bootable Live + Install ISO"
    echo "  Boot    : UEFI + Legacy BIOS"
    echo ""
    echo "  Next steps:"
    echo "  1. Write ISO to USB (8GB+) with Rufus:"
    echo "     - Open Rufus (https://rufus.ie)"
    echo "     - Select USB drive"
    echo "     - Select: $ISO_NAME"
    echo "     - Partition scheme: MBR (or GPT for UEFI)"
    echo "     - Click START"
    echo "     - Write in DD Image mode if asked"
    echo ""
    echo "  2. Boot from USB on target PC"
    echo "     - Press F12/F2/Del at startup"
    echo "     - Select USB drive"
    echo ""
    echo "  3. From GRUB menu, choose:"
    echo "     - 'Boot Live' to try without installing"
    echo "     - 'Install to Hard Drive' for permanent install"
    echo ""
    echo "  4. Access Web OS at: http://localhost:8080"
    echo "     Login: admin / admin"
    echo ""
    echo "================================================"
    echo ""
}

main "$@"
