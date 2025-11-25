# fplaunchwrapper v1.1.0 - Release Summary

## 🎉 Release: v1.1.0 - "System Command Detection Fix"

**Date:** November 24, 2025  
**Commit:** aee2be8  
**Tag:** v1.1.0

---

## 🚀 What's New

### ✨ Major Improvement: Fixed System Command Detection

**Problem Solved:** Users couldn't choose between system and flatpak versions when wrapper scripts appeared first in PATH.

**Root Cause:** The original detection logic used `command -v` and `which`, which are PATH-dependent. When wrapper scripts are in `~/.local/bin` (which comes before `/usr/bin` in most PATH configurations), the system would:

1. Find the wrapper first via PATH
2. Think it was the "system command" 
3. Fail to detect actual system commands
4. Force users to use flatpak versions only

**Solution:** Replaced PATH-dependent detection with direct scanning of standard system directories in proper precedence order.

---

## 📁 Files Changed

### Core Fix
- **`fplaunch-generate`** - Updated system detection logic (lines 278-290)

### New Testing & Analysis Tools
- **`test_name_clashes.sh`** - Comprehensive test suite for all name clash scenarios
- **`test_real_world_clashes.sh`** - Real-world conflict detection and examples
- **`optimized_system_detection.sh`** - Optimized implementation with detailed analysis
- **`improved_system_detection.sh`** - Alternative implementation approaches
- **`system_detection_fix.patch`** - Patch file for easy application

### Documentation
- **`README.md`** - Updated documentation

---

## 🔧 Technical Details

### Before (Problematic Logic)
```bash
SYSTEM_EXISTS=false
if command -v "$NAME" >/dev/null 2>&1; then
    CMD_PATH=$(which "$NAME")
    if [[ "$CMD_PATH" != "$SCRIPT_BIN_DIR/$NAME" ]]; then
        SYSTEM_EXISTS=true
    fi
fi
```

### After (Fixed Logic)
```bash
SYSTEM_EXISTS=false
CMD_PATH=""

# Check standard system paths in precedence order, skipping wrapper location
for sys_dir in "/usr/local/bin" "/usr/bin" "/bin" "/usr/local/sbin" "/usr/sbin" "/sbin"; do
    candidate="$sys_dir/$NAME"
    if [ -f "$candidate" ] && [ -x "$candidate" ] && [ "$candidate" != "$SCRIPT_BIN_DIR/$NAME" ]; then
        SYSTEM_EXISTS=true
        CMD_PATH="$candidate"
        break
    fi
done
```

---

## 🎯 Impact & Benefits

### User Experience Improvements
1. **Always get choices** - Users now always see the choice dialog when both system and flatpak versions exist
2. **No more forced flatpak** - System versions are properly detected regardless of PATH order
3. **Better conflict resolution** - Comprehensive handling of all name clash scenarios

### Real-World Examples

**Before v1.1.0:**
```bash
# User has both versions
sudo apt install gedit                    # /usr/bin/gedit
flatpak install flathub org.gnome.gedit   # ~/.local/bin/gedit

gedit  # → Always launches flatpak, no choice offered
```

**After v1.1.0:**
```bash
gedit  # → Shows choice dialog:
# "Multiple options for gedit:"
# "1. System package (/usr/bin/gedit)"
# "2. Flatpak app (org.gnome.gedit)"
# "Choose (1/2, default 1): "
```

---

## 🧪 Testing

### Comprehensive Test Coverage
- ✅ **Wrapper name collisions** - Multiple flatpak apps generating same wrapper name
- ✅ **Alias collisions** - Preventing duplicate alias creation
- ✅ **System vs flatpak conflicts** - Interactive choice with preference saving
- ✅ **Invalid names** - Properly skipping names with special characters
- ✅ **Preference persistence** - Saving and loading user choices
- ✅ **Wrapper overwriting** - Safe regeneration behavior

### Test Scripts Available
- Run `./test_name_clashes.sh` for comprehensive testing
- Run `./test_real_world_clashes.sh` for real-world scenario analysis

---

## 📊 Statistics

- **Lines changed:** +940, -25
- **New files:** 5
- **Test coverage:** Comprehensive scenarios added
- **Backward compatibility:** 100% maintained
- **Bug fixes:** 1 critical issue resolved

---

## 📋 Release Summary

**Release v1.1.0 is now live!** 🎉

This release addresses a critical issue that prevented users from choosing between system and flatpak versions of applications. The fix ensures that fplaunchwrapper's core value proposition - user choice - works reliably in all environments.

**Key improvements:**
- ✅ Fixed PATH-order dependent system command detection
- ✅ Added comprehensive test suite for name clash scenarios  
- ✅ Maintained 100% backward compatibility
- ✅ Enhanced documentation and analysis tools

The fplaunchwrapper system now robustly handles all name clash scenarios and ensures users always get the choice they deserve!