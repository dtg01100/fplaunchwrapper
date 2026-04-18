# fplaunchwrapper Test Suite

The primary automated test suite lives under `tests/python` and is run with `pytest`.

## What These Tests Cover

- Focused regression tests for previously fixed bugs
- CLI behavior tests using Click's `CliRunner`
- Wrapper generation and wrapper option behavior
- Configuration, profiles, presets, and manager operations
- Utility-level contracts in `lib.python_utils`

## What This Suite Does Not Guarantee

- Exact coverage percentages or benchmark numbers
- Zero real subprocess usage in every test file
- Full end-to-end validation of shell/adversarial test paths

## Running Tests

Run the full Python suite:

```bash
pytest tests/python -v
```

Run one file while iterating:

```bash
pytest tests/python/test_regression_fixes.py -v
```

Run a single test:

```bash
pytest tests/python/test_missing_cli_coverage.py::TestManifestCLI::test_manifest_failure_returns_error_exit_and_message -v
```

## Test Design Guidelines

- Prefer focused behavioral assertions over broad smoke tests.
- Do not keep tests that only prove code "did not crash".
- When fixing a bug, add or update a regression test that states the specific contract.
- Use `tmp_path`, fixtures, and mocking to isolate file-system and subprocess side effects where practical.
- Keep helper logic small inside the test file unless multiple files need the same fixture.
