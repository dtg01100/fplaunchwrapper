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

# Copy source files - use installed scripts or generate stubs
copy_scripts() {
    local dest="$1"
    # Copy installed fplaunch-* scripts if they exist (from editable install)
    for script in fplaunch-generate fplaunch-cleanup fplaunch-setup-systemd; do
        if command -v "$script" &> /dev/null; then
            cp "$(which "$script")" "$dest/"
            chmod +x "$dest/$script"
        fi
    done

    # Also look in common locations
    for script in fplaunch-generate fplaunch-cleanup fplaunch-setup-systemd; do
        for path in "./$script" "$HOME/.local/bin/$script" "$HOME/.cargo/bin/$script"; do
            if [ -f "$path" ] && [ ! -f "$dest/$script" ]; then
                cp "$path" "$dest/"
                chmod +x "$dest/$script"
            fi
        done
    done
}

copy_scripts "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}"

# Copy other files
cp -r \
    fplaunch_completion.bash \
    fplaunch_completion.zsh \
    fplaunch_completion.fish \
    lib/ \
    docs/ \
    examples/ \
    README.md \
    QUICKSTART.md \
    "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}/"

# Copy packaging files
mkdir -p "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}/debian"
cp packaging/debian/* "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}/debian/"

# Update version in changelog
sed -i "s/@VERSION@/$VERSION/g" "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}/debian/changelog"
sed -i "s/@DATE@/$(date -R)/g" "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}/debian/changelog"

cd "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}"
dpkg-buildpackage -us -uc -b

cd ../../..
mv "$BUILD_DIR"/*.deb .

echo "Debian package built successfully: ${PACKAGE_NAME}_${VERSION}_all.deb"