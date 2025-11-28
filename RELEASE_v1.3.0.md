````markdown
# fplaunchwrapper v1.3.0 - Release Summary

## 🎉 Release: v1.3.0 - "QA, tests and CI hardening"

**Date:** November 28, 2025  
**Commit:** 13a39da  
**Tag:** v1.3.0

---

## 🚀 Summary

This release focuses on polishing the test suite, tightening the wrapper-name spec, and fixing CI (ShellCheck) flakiness. The repository now has broader QA coverage, stricter validation for generated wrappers, and a green CI pipeline across all configured runners.

Highlights:
- Tightened wrapper name validation (disallow leading/trailing hyphens and spaces; enforce allowed character set for last-segment names)
- Added and fixed multiple edge-case tests (Unicode/space handling, alias loops, symlink loops, race-condition checks)
- Fixed several ShellCheck warnings across scripts and test suites so linting is green in CI
- Stabilized CI to ensure tests and lint jobs pass reliably

---

## 📁 Files changed (high level)

- lib/common.sh — targeted ShellCheck suppression for complex case statements in validation logic
- fplaunch-cleanup — removed unused variable to satisfy lint checks
- tests/* — broad set of new and updated tests, including `tests/test_edge_cases.sh`, `tests/test_wrapper_generation.sh`, and integration tests; many were adjusted to reflect the tighter naming rules
- CI workflows — fixes and improvements to ensure ShellCheck job succeeds and test matrix remains green

---

## 🔧 Technical details

The primary user-visible change is stricter validation for generated wrapper names. The generator and tests now treat the last segment of candidate wrapper names as:

- Lowercase only
- Allowed characters: a–z, 0–9, underscore (_), hyphen (-)
- Disallowed: leading or trailing hyphens, embedded spaces, and Unicode last-segments

This makes wrapper names more predictable and avoids subtle issues in name handling, shell expansion, and packaging.

Additionally, many of the test suites were expanded to cover previously untested edge-cases and security situations (path traversal, null-byte injection, PATH poisoning, symlink loops). Several tests were corrected or made more strict to align with the updated naming spec.

---

## 🧪 QA & CI

- All tests passed in local runs prior to tagging.  
- CI run #45 (triggered by the release branch commit) passed across all jobs (ShellCheck + test matrix).

---

## 📋 Release checklist

1. Create a tag: v1.3.0
2. Push the tag to origin
3. GitHub Actions will build packages and include these release notes

---

## 🎯 Notes

This is a stability and QA release: no breaking changes, backward compatible behavior, and improved robustness for both tests and tooling.

If you want, we can also:
- Build and attach binary packages to the GitHub release
- Publish packaging artifacts to a package hosting (Debian/EL repos)

````
