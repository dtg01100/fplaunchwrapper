# Guidelines for AI Agents

This document provides guidelines for AI agents working on the fplaunchwrapper project.

## General Principles

1. **Understand before acting**: Read and understand the codebase structure, existing patterns, and tests before making changes.
2. **Preserve functionality**: Ensure existing tests continue to pass after any modifications.
3. **Be systematic**: Break complex tasks into smaller, manageable steps and verify each step.
4. **Test hermetically**: All tests must be hermetic - they must not depend on external state.

## Testing Requirements

### Hermetic Testing (Critical)

**All tests MUST be hermetic.** A hermetic test:

- Does not depend on external state (environment variables, filesystem outside temp dirs, network, etc.)
- Does not modify the host system
- Cleans up after itself
- Can run in parallel with other tests
- Can run multiple times with the same results

**Requirements for hermetic tests:**

```python
# GOOD: Uses monkeypatch for environment isolation
def test_example(self, monkeypatch):
    monkeypatch.setenv("FPWRAPPER_TEST_ENV", "true")
    # test code...

# BAD: Directly modifies os.environ
def test_example():
    os.environ["FPWRAPPER_TEST_ENV"] = "true"
    # test code...
    # Does NOT clean up - pollutes other tests!

# GOOD: Uses fixtures with proper cleanup
@pytest.fixture
def temp_env(self, tmp_path):
    # Setup
    old_env = os.environ.get("KEY")
    os.environ["KEY"] = "value"
    yield tmp_path
    # Cleanup
    if old_env is None:
        del os.environ["KEY"]
    else:
        os.environ["KEY"] = old_env
```

**Mock external commands:**

```python
# GOOD: Mocks subprocess.run for external commands
@patch("subprocess.run")
def test_flatpak_command(self, mock_run):
    mock_run.return_value = Mock(returncode=0, stdout="app.id\n", stderr="")
    # test code...
```

### Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/python/test_generate_real.py -v

# Run tests multiple times to check for flakiness
for i in {1..5}; do python3 -m pytest tests/ -q; done
```

## Code Changes

### Before Making Changes

1. Read the relevant source files
2. Understand the existing patterns and conventions
3. Identify all files that need modification
4. Plan the changes

### After Making Changes

1. Run affected tests to verify they pass
2. Run full test suite to ensure no regressions
3. Run tests multiple times to check for hermeticity/flakiness
4. Verify code formatting with Black

## Bug Fix Guidelines

When fixing bugs:

1. **Identify the root cause**: Don't just patch symptoms
2. **Write a regression test**: Ensure the bug doesn't reappear
3. **Verify the fix**: Run tests to confirm the fix works

## Security Considerations

- Never execute user input as shell commands
- Validate all file paths before use
- Sanitize environment variables
- Use secure temporary files with proper permissions
- Mock external commands (flatpak, systemctl) in tests

## Project Structure

```
lib/
├── cli.py               # CLI interface (Click)
├── generate.py          # Wrapper generation
├── manage.py            # Wrapper management
├── launch.py            # App launching
├── cleanup.py           # Cleanup functionality
├── systemd_setup.py     # Systemd setup
├── config_manager.py    # Configuration management
├── flatpak_monitor.py   # File monitoring
├── python_utils.py      # Utility functions
└── safety.py            # Safety mechanisms

tests/
├── python/              # Python tests
└── adversarial/         # Adversarial tests
```

## Common Patterns

### Testing CLI Commands

```python
from click.testing import CliRunner

def test_cli_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
```

### Mocking Environment Variables

```python
def test_with_env(self, monkeypatch):
    # Save original
    old = os.environ.get("VAR")
    monkeypatch.setenv("VAR", "test_value")
    yield
    # Cleanup happens via monkeypatch
```

### Mocking Subprocess

```python
@patch("subprocess.run")
@patch("lib.generate.find_executable")
def test_flatpak_mock(self, mock_find, mock_run):
    mock_find.return_value = "/usr/bin/flatpak"
    mock_run.return_value = Mock(returncode=0, stdout="app.id\n", stderr="")
```

## Code Quality Checklist

- [ ] Tests are hermetic (no external state dependency)
- [ ] Tests pass consistently (run 3+ times)
- [ ] Code follows existing patterns
- [ ] Type hints present
- [ ] Docstrings for new functions
- [ ] No injection vulnerabilities
- [ ] External commands mocked in tests
