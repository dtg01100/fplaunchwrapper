# Memories

## Patterns

## Decisions

## Fixes

### mem-1774608669-d492
> Fixed bugs in fplaunchwrapper: (1) set_preference accepted any string - now validates against system/flatpak/auto, (2) symlink cleanup compared Path to strings - now checks target.name, (3) cron-interval didn't catch ValueError, (4) uninstall silently swallowed exceptions, (5) hook script loading silent exceptions, (6) wrapper file reading silent exceptions, (7) systemd_setup missing return False on error
<!-- tags: bugs, validation, error-handling | created: 2026-03-27 -->

## Context
