---
name: ci-post-commit
description: "Use after making commits: check CI status and automatically resolve errors"
applyTo: '**'
---

## CI Error Resolution After Commit

After every commit, monitor the associated CI pipeline status and automatically fix any reported errors.

### Workflow

1. **After commit**: Identify the CI pipeline associated with the commit (e.g., from GitHub Actions status check, git log, or remote)
2. **Wait for CI**: Allow sufficient time for CI to complete
3. **Check results**: Query CI status (e.g., `gh pr status`, `gh run list`, or fetch workflow logs)
4. **Fix errors**: If CI fails, analyze failures and push fixes automatically

### CI Integration

- **GitHub Actions**: Use `gh` CLI commands to check workflow status and fetch logs
- **GitLab CI**: Use `glab` CLI or API to check pipeline status
- **Other CIs**: Adapt to available CLI/API tools

### Auto-fix Scope

- Linting/formatting errors → fix and commit
- Test failures → analyze, fix tests or code, commit
- Type errors → fix and commit
- Security vulnerabilities → fix and commit
- Build failures → diagnose and fix, commit if straightforward

### Limits

If errors cannot be automatically fixed (require user decision, complex architectural changes, or external dependencies), report the findings and suggest manual resolution steps.

### Example Prompts

- "I just pushed commit abc123, check if CI passes"
- "Commit and fix any CI errors"
- "Push my changes and resolve any workflow failures"