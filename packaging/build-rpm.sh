#!/bin/bash
# Build RPM package for fplaunchwrapper

set -e

VERSION="${1:-1.1.0}"
PACKAGE_NAME="fplaunchwrapper"
BUILD_DIR="build/rpm"

echo "Building RPM package for $PACKAGE_NAME version $VERSION"

# Clean and create build directories
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

# Create source tarball
TARBALL_DIR="${PACKAGE_NAME}-${VERSION}"
mkdir -p "$BUILD_DIR/SOURCES/$TARBALL_DIR"

cp -r \
    fplaunch-generate \
    fplaunch-setup-systemd \
    fplaunch-cleanup \
    manage_wrappers.sh \
    fplaunch_completion.bash \
    docs/ \
    lib/ \
    examples/ \
    README.md \
    QUICKSTART.md \
    "$BUILD_DIR/SOURCES/$TARBALL_DIR/"

# Add LICENSE if it doesn't exist
if [ ! -f LICENSE ]; then
    cat > "$BUILD_DIR/SOURCES/$TARBALL_DIR/LICENSE" << 'EOF'
MIT License

Copyright (c) 2025 fplaunchwrapper Developers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
else
    cp LICENSE "$BUILD_DIR/SOURCES/$TARBALL_DIR/"
fi

# Copy any release notes
if ls RELEASE_*.md 1> /dev/null 2>&1; then
    cp RELEASE_*.md "$BUILD_DIR/SOURCES/$TARBALL_DIR/"
fi

# Create tarball
cd "$BUILD_DIR/SOURCES"
tar -czf "${PACKAGE_NAME}-${VERSION}.tar.gz" "$TARBALL_DIR"
rm -rf "$TARBALL_DIR"
cd ../../..

# Copy spec file and substitute version
cp packaging/fplaunchwrapper.spec "$BUILD_DIR/SPECS/"
sed -i "s/%{version}/$VERSION/g" "$BUILD_DIR/SPECS/fplaunchwrapper.spec"

# Build the RPM
rpmbuild \
    --define "_topdir $(pwd)/$BUILD_DIR" \
    --define "_sourcedir $(pwd)/$BUILD_DIR/SOURCES" \
    --define "_builddir $(pwd)/$BUILD_DIR/BUILD" \
    --define "_buildrootdir $(pwd)/$BUILD_DIR/BUILDROOT" \
    --define "_rpmdir $(pwd)/$BUILD_DIR/RPMS" \
    --define "_specdir $(pwd)/$BUILD_DIR/SPECS" \
    --define "_srcrpmdir $(pwd)/$BUILD_DIR/SRPMS" \
    -bb "$BUILD_DIR/SPECS/fplaunchwrapper.spec"

# Move package to root
mv "$BUILD_DIR"/RPMS/*/*.rpm .

echo "RPM package built successfully: ${PACKAGE_NAME}-${VERSION}-1.noarch.rpm"