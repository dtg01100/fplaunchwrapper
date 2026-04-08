#compdef fplaunch

# Zsh completion for fplaunchwrapper
# Place in ~/.zsh/site-functions/_fplaunch or /usr/local/share/zsh/site-functions/_fplaunch

_fplaunch_commands() {
    local -a commands
    commands=(
        'generate:Generate Flatpak application wrappers'
        'list:List installed Flatpak wrappers'
        'set-pref:Set launch preference for a wrapper'
        'pref:Alias for set-pref'
        'remove:Remove a wrapper by name'
        'rm:Alias for remove'
        'launch:Launch a Flatpak application via its wrapper'
        'cleanup:Clean up orphaned wrapper files'
        'clean:Alias for cleanup'
        'config:Manage fplaunchwrapper configuration'
        'info:Show information about a wrapper'
        'search:Search or discover wrappers'
        'discover:Alias for search'
        'install:Install a Flatpak application'
        'uninstall:Uninstall a Flatpak application'
        'manifest:Show manifest information'
        'monitor:Start Flatpak monitoring daemon'
        'files:Display managed files'
        'profiles:Manage configuration profiles'
        'presets:Manage permission presets'
        'systemd:Manage systemd user units'
        'systemd-setup:Install/enable systemd units'
    )
    _describe 'command' commands
}

_fplaunch() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \
        '-v[Enable verbose output]' \
        '--verbose[Enable verbose output]' \
        '--emit[Emit commands instead of executing (dry run)]' \
        '--emit-verbose[Show detailed file contents in emit mode]' \
        '--config-dir[Custom configuration directory]:directory:_files -/' \
        '--version[Show the version]' \
        '--help[Show help message]' \
        '1: :_fplaunch_commands' \
        '*::arg: _args'
}

_fplaunch_set-pref() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \
        '--force[Force override existing preference]' \
        '*::arg: _args'
}

_fplaunch_cleanup() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \
        '-y[Assume yes to all prompts]' \
        '--yes[Assume yes to all prompts]' \
        '--dry-run[Preview cleanup without deleting]' \
        '--bin-dir[Specify bin directory]:directory:_files -/' \
        '--config-dir[Specify config directory]:directory:_files -/'
}

_fplaunch_generate() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \
        '--force[Force regenerate existing wrappers]' \
        '--all[Generate wrappers for all installed Flatpaks]' \
        '--include[Only include specified apps]:app' \
        '--exclude[Exclude specified apps]:app' \
        '::directory:_files -/'
}

_fplaunch "$@"
