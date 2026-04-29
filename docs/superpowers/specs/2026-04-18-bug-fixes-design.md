## Summary

This design covers three bug fixes discovered after review and manual CLI exercise:

1. `fplaunch launch` must honor CLI context such as `--config-dir` and `--verbose`.
2. Wrapper lookup must fail closed when path-safety checks raise.
3. Active profile selection must persist across manager instances and CLI invocations.

## Scope

The work is intentionally narrow:

- Add regression tests for each bug before production edits.
- Make the smallest production changes needed to satisfy those tests.
- Re-run focused and full verification after the fixes.

Out of scope:

- Broad CLI refactoring.
- Template/env-file hardening beyond the three confirmed issues.
- Changes to unrelated command behavior.

## Design

### Launch CLI Context

The `launch` command currently constructs `AppLauncher` without passing the resolved CLI context. The fix is to pass `config_dir` and `verbose` from `ctx.obj` so launcher resolution uses the same configuration root as other commands. `bin_dir` will continue to be derived by `AppLauncher` from the provided config directory to avoid duplicating resolution logic in the CLI layer.

### Path-Safety Fail-Closed Behavior

`_wrapper_exists()` and `_find_wrapper()` currently continue to raw filesystem checks if `_is_path_safe()` raises. That creates a fail-open path for traversal or safety-check errors. The fix is to treat any exception from the safety check as unsafe and return `False` or `None` immediately.

### Profile Persistence

`switch_profile()` persists `active_profile`, but config loading does not restore it. The fix is to load `active_profile` from serialized configuration during both validated and unvalidated config application so a new `EnhancedConfigManager` instance sees the selected profile.

## Testing

Tests will be added first for:

- CLI launch propagation of `config_dir` and `verbose`.
- Fail-closed wrapper lookup when `_is_path_safe()` raises.
- Cross-instance persistence of `active_profile`.

Verification will include focused regression tests followed by the existing repo checks:

- `pytest`
- `ruff check lib fplaunch tests/python`
- `python -m compileall lib fplaunch tests/python`

## Risk Notes

Risk is low because the changes are localized and behavior-preserving outside the three bug paths. The main compatibility impact is that invalid or unsafe wrapper resolution will now stop immediately instead of silently falling back to filesystem checks.
