#!/bin/bash
# Test RPM building in a minimal Fedora chroot

set -e

CHROOT_DIR="/tmp/fedora-chroot"
VERSION="${1:-1.1.0}"

echo "Setting up minimal Fedora chroot for RPM building..."

# Clean up old chroot if exists
if [ -d "$CHROOT_DIR" ]; then
    echo "Cleaning up old chroot..."
    sudo rm -rf "$CHROOT_DIR"
fi

# Create chroot directory
sudo mkdir -p "$CHROOT_DIR"

# Download and extract Fedora base system
echo "Downloading Fedora container image..."
FEDORA_IMAGE="fedora:latest"
CONTAINER_ID=$(sudo docker create $FEDORA_IMAGE)

echo "Extracting filesystem..."
sudo docker export $CONTAINER_ID | sudo tar -C "$CHROOT_DIR" -xf -
sudo docker rm $CONTAINER_ID

# Copy project files into chroot
echo "Copying project files..."
sudo mkdir -p "$CHROOT_DIR/build"
sudo cp -r . "$CHROOT_DIR/build/fplaunchwrapper"

# Create build script to run inside chroot
cat > /tmp/chroot-build.sh << 'INNEREOF'
#!/bin/bash
set -e

cd /build/fplaunchwrapper

# Install dependencies
echo "Installing build dependencies..."
dnf install -y rpm-build tar gzip

# Run the build
echo "Building RPM package..."
bash packaging/build-rpm.sh "$1"

# Copy result to host-accessible location
if [ -f *.rpm ]; then
    cp *.rpm /build/
    echo "RPM package copied to /build/"
    ls -lh /build/*.rpm
fi
INNEREOF

sudo cp /tmp/chroot-build.sh "$CHROOT_DIR/build/build.sh"
sudo chmod +x "$CHROOT_DIR/build/build.sh"

# Run build in chroot
echo "Running RPM build in chroot..."
sudo chroot "$CHROOT_DIR" /build/build.sh "$VERSION"

# Copy result back
if [ -f "$CHROOT_DIR/build/"*.rpm ]; then
    sudo cp "$CHROOT_DIR/build/"*.rpm .
    sudo chown $(id -u):$(id -g) *.rpm
    echo ""
    echo "=========================================="
    echo "RPM package built successfully!"
    ls -lh *.rpm
    echo "=========================================="
else
    echo "Error: RPM package not found"
    exit 1
fi

# Cleanup
echo "Cleaning up chroot..."
sudo rm -rf "$CHROOT_DIR"

echo "Done!"
