Name:           fplaunchwrapper
Version:        %{version}
Release:        1%{?dist}
Summary:        Simplified launcher wrappers for Flatpak applications

License:        MIT
URL:            https://github.com/dtg01100/fplaunchwrapper
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       bash >= 4.0, flatpak
Recommends:     systemd, dialog

%description
Creates small wrapper scripts for Flatpak applications, allowing you to
launch them by their simplified name (e.g., 'chrome' instead of
'flatpak run com.google.Chrome').

Features include:
- Automatic wrapper generation for user and system Flatpak apps
- Conflict resolution between system packages and Flatpak apps
- Customizable aliases and preferences
- Environment variable management per wrapper
- Pre-launch and post-run script support
- Sandbox permission management
- Automatic updates via systemd or crontab

%prep
%setup -q

%build
# Skip info page generation to avoid texinfo dependency
echo "Info page generation skipped to avoid texinfo dependency"

%install
rm -rf $RPM_BUILD_ROOT

# Install to /usr/lib/fplaunchwrapper
mkdir -p %{buildroot}/usr/lib/fplaunchwrapper
install -m 755 fplaunch-cleanup %{buildroot}/usr/lib/fplaunchwrapper/
install -m 755 fplaunch-generate %{buildroot}/usr/lib/fplaunchwrapper/
install -m 755 fplaunch-setup-systemd %{buildroot}/usr/lib/fplaunchwrapper/
install -m 755 manage_wrappers.sh %{buildroot}/usr/lib/fplaunchwrapper/
install -m 644 fplaunch_completion.bash %{buildroot}/usr/lib/fplaunchwrapper/

# Install lib directory
mkdir -p %{buildroot}/usr/lib/fplaunchwrapper/lib
install -m 755 lib/*.sh %{buildroot}/usr/lib/fplaunchwrapper/lib/

# Install documentation
mkdir -p %{buildroot}/usr/share/doc/fplaunchwrapper
install -m 644 README.md %{buildroot}/usr/share/doc/fplaunchwrapper/
install -m 644 QUICKSTART.md %{buildroot}/usr/share/doc/fplaunchwrapper/
cp -r examples %{buildroot}/usr/share/doc/fplaunchwrapper/
[ -f RELEASE_*.md ] && install -m 644 RELEASE_*.md %{buildroot}/usr/share/doc/fplaunchwrapper/ || true

# Install man pages
mkdir -p %{buildroot}/usr/share/man/man1
mkdir -p %{buildroot}/usr/share/man/man7
install -m 644 docs/man/fplaunch-manage.1 %{buildroot}/usr/share/man/man1/
install -m 644 docs/man/fplaunch-generate.1 %{buildroot}/usr/share/man/man1/
install -m 644 docs/man/fplaunch-setup-systemd.1 %{buildroot}/usr/share/man/man1/
install -m 644 docs/man/fplaunch-cleanup.1 %{buildroot}/usr/share/man/man1/
install -m 644 docs/man/fplaunchwrapper.7 %{buildroot}/usr/share/man/man7/

# Info pages are not included in the package to avoid texinfo dependency
# Remove info file if it was built (to avoid dependency detection)
if [ -f docs/info/fplaunchwrapper.info ]; then
  echo "Info file built but will be excluded from package to avoid texinfo dependency"
fi

# Install bash completion
mkdir -p %{buildroot}/usr/share/bash-completion/completions
install -m 644 fplaunch_completion.bash %{buildroot}/usr/share/bash-completion/completions/fplaunch-manage

# Provide user-facing commands in /usr/bin via symlinks
mkdir -p %{buildroot}/usr/bin
ln -s ../lib/fplaunchwrapper/manage_wrappers.sh %{buildroot}/usr/bin/fplaunch-manage
ln -s ../lib/fplaunchwrapper/fplaunch-generate %{buildroot}/usr/bin/fplaunch-generate
ln -s ../lib/fplaunchwrapper/fplaunch-setup-systemd %{buildroot}/usr/bin/fplaunch-setup-systemd
ln -s ../lib/fplaunchwrapper/fplaunch-cleanup %{buildroot}/usr/bin/fplaunch-cleanup

%files
%license LICENSE
%doc README.md
/usr/lib/fplaunchwrapper/
/usr/share/doc/fplaunchwrapper/
/usr/share/bash-completion/completions/fplaunch-manage
/usr/share/man/man1/fplaunch-*.1*
/usr/share/man/man7/fplaunchwrapper.7*
/usr/bin/fplaunch-manage
/usr/bin/fplaunch-generate
/usr/bin/fplaunch-setup-systemd
/usr/bin/fplaunch-cleanup

%post
echo "=========================================="
echo "fplaunchwrapper successfully installed!"
echo "=========================================="
echo ""
echo "User setup:"
echo "  1) Generate wrappers in ~/.local/bin:"
echo "       fplaunch-manage regenerate"
echo "  2) (Optional) Enable automatic updates (user systemd):"
echo "       fplaunch-setup-systemd"
echo ""
echo "Note: Systemd user units are not enabled by default; running"
echo "      fplaunch-setup-systemd is a user-initiated action and signals intent."
echo ""
echo "Documentation:"
echo "  man fplaunchwrapper"
echo "  man fplaunch-manage"
echo ""
echo "Cleanup (before uninstall, per user):"
echo "       fplaunch-cleanup"
echo "=========================================="

%changelog
* Tue Nov 26 2025 fplaunchwrapper Developers <dev@example.com> - %{version}-1
- New release version %{version}
- See README.md and RELEASE_*.md for changes
