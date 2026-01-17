# Contributing to fplaunchwrapper

This Python utility welcomes contributions from developers.

## 🌟 Ways to Contribute

- **🐛 Bug Reports**: Open detailed issues with reproduction steps
- **💡 Feature Requests**: Suggest improvements and new functionality
- **🛠️ Code Contributions**: Submit pull requests with fixes and features
- **📚 Documentation**: Improve docs, add examples, write guides
- **🧪 Testing**: Test on different platforms and report results
- **🎨 Design**: Improve CLI UX and user experience
- **🌍 Localization**: Add support for new languages

## 🚀 Development Setup

### Quick Setup (Recommended)

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/fplaunchwrapper.git
cd fplaunchwrapper

# Set up complete development environment
./setup-dev.sh

# This installs:
# - uv package manager
# - Python dependencies
# - Development tools (pytest, black, flake8)
# - System dependencies (flatpak, shellcheck, bats)
```

### Manual Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -e ".[dev]"

# Install system tools
brew install flatpak shellcheck bats-core  # macOS
# OR
sudo apt install flatpak dialog shellcheck bats  # Linux
```

## 🧪 Testing

### Run Full Test Suite

```bash
# Run comprehensive test suite (recommended)
./setup-dev.sh test

# Run performance benchmarks
python3 test_performance_simple.py

# Run safety validation
python3 test_integration_safety.py

# Run Python unit tests manually
python3 -c "
from tests.python.test_safe_constructor import TestSafeConstructorValidation
from tests.python.test_edge_cases_focused import TestInputValidationEdgeCases

test_constructor = TestSafeConstructorValidation()
test_constructor.test_wrapper_generator_constructor()
test_constructor.test_wrapper_manager_constructor()

test_edges = TestInputValidationEdgeCases()
test_edges.test_empty_and_none_inputs()
print('✅ Tests completed successfully')
"
```

### Test Categories

#### Performance Testing
```bash
# Benchmark core operations
python3 test_performance_simple.py

# Expected output: <2ms operations
# Wrapper Generation: 1.1ms ±0.6ms (FAST)
# Manager Operations: 2.4ms ±0.3ms (FAST)
```

#### Safety Validation
```bash
# Verify zero side effects
python3 test_integration_safety.py

# Expected: All safety checks pass
```

#### Edge Case Testing
```bash
# Test input validation and boundaries
python3 -c "
from tests.python.test_edge_cases_focused import TestInputValidationEdgeCases
test = TestInputValidationEdgeCases()
test.test_empty_and_none_inputs()
test.test_extremely_long_inputs()
print('✅ Edge case tests passed')
"
```

### Manual Testing

```bash
# Test CLI functionality (requires installation)
pip install -e .
fplaunch generate ~/test-wrappers
fplaunch list
fplaunch set-pref firefox flatpak

# Test wrapper functionality
~/test-wrappers/firefox --fpwrapper-help

# Verify zero side effects
ls -la ~/test-wrappers/  # Should only contain generated files
```

## 💻 Code Style & Quality

### Python Code

```bash
# Format code
uv run black lib/ tests/python/

# Lint code
uv run flake8 lib/ tests/python/

# Type checking
uv run mypy lib/

# Security scanning
uv run bandit lib/
```

### Standards

- **PEP 8** compliant with Black formatting
- **Type hints** for all function parameters
- **Docstrings** for all modules, classes, and functions
- **Descriptive variable names** and clear logic
- **Comprehensive error handling** with meaningful messages
- **Security-conscious coding** (no injection vulnerabilities)

### Example Code Structure

```python
from typing import Optional, List
import os

def generate_wrapper(app_id: str, bin_dir: str) -> bool:
    """
    Generate a wrapper script for a Flatpak application.

    Args:
        app_id: Flatpak application ID (e.g., 'org.mozilla.firefox')
        bin_dir: Directory to place the wrapper script

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If app_id is invalid
        PermissionError: If bin_dir is not writable
    """
    if not app_id or not bin_dir:
        raise ValueError("app_id and bin_dir are required")

    # Implementation here...
    return True
```

## 🔄 Pull Request Process

### 1. Choose the Right Branch
- **Bug fixes**: `git checkout -b fix/issue-description`
- **Features**: `git checkout -b feature/feature-name`
- **Documentation**: `git checkout -b docs/improvement`
- **Refactoring**: `git checkout -b refactor/component-name`

### 2. Development Workflow

```bash
# Create and switch to feature branch
git checkout -b feature/amazing-feature

# Make your changes
# ... code ...

# Run tests
./setup-dev.sh test

# Format code
uv run black lib/ tests/python/

# Commit changes
git add .
git commit -m "feat: add amazing feature

- What this change does
- Why it's needed
- Any breaking changes"

# Push branch
git push origin feature/amazing-feature
```

### 3. Pull Request Requirements

**✅ Must Include:**
- [ ] **Tests** for new functionality
- [ ] **Documentation** updates if needed
- [ ] **Code formatting** (Black)
- [ ] **Type hints** for new functions
- [ ] **Security review** for user input handling

**✅ Must Pass:**
- [ ] All Python tests: `pytest tests/python/`
- [ ] Security verification: `./test_security_fixes.sh`
- [ ] Code formatting: `black --check lib/ tests/python/`
- [ ] Linting: `flake8 lib/ tests/python/`
- [ ] Type checking: `mypy lib/`

### 4. Pull Request Template

**Title:** `feat/fix/docs/refactor: brief description`

**Description:**
```markdown
## What
Brief description of the change

## Why
Why this change is needed

## How
Technical details of the implementation

## Testing
How this was tested

## Breaking Changes
Any breaking changes (if applicable)
```

## 🐛 Issue Reporting

### Bug Reports
**Include:**
- Python version: `python --version`
- uv version: `uv --version`
- Flatpak version: `flatpak --version`
- Operating system and version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

### Feature Requests
**Include:**
- Use case description
- Current workaround (if any)
- Proposed solution
- Alternative approaches considered

## 📋 Development Guidelines

### Code Organization

```
lib/
├── fplaunch.py          # Main entry point
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

### Naming Conventions

- **Modules**: `snake_case.py`
- **Functions**: `snake_case()`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Variables**: `snake_case`

### Error Handling

```python
# Good: Specific exceptions with context
def validate_app_id(app_id: str) -> bool:
    if not app_id:
        raise ValueError("app_id cannot be empty")

    if not re.match(r'^[a-zA-Z0-9._-]+$', app_id):
        raise ValueError(f"Invalid app_id format: {app_id}")

    return True

# Bad: Generic exceptions
def bad_validate(app_id):
    if not app_id:
        raise Exception("Error")  # Too generic
```

### Security Considerations

- **Never execute user input** as shell commands
- **Validate all file paths** before use
- **Sanitize environment variables** in scripts
- **Use secure temporary files** with proper permissions
- **Log security events** appropriately

### Performance Guidelines

- **Minimize subprocess calls** - use Python libraries when possible
- **Cache expensive operations** - Flatpak discovery, file reads
- **Use efficient data structures** - dicts for lookups, sets for uniqueness
- **Profile performance-critical code** - use `time` module for measurements
- **Lazy loading** for optional dependencies

## 🧪 Testing Guidelines

### Test Structure

```python
# tests/python/test_feature.py
import pytest
from lib.feature import FeatureClass

class TestFeature:
    def test_basic_functionality(self):
        """Test basic feature operation"""
        feature = FeatureClass()
        result = feature.do_something()
        assert result == expected_value

    def test_error_conditions(self):
        """Test error handling"""
        with pytest.raises(ValueError):
            FeatureClass().do_something_invalid()

    def test_edge_cases(self):
        """Test boundary conditions"""
        # Test empty inputs, large inputs, special characters, etc.
        pass
```

### Test Categories

- **Unit Tests**: Test individual functions/classes
- **Integration Tests**: Test component interactions
- **Security Tests**: Verify input validation and injection prevention
- **Performance Tests**: Ensure efficient execution
- **Regression Tests**: Prevent reintroduction of fixed bugs

### Mocking Best Practices

```python
import pytest
from unittest.mock import Mock, patch

def test_with_mocking():
    """Test with proper mocking"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "success"

        # Test your function
        result = my_function()
        assert result == "success"

        # Verify correct subprocess call
        mock_run.assert_called_once_with(['command'], capture_output=True)
```

## 📚 Documentation

### Code Documentation

```python
def generate_wrapper(app_id: str, bin_dir: str) -> bool:
    """
    Generate a wrapper script for a Flatpak application.

    This function creates an intelligent wrapper script that can choose
    between system packages and Flatpak applications based on user
    preferences and availability.

    Args:
        app_id: Flatpak application ID (e.g., 'org.mozilla.firefox')
        bin_dir: Directory to place the wrapper script

    Returns:
        True if wrapper was generated successfully

    Raises:
        ValueError: If app_id is invalid or bin_dir doesn't exist
        PermissionError: If bin_dir is not writable

    Example:
        >>> generate_wrapper('org.mozilla.firefox', '/home/user/bin')
        True
    """
    # Implementation...
```

### README Updates

When adding new features, update:
- **README.md**: Installation and usage examples
- **QUICKSTART.md**: Quick start guide
- **docs/**: Detailed documentation
- **examples/**: Usage examples

## 🎯 Commit Message Guidelines

### Format
```
type(scope): brief description

Detailed description of changes if needed

- Bullet points for changes
- Reference issue numbers
- Breaking changes noted
```

### Types
- **feat**: New features
- **fix**: Bug fixes
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Test additions/modifications
- **chore**: Maintenance tasks

### Examples
```
feat: add systemd monitoring support

- Add real-time Flatpak app monitoring
- Auto-regenerate wrappers on app install/remove
- Support both systemd and cron fallbacks

Closes #123
```

```
fix: prevent command injection in wrapper scripts

- Sanitize app IDs before script generation
- Add input validation for all user inputs
- Implement secure temporary file creation

Security fix for CVE-2024-XXXX
```

## 🌍 Community & Communication

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Code Reviews**: All PRs require review before merge
- **CI/CD**: Automated testing and quality checks
- **Releases**: Semantic versioning with changelogs

## 🙏 Recognition

Contributors are recognized in:
- **GitHub contributor statistics**
- **CHANGELOG.md** for significant contributions
- **README.md** acknowledgments section

Thank you for contributing to fplaunchwrapper! 🚀
2. **Make your changes**: Follow code style guidelines
3. **Test thoroughly**: Run the test suite and test manually
4. **Commit with clear messages**: Describe what and why
5. **Push to your fork**: `git push origin feature/your-feature-name`
6. **Open a pull request**: Describe your changes and link related issues

## Commit Message Format

Use clear, descriptive commit messages:

```
type: Brief description (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Explain the problem this commit solves and why this approach
was chosen.

Fixes #123
```

Types:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Adding or updating tests
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

## Adding New Features

When adding new features:

1. **Discuss first**: Open an issue to discuss major changes
2. **Update documentation**: README, help text, examples
3. **Add tests**: Include test coverage for new functionality
4. **Update completion**: Add to `fplaunch_completion.bash` if applicable
5. **Consider packaging**: Update packaging files if needed

## Testing on Different Distributions

We aim to support major Linux distributions:

- **Debian/Ubuntu**: Test with apt
- **Fedora/RHEL**: Test with dnf/rpm
- **Arch Linux**: Test with pacman
- **openSUSE**: Test with zypper

Report compatibility issues or successes!

## Code Review

All submissions require review. We will:

- Check code quality and style
- Verify tests pass
- Ensure documentation is updated
- Test functionality when possible

## Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Documentation improvements
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention needed

## Questions?

Open an issue or discussion if you have questions about:
- How to implement something
- Project architecture
- Best practices
- Anything else!

## Code of Conduct

Be respectful and constructive in all interactions. We want this to be a welcoming community for everyone.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to fplaunchwrapper! 🚀
