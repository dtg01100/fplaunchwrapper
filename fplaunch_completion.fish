# Fish completion for fplaunchwrapper
# Place in ~/.config/fish/completions/fplaunch.fish

complete -c fplaunch -f

# Global options
complete -c fplaunch -l verbose -s v -d 'Enable verbose output'
complete -c fplaunch -l emit -d 'Emit commands instead of executing (dry run)'
complete -c fplaunch -l emit-verbose -d 'Show detailed file contents in emit mode'
complete -c fplaunch -l config-dir -d 'Custom configuration directory' -r
complete -c fplaunch -l version -d 'Show the version'
complete -c fplaunch -l help -d 'Show help message'

# Commands
complete -c fplaunch -n '__fish_use_subcommand' -a 'generate' -d 'Generate Flatpak application wrappers'
complete -c fplaunch -n '__fish_use_subcommand' -a 'list' -d 'List installed Flatpak wrappers'
complete -c fplaunch -n '__fish_use_subcommand' -a 'set-pref' -d 'Set launch preference for a wrapper'
complete -c fplaunch -n '__fish_use_subcommand' -a 'pref' -d 'Alias for set-pref'
complete -c fplaunch -n '__fish_use_subcommand' -a 'remove' -d 'Remove a wrapper by name'
complete -c fplaunch -n '__fish_use_subcommand' -a 'rm' -d 'Alias for remove'
complete -c fplaunch -n '__fish_use_subcommand' -a 'launch' -d 'Launch a Flatpak application via its wrapper'
complete -c fplaunch -n '__fish_use_subcommand' -a 'cleanup' -d 'Clean up orphaned wrapper files'
complete -c fplaunch -n '__fish_use_subcommand' -a 'clean' -d 'Alias for cleanup'
complete -c fplaunch -n '__fish_use_subcommand' -a 'config' -d 'Manage fplaunchwrapper configuration'
complete -c fplaunch -n '__fish_use_subcommand' -a 'info' -d 'Show information about a wrapper'
complete -c fplaunch -n '__fish_use_subcommand' -a 'search' -d 'Search or discover wrappers'
complete -c fplaunch -n '__fish_use_subcommand' -a 'discover' -d 'Alias for search'
complete -c fplaunch -n '__fish_use_subcommand' -a 'install' -d 'Install a Flatpak application'
complete -c fplaunch -n '__fish_use_subcommand' -a 'uninstall' -d 'Uninstall a Flatpak application'
complete -c fplaunch -n '__fish_use_subcommand' -a 'manifest' -d 'Show manifest information'
complete -c fplaunch -n '__fish_use_subcommand' -a 'monitor' -d 'Start Flatpak monitoring daemon'
complete -c fplaunch -n '__fish_use_subcommand' -a 'files' -d 'Display managed files'
complete -c fplaunch -n '__fish_use_subcommand' -a 'profiles' -d 'Manage configuration profiles'
complete -c fplaunch -n '__fish_use_subcommand' -a 'presets' -d 'Manage permission presets'
complete -c fplaunch -n '__fish_use_subcommand' -a 'systemd' -d 'Manage systemd user units'
complete -c fplaunch -n '__fish_use_subcommand' -a 'systemd-setup' -d 'Install/enable systemd units'

# generate subcommand options
complete -c fplaunch -n '__fish_seen_subcommand_from generate' -l force -d 'Force regenerate existing wrappers'
complete -c fplaunch -n '__fish_seen_subcommand_from generate' -l all -d 'Generate wrappers for all installed Flatpaks'
complete -c fplaunch -n '__fish_seen_subcommand_from generate' -l include -d 'Only include specified apps'
complete -c fplaunch -n '__fish_seen_subcommand_from generate' -l exclude -d 'Exclude specified apps'

# cleanup subcommand options
complete -c fplaunch -n '__fish_seen_subcommand_from cleanup' -l yes -s y -d 'Assume yes to all prompts'
complete -c fplaunch -n '__fish_seen_subcommand_from cleanup' -l dry-run -d 'Preview cleanup without deleting'
complete -c fplaunch -n '__fish_seen_subcommand_from cleanup' -l bin-dir -d 'Specify bin directory' -r

# set-pref subcommand options
complete -c fplaunch -n '__fish_seen_subcommand_from set-pref' -l force -d 'Force override existing preference'

# profiles subcommand
complete -c fplaunch -n '__fish_seen_subcommand_from profiles' -a list -d 'List all profiles'
complete -c fplaunch -n '__fish_seen_subcommand_from profiles' -a create -d 'Create a new profile'
complete -c fplaunch -n '__fish_seen_subcommand_from profiles' -a switch -d 'Switch to a profile'
complete -c fplaunch -n '__fish_seen_subcommand_from profiles' -a current -d 'Show current profile'
complete -c fplaunch -n '__fish_seen_subcommand_from profiles' -a export -d 'Export profile to file'
complete -c fplaunch -n '__fish_seen_subcommand_from profiles' -a import -d 'Import profile from file'

# presets subcommand
complete -c fplaunch -n '__fish_seen_subcommand_from presets' -a list -d 'List all presets'
complete -c fplaunch -n '__fish_seen_subcommand_from presets' -a get -d 'Get preset permissions'
complete -c fplaunch -n '__fish_seen_subcommand_from presets' -a add -d 'Add a preset'
complete -c fplaunch -n '__fish_seen_subcommand_from presets' -a remove -d 'Remove a preset'

# systemd subcommand
complete -c fplaunch -n '__fish_seen_subcommand_from systemd' -a enable -d 'Enable systemd units'
complete -c fplaunch -n '__fish_seen_subcommand_from systemd' -a disable -d 'Disable systemd units'
complete -c fplaunch -n '__fish_seen_subcommand_from systemd' -a status -d 'Check systemd status'
complete -c fplaunch -n '__fish_seen_subcommand_from systemd' -a start -d 'Start systemd unit'
complete -c fplaunch -n '__fish_seen_subcommand_from systemd' -a stop -d 'Stop systemd unit'
complete -c fplaunch -n '__fish_seen_subcommand_from systemd' -a restart -d 'Restart systemd unit'
complete -c fplaunch -n '__fish_seen_subcommand_from systemd' -a reload -d 'Reload systemd unit'
complete -c fplaunch -n '__fish_seen_subcommand_from systemd' -a logs -d 'Show unit logs'
complete -c fplaunch -n '__fish_seen_subcommand_from systemd' -a list -d 'List units'
complete -c fplaunch -n '__fish_seen_subcommand_from systemd' -a test -d 'Test configuration'
