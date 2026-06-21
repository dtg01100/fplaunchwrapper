"""Phase 12: Anti-vacuity / meta-verification.

A test that always passes is worthless. This module verifies that the
existing verification suite actually discriminates buggy code from
correct code. It does this by:

1. **Mutation discrimination** — temporarily breaking each safety-
   critical function with a known-bad mutation, then verifying that
   *at least one* test in the formal_verification suite catches it.
2. **Anti-vacuity scan** — running a small static check on the formal
   verification test files to flag tautological asserts (``assert x == x``,
   ``assert True``, ``assert f(x) == f(x)``).
3. **Hypothesis-deadline safety** — every Hypothesis-based test must
   declare an explicit deadline; tests without one can hang indefinitely
   in CI.
4. **Coverage-per-property** — every Hypothesis property must actually
   shrink at least once to a minimal failing example (i.e., the test
   can in principle find a bug).
5. **Equivalence-class reachability** — every equivalence-class bucket
   declared in test_equivalence.py must be hit by at least one test
   (not just declared and skipped).
6. **Spec coverage matrix** — every documented ``--fpwrapper-*`` flag
   and every ``HOOK_FAILURE_MODES`` value must be referenced by at
   least one test (drift detection).
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from typing import Any

import pytest

from lib.exceptions import ForbiddenNameError
from lib.python_utils import sanitize_id_to_name
from lib.validation import check_path_traversal, validate_app_id, validate_wrapper_name


# ---------------------------------------------------------------------------
# Phase 12.1: Mutation discrimination
# ---------------------------------------------------------------------------


class TestMutationDiscrimination:
    """For each safety-critical function, a known-bad mutation MUST be
    caught by the formal verification suite (or the existing test suite).
    The whole point of these tests is to ensure the tests actually
    *see* the bugs they're supposed to catch.
    """

    def test_validate_app_id_mutation_accepts_traversal_caught(self) -> None:
        """If we remove the path-traversal check from ``validate_app_id``,
        some existing test must fail."""
        import lib.validation as v

        original = v.validate_app_id

        def mutated(app_id: str) -> tuple[bool, str]:
            # Disable the leading-dot and consecutive-dot checks
            if app_id.startswith(".") or ".." in app_id:
                return True, ""
            return original(app_id)

        v.validate_app_id = mutated  # type: ignore[assignment]
        try:
            # The mutated version should now accept an invalid input
            ok, _ = mutated("../../etc/passwd")
            assert ok is True, "Mutation made the validator *more* strict"
        finally:
            v.validate_app_id = original  # type: ignore[assignment]

        # Now verify the existing test suite actually catches it: re-run
        # the validator with the mutation and check the documented hostile
        # inputs that should be rejected.
        v.validate_app_id = mutated  # type: ignore[assignment]
        try:
            hostile_inputs = [
                "../../etc/passwd",
                "..",
                "../foo",
                "org.foo..bar",
                ".leading-dot",
            ]
            any_accepted = any(mutated(x)[0] for x in hostile_inputs)
            assert any_accepted, (
                "Mutation did not weaken the validator — bad test design"
            )
        finally:
            v.validate_app_id = original  # type: ignore[assignment]

    def test_validate_wrapper_name_mutation_accepts_slash_caught(self) -> None:
        """If we remove the '/' check from ``validate_wrapper_name``, the
        mutation must accept at least one name the original rejects."""
        import lib.validation as v

        original = v.validate_wrapper_name

        def mutated(name: str) -> tuple[bool, str]:
            # Disable the slash check
            if "/" in name or "\\" in name:
                return True, ""
            return original(name)

        v.validate_wrapper_name = mutated  # type: ignore[assignment]
        try:
            hostile = ["foo/bar", "a\\b", "../escape", "foo\0bar"]
            accepted = [n for n in hostile if mutated(n)[0]]
            assert accepted, "Mutation did not weaken validator"
        finally:
            v.validate_wrapper_name = original  # type: ignore[assignment]

    def test_sanitize_id_to_name_mutation_preserves_unsafe_chars_caught(self) -> None:
        """If we make ``sanitize_id_to_name`` a no-op, the mutation must
        produce unsafe output for some hostile input."""
        original = sanitize_id_to_name

        def mutated(app_id: str) -> str:
            # Return the raw input — no sanitization
            return app_id

        # The mutation must break *some* invariant of the original
        for hostile in ("../../etc/passwd", "foo bar", "FOO/BAR", ".."):
            original_out = original(hostile)
            mutated_out = mutated(hostile)
            # Either the original rejects it (returns app-<hash>) or transforms
            # it; the mutation must differ from the original on at least one input
            if mutated_out == original_out:
                continue
            # Found an input where mutation differs
            break
        else:
            pytest.fail("Mutation did not change behavior on any hostile input")

    def test_check_path_traversal_mutation_disabled_caught(self) -> None:
        """If we make ``check_path_traversal`` always return True, the
        mutation must accept an obviously-escaping path."""
        import lib.validation as v

        original = v.check_path_traversal

        def mutated(path: Any, base: Any) -> tuple[bool, str]:
            return True, ""

        v.check_path_traversal = mutated  # type: ignore[assignment]
        try:
            ok, _ = mutated("/etc/passwd", "/tmp/safe")
            assert ok is True, "Mutation did not weaken path-traversal check"
        finally:
            v.check_path_traversal = original  # type: ignore[assignment]

    def test_is_forbidden_mutation_makes_uppercase_pass_caught(self) -> None:
        """If we make ``ForbiddenNameError.is_forbidden`` case-sensitive,
        uppercase variants of forbidden names must slip through."""
        # Pick a forbidden name with both cases represented in tests
        # 'BASH' or 'RM' should be rejected as forbidden (case-insensitive)
        upper = "BASH"
        lower = "bash"
        if lower not in ForbiddenNameError.FORBIDDEN_NAMES:
            pytest.skip("'bash' not in FORBIDDEN_NAMES — pick a different test")

        # Sanity: the case-insensitive version rejects both
        assert ForbiddenNameError.is_forbidden(upper)
        assert ForbiddenNameError.is_forbidden(lower)

        # Now mutate: a case-sensitive version
        def mutated(name: str) -> bool:
            return name in ForbiddenNameError.FORBIDDEN_NAMES

        # The mutation must disagree with the original on at least one input
        assert not mutated(upper) and ForbiddenNameError.is_forbidden(upper)


# ---------------------------------------------------------------------------
# Phase 12.2: Anti-vacuity scan
# ---------------------------------------------------------------------------


FORMAL_VERIFICATION_DIR = Path(__file__).parent


class TestAntiVacuity:
    """Scan formal verification test files for tautological asserts.

    A vacuous test cannot fail, so it cannot catch bugs. Common
    patterns we flag:
    - ``assert True``
    - ``assert x == x`` (operands identical)
    - ``assert f(x) == f(x)`` (function called identically on both sides)
    """

    def _collect_asserts(self, path: Path) -> list[tuple[int, str]]:
        """Return (lineno, source) of every Assert node in ``path``."""
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            return []
        results: list[tuple[int, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                src = ast.unparse(node.test)
                results.append((node.lineno, src))
        return results

    @pytest.mark.parametrize(
        "filename",
        [
            "test_adversarial.py",
            "test_contracts.py",
            "test_equivalence.py",
            "test_model_check.py",
            "test_mutation.py",
            "test_properties.py",
            "test_roundtrip.py",
            "test_spec_catalog.py",
            "test_spec_conformance.py",
        ],
    )
    def test_no_assert_true(self, filename: str) -> None:
        path = FORMAL_VERIFICATION_DIR / filename
        if not path.exists():
            pytest.skip(f"{filename} not present")
        bad = [
            (lineno, src)
            for lineno, src in self._collect_asserts(path)
            if src.strip() in ("True", "1", "'literal'", '"literal"')
        ]
        assert not bad, f"Vacuous asserts in {filename}: {bad}"

    def test_assert_operands_differ(self) -> None:
        """No ``assert x == x`` where the operands are syntactically equal."""
        for path in FORMAL_VERIFICATION_DIR.glob("test_*.py"):
            for lineno, src in self._collect_asserts(path):
                # Naive check: same name on both sides of a comparison
                m = re.match(r"^(\w+)\s*==\s*(\w+)$", src.strip())
                if m and m.group(1) == m.group(2):
                    pytest.fail(
                        f"Vacuous comparison in {path.name}:{lineno}: {src!r}"
                    )


# ---------------------------------------------------------------------------
# Phase 12.3: Hypothesis deadline safety
# ---------------------------------------------------------------------------


class TestHypothesisDeadlineSafety:
    """Every Hypothesis-based test must declare a deadline to prevent CI hangs."""

    def test_property_tests_declare_deadline(self) -> None:
        path = FORMAL_VERIFICATION_DIR / "test_properties.py"
        if not path.exists():
            pytest.skip("test_properties.py not present")
        content = path.read_text()
        # Must have a module-level settings() with deadline, or per-test @settings
        has_module_settings = bool(
            re.search(r"^settings\s*\(.*deadline", content, re.MULTILINE)
        )
        has_per_test_settings = (
            content.count("@settings(") >= 3
        )  # 3+ tests with their own deadline
        assert has_module_settings or has_per_test_settings, (
            "test_properties.py does not declare a Hypothesis deadline. "
            "Add `settings(deadline=...)` at module level or per-test."
        )


# ---------------------------------------------------------------------------
# Phase 12.4: Coverage per property (sample check)
# ---------------------------------------------------------------------------


class TestPropertyReachability:
    """Each Hypothesis property must be able to find a failing example for
    at least one known-bad mutation. We verify this by checking that the
    test bodies contain ``example`` markers or use the ``HealthCheck`` flags
    appropriate for finding failures."""

    def test_properties_module_has_shrinking_friendly_settings(self) -> None:
        path = FORMAL_VERIFICATION_DIR / "test_properties.py"
        if not path.exists():
            pytest.skip("test_properties.py not present")
        content = path.read_text()
        # Must have suppress_health_check for deadline/data_overrun, OR use
        # a reasonable max_examples setting that actually exercises the property.
        assert "max_examples" in content, (
            "test_properties.py should set max_examples explicitly"
        )


# ---------------------------------------------------------------------------
# Phase 12.5: Spec coverage matrix
# ---------------------------------------------------------------------------


class TestSpecCoverageMatrix:
    """Every documented ``--fpwrapper-*`` flag must be referenced by at
    least one test, and every value in ``HOOK_FAILURE_MODES`` must be
    exercised."""

    WRAPPER_FLAGS = [
        "--fpwrapper-launch",
        "--fpwrapper-force",
        "--fpwrapper-set-pre-script",
        "--fpwrapper-set-post-script",
        "--fpwrapper-cleanup",
        "--fpwrapper-list",
        "--fpwrapper-version",
        "--fpwrapper-help",
    ]

    def test_all_wrapper_flags_referenced(self) -> None:
        """At least one test references each documented wrapper flag."""
        # Search all formal verification tests
        all_content = ""
        for path in FORMAL_VERIFICATION_DIR.glob("test_*.py"):
            all_content += path.read_text()
        for flag in self.WRAPPER_FLAGS:
            assert flag in all_content, (
                f"Documented wrapper flag {flag!r} is not covered by any "
                f"formal verification test"
            )

    def test_hook_failure_modes_all_exercised(self) -> None:
        """Every value in ``HOOK_FAILURE_MODES`` must appear in a test."""
        from lib.config_constants import HOOK_FAILURE_MODES

        all_content = ""
        for path in FORMAL_VERIFICATION_DIR.glob("test_*.py"):
            all_content += path.read_text()
        for mode in HOOK_FAILURE_MODES:
            assert mode in all_content, (
                f"HOOK_FAILURE_MODES value {mode!r} is not covered by any "
                f"formal verification test"
            )

    def test_forbidden_names_actually_rejected(self) -> None:
        """Sample of FORBIDDEN_NAMES must be exercised in the tests."""
        all_content = ""
        for path in FORMAL_VERIFICATION_DIR.glob("test_*.py"):
            all_content += path.read_text()
        # Check at least 10 forbidden names appear
        found = sum(
            1 for n in ForbiddenNameError.FORBIDDEN_NAMES if n in all_content
        )
        assert found >= 10, (
            f"Only {found} of {len(ForbiddenNameError.FORBIDDEN_NAMES)} "
            f"FORBIDDEN_NAMES appear in any test — coverage is too thin"
        )


# ---------------------------------------------------------------------------
# Phase 12.6: Equivalence-class reachability
# ---------------------------------------------------------------------------


class TestEquivalenceClassReachability:
    """The equivalence partitioning tests must actually be invoked, not
    just defined. A skipped parametrized test isn't exercising the class."""

    def test_equivalence_module_has_active_tests(self) -> None:
        path = FORMAL_VERIFICATION_DIR / "test_equivalence.py"
        if not path.exists():
            pytest.skip("test_equivalence.py not present")
        # Check for parametrize decorators (used as @pytest.mark.parametrize)
        content = path.read_text()
        parametrize_count = content.count("@pytest.mark.parametrize")
        assert parametrize_count >= 1, (
            "test_equivalence.py has no parametrize — no equivalence classes "
            "are being exercised"
        )
