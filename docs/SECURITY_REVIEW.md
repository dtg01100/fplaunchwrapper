Security Review for fplaunchwrapper

Scope
- Review covers repository code in lib/, packaging, CI, and runtime behavior (wrappers that call flatpak).

Findings
- No hardcoded secrets found in repo.
- Uses subprocess calls to `flatpak` — ensure inputs are sanitized and not shell-interpolated.
- CLI entry points accept user-supplied names; validate and sanitize wrapper names to avoid path traversal.
- Systemd unit generation writes to user config dir — ensure safe file permissions and atomic writes.
- Tests use a mock flatpak binary; CI must avoid running real flatpak as root.

Recommendations
- Run ruff/black and bandit in CI; add SAST (e.g., GitHub CodeQL) for PRs.
- Validate and sanitize all external inputs (flatpak IDs, filenames).
- Use subprocess.run with list args and avoid shell=True.
- Add unit tests covering malformed inputs and permission errors.
- Document secrets policy and add a pre-commit hook to block accidental commits of credentials.

Notes
- No third-party proprietary code detected; verify pinned dependency versions in pyproject.toml.
- Consider adding a security contact in SECURITY.md if desired.
