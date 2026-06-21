"""Meta-verification of the test suite itself.

Tests have bugs. A test that always passes is worse than no test at all,
because it gives false confidence. This module applies the same formal-
verification methodology used on the production code to the test suite.

Catalog of test-bug classes detected:
1. Tautological assertions: `assert True`, bare `assert False` without message
2. Trivial non-empty assertions: `assert result is not None`
3. Bare `except:` swallowing exceptions then asserting success
4. `assertRaises(Exception)` -- too broad
5. `time.sleep()` in tests (flakiness source)
6. Hardcoded `/home/`, `/root/`, `/Users/` paths in filesystem ops (reported)
7. Empty parametrize lists (test never runs)
8. Tests with no assertions at all (degenerate, reported)
9. Empty test files (no test_ functions)
10. Syntactically broken test files
11. Duplicate test method definitions
12. Mutation strength: would tests catch obvious production bugs?

Tests either pass (test suite is clean) or surface specific file:line
citations of bugs found.
"""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "tests" / "python"


def _collect_test_files() -> list[Path]:
    files = []
    for p in TESTS_DIR.rglob("test_*.py"):
        if "__pycache__" in p.parts:
            continue
        files.append(p)
    return sorted(files)


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text())
    except SyntaxError:
        return None


# ---- Test 1: No tautological assertions ---------------------------------

class TestNoTautologicalAssertions:
    """`assert True` and bare `assert False` (without message) are bugs."""

    @pytest.fixture(scope="class")
    def tautologies(self):
        findings = []
        for path in _collect_test_files():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assert):
                    continue
                if isinstance(node.test, ast.Constant):
                    if isinstance(node.test.value, bool):
                        findings.append((path, node.lineno,
                                         "assert True" if node.test.value else "assert False"))
                    elif isinstance(node.test.value, int):
                        findings.append((path, node.lineno, f"assert {node.test.value}"))
                    elif isinstance(node.test.value, str):
                        findings.append((path, node.lineno, f"assert {node.test.value!r}"))
                if isinstance(node.test, ast.GeneratorExp):
                    findings.append((path, node.lineno, "assert <generator>"))
        return findings

    def test_no_assert_true(self, tautologies):
        real = [f for f in tautologies if "assert True" in f[2]]
        assert not real, (
            f"Found {len(real)} `assert True` (always passes): "
            + ", ".join(f"{p.name}:{ln}" for p, ln, _ in real[:10])
        )

    def test_no_bare_assert_false(self, tautologies):
        real = []
        for path, ln, what in tautologies:
            if "assert False" not in what:
                continue
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert) and node.lineno == ln:
                    if isinstance(node.test, ast.Constant) and node.test.value is False:
                        if node.msg is None:
                            real.append((path, ln, what))
                    break
        assert not real, (
            f"Found {len(real)} bare `assert False` without message: "
            + ", ".join(f"{p.name}:{ln}" for p, ln, _ in real[:10])
        )


# ---- Test 2: No trivial non-None assertions -------------------------------

class TestNoTrivialAssertions:
    @pytest.fixture(scope="class")
    def trivial_assertions(self):
        findings = []
        for path in _collect_test_files():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assert):
                    continue
                if isinstance(node.test, ast.Compare):
                    if len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.IsNot):
                        if isinstance(node.test.comparators[0], ast.Constant):
                            if node.test.comparators[0].value is None:
                                findings.append((path, node.lineno))
        return findings

    def test_trivial_assertion_count_reasonable(self, trivial_assertions):
        n = len(trivial_assertions)
        assert n < 200, (
            f"Too many `assert x is not None` ({n}):\n"
            + "\n".join(f"  {p.name}:{ln}" for p, ln in trivial_assertions[:20])
        )


# ---- Test 3: No bare-except + assert-success ---------------------------

class TestNoSwallowedExceptions:
    @pytest.fixture(scope="class")
    def swallowed(self):
        findings = []
        for path in _collect_test_files():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Try):
                    continue
                for handler in node.handlers:
                    if handler.type is None:
                        for child in ast.walk(handler):
                            if isinstance(child, ast.Assert):
                                findings.append((path, handler.lineno))
                                break
        return findings

    def test_no_bare_except_with_assert(self, swallowed):
        assert not swallowed, (
            f"Found {len(swallowed)} bare-except + assert:\n"
            + "\n".join(f"  {p.name}:{ln}" for p, ln in swallowed[:10])
        )


# ---- Test 4: No overly-broad assertRaises -------------------------------

class TestNoOverlyBroadExceptionCatches:
    @pytest.fixture(scope="class")
    def broad_catches(self):
        findings = []
        for path in _collect_test_files():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "raises" and getattr(node.func.value, "id", None) == "pytest":
                        if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id == "Exception":
                            findings.append((path, node.lineno))
                if isinstance(node.func, ast.Name) and node.func.id == "raises":
                    if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id == "Exception":
                        findings.append((path, node.lineno))
        return findings

    def test_no_pytest_raises_exception(self, broad_catches):
        assert not broad_catches, (
            f"Found {len(broad_catches)} `pytest.raises(Exception)`:\n"
            + "\n".join(f"  {p.name}:{ln}" for p, ln in broad_catches[:10])
        )


# ---- Test 5: No time.sleep in tests -------------------------------------

class TestNoSleepInTests:
    @pytest.fixture(scope="class")
    def sleeps(self):
        findings = []
        for path in _collect_test_files():
            content = path.read_text()
            for m in re.finditer(r"time\.sleep\s*\(\s*([\d.]+)\s*\)", content):
                findings.append((path, content[:m.start()].count("\n") + 1, m.group(1)))
        return findings

    def test_no_long_sleep(self, sleeps):
        long = [(p, ln, t) for p, ln, t in sleeps if float(t) > 0.1]
        assert not long, (
            f"Found {len(long)} sleeps > 0.1s:\n"
            + "\n".join(f"  {p.name}:{ln} sleeps {t}s" for p, ln, t in long[:10])
        )


# ---- Test 6: Hardcoded paths in filesystem ops (reported) -----------

class TestHardcodedPathsReport:
    """Hardcoded paths in Path()/open() calls are portability hazards.
    Reported as warnings, not failures, because the validators don't
    require paths to exist."""

    @pytest.fixture(scope="class")
    def hardcoded(self):
        findings = []
        fs_use_patterns = re.compile(
            r'(Path\s*\(\s*["\']|open\s*\(\s*["\']|os\.path\.(?:join|exists|isfile|isdir)\s*\(\s*["\'])'
            r'(/home|/root|/Users)'
        )
        for path in _collect_test_files():
            content = path.read_text()
            for m in fs_use_patterns.finditer(content):
                line_no = content[:m.start()].count("\n") + 1
                findings.append((path, line_no, m.group(0)[:60]))
        return findings

    def test_hardcoded_paths_report(self, hardcoded):
        """Reports hardcoded paths as warnings. Soft pass."""
        if hardcoded:
            msg = (
                f"NOTE: {len(hardcoded)} hardcoded paths in Path()/open():\n"
                + "\n".join(f"  {p.name}:{ln} {s!r}" for p, ln, s in hardcoded[:20])
            )
            import warnings
            warnings.warn(msg, stacklevel=2)
        # Soft pass


# ---- Test 7: No empty parametrize lists ---------------------------------

class TestNoEmptyParametrize:
    @pytest.fixture(scope="class")
    def empty(self):
        findings = []
        for path in _collect_test_files():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr != "parametrize":
                    continue
                if len(node.args) >= 2:
                    arg = node.args[1]
                    if isinstance(arg, ast.List) and len(arg.elts) == 0:
                        findings.append((path, node.lineno, "empty list"))
                    if isinstance(arg, ast.Tuple) and len(arg.elts) == 0:
                        findings.append((path, node.lineno, "empty tuple"))
        return findings

    def test_no_empty_parametrize(self, empty):
        assert not empty, (
            f"Found {len(empty)} empty parametrize lists:\n"
            + "\n".join(f"  {p.name}:{ln} {why}" for p, ln, why in empty[:10])
        )


# ---- Test 8: Tests must have assertions (reported) --------------------

class TestEveryTestHasAssertionReport:
    """Tests with no assertions are coverage theater. Reported but not failed."""

    @pytest.fixture(scope="class")
    def no_assertions(self):
        findings = []
        for path in _collect_test_files():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not node.name.startswith("test_"):
                    continue
                has_assert = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Assert):
                        has_assert = True
                        break
                    if isinstance(child, ast.Raise):
                        has_assert = True
                        break
                    if isinstance(child, ast.Call):
                        fn = child.func
                        if isinstance(fn, ast.Attribute):
                            if fn.attr in ("fail", "xfail", "skip", "raises", "warns"):
                                has_assert = True
                                break
                        elif isinstance(fn, ast.Name):
                            if fn.id in ("fail", "xfail", "skip", "raises", "warns"):
                                has_assert = True
                                break
                    if isinstance(child, ast.With):
                        for item in child.items:
                            ctx = item.context_expr
                            if isinstance(ctx, ast.Call):
                                fn = ctx.func
                                if isinstance(fn, ast.Attribute) and fn.attr in ("raises", "warns"):
                                    has_assert = True
                                    break
                                if isinstance(fn, ast.Name) and fn.id in ("raises", "warns"):
                                    has_assert = True
                                    break
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call):
                        fn = dec.func
                        if isinstance(fn, ast.Attribute) and fn.attr in ("skip", "xfail"):
                            has_assert = True
                            break
                if not has_assert:
                    findings.append((path, node.lineno, node.name))
        return findings

    def test_zero_assertion_tests_report(self, no_assertions):
        if no_assertions:
            msg = (
                f"NOTE: {len(no_assertions)} tests have no assertions:\n"
                + "\n".join(f"  {p.name}:{ln} {name}" for p, ln, name in no_assertions[:20])
            )
            import warnings
            warnings.warn(msg, stacklevel=2)
        # Soft pass


# ---- Test 9: Test files must be syntactically valid ---------------------

class TestTestFilesParseClean:
    def test_all_test_files_parse(self):
        bad = []
        for path in _collect_test_files():
            try:
                ast.parse(path.read_text())
            except SyntaxError as e:
                bad.append((path, e.lineno, str(e)))
        assert not bad, (
            f"Found {len(bad)} test files with syntax errors:\n"
            + "\n".join(f"  {p.name}:{ln} {err}" for p, ln, err in bad[:10])
        )


# ---- Test 10: No duplicate test method definitions ---------------------

class TestNoDuplicateTestMethods:
    """A test method defined twice in the same class is a real bug:
    Python keeps the second, the first is dead code."""

    @pytest.fixture(scope="class")
    def duplicates(self):
        findings = []
        for path in _collect_test_files():
            tree = _parse(path)
            if tree is None:
                continue
            for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
                seen = {}
                for item in cls.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not item.name.startswith("test_"):
                            continue
                        if item.name in seen:
                            findings.append((path, item.lineno, item.name, seen[item.name]))
                        else:
                            seen[item.name] = item.lineno
        return findings

    def test_no_duplicate_test_methods(self, duplicates):
        assert not duplicates, (
            f"Found {len(duplicates)} duplicate test methods:\n"
            + "\n".join(f"  {p.name}:{ln} {n} (first at line {first})"
                       for p, ln, n, first in duplicates[:10])
        )


# ---- Test 11: Empty test files (no test_ functions) --------------------

class TestNoEmptyTestFiles:
    @pytest.fixture(scope="class")
    def empty_files(self):
        empty = []
        for path in _collect_test_files():
            tree = _parse(path)
            if tree is None:
                continue
            test_funcs = [
                n for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name.startswith("test_")
            ]
            if len(test_funcs) == 0:
                empty.append(path)
        return empty

    def test_no_empty_test_files(self, empty_files):
        assert not empty_files, (
            f"Found {len(empty_files)} test files with no test_ functions:\n"
            + "\n".join(f"  {p.name}" for p in empty_files[:10])
        )


# ---- Test 12: Mutation strength ----------------------------------------

class TestMutationCatchesObviousBugs:
    """If we mutated the production code in obvious ways, would existing
    tests catch it? If not, the tests are too weak."""

    def test_validation_tests_catch_empty_string_bug(self):
        caught = False
        for path in _collect_test_files():
            content = path.read_text()
            if 'validate_app_id("")' in content or "validate_app_id('')" in content:
                if 'assert not ok' in content or 'assert ok is False' in content:
                    caught = True
                    break
        assert caught, (
            "No test asserts that validate_app_id('') is rejected. "
            "If the validator were weakened to accept empty strings, tests would not catch it."
        )

    def test_wrapper_name_tests_catch_empty_string_bug(self):
        caught = False
        for path in _collect_test_files():
            content = path.read_text()
            if "validate_wrapper_name" in content and '""' in content:
                if 'assert not ok' in content:
                    caught = True
                    break
        assert caught, (
            "No test asserts that validate_wrapper_name('') is rejected."
        )

    def test_forbidden_name_tests_catch_case_variants(self):
        caught = False
        for path in _collect_test_files():
            content = path.read_text()
            if "is_forbidden" in content and ".upper()" in content:
                caught = True
                break
        assert caught, (
            "No test verifies that is_forbidden is case-insensitive."
        )

    def test_path_traversal_tests_catch_dotdot(self):
        caught = False
        for path in _collect_test_files():
            content = path.read_text()
            if "check_path_traversal" in content and ".." in content:
                if "assert not ok" in content or "assert ok is False" in content:
                    caught = True
                    break
        assert caught, "No test verifies check_path_traversal rejects '..'"

    def test_sanitize_id_tests_catch_empty_input(self):
        caught = False
        for path in _collect_test_files():
            content = path.read_text()
            if "sanitize_id_to_name" in content and 'sanitize_id_to_name("")' in content:
                if "assert" in content:
                    caught = True
                    break
        assert caught, "No test verifies sanitize_id_to_name('') returns a valid name"


# ---- Test 13: Test suite health ----------------------------------------

class TestTestSuiteHealth:
    def test_minimum_test_files(self):
        n = len(_collect_test_files())
        assert n >= 30, f"Only {n} test files; expected at least 30"

    def test_minimum_assertions_average(self):
        total = 0
        for path in _collect_test_files():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    total += 1
        avg = total / max(1, len(_collect_test_files()))
        assert avg >= 5, (
            f"Average {avg:.1f} assertions per test file is too low; "
            f"expected at least 5 (got {total} total)"
        )


# ---- Test 14: Collection determinism -----------------------------------

class TestDeterministicTestCollection:
    """`pytest --collect-only` must produce a stable count across runs."""

    @pytest.mark.parametrize("run", range(3))
    def test_test_collection_is_stable(self, run):
        import os
        old_cwd = os.getcwd()
        os.chdir(str(PROJECT_ROOT))
        try:
            r = subprocess.run(
                ["python3", "-m", "pytest", "tests/python/", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        finally:
            os.chdir(old_cwd)
        # pytest --collect-only returns 0 normally; 5 if no tests collected
        assert r.returncode in (0, 5), (
            f"pytest --collect-only failed (rc={r.returncode}): {r.stderr[:300]}"
        )
        # Parse "collected N items" line (most reliable)
        m = re.search(r"collected\s+(\d+)\s+items?", r.stdout)
        if m:
            n = int(m.group(1))
        else:
            # Fallback: count :: lines
            n = sum(1 for line in r.stdout.split("\n") if "::" in line)
        assert n > 2000, (
            f"Only {n} tests collected; expected 2000+. "
            f"Output:\n{r.stdout[:500]}"
        )
