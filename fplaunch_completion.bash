# Bash completion for fplaunch-manage

_fplaunch_manage() {
    local cur prev words cword
    _init_completion || return

    # Get BIN_DIR from config
    local config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/flatpak-wrappers"
    local bin_dir_file="$config_dir/bin_dir"
    local bin_dir="$HOME/.local/bin"
    if [ -f "$bin_dir_file" ]; then
        bin_dir=$(cat "$bin_dir_file")
    fi

    case $prev in
        set-pref|set-env|remove-env|list-env|set-script|set-post-script|remove-script|remove-post-script|set-alias|remove-alias|block|unblock|launch)
            # Complete wrapper names
            local wrappers=$(ls "$bin_dir" 2>/dev/null | grep -v fplaunch-manage | tr '\n' ' ')
            COMPREPLY=( $(compgen -W "$wrappers" -- "$cur") )
            ;;
        set-env)
            if [ $cword -eq 3 ]; then
                # For var, no completion
                :
            fi
            ;;
        export-prefs|import-prefs|export-config|import-config)
            _filedir
            ;;
        install)
            # Complete app names? Hard, skip
            ;;
        *)
            COMPREPLY=( $(compgen -W "help list remove remove-pref set-pref set-env remove-env list-env set-pref-all set-script set-post-script remove-script remove-post-script set-alias remove-alias export-prefs import-prefs export-config import-config block unblock list-blocked install launch regenerate" -- "$cur") )
            ;;
    esac
}

complete -F _fplaunch_manage fplaunch-manage

# Completion for wrapper flags
_fplaunch_wrapper() {
    local cur prev
    _init_completion || return

    COMPREPLY=( $(compgen -W "--help --fpwrapper-help --fpwrapper-info --fpwrapper-config-dir --fpwrapper-sandbox-info --fpwrapper-edit-sandbox --fpwrapper-sandbox-yolo --fpwrapper-sandbox-reset --fpwrapper-run-unrestricted --fpwrapper-set-override --fpwrapper-set-pre-script --fpwrapper-set-post-script --fpwrapper-remove-pre-script --fpwrapper-remove-post-script" -- "$cur") )
}

# Complete for all wrappers
for wrapper in "$bin_dir"/*; do
    if [ -f "$wrapper" ] && [ -x "$wrapper" ] && [[ $(basename "$wrapper") != fplaunch-manage ]]; then
        complete -F _fplaunch_wrapper "$(basename "$wrapper")"
    fi
done