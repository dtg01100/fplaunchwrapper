# AI Coding Agent Instructions for fplaunchwrapper

## Architecture Overview

This project manages Flatpak application wrappers, enabling simplified commands like `firefox` instead of `flatpak run org.mozilla.firefox`. The architecture uses a **direct package structure** with all implementation in the `lib/` directory.

### Package Structure

- **`lib/`** - Implementation modules (actual code: `cleanup.py`, `cli.py`, `config_manager.py`, `generate.py`, `launch.py`, `manage.py`, `systemd_setup.py`, etc.)

**Import Strategy**: Always import from `lib.*` directly since this is now the package structure.

```python
# ✅ Correct - works in both dev and installed environments
from lib.manage import WrapperManager
from lib.cleanup import WrapperCleanup
from lib.generate import WrapperGenerator
```

## Key Entry Points

The project defines 9 CLI entry points in `pyproject.toml`:

| Command | Entry Point | Purpose |
|---------|-------------|---------|
| `fplaunch` | `fplaunch.fplaunch:main` | Main CLI |
| `fplaunch-generate` | `fplaunch.generate:main` | Generate wrappers |
| `fplaunch-manage` | `fplaunch.manage:main` | Manage wrappers |
| `fplaunch-launch` | `fplaunch.launch:main` | Launch apps |
| `fplaunch-cleanup` | `fplaunch.cleanup:main` | Cleanup artifacts |
| `fplaunch-setup-systemd` | `fplaunch.systemd_setup:main` | Systemd integration |
| `fplaunch-config` | `fplaunch.config_manager:main` | Configuration |
| `fplaunch-monitor` | `fplaunch.flatpak_monitor:main` | Flatpak monitoring |
| `fplaunch-cli` | `fplaunch.cli:main` | CLI utilities |

## Testing Conventions

### Test Location & Structure

- **Unit tests**: `tests/python/` - 40+ test files
- **Pytest config**: `tests/conftest.py` with shared fixtures
- **Test runner**: Custom `run_tests.py` for simple tests, pytest for full suite

### Important Test Fixtures

The `tests/conftest.py` provides autouse fixtures that run for every test:

1. **`mock_flatpak_binary`** - Creates a mock `flatpak` binary that logs calls instead of executing real Flatpak commands. Supports `list`, `info`, `run`, and `override` commands.

2. **`isolated_home`** - Provides isolated HOME/XDG directories (`~/.config/fplaunchwrapper`, `~/.local/share/fplaunchwrapper`, etc.) for test isolation.

3. **`cleanup_legacy_config`** - Removes default `~/.config/fplaunchwrapper` after tests.

### Running Tests

```bash
# Run all tests with pytest
python3 -m pytest tests/python/ -v

# Run specific test file
python3 -m pytest tests/python/test_config_manager.py -v

# Run custom test runner (simpler tests only)
python3 run_tests.py

# Run with coverage
python3 -m pytest tests/python/ --cov=lib --cov-report=html
```

**Note**: The custom `run_tests.py` cannot run tests requiring pytest fixtures. Use `python3 -m pytest` for the full suite.

### Mock Pattern

Tests use `@pytest.fixture` with `tmp_path_factory` and `monkeypatch` for isolation. Example from `tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def mock_flatpak_binary(tmp_path_factory, monkeypatch):
    mock_bin_dir = tmp_path_factory.mktemp("mock_bin")
    flatpak_path = mock_bin_dir / "flatpak"
    # ... create mock script ...
    monkeypatch.setenv("PATH", f"{mock_bin_dir}:{old_path}")
    yield flatpak_log
```

## Build & Development Workflow

### Installation

```bash
# Development installation
pip install -e ".[dev]"

# Or with uv
uv tool install fplaunchwrapper
```

### Code Style & Quality

```bash
# Format code
ruff check --fix .
black .

# Run linters
ruff check .
flake8 .
pylint lib/

# Security scan
bandit -r lib/
```

### Project Configuration

- **Python versions**: 3.8-3.13 (configured in `pyproject.toml`)
- **Dependencies**: Split into `dependencies`, `robustness`, `advanced`, `dev`, `security`, `integration`
- **Build system**: setuptools with pyproject.toml
- **Package manager**: Entry points defined in `[project.scripts]`

## Critical Patterns

### 1. Path Handling

Use `pathlib.Path` throughout. Key paths:
- `Path.home() / "bin"` - default wrapper directory
- `Path.home() / ".config" / "fplaunchwrapper"` - config directory
- `Path.home() / ".local" / "share" / "fplaunchwrapper"` - data directory

### 2. Flatpak ID Handling

Flatpak IDs follow pattern: `com.example.App_Version` (e.g., `org.mozilla.firefox`). Use `sanitize_id_to_name()` in `lib/python_utils.py` to convert IDs to wrapper names.

### 3. Systemd Integration

The `systemd_setup.py` module handles:
- Creating service/path/timer units in `~/.config/systemd/user/`
- Enabling/disabling units with `systemctl --user`
- Cron fallback when systemd unavailable

### 4. Emit Mode Pattern

Many modules support "emit mode" (`emit_mode=True`) that prints actions without executing:
- `generate.py` - shows what wrappers would be created
- `cleanup.py` - shows what would be removed
- `manage.py` - shows what changes would be made

### 5. Error Handling Pattern

Modules log via `self.log(message, level)` where level is `info`, `warning`, `error`, or `success`. Rich console output when available, plain print fallback.

## Important Files & Directories

| Path | Purpose |
|------|---------|
| `lib/` | Implementation modules (Python package) |
| `tests/python/` | Unit tests |
| `tests/conftest.py` | Pytest fixtures and configuration |
| `pyproject.toml` | Project metadata and configuration |
| `Makefile` | Man page generation |
| `docs/` | Documentation including man pages |
| `run_tests.py` | Custom simple test runner |

## Common Tasks

### Adding a New Module

1. Create implementation in `lib/newmodule.py`
2. Add entry point to `pyproject.toml` if CLI command needed

### Adding a New Test

1. Create `tests/python/test_newmodule.py`
2. Import from `lib.*` directly
3. Use pytest fixtures from `conftest.py`
4. Mock flatpak with provided fixtures

### Modifying CLI Commands

1. Find entry point in `pyproject.toml` → maps to `lib.<module>:main`
2. Modify implementation in `lib/<module>.py`

## Known Issues & Workarounds

1. **Test isolation**: Some tests fail when run together due to global state (PATH, sys.path). Run individual test files to verify fixes.

2. **Mock objects**: Tests with complex mocking may need `MagicMock` or `side_effect` for proper configuration.

3. **Systemd availability**: Tests skip when systemd not available (use cron fallback tests instead).

## References

- Main docs: `README.md`
- Quick start: `QUICKSTART.md`
- Examples: `examples.md`
- Testing guide: `tests/COMPLEHENSIVE_QA_GUIDE.md`
- Contributing: `CONTRIBUTING.md`
