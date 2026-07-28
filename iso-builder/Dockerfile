# ═══════════════════════════════════════════════════════
# Web OS v1.0 — Docker ISO Builder
# Build the Web OS bootable ISO inside a Docker container
# ═══════════════════════════════════════════════════════
FROM debian:bookworm-slim AS builder

LABEL org.webos.version="1.0"
LABEL org.webos.description="Web OS Bootable ISO Builder"

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    debootstrap \
    grub-pc-bin \
    grub-efi-amd64-bin \
    grub-efi-amd64-signed \
    xorriso \
    squashfs-tools \
    cpio \
    gzip \
    wget \
    ca-certificates \
    python3 \
    python3-pip \
    rsync \
    dosfstools \
    mtools \
    && rm -rf /var/lib/apt/lists/*

# Copy Web OS source
WORKDIR /build
COPY . /build/web-os/

# Run the ISO builder
RUN cd /build/web-os/iso-builder && bash build-iso.sh

# Output stage
FROM scratch AS output
COPY --from=builder /build/web-os/dist/*.iso /
