# AGENTS.md

**Version:** 1.0
**Date:** 2026-06-02
**Purpose:** Technical reference for fplaunchwrapper development (methodology in `.clio/instructions.md`)

---

## Project Overview

**fplaunchwrapper** is a Python utility that generates and manages wrapper scripts for Flatpak applications. It lets users launch sandboxed apps by their simple name (e.g. `firefox` instead of `flatpak run org.mozilla.firefox`) while intelligently choosing between system packages, Flatpak installations, and per-app user preferences.

- **Language:** Python 3.10+ (3.8 declared minimum, 3.10 enforced in `pyproject.toml`)
- **Package layout:** Direct - all implementation lives in the `lib/` directory, installed as the `lib` package
- **Architecture:** Click-based CLI dispatcher → domain modules (`generate`, `manage`, `launch`, `cleanup`, `config_manager`, `systemd_setup`, `flatpak_monitor`) → safety/path/util helpers
- **Status:** Production/Stable (v1.4.0)
- **License:** MIT (see `LICENSE` - do not modify)

---

## Quick Setup

```bash
# Install uv (fast Python package manager) - one-time
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and set up dev environment (creates .venv, installs all extras)
git clone https://github.com/dtg01100/fplaunchwrapper.git
cd fplaunchwrapper
./setup-dev.sh              # installs [dev] extras by default

# Or minimal manual setup
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Verify
fplaunch --help
python3 -m pytest tests/python/ -q
```

---

## Architecture

```
                          User terminal
                               │
                               ▼
                 ┌──────────────────────────────┐
                 │  lib/cli.py (Click group)    │
                 │  lib/fplaunch.py (entry)     │
                 └──────────────────────────────┘
                               │
        ┌──────────┬───────────┼───────────┬──────────────┐
        ▼          ▼           ▼           ▼              ▼
   generate.py  manage.py  launch.py  cleanup.py   systemd_setup.py
   (wrappers)   (CRUD)     (exec)     (orphans)    (units/cron)
        │          │           │           │              │
        └──────────┴───────────┼───────────┴──────────────┘
                               ▼
                ┌──────────────────────────────┐
                │  config_manager.py           │
                │  EnhancedConfigManager       │
                │  + Pydantic validation       │
                │  + profiles + presets        │
                └──────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        flatpak_monitor    notifications   safety.py
        (watchdog FS       (libnotify)     (forbidden
         events)                            names, path
                                            traversal)
                               │
                               ▼
       lib/paths.py, lib/validation.py, lib/python_utils.py
       lib/exceptions.py, lib/subprocess_helpers.py,
       lib/import_utils.py, lib/logging_utils.py
```

**Generated artifact:** `lib/templates/wrapper.template.sh` is a bash script that detects context (interactive vs. desktop), reads prefs from `~/.config/fplaunchwrapper/<app>.pref`, and dispatches to either the system binary or `flatpak run <id>`. The Python side never runs user code - it only writes the template once per wrapper.

---

## Directory Structure

| Path | Purpose |
|------|---------|
| `lib/` | Implementation package (installed as `lib`) |
| `lib/cli.py` | Click CLI dispatcher (fplaunch-cli entry point) |
| `lib/fplaunch.py` | Main `fplaunch` entry point |
| `lib/cli_commands.py` | Click subcommand definitions |
| `lib/cli_generation.py` | `generate` subcommand group |
| `lib/cli_inspect.py` | `inspect` / read-only diagnostic subcommands |
| `lib/cli_profiles.py` | `profiles` subcommand group |
| `lib/cli_presets.py` | `presets` subcommand group |
| `lib/cli_system.py` | `system` / install/uninstall subcommands |
| `lib/cli_systemd.py` | `systemd` subcommand group |
| `lib/cli_utils.py` | Utility subcommand helpers |
| `lib/generate.py` | `WrapperGenerator` - discover flatpaks, write wrappers |
| `lib/manage.py` | `WrapperManager` - list/remove/set-preference |
| `lib/launch.py` | `AppLauncher` - launch apps with preference handling |
| `lib/cleanup.py` | `WrapperCleanup` - remove orphaned wrappers |
| `lib/systemd_setup.py` | `SystemdSetup` - create user units, cron fallback |
| `lib/flatpak_monitor.py` | `FlatpakMonitor` - watchdog-based daemon |
| `lib/config_manager.py` | `EnhancedConfigManager` - TOML config + Pydantic |
| `lib/config_manager_presets.py` | Built-in `BUILTIN_PRESETS` dict |
| `lib/config_manager_cli.py` | `fplaunch-config` console script |
| `lib/config_models.py` | `AppPreferences`, `WrapperConfig` dataclasses |
| `lib/config_validation.py` | Pydantic validation models |
| `lib/config_constants.py` | `HOOK_FAILURE_MODES` etc. |
| `lib/exceptions.py` | `FplaunchError` hierarchy + `FORBIDDEN_NAMES` |
| `lib/safety.py` | `is_test_environment`, `safe_launch_check`, etc. |
| `lib/validation.py` | `validate_app_id`, `validate_wrapper_name`, `check_path_traversal` |
| `lib/paths.py` | Centralized XDG path resolution |
| `lib/python_utils.py` | Path normalization, locks, temp files, exec lookup |
| `lib/subprocess_helpers.py` | `run_systemctl`, `run_crontab` |
| `lib/import_utils.py` | `safe_import`, `ImportErrorHandler` |
| `lib/logging_utils.py` | `LoggingMixin`, `console`, `console_err` |
| `lib/desktop_parser.py` | `.desktop` file parser |
| `lib/portal_launcher.py` | XDG portal launch path |
| `lib/notifications.py` | libnotify wrapper |
| `lib/templates/wrapper.template.sh` | The actual wrapper bash template |
| `tests/python/` | pytest test suite (~50 files, 1397+ tests) |
| `tests/conftest.py` | Shared fixtures: `mock_flatpak_binary`, `isolated_home`, etc. |
| `tests/adversarial/` | Adversarial / fuzz tests |
| `tests/shell/` | Shell-level integration tests |
| `docs/man/` | Man pages (`fplaunch-generate.1` etc.) |
| `docs/info/` | Texinfo source for `fplaunchwrapper.info` |
| `docs/reports/` | Archived bug-fix reports |
| `docs/superpowers/` | Internal design notes |
| `packaging/` | Debian packaging helpers |
| `plans/` | Forward-looking design specs |
| `examples/` | Example pre/post-launch hook scripts |
| `pyproject.toml` | Package metadata, dependencies, tool config |
| `setup-dev.sh` | One-shot dev environment bootstrap |
| `Makefile` | Man/info page generation |
| `CHANGES.md` | Keep-a-Changelog format release notes |

---

## Code Style

**Python Conventions:**

- **Target:** Python 3.10+ (`target-version = "py310"` in ruff/black)
- **Line length:** 100 (ruff, black, flake8 all agree)
- **Indentation:** 4 spaces, no tabs
- **Strings:** Double quotes preferred, but match local style
- **Type hints:** Required for all public functions; encouraged internally
- **Docstrings:** Module-level docstring on every `.py` file; function docstrings on public API
- **Future imports:** `from __future__ import annotations` at top of new modules
- **Pathlib:** Use `pathlib.Path`, not `os.path`. `paths.py` is the centralized resolver.
- **Subprocess:** Always list-form `subprocess.run([...])`, never `shell=True`. Use `lib/subprocess_helpers.py` for systemctl/crontab.
- **Logging:** Use the `LoggingMixin` (`self.log(msg, level)`) for user-facing output; stdlib `logging` for diagnostic output.
- **Rich console:** Use the module-level `console` / `console_err` from `lib/logging_utils.py`.

**Module Header Template:**

```python
#!/usr/bin/env python3
"""One-line description of module purpose.

Longer description if needed. Explain WHY the module exists,
not just what it does.
"""

from __future__ import annotations

# imports (stdlib, then third-party, then local `from . import ...`)
```

**Exception Hierarchy:**

Always raise the most specific `FplaunchError` subclass from `lib/exceptions.py`. Catch the same. Never use bare `except:` or catch `Exception` broadly. Example:

```python
from lib.exceptions import WrapperNotFoundError

try:
    wrapper = self._read_wrapper(name)
except FileNotFoundError as e:
    raise WrapperNotFoundError(name) from e
```

**Emit Mode Pattern:**

Any function that mutates the filesystem or calls external commands must support `emit_mode=True` (dry-run). Convention:

```python
def do_thing(self, target: Path, emit_mode: bool = False) -> bool:
    if emit_mode:
        self.log(f"Would modify {target}", "emit")
        return True
    target.write_text("...")
    return True
```

**Validation:**

- Use `validate_app_id()` / `validate_wrapper_name()` / `check_path_traversal()` from `lib/validation.py` for any user-supplied identifier.
- Use `is_forbidden(name)` from `exceptions.ForbiddenNameError` before creating a wrapper.

---

## Module Naming Conventions

| File | Role | Naming |
|------|------|--------|
| `lib/<domain>.py` | Core domain logic | snake_case |
| `lib/cli_<group>.py` | Click subcommand group | `cli_` prefix + group name |
| `lib/<domain>_<role>.py` | Helper module for a domain | `<domain>_<role>.py` |
| `lib/templates/*.sh` | Generated script templates | `*.template.sh` |
| `tests/python/test_<name>.py` | pytest module | `test_` prefix |
| `tests/python/test_<domain>_<aspect>.py` | Aspect-focused tests | `test_<domain>_<aspect>.py` |

**Avoid:**

- `lib/old_<name>.py`, `lib/backup_<name>.py` - delete dead code, don't archive it in the package
- `lib/<name>_v2.py` - rename in place, use git history
- Two modules with the same public class name

---

## Testing

**Test command (must pass before every commit):**

```bash
# Full suite (1397+ tests, takes ~7s)
python3 -m pytest tests/python/ -q

# Single file while iterating
python3 -m pytest tests/python/test_config_manager.py -v

# Single test
python3 -m pytest tests/python/test_xxx.py::TestClass::test_method -v

# With coverage
python3 -m pytest tests/python/ --cov=lib --cov-report=term-missing
```

**Test layout rules:**

- File: `tests/python/test_<module>.py`
- Class: `Test<Subject>` (e.g. `TestConfigManager`, `TestAppLauncher`)
- Function: `test_<behavior>` - describe the contract, not the implementation
- Use fixtures from `conftest.py`: `isolated_home`, `wrapper_generator`, `wrapper_manager`, `app_launcher`
- **Do not** modify `conftest.py` fixtures unless absolutely necessary - add a new fixture in the test file instead
- **Do not** mock `lib.*` modules - mock the boundary (`subprocess.run`, `Path.write_text`, etc.) not the internals

**Hermeticity checklist:**

- No `os.environ[...] = ...` outside `monkeypatch` context
- No reliance on real `~/.config/fplaunchwrapper`
- No real `flatpak` invocations (the autouse `mock_flatpak_binary` fixture handles this)
- No network calls
- Tests must pass in any order, in parallel, and multiple times consecutively

**Test markers** (registered in `pyproject.toml` and `conftest.py`):

| Marker | Purpose |
|--------|---------|
| `slow` | Long-running; deselect with `-m "not slow"` |
| `integration` | Cross-module; may touch real filesystem |
| `security` | Adversarial / fuzz-style input validation |
| `unit` | Single-function isolated test |
| `real_execution` | Minimal mocking |

**When fixing a bug, the test must come first:**

1. Write a failing test that reproduces the bug
2. Confirm it fails: `python3 -m pytest tests/python/test_xxx.py -v`
3. Fix the code
4. Confirm the test passes and the full suite still passes

---

## Commit Format

```
<type>(<scope>): <brief description>

[optional body: WHY this change, not WHAT]
[optional footer: BREAKING CHANGE, Closes #N, etc.]
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`

**Scope examples:** `cli`, `generate`, `manage`, `launch`, `config`, `cleanup`, `monitor`, `paths`, `safety`, `validation`, `exceptions`, `docs`, `tests`

**Examples:**

```
fix(manage): validate wrapper name before touching filesystem

remove_wrapper and set_preference were accepting any string as a
wrapper name, allowing names with /, \\0, or leading hyphens to
slip through. Wire validate_wrapper_name() into both code paths.
```

```
refactor(config): split config_manager into presets + cli modules

Extract BUILTIN_PRESETS into config_manager_presets.py and the
fplaunch-config main() into config_manager_cli.py. Re-export from
config_manager.py for backward compatibility.
```

**Pre-commit checklist:**

- [ ] `python3 -m pytest tests/python/ -q` passes
- [ ] `python3 -m ruff check lib/` passes (0 errors)
- [ ] `python3 -m mypy lib/` passes (0 errors)
- [ ] `python3 -m pylint lib/<changed_module>.py` >= 9.5/10
- [ ] Commit message explains WHY, not just WHAT
- [ ] No handoff files (`ai-assisted/`, `.clio/memory/`) staged
- [ ] No `TODO` / `FIXME` left in the diff (finish the work or revert)

---

## Development Tools

**Lint / format / type-check:**

```bash
# Lint (preferred - faster, replaces flake8/isort/pyupgrade)
python3 -m ruff check lib/
python3 -m ruff check --fix lib/          # auto-fix safe issues

# Format
python3 -m black lib/ tests/python/

# Type check
python3 -m mypy lib/

# Lint (supplemental)
python3 -m flake8 lib/
python3 -m pylint lib/                    # reports 9.7-9.9/10 on healthy modules
python3 -m bandit -c .bandit.yml -r lib/  # security scan

# All of the above
pre-commit run --all-files
```

**Run a specific entry point locally:**

```bash
# Editable install (already done if you ran setup-dev.sh)
fplaunch --help
fplaunch generate --emit ~/bin
fplaunch list
fplaunch config list-presets

# Or via the module
python3 -m lib.fplaunch --help
python3 -m lib.config_manager list-presets
```

**Coverage:**

```bash
python3 -m pytest tests/python/ --cov=lib --cov-report=term-missing
python3 -m pytest tests/python/ --cov=lib --cov-report=html  # htmlcov/
```

**Useful one-liners:**

```bash
# Find the largest modules
find lib -name "*.py" -not -path "*/templates/*" -exec wc -l {} \; | sort -rn | head -10

# Find unused imports (catches re-exported ones too)
python3 -m ruff check lib/ --select F401

# Run a flaky test 10 times
for i in {1..10}; do python3 -m pytest tests/python/test_xxx.py -q || break; done

# Show what a recent commit changed
git show --stat HEAD

# See test discovery timing
python3 -m pytest tests/python/ --durations=20
```

---

## Common Patterns

**LoggingMixin (preferred for user-facing output):**

```python
from lib.logging_utils import LoggingMixin

class MyTool(LoggingMixin):
    def run(self) -> None:
        self.log("Starting", "info")
        self.log("Something off", "warning")  # goes to stderr
        self.log("Done", "success")
```

**Adding a Click subcommand:**

```python
# lib/cli_<group>.py
import click
from lib.cli import cli  # root group

@cli.group()
def mygroup() -> None:
    """My command group."""

@mygroup.command("list")
@click.pass_context
def mygroup_list(ctx: click.Context) -> None:
    """List things."""
    from lib.mymodule import list_things
    items = list_things()
    click.echo("\n".join(items))
```

**Exception hierarchy (extend, don't replace):**

```python
from lib.exceptions import FplaunchError

class MySpecificError(FplaunchError):
    """Raised when my thing goes wrong."""
    def __init__(self, name: str) -> None:
        super().__init__(f"My thing failed: {name}", {"name": name})
```

**Optional dependency (e.g. watchdog, pydantic):**

```python
# At top of module
try:
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except ImportError:
    Observer = None  # type: ignore[assignment,misc]
    WATCHDOG_AVAILABLE = False

# At use site
if not WATCHDOG_AVAILABLE:
    raise RuntimeError("Install fplaunchwrapper[monitor] to use this feature")
```

**Generating a wrapper safely:**

```python
from lib.validation import validate_app_id, validate_wrapper_name
from lib.exceptions import ForbiddenNameError, InvalidFlatpakIdError

def generate(app_id: str, name: str, *, emit_mode: bool = False) -> Path:
    ok, err = validate_app_id(app_id)
    if not ok:
        raise InvalidFlatpakIdError(app_id, reason=err)
    ok, err = validate_wrapper_name(name)
    if not ok:
        raise ValueError(err)
    if ForbiddenNameError.is_forbidden(name):
        raise ForbiddenNameError(name, is_builtin=True)
    # ... write the wrapper ...
```

---

## Documentation

### What Needs Documentation

| Change Type | Required Documentation |
|-------------|------------------------|
| New CLI subcommand | Update `COMMAND_REFERENCE.md` |
| New wrapper template flag | Update `docs/FPWRAPPER_FORCE.md` (or the relevant docs page) and `COMMAND_REFERENCE.md` |
| New dependency | Update `pyproject.toml`, `DESIGN.md` dependency table, `QUICKSTART.md` install snippet |
| New exception type | Update `docs/IMPLEMENTATION_STATUS.md` exception hierarchy section |
| New module | Update `DESIGN.md` "Directory Structure" + "Core Components" sections |
| Behavior change in `safety.py` | Update `DESIGN.md` "Security Model" section |
| Bug fix with a regression | Add a short entry to `docs/reports/<bug-name>.md` then move to `docs/reports/` |

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview, install, quick start |
| `QUICKSTART.md` | 2-minute getting-started |
| `DESIGN.md` | Architecture, components, configuration, security model |
| `COMMAND_REFERENCE.md` | All `fplaunch` commands and subcommands |
| `CONTRIBUTING.md` | Dev setup, testing, PR process |
| `CHANGES.md` | Keep-a-Changelog release notes |
| `docs/ADVANCED_USAGE.md` | Power-user recipes |
| `docs/FPWRAPPER_FORCE.md` | Interactive/desktop mode reference |
| `docs/IMPLEMENTATION_STATUS.md` | Feature completion status |
| `docs/SECURITY_REVIEW.md` | Security review notes |
| `docs/TEST_COVERAGE_ANALYSIS.md` | Coverage analysis |
| `docs/reports/` | Archived bug-fix reports (historical) |
| `docs/man/*.1`, `*.7` | Man pages (generated/checked-in) |
| `.clio/instructions.md` | Project methodology (this project's Unbroken Method) |
| `AGENTS.md` | This file - technical reference |
| `agents.md` (lowercase) | Legacy AI-agent guidelines - kept for historical context |

---

## Anti-Patterns (What NOT To Do)

| Anti-Pattern | Why It's Wrong | What To Do |
|--------------|----------------|------------|
| `except Exception: pass` | Hides bugs and breaks the safety model | Catch the specific exception type from `lib/exceptions.py` |
| `subprocess.run(cmd, shell=True)` | Command injection; the entire safety model assumes list-form args | Use list-form args; use `lib/subprocess_helpers.py` for systemctl/crontab |
| Bypassing `validate_wrapper_name` / `ForbiddenNameError.is_forbidden` | Allows wrappers named `bash`, `rm`, `git`, etc. | Always validate first |
| Writing to `~/.config/fplaunchwrapper` directly in tests | Pollutes the user's real config | Use the `isolated_home` fixture from `conftest.py` |
| `os.environ["VAR"] = "value"` in test bodies | Doesn't clean up; breaks parallel test runs | Use `monkeypatch.setenv("VAR", "value")` |
| Hardcoded paths like `/home/user/.config/...` | Breaks on systems with different HOME / XDG | Use `lib/paths.py` |
| Catching `KeyboardInterrupt` to "clean up" | Hides cancellation; interferes with `--timeout` test safety | Let it propagate; clean up in `finally` blocks only for non-cancellation paths |
| Adding a new entry point to `pyproject.toml` without a console script wrapper | Breaks the `fplaunch-<sub>` helper pattern | Add `[project.scripts]` entry AND the `main()` function in the module |
| Modifying `tests/conftest.py` fixtures to fix one test | Breaks isolation for all other tests | Add a local fixture in the failing test file |
| Committing `ai-assisted/`, `.clio/memory/`, or `.clio/sessions/` | Internal session data must not be public | Verify with `git status` before every commit; add to `.gitignore` if missing |

---

## Quick Reference

```bash
# Tests
python3 -m pytest tests/python/ -q                       # full suite
python3 -m pytest tests/python/test_X.py::TestY::test_z  # one test
python3 -m pytest tests/python/ --cov=lib                # with coverage

# Lint / type / format
python3 -m ruff check lib/
python3 -m black lib/ tests/python/
python3 -m mypy lib/
python3 -m pylint lib/<module>.py
python3 -m bandit -c .bandit.yml -r lib/

# Run the CLI locally
fplaunch --help
fplaunch generate --emit ~/bin
fplaunch list
fplaunch config list-presets

# Entry points map
fplaunch               -> lib.fplaunch:main
fplaunch-cli           -> lib.cli:main
fplaunch-generate      -> lib.generate:main
fplaunch-manage        -> lib.manage:main
fplaunch-launch        -> lib.launch:main
fplaunch-cleanup       -> lib.cleanup:main
fplaunch-setup-systemd -> lib.systemd_setup:main
fplaunch-config        -> lib.config_manager:main
fplaunch-monitor       -> lib.flatpak_monitor:main

# Project metadata
Version: 1.4.0
Python: 3.10+
License: MIT
Repository: https://github.com/dtg01100/fplaunchwrapper
```

---

*For project methodology and workflow, see `.clio/instructions.md`.*
