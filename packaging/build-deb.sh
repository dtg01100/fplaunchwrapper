#!/bin/bash
# Build Debian package for fplaunchwrapper

set -e

VERSION="${1:-1.1.0}"
PACKAGE_NAME="fplaunchwrapper"
BUILD_DIR="build/deb"

echo "Building Debian package for $PACKAGE_NAME version $VERSION"

# Clean and create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}"

# Copy source files
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
    "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}/"

# Copy packaging files
mkdir -p "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}/debian"
cp packaging/debian/* "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}/debian/"

# Update version in changelog
sed -i "s/@VERSION@/$VERSION/g" "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}/debian/changelog"
sed -i "s/@DATE@/$(date -R)/g" "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}/debian/changelog"

# Build the package
cd "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}"
dpkg-buildpackage -us -uc -b

# Move package to root
cd ../../..
mv "$BUILD_DIR"/*.deb .

echo "Debian package built successfully: ${PACKAGE_NAME}_${VERSION}_all.deb"
