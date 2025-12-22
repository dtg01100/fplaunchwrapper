# Firefox Launch Prevention in Tests

## Problem

When running tests on a host system, there was a habit of Firefox being launched as a side-effect. This occurred because:

1. Test files created executable Firefox wrapper scripts in temporary directories
2. Some wrapper scripts contained actual `flatpak run org.mozilla.firefox` commands
3. There was no safety mechanism to prevent accidental Firefox launches during tests

## Solution

We implemented a comprehensive safety system to prevent Firefox from being launched during tests:

### 1. Safe Wrapper Scripts

All test wrapper scripts now use safe echo commands instead of actual application launches:

**Before:**
```bash
#!/bin/bash
flatpak run org.mozilla.firefox $@
```

**After:**
```bash
#!/usr/bin/env bash
echo 'Firefox launched'
exit 0
```

### 2. Safety Module

Created `fplaunch/safety.py` with comprehensive safety checks:

- `is_test_environment()`: Detects if code is running in a test environment
- `is_dangerous_wrapper()`: Checks if wrapper scripts contain dangerous commands
- `safe_launch_check()`: Performs pre-launch safety validation

### 3. AppLauncher Integration

Modified `lib/launch.py` to integrate safety checks:

- Added safety module import with graceful fallback
- Integrated `safe_launch_check()` before any application launch
- Blocks Firefox launches in test environments
- Allows non-browser applications to launch normally

### 4. Files Modified

1. **`tests/python/test_cleanup_real.py`**:
   - Changed Firefox wrapper from `flatpak run org.mozilla.firefox` to safe echo command
   - Changed Chrome wrapper from `flatpak run com.google.Chrome` to safe echo command  
   - Changed GIMP wrapper from `flatpak run org.gimp.GIMP` to safe echo command
   - Changed MyApp wrapper from `flatpak run com.example.MyApp` to safe echo command

2. **`lib/launch.py`**:
   - Added safety module import
   - Integrated safety checks in `launch()` method

3. **`fplaunch/safety.py`** (new file):
   - Comprehensive safety mechanisms

## Testing

The solution has been tested with:

1. **Safety Mechanism Tests**: Verified that the safety module correctly detects test environments and dangerous wrappers
2. **Firefox Launch Prevention**: Confirmed that Firefox launches are blocked in test environments
3. **Non-browser App Launching**: Verified that non-browser applications can still launch normally

## Impact

- ✅ **No more accidental Firefox launches** during tests
- ✅ **Safe test execution** with proper isolation
- ✅ **Non-browser apps** continue to work normally
- ✅ **Graceful fallback** if safety module is not available
- ✅ **Comprehensive coverage** of all test scenarios

## Future Considerations

- Consider adding environment variable `FPWRAPPER_TEST_ENV=true` for explicit test environment marking
- Extend safety checks to other browsers (Chrome, Chromium, etc.)
- Add logging for safety events in production environments