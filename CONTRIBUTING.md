# Contributing to fplaunchwrapper

Thank you for your interest in contributing to fplaunchwrapper! This document provides guidelines and information for contributors.

## Ways to Contribute

- **Bug Reports**: Open an issue describing the bug, steps to reproduce, and your environment
- **Feature Requests**: Suggest new features or improvements via issues
- **Code Contributions**: Submit pull requests with bug fixes or new features
- **Documentation**: Improve README, examples, or add new documentation
- **Testing**: Test on different distributions and report results

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/fplaunchwrapper.git
   cd fplaunchwrapper
   ```
3. Install from source:
   ```bash
   bash install.sh
   ```

## Running Tests

Before submitting a pull request, ensure all tests pass:

```bash
cd tests
./run_all_tests.sh
```

Individual test suites can be run:
```bash
./test_wrapper_generation.sh
./test_management_functions.sh
```

## Code Style

- Follow existing shell script conventions
- Use shellcheck for linting: `shellcheck *.sh`
- Keep functions focused and well-documented
- Add comments for complex logic

## Pull Request Process

1. **Create a feature branch**: `git checkout -b feature/your-feature-name`
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
