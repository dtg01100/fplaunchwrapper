# Path Resolution to System Binaries in fplaunchwrapper

## Overview

fplaunchwrapper uses a sophisticated, multi-layered approach to resolve paths to system binaries, ensuring reliable detection of system packages while avoiding conflicts with its own wrapper scripts. This system is designed to be **PATH-order independent**, **collision-safe**, and **security-hardened** against various attack vectors.

## Security-Hardened Resolution Process

### 1. **Wrapper Script Generation** (`fplaunch-generate`)

When a wrapper is created, the system binary path resolution logic is **embedded directly into each wrapper script** at generation time. This ensures that:

- Each wrapper has its own self-contained resolution logic
- No runtime PATH dependency issues
- Consistent behavior regardless of shell environment
- **Security hardening is baked in at generation time**

### 2. **Security-Hardened System Binary Search Algorithm**

The wrapper uses this security-focused algorithm to find system binaries:

```bash
# Security-hardened PATH parsing with input validation
# Sanitize PATH to prevent injection attacks
SAFE_PATH="${PATH:-/usr/local/bin:/usr/bin:/bin}"

# Remove dangerous characters and normalize
# This prevents PATH injection attacks
SAFE_PATH=$(echo "$SAFE_PATH" | sed 's/[^a-zA-Z0-9\/\:\.\-\_]/:/g')

SYSTEM_EXISTS=false
CMD_PATH=""

# Parse PATH defensively
IFS=':' read -ra PATH_DIRS <<< "$SAFE_PATH"
for sys_dir in "${PATH_DIRS[@]}"; do
    # Skip empty directories
    [ -z "$sys_dir" ] && continue
    
    # Skip dangerous patterns (directory traversal)
    case "$sys_dir" in
        *\.\.*|*\/\.\.\/|*\/\.\.$|\.\.\/\*|\/\.\.\/\*)
            echo "SECURITY: Skipping dangerous path: $sys_dir" >&2
            continue
            ;;
    esac
    
    # Skip user directories (prevents user script execution)
    case "$sys_dir" in
        "$HOME"/*|\~/*)
            echo "SECURITY: Skipping user directory: $sys_dir" >&2
            continue
            ;;
    esac
    
    # Skip paths with suspicious characters
    if [[ ! "$sys_dir" =~ ^/([a-zA-Z0-9\.\_\-]+/)*[a-zA-Z0-9\.\_\-]+$ ]]; then
        echo "SECURITY: Skipping malformed path: $sys_dir" >&2
        continue
    fi
    
    # Skip excessively long paths (potential buffer overflow protection)
    if [ ${#sys_dir} -gt 256 ]; then
        echo "SECURITY: Skipping overly long path" >&2
        continue
    fi
    
    # Skip if directory doesn't exist (prevents false positives)
    if [ ! -d "$sys_dir" ]; then
        continue
    fi
    
    # Skip if directory is not readable (security check)
    if [ ! -r "$sys_dir" ]; then
        echo "SECURITY: Skipping unreadable directory: $sys_dir" >&2
        continue
    fi
    
    candidate="$sys_dir/$NAME"
    
    # Additional validation of candidate path
    # Skip if candidate path is suspicious
    if [[ "$candidate" =~ [\;\|\&\$\`\<\>] ]]; then
        echo "SECURITY: Skipping candidate with dangerous characters: $candidate" >&2
        continue
    fi
    
    # Skip if candidate path is excessively long
    if [ ${#candidate} -gt 512 ]; then
        echo "SECURITY: Skipping overly long candidate path" >&2
        continue
    fi
    
    # Check if this is our own wrapper script - if so, skip it
    if [ "$candidate" = "$SCRIPT_BIN_DIR/$NAME" ]; then
        echo "SECURITY: Skipping our own wrapper at $candidate" >&2
        continue
    fi
    
    # Final security checks before testing file
    # Ensure candidate is within expected system directories
    case "$sys_dir" in
        /usr/local/bin|/usr/bin|/bin|/usr/local/sbin|/usr/sbin|/sbin|/opt/*/bin|/opt/bin)
            # Allow standard system directories
            ;;
        *)
            echo "SECURITY: Skipping non-system directory: $sys_dir" >&2
            continue
            ;;
    esac
    
    # Check if executable exists in this PATH directory
    if [ -f "$candidate" ] && [ -x "$candidate" ]; then
        # Additional verification: ensure file is not a symlink to wrapper location
        if [ -L "$candidate" ]; then
            link_target=$(readlink -f "$candidate" 2>/dev/null)
            if [ "$link_target" = "$SCRIPT_BIN_DIR/$NAME" ]; then
                echo "SECURITY: Skipping symlink to wrapper: $candidate" >&2
                continue
            fi
        fi
        
        # Verify file is owned by root or system user (additional security)
        if [ "$(stat -c %u "$candidate" 2>/dev/null)" != "0" ] && [ "$(stat -c %u "$candidate" 2>/dev/null)" != "1" ]; then
            echo "SECURITY: Skipping non-system owned file: $candidate" >&2
            continue
        fi
        
        SYSTEM_EXISTS=true
        CMD_PATH="$candidate"
        echo "SECURITY: Found system binary at $candidate" >&2
        break
    fi
done
```

#### **Security Features:**

1. **PATH Injection Prevention**: Sanitizes PATH to remove dangerous characters
   - Prevents `PATH="/tmp/evil;rm -rf /"` style attacks
   - Only allows alphanumeric, slash, dot, hyphen, and underscore characters

2. **Directory Traversal Protection**: Blocks `../` patterns
   - Prevents access to parent directories
   - Blocks various `../` attack vectors

3. **User Directory Exclusion**: Skips `$HOME/*` and `~/*` paths
   - Prevents execution of user-controlled scripts
   - Forces system-only binary resolution

4. **Path Validation**: Regex validation for well-formed paths
   - Ensures paths follow standard Unix filesystem patterns
   - Rejects malformed or suspicious path structures

5. **Length Limits**: Protects against buffer overflow attacks
   - 256-character limit for directory paths
   - 512-character limit for full candidate paths

6. **Readability Checks**: Verifies directory accessibility
   - Skips non-existent directories
   - Skips unreadable directories

7. **Character Filtering**: Blocks dangerous shell metacharacters
   - Prevents command injection via path components
   - Blocks `;`, `|`, `&`, `$`, `` ` ``, `<`, `>` characters

8. **System Directory Whitelisting**: Only allows known system directories
   - `/usr/local/bin`, `/usr/bin`, `/bin`, `/usr/local/sbin`, `/usr/sbin`, `/sbin`
   - `/opt/*/bin`, `/opt/bin` for third-party system software
   - Rejects all other directories

9. **Symlink Attack Detection**: Detects and blocks malicious symlinks
   - Checks if symlink target points to wrapper script
   - Prevents symlink-based wrapper hijacking

10. **Ownership Verification**: Ensures system ownership
    - Only allows files owned by root (uid 0) or system user (uid 1)
    - Prevents execution of user-owned files

### 3. **Preference-Based Decision Logic**

Once system binary detection is complete, the wrapper uses a three-tier preference system:

#### **Tier 1: User Preference File**
```bash
if [ -f "$PREF_FILE" ]; then
    PREF=$(cat "$PREF_FILE")
else
    PREF=""
fi
```

#### **Tier 2: Preference-Based Execution**

**Case A: User prefers system (`PREF="system"`)**
```bash
if [ "$PREF" = "system" ]; then
    if [ "$SYSTEM_EXISTS" = true ]; then
        # Execute system command
        load_env_vars
        run_pre_launch_script "$@"
        run_and_cleanup "$NAME" "$@"
    else
        # System command gone, fall back to flatpak
        PREF="flatpak"
        echo "flatpak" > "$PREF_FILE"
        load_env_vars
        run_pre_launch_script "$@"
        run_and_cleanup flatpak run "$ID" "$@"
    fi
```

**Case B: User prefers flatpak (`PREF="flatpak"`)**
```bash
elif [ "$PREF" = "flatpak" ]; then
    load_env_vars
    run_pre_launch_script "$@"
    run_and_cleanup flatpak run "$ID" "$@"
```

**Case C: No preference set (Interactive choice)**
```bash
else
    # No pref set
    if [ "$SYSTEM_EXISTS" = true ]; then
        echo "Multiple options for '$NAME':"
        echo "1. System package ($CMD_PATH)"
        echo "2. Flatpak app ($ID)"
        read -r -p "Choose (1/2, default 1): " choice
        choice=${choice:-1}
        if [ "$choice" = "1" ]; then
            PREF="system"
            echo "$PREF" > "$PREF_FILE"
            # ... execute system
        elif [ "$choice" = "2" ]; then
            PREF="flatpak"
            echo "$PREF" > "$PREF_FILE"
            # ... execute flatpak
        fi
    else
        PREF="flatpak"
        echo "$PREF" > "$PREF_FILE"
        # ... execute flatpak
    fi
fi
```

## Key Design Decisions and Their Rationale

### 1. **Explicit Path Enumeration vs `which`/`command -v`**

**Why not use `which` or `command -v`?**
- **PATH Order Dependency**: `which` and `command -v` respect the current PATH order
- **Wrapper Location Interference**: If wrapper is earlier in PATH, these commands would find the wrapper itself
- **Inconsistent Behavior**: Different shells/environments might have different PATH configurations

**Benefits of explicit enumeration:**
- **Predictable Order**: Always searches in the same order regardless of PATH
- **Collision Safety**: Explicit check prevents wrapper self-reference
- **Environment Independence**: Works the same in all shell environments

### 2. **Pre-resolution at Wrapper Generation Time**

**Why embed resolution in wrapper vs runtime lookup?**
- **Performance**: No need to search paths on every wrapper invocation
- **Reliability**: Resolution logic is frozen at generation time
- **Simplicity**: Wrapper is self-contained, no external dependencies

### 3. **Fallback Mechanism**

**Automatic preference update when system package disappears:**
```bash
if [ "$SYSTEM_EXISTS" = true ]; then
    # Execute system
else
    # System command gone, fall back to flatpak
    PREF="flatpak"
    echo "flatpak" > "$PREF_FILE"
    # ... execute flatpak
fi
```

This ensures:
- **Graceful Degradation**: System upgrades/removals don't break wrappers
- **User Experience**: Automatically switches to available option
- **Preference Persistence**: Remembers the fallback choice

### 4. **Conflict Resolution Priority**

The system implements a clear priority hierarchy:
1. **User Explicit Preference** (highest priority)
2. **System Package Availability** (when no preference)
3. **Flatpak Package** (fallback/default)

## Edge Cases and Safety Features

### 1. **Wrapper Self-Reference Prevention**
```bash
[ "$candidate" != "$SCRIPT_BIN_DIR/$NAME" ]
```
Prevents infinite recursion where wrapper calls itself.

### 2. **Broken Symlink Detection**
```bash
[ -f "$candidate" ] && [ -x "$candidate" ]
```
Ensures found file actually exists and is executable.

### 3. **Interactive Choice with Sensible Defaults**
When both options exist but no preference is set:
- Shows clear options with full paths
- Defaults to system package (choice 1)
- Updates preference file for future runs

### 4. **Environment Variable Loading**
```bash
load_env_vars() {
    ENV_FILE="$PREF_DIR/$NAME.env"
    if [ -f "$ENV_FILE" ]; then
        source "$ENV_FILE"
    fi
}
```
Allows per-application environment customization that applies to both system and flatpak execution.

## Performance Considerations

### **Generation Time vs Runtime Trade-off**
- **Generation**: More complex (embeds resolution logic)
- **Runtime**: Very fast (no path searching, just preference check)

### **Preference File Caching**
- User choices are cached in preference files
- Subsequent runs bypass interactive selection
- Automatic preference updates when system state changes

## Security Considerations

### 1. **Path Hardening**
- Uses absolute paths for system binaries
- No reliance on PATH environment variable
- Explicit executable permission checks

### 2. **Wrapper Isolation**
- Clear separation between wrapper location and system locations
- Prevents wrapper hijacking through PATH manipulation

### 3. **File Validation**
- Verifies file existence and executability
- Prevents execution of broken or malicious symlinks

## Integration with Management Commands

The path resolution works seamlessly with fplaunchwrapper's management features:

- **`fplaunch-manage set-pref`**: Sets user preferences that override automatic detection
- **`fplaunch-manage block`**: Prevents wrapper creation for specific applications
- **`fplaunch-manage alias`**: Creates alternative names when path conflicts occur
- **Environment Variables**: Customizable per-application environment for both execution modes

This comprehensive path resolution system ensures that fplaunchwrapper provides a seamless user experience while maintaining system security and reliability.