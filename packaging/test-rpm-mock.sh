#!/bin/bash
# Mock RPM build test - validates spec file and build script without actually building

set -e

VERSION="${1:-1.1.0}"
PACKAGE_NAME="fplaunchwrapper"

echo "=========================================="
echo "Mock RPM Build Test"
echo "=========================================="
echo ""

# Test 1: Verify spec file syntax
echo "Test 1: Validating RPM spec file..."
if grep -q "Name:.*$PACKAGE_NAME" packaging/fplaunchwrapper.spec; then
    echo "  ✅ Package name found"
else
    echo "  ❌ Package name not found"
    exit 1
fi

if grep -q "Version:.*%{version}" packaging/fplaunchwrapper.spec; then
    echo "  ✅ Version placeholder found"
else
    echo "  ❌ Version placeholder not found"
    exit 1
fi

if grep -q "%install" packaging/fplaunchwrapper.spec; then
    echo "  ✅ Install section found"
else
    echo "  ❌ Install section not found"
    exit 1
fi

if grep -q "%files" packaging/fplaunchwrapper.spec; then
    echo "  ✅ Files section found"
else
    echo "  ❌ Files section not found"
    exit 1
fi

if grep -q "%post" packaging/fplaunchwrapper.spec; then
    echo "  ✅ Post-install section found"
else
    echo "  ❌ Post-install section not found"
    exit 1
fi

echo ""

# Test 2: Verify build script exists and is executable
echo "Test 2: Validating build script..."
if [ -x packaging/build-rpm.sh ]; then
    echo "  ✅ Build script is executable"
else
    echo "  ❌ Build script not executable"
    exit 1
fi

echo ""

# Test 3: Simulate tarball creation
echo "Test 3: Testing tarball creation..."
TARBALL_DIR="${PACKAGE_NAME}-${VERSION}"
TEST_BUILD_DIR="/tmp/rpm-test-$$"
mkdir -p "$TEST_BUILD_DIR/SOURCES"

# Create test tarball
mkdir -p "$TEST_BUILD_DIR/SOURCES/$TARBALL_DIR"
cp -r \
    install.sh \
    uninstall.sh \
    fplaunch-generate \
    fplaunch-setup-systemd \
    manage_wrappers.sh \
    fplaunch_completion.bash \
    lib/ \
    examples/ \
    README.md \
    QUICKSTART.md \
    "$TEST_BUILD_DIR/SOURCES/$TARBALL_DIR/" 2>/dev/null || true

if [ -f LICENSE ]; then
    cp LICENSE "$TEST_BUILD_DIR/SOURCES/$TARBALL_DIR/"
fi

cd "$TEST_BUILD_DIR/SOURCES"
tar -czf "${PACKAGE_NAME}-${VERSION}.tar.gz" "$TARBALL_DIR"

if [ -f "${PACKAGE_NAME}-${VERSION}.tar.gz" ]; then
    SIZE=$(ls -lh "${PACKAGE_NAME}-${VERSION}.tar.gz" | awk '{print $5}')
    echo "  ✅ Source tarball created: $SIZE"
else
    echo "  ❌ Tarball creation failed"
    exit 1
fi

cd - > /dev/null
rm -rf "$TEST_BUILD_DIR"

echo ""

# Test 4: Check post-install script content
echo "Test 4: Validating post-install message..."
if grep -q "IMPORTANT: Per-user setup required" packaging/fplaunchwrapper.spec; then
    echo "  ✅ Per-user setup message found"
else
    echo "  ❌ Per-user setup message not found"
    exit 1
fi

if grep -q "Optionally enable automatic updates" packaging/fplaunchwrapper.spec; then
    echo "  ✅ Optional auto-update message found"
else
    echo "  ❌ Optional auto-update message not found"
    exit 1
fi

echo ""

# Test 5: Verify required files
echo "Test 5: Checking required files..."
REQUIRED_FILES=(
    "install.sh"
    "uninstall.sh"
    "fplaunch-generate"
    "fplaunch-setup-systemd"
    "manage_wrappers.sh"
    "fplaunch_completion.bash"
    "README.md"
    "QUICKSTART.md"
    "LICENSE"
    "lib/alias.sh"
    "lib/config.sh"
    "lib/env.sh"
    "lib/install.sh"
    "lib/launch.sh"
    "lib/pref.sh"
    "lib/script.sh"
    "lib/wrapper.sh"
)

MISSING=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
        MISSING=$((MISSING + 1))
    fi
done

echo ""

if [ $MISSING -gt 0 ]; then
    echo "❌ $MISSING required files missing"
    exit 1
fi

echo "=========================================="
echo "✅ All RPM build validation tests passed!"
echo "=========================================="
echo ""
echo "The RPM spec file and build script are ready."
echo "Actual RPM building requires:"
echo "  - Fedora/RHEL system with rpmbuild"
echo "  - OR GitHub Actions CI (will build on Fedora container)"
echo ""
echo "To build manually on Fedora/RHEL:"
echo "  bash packaging/build-rpm.sh $VERSION"
echo ""
