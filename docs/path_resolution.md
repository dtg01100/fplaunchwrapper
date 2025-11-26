# Path Resolution to System Binaries in fplaunchwrapper

## Overview

fplaunchwrapper uses a sophisticated, multi-layered approach to resolve paths to system binaries, ensuring reliable detection of system packages while avoiding conflicts with its own wrapper scripts. This system is designed to be **PATH-order independent** and **collision-safe**.

## The Resolution Process

### 1. **Wrapper Script Generation** (`fplaunch-generate`)

When a wrapper is created, the system binary path resolution logic is **embedded directly into each wrapper script** at generation time. This ensures that:

- Each wrapper has its own self-contained resolution logic
- No runtime PATH dependency issues
- Consistent behavior regardless of shell environment

### 2. **System Binary Search Algorithm**

The wrapper uses this specific algorithm to find system binaries:

```bash
# Check standard system paths in precedence order, skipping wrapper location
SYSTEM_EXISTS=false
CMD_PATH=""

for sys_dir in "/usr/local/bin" "/usr/bin" "/bin" "/usr/local/sbin" "/usr/sbin" "/sbin"; do
    candidate="$sys_dir/$NAME"
    if [ -f "$candidate" ] && [ -x "$candidate" ] && [ "$candidate" != "$SCRIPT_BIN_DIR/$NAME" ]; then
        SYSTEM_EXISTS=true
        CMD_PATH="$candidate"
        break
    fi
done
```

#### **Key Features:**

1. **Explicit Path Order**: Searches `/usr/local/bin` → `/usr/bin` → `/bin` → `/usr/local/sbin` → `/usr/sbin` → `/sbin`
   - This mirrors the standard Unix filesystem hierarchy
   - `/usr/local/bin` takes precedence (for locally compiled software)
   - System binaries in `/bin` and `/usr/bin` are found reliably

2. **Collision Avoidance**: The critical check `[ "$candidate" != "$SCRIPT_BIN_DIR/$NAME" ]`
   - Prevents wrapper from calling itself (infinite recursion)
   - Ensures wrapper in `~/.local/bin/chrome` doesn't call itself instead of `/usr/bin/chrome`

3. **File System Checks**: Validates both existence (`-f`) and executability (`-x`)
   - Prevents calling broken symlinks or non-executable files
   - Ensures the found file is actually runnable

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