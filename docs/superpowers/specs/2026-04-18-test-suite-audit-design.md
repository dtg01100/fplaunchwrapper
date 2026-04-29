## Summary

This design covers a targeted audit of the pytest suite with the primary goal of removing redundant and low-value tests while preserving or improving meaningful behavioral coverage.

The test pass will:

1. Keep tests that protect concrete product behavior or previously fixed bugs.
2. Tighten tests that currently exercise real commands but accept broken behavior.
3. Delete tests that mostly assert "does not crash", "returns a bool", or unrelated Python/runtime behavior rather than project behavior.
4. Refresh stale test documentation so it matches the real suite.

## Scope

The work is intentionally narrow:

- Audit the live repo test suite under `tests/python` and supporting test docs.
- Remove low-signal or duplicate tests when stronger coverage already exists.
- Add or rewrite only a small number of focused tests where deletion would otherwise create a real behavior gap.
- Verify the edited test suite with focused and broader pytest runs.

Out of scope:

- Broad production refactoring unrelated to making tests more meaningful.
- Suite-wide reorganization by domain or a full rewrite of the test architecture.
- Preserving approximate test counts for their own sake.
- Changes to shell/adversarial coverage unless they are directly needed to keep behavior protected after Python test cleanup.

## Design

### Test Classification

Each test file will be evaluated using a simple rule: what user-visible or developer-relevant behavior does this test protect, and is that behavior already protected better elsewhere?

Files and cases will be sorted into three buckets:

- Keep: focused regression, command-construction, configuration, or user-visible CLI behavior tests with specific assertions.
- Tighten: tests that hit a real behavior path but currently allow incorrect outcomes or use vague assertions.
- Delete: tests whose only signal is that code ran without crashing, returned a boolean, or performed generic filesystem/Python operations disconnected from product logic.

### Expected Cleanup Targets

The current suite already shows likely low-value concentration in broad files such as `tests/python/test_comprehensive.py`, `tests/python/test_focused.py`, and large parts of `tests/python/test_edge_cases_comprehensive.py`.

These files contain patterns that should generally be removed rather than preserved:

- `assert isinstance(result, bool)` without validating the actual outcome.
- Tests that treat known CLI bugs as acceptable behavior.
- Generic concurrency, unicode, or filesystem checks that do not assert a project-specific contract.
- Duplicate smoke coverage where a stronger targeted test already exists elsewhere.

By contrast, files like `tests/python/test_regression_fixes.py` are the model to keep: they encode a real bug, set up a focused scenario, and assert one concrete behavioral contract.

### Replacement Strategy

Deletion is the default when a test adds little signal and stronger coverage already exists. Replacement is only justified when removing a weak test would leave an important behavior unprotected.

Any replacement tests should be smaller and stricter than what they replace. They should assert one of the following:

- exact CLI exit behavior
- exact command construction
- exact file or config side effect
- exact user-visible output
- exact regression contract for a previously broken path

This keeps the suite smaller while improving the meaning of failures.

### Documentation

`tests/README.md` should be updated as part of this pass because it appears stale and overstates current guarantees and metrics. The revised document should describe the actual test categories and local execution paths without unverifiable claims.

## Testing

Verification should follow the same principle as the cleanup:

- run the edited test files directly while iterating
- run the broader `tests/python` suite before completion if feasible

The expected verification set is:

- `pytest tests/python/<edited files> -v`
- `pytest tests/python -v`

If a broader run reveals that a deleted test removed unique coverage, the fix is to add one focused behavioral test rather than restore a broad low-signal block.

## Risk Notes

The main risk is deleting a noisy test that incidentally covered an otherwise untested path. That risk is managed by checking remaining coverage by behavior, not by file count, and by running the affected and broader suites after changes.

This pass intentionally prefers fewer, sharper tests over a larger nominal test count. A smaller suite is acceptable if failures become more actionable and the important behaviors remain protected.
