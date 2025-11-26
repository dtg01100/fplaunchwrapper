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
# No build required for shell scripts

%install
rm -rf $RPM_BUILD_ROOT

# Install to /usr/lib/fplaunchwrapper
mkdir -p %{buildroot}/usr/lib/fplaunchwrapper
install -m 755 install.sh %{buildroot}/usr/lib/fplaunchwrapper/
install -m 755 uninstall.sh %{buildroot}/usr/lib/fplaunchwrapper/
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

# Install bash completion
mkdir -p %{buildroot}/usr/share/bash-completion/completions
install -m 644 fplaunch_completion.bash %{buildroot}/usr/share/bash-completion/completions/fplaunch-manage

%files
%license LICENSE
%doc README.md
/usr/lib/fplaunchwrapper/
/usr/share/doc/fplaunchwrapper/
/usr/share/bash-completion/completions/fplaunch-manage

%post
echo "=========================================="
echo "fplaunchwrapper successfully installed!"
echo "=========================================="
echo ""
echo "Installation location: /usr/lib/fplaunchwrapper"
echo ""
echo "IMPORTANT: Per-user setup required"
echo ""
echo "Each user must run the following command to:"
echo "  - Generate wrapper scripts in ~/.local/bin"
echo "  - Optionally enable automatic updates"
echo ""
echo "  bash /usr/lib/fplaunchwrapper/install.sh"
echo ""
echo "The install script will prompt you whether to enable"
echo "automatic wrapper updates via systemd or crontab."
echo ""
echo "For more information:"
echo "  - Documentation: /usr/share/doc/fplaunchwrapper/README.md"
echo "  - Quick start: /usr/share/doc/fplaunchwrapper/QUICKSTART.md"
echo "=========================================="

%changelog
* Tue Nov 26 2025 fplaunchwrapper Developers <dev@example.com> - %{version}-1
- New release version %{version}
- See README.md and RELEASE_*.md for changes
