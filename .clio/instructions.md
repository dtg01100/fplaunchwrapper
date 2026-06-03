# CLIO Project Instructions

**Project Methodology:** The Unbroken Method for Human-AI Collaboration

## The Unbroken Method

This project follows **The Unbroken Method** for human-AI collaboration. This is the core operational framework.

**The Seven Pillars:**

1. **Continuous Context** - Never break the conversation. Maintain momentum through collaboration checkpoints.
2. **Complete Ownership** - If you find a bug, fix it. No "out of scope."
3. **Investigation First** - Read code before changing it. Never assume.
4. **Root Cause Focus** - Fix problems, not symptoms.
5. **Complete Deliverables** - No partial solutions. Finish what you start.
6. **Structured Handoffs** - Document everything for the next session.
7. **Learning from Failure** - Document mistakes to prevent repeats.

---

## Core Workflow

```
1. Read code first (investigation)
2. Use collaboration tool (get approval)
3. Make changes (implementation)
4. Test thoroughly (verify)
5. Commit with clear message (handoff)
```

---

## Session Handoff Procedures

**When ending a session, ALWAYS create handoff directory:**

```
ai-assisted/YYYYMMDD/HHMM/
├── CONTINUATION_PROMPT.md  [MANDATORY] - Next session's complete context
├── AGENT_PLAN.md           [MANDATORY] - Remaining priorities & blockers
└── NOTES.md                [OPTIONAL]  - Technical notes
```

**Format:**
- `YYYYMMDD` = Date (e.g., `20260203`)
- `HHMM` = Time in UTC (e.g., `0650` for 06:50)

### NEVER COMMIT Handoff Files

**Before every commit:**

```bash
# Verify no handoff files staged:
git status

# If ai-assisted/ appears:
git reset HEAD ai-assisted/

# Then commit only code/docs:
git add -A && git commit -m "type(scope): description"
```

**Why:** Handoff files contain internal session context and should NEVER be in public repository.

### CONTINUATION_PROMPT.md

**Purpose:** Complete standalone context for next session to start immediately.

**Required Sections:**

1. **What Was Accomplished** - Completed tasks, code changes, test results
2. **Current State** - Git activity, files modified, known issues
3. **What's Next** - Priority 1/2/3 tasks, dependencies, blockers
4. **Key Discoveries & Lessons** - What you learned, patterns identified
5. **Context for Next Developer** - Architecture notes, limitations
6. **Quick Reference: How to Resume** - Commands, files, starting points

**Principle:** This document must be so complete the next developer can START WORK immediately without investigation.

### AGENT_PLAN.md

**Purpose:** Quick reference for next session's task breakdown.

**Required Sections:**

1. **Work Prioritization Matrix** - Priority, Task, Estimated Time, Status, Blocker
2. **Task Breakdown** - Status, Effort, Dependencies, What to do, Files, Success criteria
3. **Testing Requirements** - What needs testing, how to verify, regression checks
4. **Known Blockers** - What's blocking, what's needed, workarounds

---

## Project-Specific Workflow Adjustments

This project is **fplaunchwrapper**, a Python CLI tool. A few methodology adjustments apply:

### Test-First is Mandatory

This project has a hermetic test culture. Before making any non-trivial change:

```bash
# Run the relevant existing tests first to establish baseline
python3 -m pytest tests/python/<relevant_test_file> -v
```

**Then make the change.**

**Then update or add tests** for new behavior. Never commit code without a test covering it (or an explicit justification in the commit body).

### Hermetic Tests Are Non-Negotiable

`tests/conftest.py` enforces hermeticity with autouse fixtures:

- `mock_flatpak_binary` (session-scoped) - replaces the real `flatpak` binary with a shell-script mock that logs calls
- `isolated_home` - rewrites `HOME`, `XDG_*_HOME`, and `FPLAUNCHWRAPPER_CONFIG` to a temp dir
- `cleanup_legacy_config` - removes any default config that leaked to real `~/.config`

**Rule:** Never modify these fixtures without confirming the new behavior. If a test needs different isolation, add a new fixture in the test file rather than touching `conftest.py`.

### Lint/Type/Test Gate Before Commit

Before every commit:

```bash
python3 -m pytest tests/python/ -q          # 1397+ tests
python3 -m ruff check lib/                  # 0 errors
python3 -m mypy lib/                        # 0 errors
python3 -m pylint lib/<changed_module>.py   # >= 9.5/10
```

If any of these fail, **fix them or revert**. Do not commit with a known failure even if the failure is "pre-existing."

### Conventional Commits

Commit messages use the format from `CONTRIBUTING.md`:

```
type(scope): brief description

[optional body explaining WHY]
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`.

For multi-area changes, prefer one focused commit per area (refactor, fix, test split into separate commits).

### Safety Boundaries

This is a security-aware project. Do not weaken these without explicit user approval:

- `safety.py` - input validation, path traversal, forbidden names, test environment detection
- `exceptions.py` - `ForbiddenNameError` with 159-entry `FORBIDDEN_NAMES` set
- `validation.py` - `validate_app_id`, `validate_wrapper_name`, `check_path_traversal`
- All wrapper generation must go through `generate.py` -> `lib/templates/wrapper.template.sh`
- `subprocess.run` always uses list args, never `shell=True`

If a task requires changing one of these, **call it out explicitly** at the checkpoint and get approval before proceeding.

---

*For universal agent behavior (checkpoints, tool-first, ownership, error recovery, etc.), see system prompt.*
*For technical reference (code style, testing, module structure, commands), see AGENTS.md.*
