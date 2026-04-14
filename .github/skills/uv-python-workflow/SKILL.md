---
name: uv-python-workflow
description: 'Workflow skill for using uv to perform Python development tasks in the fplaunchwrapper project. Use when installing, testing, formatting, linting, type-checking, or running project commands with uv.'
---

# uv Python Workflow

This skill guides the agent to use `uv` as the primary Python toolchain manager for all Python-related work in this repository.

## When to use

- You're working on `fplaunchwrapper` and need to run tests, format code, lint, or execute Python commands.
- You want to prefer the repository's documented `uv` workflow instead of raw `python3`/`pip` commands.
- You need a reproducible, workspace-local Python execution path for development tasks.

## Workflow

1. Confirm `uv` is available.
   - If missing, use the documented installer:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

2. Install the project toolchain via `uv` where appropriate.
   - Recommended for development:
     ```bash
     uv tool install fplaunchwrapper
     ```
   - If you need to refresh the installation:
     ```bash
     uv tool install --force fplaunchwrapper
     ```
   - If a specific Python version is required, use `uv` to install or select it:
     ```bash
     uv tool install python@3.11
     uv run python --version
     ```

3. Run Python tests with `uv run`.
   - Full suite:
     ```bash
     uv run pytest tests/python/ -v
     ```
   - Specific file or path:
     ```bash
     uv run pytest tests/python/test_example.py -v
     ```

4. Run formatting and linting with `uv run`.
   - Format code:
     ```bash
     uv run black lib/ tests/python/
     ```
   - Lint code:
     ```bash
     uv run flake8 lib/ tests/python/
     ```
   - Type-checking:
     ```bash
     uv run mypy lib/
     ```

5. Prefer `uv` whenever possible for all Python-related work.
   - If a README or CONTRIBUTING file shows `python3 -m pytest`, substitute `uv run pytest`.
   - If a task uses a local script or tool in the workspace, run it with `uv run python` or the installed uv tool.
   - If a dependency or CLI is needed, install it through `uv` rather than globally.

6. Keep the workflow hermetic.
   - Avoid using global `pip install` or system Python packages when `uv` can provide the environment.
   - Use `uv` to keep commands consistent across environments.

## Quality checks

- Use `uv run pytest` for test validation.
- Use `uv run black` before committing code.
- Use `uv run flake8` and `uv run mypy` when adding or changing Python logic.

## Example agent prompts

- "Use uv to run the fplaunchwrapper test suite and report any failures."
- "Format the changed Python files with uv and then run linting with uv run flake8."
- "Install the project via uv and run the targeted pytest file using uv."
