#!/bin/bash
# Web OS v5.0 - Installation Script for Linux
# Two modes:
#   1. Systemd service (run on existing Linux)
#   2. Bootable ISO builder (create standalone OS)

set -e

if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root: sudo bash install.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   🌐 Web OS v5.0 Ultimate Installer          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Select installation mode:"
echo "  1) Install as systemd service (run on existing Linux)"
echo "  2) Install as standalone OS (bootable ISO for hard drive)"
echo "  3) Build bootable USB ISO (for installing like Windows/Linux)"
echo ""
read -rp "Choice [1-3]: " mode

case $mode in
    1)
        INSTALL_DIR="/opt/webos"
        echo "📦 Installing Web OS to $INSTALL_DIR..."

        rm -rf "$INSTALL_DIR"
        cp -r "$SCRIPT_DIR" "$INSTALL_DIR"
        cd "$INSTALL_DIR"

        echo "📦 Installing Python dependencies..."
        pip3 install -r requirements.txt 2>/dev/null || pip install -r requirements.txt 2>/dev/null

        cat > /etc/systemd/system/webos.service << 'EOF'
[Unit]
Description=Web OS v5.0 - Complete Web-Based Operating System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/webos
ExecStart=/usr/bin/python3 /opt/webos/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

        systemctl daemon-reload
        systemctl enable webos.service
        systemctl start webos.service

        echo ""
        echo "✅ Web OS installed successfully!"
        echo "   Service: webos.service"
        echo "   Status: $(systemctl is-active webos.service)"
        echo "   Access: http://localhost:8080"
        echo "   Login:  admin / admin"
        echo ""
        echo "   Commands:"
        echo "   sudo systemctl start|stop|status webos"
        echo "   sudo journalctl -u webos -f"
        ;;

    2|3)
        echo "🛠️  Installing ISO build dependencies..."
        apt-get update
        apt-get install -y debootstrap grub-pc-bin grub-efi-amd64-bin xorriso squashfs-tools

        echo "🔨 Building Web OS bootable ISO..."
        bash "$SCRIPT_DIR/iso-builder/build-iso.sh"

        echo ""
        echo "✅ ISO built successfully!"
        echo "   File: $SCRIPT_DIR/dist/web-os-5.0-x86_64.iso"
        echo ""
        echo "📝 Next steps:"
        echo "   1. Write ISO to USB:"
        echo "      sudo dd if=$SCRIPT_DIR/dist/web-os-5.0-x86_64.iso of=/dev/sdX bs=4M status=progress"
        echo "   2. Boot from USB on target PC"
        echo "   3. Choose 'Install to Hard Drive' from GRUB menu"
        echo ""
        echo "   Or on Windows, use Rufus: https://rufus.ie"
        ;;
esac
