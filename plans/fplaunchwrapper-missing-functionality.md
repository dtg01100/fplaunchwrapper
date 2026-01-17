# fplaunchwrapper Missing Functionality - Implementation Plan

## Overview
This plan addresses the missing functionality in fplaunchwrapper identified through documentation review. The issues are prioritized based on their impact, user demand, and implementation complexity.

## High Priority Items (Must-Have)

### 1. Missing CLI Commands
- **`fplaunch-cli info` command**: Implement to show detailed wrapper information
- **`fplaunch-cli search` command**: Implement as alias for `discover` with search functionality
- **`fplaunch-cli install` command**: Implement to install Flatpak apps and create wrappers
- **`fplaunch-cli manifest` command**: Implement to show/manipulate Flatpak manifests
- **`fplaunch-cli files` command**: Implement to show generated files
- **`fplaunch-cli uninstall` command**: Implement to remove Flatpak apps and wrappers

### 2. Configuration Management Improvements
- **TOML configuration schema enforcement**: Add validation for configuration files
- **Configuration migration from older formats**: Implement backward compatibility
- **Configuration templating**: Add support for template-based config creation

### 3. Alias Management Enhancements
- **Complete namespace collision detection**: Improve collision detection for aliases
- **Recursive alias resolution**: Implement support for alias chains

## Medium Priority Items (Should-Have)

### 4. Cleanup Functionality
- **Orphaned systemd units scanning**: Add systemd unit cleanup
- **Orphaned cron entries scanning**: Add cron job cleanup
- **Shell completion files scanning**: Add completion file cleanup
- **Dependency analysis**: Add dependency checking for wrappers

### 5. Monitoring System
- **Watchdog integration for real-time monitoring**: Complete watchdog library integration
- **Event batching to prevent excessive regeneration**: Implement event coalescing
- **Integration with systemd notify protocol**: Add systemd notify support

### 6. Wrapper Script Features
- **Complete `--fpwrapper-sandbox-yolo` implementation**: Ensure YOLO mode works correctly
- **Enhanced `--fpwrapper-edit-sandbox`**: Improve sandbox editing functionality

## Low Priority Items (Nice-to-Have)

### 7. Advanced Configuration Features
- **Complete configuration profiles support**: Enhance profile management
- **Full permission presets management**: Improve preset functionality

### 8. Scripting and Automation
- **Enhanced pre-launch script execution**: Improve pre-launch script support
- **Enhanced post-launch script execution**: Improve post-run script support

### 9. System Integration
- **Complete cron fallback for automatic updates**: Implement full cron support
- **Enhanced systemd service management**: Improve systemd integration

## Implementation Strategy

### Phase 1: Foundation (Weeks 1-2)
- [ ] Implement missing CLI commands (info, search, install, etc.)
- [ ] Improve configuration management
- [ ] Enhance alias management

### Phase 2: Core Features (Weeks 3-4)
- [ ] Complete cleanup functionality
- [ ] Implement watchdog integration
- [ ] Improve monitoring system

### Phase 3: Advanced Features (Weeks 5-6)
- [ ] Enhance wrapper script features
- [ ] Complete configuration profiles
- [ ] Improve scripting support

### Phase 4: System Integration (Weeks 7-8)
- [ ] Complete cron fallback
- [ ] Enhance systemd integration
- [ ] Final testing and bug fixes

## Resources Required

- **Python developers**: 2-3 developers with experience in:
  - CLI development with Click
  - Flatpak integration
  - Systemd and cron integration
  - Configuration management with TOML

- **Testing resources**: Test environments on multiple Linux distributions

## Risk Assessment

- **Complexity risk**: Some features require deep system integration
- **Testing risk**: Need to test on multiple distributions
- **Compatibility risk**: Need to maintain backward compatibility

## Success Metrics

- All documented features implemented
- Comprehensive test coverage
- No breaking changes
- User documentation updated

## Conclusion

This plan addresses all the missing functionality identified in the fplaunchwrapper documentation. By prioritizing high-impact features first and following a phased approach, we can deliver a complete and stable version of the tool.
