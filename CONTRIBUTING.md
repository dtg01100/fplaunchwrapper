# Contributing

## Development Setup

```bash
git clone https://github.com/dtg01100/fplaunchwrapper.git
cd fplaunchwrapper
./setup-dev.sh
```

## Testing

```bash
# Run all tests
./setup-dev.sh test

# Run Python tests
uv run pytest tests/python/ -v

# Run performance benchmarks
python3 test_performance_simple.py

# Run safety validation
python3 test_integration_safety.py
```

## Code Quality

```bash
# Format code
uv run black lib/ tests/python/

# Lint
uv run flake8 lib/ tests/python/

# Type checking
uv run mypy lib/
```

## Code Style

- PEP 8 compliant (Black formatting)
- Type hints for all function parameters
- Docstrings for modules, classes, and functions
- Descriptive variable names
- Comprehensive error handling
- Security-conscious coding (no injection vulnerabilities)

## Pull Request Process

1. Fork and create branch: `git checkout -b feature/name`
2. Make changes and test
3. Format code: `uv run black lib/ tests/python/`
4. Commit with conventional commits: `feat:`, `fix:`, `docs:`, etc.
5. Push and open PR

## Requirements

- Tests for new functionality
- Documentation updates if needed
- All tests pass
- Code formatted with Black
- Security review for user input handling

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
└── python_utils.py      # Utility functions
```

## Testing Guidelines

Write tests for:
- Unit tests for individual functions
- Integration tests for component interactions
- Security tests for input validation
- Edge cases for boundary conditions
- Performance tests for critical paths

Mock external commands (flatpak, systemctl, subprocess) to ensure zero side effects.

## Security Considerations

- Never execute user input as shell commands
- Validate all file paths before use
- Sanitize environment variables
- Use secure temporary files with proper permissions

## Issue Reporting

**Bug reports:**
- Python version: `python --version`
- Flatpak version: `flatpak --version`
- OS and version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

**Feature requests:**
- Use case description
- Current workaround (if any)
- Proposed solution

## License

By contributing, you agree that contributions are licensed under MIT License.
