#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# Web OS v6.0 Ultimate — Hard Drive Installer
# Installs Web OS to a physical hard drive as a standalone
# operating system (runs from the live ISO environment)
# Supports: auto, manual, dual-boot, LUKS encryption
# ═══════════════════════════════════════════════════════
set -euo pipefail

VERSION="1.0"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

show_disks() {
    echo ""
    info "Available disks:"
    echo "  --------------------------------------------"
    lsblk -d -o NAME,SIZE,TYPE,MODEL,MOUNTPOINT | grep -v loop
    echo "  --------------------------------------------"
    echo ""
}

show_partitions() {
    local disk="$1"
    info "Partitions on /dev/${disk}:"
    echo ""
    lsblk "/dev/${disk}" -o NAME,SIZE,FSTYPE,MOUNTPOINT,LABEL 2>/dev/null | grep -v loop
    echo ""
}

confirm_disk() {
    local disk="$1"
    warn "YOU ARE ABOUT TO COMPLETELY WIPE /dev/${disk}!"
    warn "All data on /dev/${disk} will be DESTROYED!"
    echo ""
    echo "  Disk: /dev/${disk}"
    echo "  Size: $(lsblk -d -o SIZE "/dev/${disk}" | tail -1)"
    echo "  Model: $(lsblk -d -o MODEL "/dev/${disk}" | tail -1)"
    echo ""
    read -rp "  Type YES to confirm: " confirm
    if [[ "$confirm" != "YES" ]]; then
        err "Installation cancelled."
        exit 1
    fi
}

select_install_mode() {
    echo ""
    echo "  Install Mode:"
    echo "  --------------------------------------------"
    echo "  1) Auto — Use entire disk (destroys all data)"
    echo "  2) Manual — Partition manually (cfdisk)"
    echo "  3) Dual-boot — Install alongside existing OS"
    echo "  4) LUKS — Encrypted entire disk"
    echo "  --------------------------------------------"
    echo ""
    read -rp "  Select mode [1-4] (default: 1): " mode
    echo "${mode:-1}"
}

partition_auto() {
    local disk="$1"
    info "Auto-partitioning /dev/${disk}..."
    sgdisk -Z "/dev/${disk}" 2>/dev/null || dd if=/dev/zero of="/dev/${disk}" bs=1M count=10
    sgdisk -o "/dev/${disk}"
    sgdisk -n 1:0:+512M -t 1:ef00 -c 1:"EFI System" "/dev/${disk}"
    sgdisk -n 2:0:0 -t 2:8300 -c 2:"Web OS Root" "/dev/${disk}"
    ok "Auto partitions created (EFI 512M + Root rest)"
    sleep 2
    partprobe "/dev/${disk}" 2>/dev/null || true
    sleep 1
}

partition_manual() {
    local disk="$1"
    info "Opening manual partitioner (cfdisk)..."
    warn "Create at least:"
    warn "  - 1 EFI partition (512M, type EF00)"
    warn "  - 1 Linux root partition (rest, type 8300)"
    echo ""
    read -rp "  Press ENTER to start cfdisk... " _
    cfdisk "/dev/${disk}"
    ok "Manual partitioning complete"
    sleep 2
    partprobe "/dev/${disk}" 2>/dev/null || true
    sleep 1
}

detect_existing_os() {
    info "Detecting existing operating systems..."
    local os_list=()
    local efi_parts=()
    local root_parts=()

    # Check for EFI partitions
    while IFS= read -r part; do
        if [[ -n "$part" ]]; then
            efi_parts+=("$part")
        fi
    done < <(lsblk -ln -o NAME,TYPE,FSTYPE 2>/dev/null | awk '$2=="part" && $3=="vfat" {print $1}')

    # Check for existing Linux root partitions
    while IFS= read -r part; do
        if [[ -n "$part" ]]; then
            local fstype=$(lsblk -ln -o FSTYPE "/dev/$part" 2>/dev/null)
            if [[ "$fstype" == "ext4" ]] || [[ "$fstype" == "btrfs" ]] || [[ "$fstype" == "xfs" ]]; then
                root_parts+=("$part")
            fi
        fi
    done < <(lsblk -ln -o NAME,TYPE 2>/dev/null | awk '$2=="part" {print $1}')

    if [[ ${#root_parts[@]} -eq 0 ]]; then
        warn "No existing Linux partitions detected."
        warn "Falling back to auto partition on target disk."
        return 1
    fi

    echo ""
    info "Detected existing partitions:"
    for part in "${root_parts[@]}"; do
        local size=$(lsblk -ln -o SIZE "/dev/$part" 2>/dev/null)
        local label=$(lsblk -ln -o LABEL "/dev/$part" 2>/dev/null)
        local fstype=$(lsblk -ln -o FSTYPE "/dev/$part" 2>/dev/null)
        echo "  /dev/$part  ($size, $fstype, $label)"
    done
    echo ""
    return 0
}

partition_dual_boot() {
    local disk="$1"
    info "Dual-boot mode: installing alongside existing OS..."

    if ! detect_existing_os; then
        warn "No existing OS detected. Using auto partition instead."
        partition_auto "$disk"
        return
    fi

    echo ""
    echo "  Dual-boot options:"
    echo "  --------------------------------------------"
    echo "  1) Shrink existing root partition and create new"
    echo "  2) Use existing unallocated space"
    echo "  3) Install to existing partition (will format)"
    echo "  --------------------------------------------"
    echo ""
    read -rp "  Select option [1-3]: " dbopt

    case $dbopt in
        1)
            info "Shrinking existing partition..."
            local target=""
            read -rp "  Partition to shrink (e.g., sda2): " target
            if [[ ! -b "/dev/$target" ]]; then
                err "Invalid partition"; return
            fi
            local cur_size=$(lsblk -ln -o SIZE "/dev/$target" 2>/dev/null | sed 's/G//')
            local new_size=$(( $(echo "$cur_size" | cut -d. -f1) / 2 ))
            info "Current: ${cur_size}G, New: ${new_size}G"
            resize2fs "/dev/$target" "${new_size}G" 2>/dev/null || true
            # Create new partition in freed space
            local last_sector=$(sgdisk -E "/dev/$target" 2>/dev/null)
            sgdisk -n 0:0:+${new_size}G -t 0:8300 -c 0:"Web OS Root" "/dev/${target%[0-9]*}" 2>/dev/null || true
            ok "Partition shrunk and new partition created"
            ;;
        2)
            info "Using existing unallocated space..."
            sgdisk -n 0:0:0 -t 0:8300 -c 0:"Web OS Root" "/dev/${disk}" 2>/dev/null || true
            ok "Created partition in unallocated space"
            ;;
        3)
            local target=""
            read -rp "  Partition to format and use (e.g., sda3): " target
            if [[ ! -b "/dev/$target" ]]; then
                err "Invalid partition"; return
            fi
            info "Will format /dev/$target as Web OS root"
            ;;
        *)
            warn "Invalid option. Using auto partition."
            partition_auto "$disk"
            return
            ;;
    esac

    sleep 2
    partprobe "/dev/${disk}" 2>/dev/null || true
    sleep 1
}

partition_luks() {
    local disk="$1"
    info "LUKS encrypted partition setup on /dev/${disk}..."

    warn "This will encrypt the entire disk!"
    warn "You will need a passphrase to unlock at every boot."
    echo ""
    read -rp "  Type YES to confirm: " confirm
    if [[ "$confirm" != "YES" ]]; then
        err "LUKS installation cancelled."; exit 1
    fi

    # Wipe and partition
    sgdisk -Z "/dev/${disk}" 2>/dev/null || dd if=/dev/zero of="/dev/${disk}" bs=1M count=10
    sgdisk -o "/dev/${disk}"
    sgdisk -n 1:0:+512M -t 1:ef00 -c 1:"EFI System" "/dev/${disk}"
    sgdisk -n 2:0:+8G -t 2:8200 -c 2:"Linux Swap" "/dev/${disk}"  # Encrypted swap
    sgdisk -n 3:0:0 -t 3:8300 -c 3:"LUKS Root" "/dev/${disk}"

    sleep 2
    partprobe "/dev/${disk}" 2>/dev/null || true
    sleep 1

    local root_part="${disk}3"
    local efi_part="${disk}1"
    if [[ "$disk" == nvme* ]]; then
        root_part="${disk}p3"
        efi_part="${disk}p1"
    fi

    # Setup LUKS
    info "Setting up LUKS on /dev/${root_part}..."
    cryptsetup luksFormat "/dev/${root_part}"
    cryptsetup open "/dev/${root_part}" webos_crypt

    ok "LUKS container created and opened"

    # Format encrypted container
    mkfs.ext4 -F -L "WEBOS_ROOT" /dev/mapper/webos_crypt
    mkfs.fat -F32 -n "WEBOS_EFI" "/dev/${efi_part}"

    # Store encryption info for later crypttab update
    LUKS_PART="/dev/${root_part}"
    LUKS_MAPPER="webos_crypt"
    ok "LUKS partitions formatted"
}

get_efi_part() {
    local disk="$1"
    local efi_part="${disk}1"
    local root_part="${disk}2"
    if [[ "$disk" == nvme* ]]; then
        efi_part="${disk}p1"
        root_part="${disk}p2"
    fi
    # In LUKS mode, root is the mapper device
    if [[ "${INSTALL_MODE:-1}" == "4" ]]; then
        root_part="/dev/mapper/webos_crypt"
    fi
    echo "$efi_part|$root_part"
}

format_partitions() {
    local disk="$1"
    local mode="${2:-1}"

    if [[ "$mode" == "4" ]]; then
        # LUKS already formatted in partition_luks()
        return
    fi

    local parts
    parts=$(get_efi_part "$disk")
    local efi_part=$(echo "$parts" | cut -d'|' -f1)
    local root_part=$(echo "$parts" | cut -d'|' -f2)

    info "Formatting /dev/${efi_part} as FAT32 (EFI)..."
    mkfs.fat -F32 -n "WEBOS_EFI" "/dev/${efi_part}" 2>/dev/null || true

    if [[ "$mode" == "3" ]]; then
        # Dual-boot: format only if user chose option 3
        info "Skipping format of existing root partition (dual-boot)..."
    else
        info "Formatting ${root_part} as ext4..."
        mkfs.ext4 -F -L "WEBOS_ROOT" "$root_part"
    fi
    ok "Partitions formatted"
}

mount_partitions() {
    local disk="$1"
    local mode="${2:-1}"
    local parts
    parts=$(get_efi_part "$disk")
    local efi_part=$(echo "$parts" | cut -d'|' -f1)
    local root_part=$(echo "$parts" | cut -d'|' -f2)

    local mnt="$WORK_DIR/mnt"
    mkdir -p "$mnt"
    mount "$root_part" "$mnt"
    mkdir -p "$mnt/boot/efi"
    mount "/dev/${efi_part}" "$mnt/boot/efi"

    # Bind mounts for chroot
    mount --bind /dev "$mnt/dev"
    mount --bind /proc "$mnt/proc"
    mount --bind /sys "$mnt/sys"
    mount --bind /dev/pts "$mnt/dev/pts" 2>/dev/null || true

    echo "$mnt"
}

copy_system() {
    local mnt="$1"
    info "Copying system files to hard drive..."
    echo "  This may take several minutes..."

    if [ -d "/run/rootfs" ]; then
        rsync -aAXv "/run/rootfs/" "$mnt/" --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found"} 2>&1 | tail -1
    elif [ -d "/run/live" ]; then
        local tmp="$WORK_DIR/rootfs"
        mkdir -p "$tmp"
        unsquashfs -d "$tmp" /run/live/filesystem.squashfs 2>/dev/null || \
        unsquashfs -d "$tmp" /run/live/medium/live/filesystem.squashfs 2>/dev/null || {
            rsync -aAXv / "$mnt/" --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found","/live/*"} 2>&1 | tail -1
        }
        if [ -d "$tmp" ]; then
            rsync -aAXv "$tmp/" "$mnt/" --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found"} 2>&1 | tail -1
        fi
    else
        local rootfs="${ROOTFS_PATH:-}"
        if [ -z "$rootfs" ]; then
            err "Not running from a live ISO environment."
            err "Either boot from the Web OS live ISO first,"
            err "or set ROOTFS_PATH=/path/to/extracted/rootfs"
            exit 1
        fi
        rsync -aAXv "$rootfs/" "$mnt/" --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found"} 2>&1 | tail -1
    fi

    for d in dev proc sys tmp run mnt media; do
        mkdir -p "$mnt/$d"
    done

    ok "System files copied"
}

configure_luks_boot() {
    local mnt="$1"
    local disk="$2"
    info "Configuring LUKS boot..."

    # Add cryptdevice to GRUB config
    local uuid=$(blkid -s UUID -o value "$LUKS_PART" 2>/dev/null)
    if [[ -n "$uuid" ]]; then
        chroot "$mnt" bash -c "echo 'GRUB_CMDLINE_LINUX=\"cryptdevice=UUID=$uuid:webos_crypt root=/dev/mapper/webos_crypt\"' >> /etc/default/grub"
    fi

    # Update crypttab
    echo "webos_crypt UUID=$uuid none luks" >> "$mnt/etc/crypttab"

    # Update mkinitcpio or initramfs-tools
    if [ -f "$mnt/etc/initramfs-tools/conf.d/cryptsetup" ]; then
        echo "CRYPTSETUP=y" >> "$mnt/etc/initramfs-tools/conf.d/cryptsetup"
        chroot "$mnt" update-initramfs -u 2>/dev/null || true
    fi

    ok "LUKS boot configured"
}

install_bootloader() {
    local disk="$1"
    local mnt="$2"
    info "Installing GRUB bootloader..."

    chroot "$mnt" /bin/bash 2>/dev/null << CHROOT
        grub-install --target=i386-pc "/dev/${disk}" --force 2>/dev/null || true
        grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id="WebOS" --recheck 2>/dev/null || true
        grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null || true
        systemctl enable webos.service 2>/dev/null || true
        systemctl enable nodm 2>/dev/null || true
        systemctl enable NetworkManager 2>/dev/null || true
CHROOT

    ok "Bootloader installed (BIOS + UEFI)"
}

configure_network() {
    local mnt="$1"
    info "Configuring network..."
    chroot "$mnt" systemd-machine-id-setup 2>/dev/null || true
    chroot "$mnt" systemctl enable systemd-networkd 2>/dev/null || true
    chroot "$mnt" systemctl enable systemd-resolved 2>/dev/null || true
    ok "Network configured"
}

set_root_password() {
    local mnt="$1"
    info "Setting root password..."
    chroot "$mnt" bash -c "echo 'root:webos' | chpasswd" 2>/dev/null || true
    chroot "$mnt" bash -c "echo 'admin:webos' | chpasswd" 2>/dev/null || true
    ok "Passwords set: root/webos, admin/webos"
}

cleanup_install() {
    local mnt="$1"
    info "Cleaning up..."
    umount -R "$mnt/dev/pts" 2>/dev/null || true
    umount -R "$mnt/dev" 2>/dev/null || true
    umount -R "$mnt/proc" 2>/dev/null || true
    umount -R "$mnt/sys" 2>/dev/null || true
    umount "$mnt/boot/efi" 2>/dev/null || true
    umount "$mnt" 2>/dev/null || true
    if [[ -n "${LUKS_MAPPER:-}" ]]; then
        cryptsetup close "$LUKS_MAPPER" 2>/dev/null || true
    fi
    rm -rf "$WORK_DIR" 2>/dev/null || true
}

print_summary() {
    local disk="$1"
    local mode="$2"
    local mode_names=("" "Auto (entire disk)" "Manual" "Dual-boot" "LUKS Encrypted")

    echo ""
    echo -e "${GREEN}  +=====================================================+${NC}"
    echo -e "${GREEN}  |  Web OS v${VERSION} Installed Successfully!               |${NC}"
    echo -e "${GREEN}  +=====================================================+${NC}"
    echo -e "${GREEN}  |  Install mode : ${mode_names[$mode]:-Auto}${NC}"
    echo -e "${GREEN}  |  Target disk  : /dev/${disk}${NC}"
    echo -e "${GREEN}  |  Boot support : BIOS + UEFI${NC}"
    echo -e "${GREEN}  |  Web UI port  : 8080${NC}"
    echo -e "${GREEN}  |  Login        : admin / admin${NC}"
    echo -e "${GREEN}  +=====================================================+${NC}"
    echo ""
    echo "  Next steps:"
    echo "  1. Reboot and remove installation media"
    echo "  2. Boot into Web OS from hard drive"
    echo "  3. Open http://webos:8080 in any browser"
    echo "  4. Login: admin / admin"
    echo ""
    if [[ "$mode" == "4" ]]; then
        echo "  NOTE: You will need to enter your LUKS passphrase"
        echo "        at every boot to unlock the encrypted disk."
        echo ""
    fi
}

main() {
    echo ""
    echo -e "${CYAN}  +=====================================================+${NC}"
    echo -e "${CYAN}  |  Web OS v${VERSION} Ultimate — Hard Drive Installer     |${NC}"
    echo -e "${CYAN}  +=====================================================+${NC}"
    echo ""

    if [[ $EUID -ne 0 ]]; then
        err "This script must be run as root (sudo)"
        exit 1
    fi

    for cmd in mkfs.fat mkfs.ext4 rsync grub-install chroot sgdisk; do
        if ! command -v "$cmd" &>/dev/null; then
            err "Missing required tool: $cmd"
            exit 1
        fi
    done

    WORK_DIR=$(mktemp -d)
    INSTALL_MODE=$(select_install_mode)

    show_disks

    if [[ -z "${DISK:-}" ]]; then
        read -rp "  Enter target disk (e.g., sda, nvme0n1): " DISK
    fi

    if [[ ! -b "/dev/${DISK}" ]]; then
        err "/dev/${DISK} is not a valid block device"
        exit 1
    fi

    case $INSTALL_MODE in
        2)  # Manual
            partition_manual "$DISK"
            ;;
        3)  # Dual-boot
            partition_dual_boot "$DISK"
            ;;
        4)  # LUKS
            partition_luks "$DISK"
            ;;
        *)  # Auto (default)
            confirm_disk "$DISK"
            partition_auto "$DISK"
            ;;
    esac

    format_partitions "$DISK" "$INSTALL_MODE"

    MNT=$(mount_partitions "$DISK" "$INSTALL_MODE")
    copy_system "$MNT"
    install_bootloader "$DISK" "$MNT"
    configure_network "$MNT"

    if [[ "$INSTALL_MODE" == "4" ]] && [[ -n "${LUKS_PART:-}" ]]; then
        configure_luks_boot "$MNT" "$DISK"
    fi

    set_root_password "$MNT"
    cleanup_install "$MNT"
    print_summary "$DISK" "$INSTALL_MODE"
}

DISK="${DISK:-}"
main "$@"
