#!/usr/bin/env python3
"""CLI dispatcher for ``lib.python_utils`` helpers.

Extracted from ``lib.python_utils.py`` so the utilities module can stay
a pure library. Invoked by ``lib/common.sh`` for the BATS test suite:

    python3 -m lib.python_utils_cli <op> [args...]

Each operation corresponds to one function in ``lib.python_utils``:

* ``canonicalize_path <path>``           -> ``canonicalize_path_no_resolve``
* ``validate_home <dir>``                -> ``validate_home_dir``
* ``sanitize_name <flatpak_id>``         -> ``sanitize_id_to_name``
* ``find_executable <cmd>``              -> ``find_executable``
* ``is_wrapper_file <path>``             -> ``is_wrapper_file``
* ``get_wrapper_id <path>``              -> ``get_wrapper_id``
* ``safe_mktemp <template> [dir]``       -> ``safe_mktemp``

Exit codes: 0 success, 1 failure / bad args. ``bool`` returns become
0/1; ``None`` becomes 1 with no output; other values print to stdout.
"""

from __future__ import annotations

import sys
from typing import Any, Callable

from . import python_utils


_DISPATCH: dict[str, tuple[Callable[..., Any], int, int]] = {
    # name            -> (callable, min_args, max_args)
    "canonicalize_path": (python_utils.canonicalize_path_no_resolve, 1, 1),
    "validate_home": (python_utils.validate_home_dir, 1, 1),
    "sanitize_name": (python_utils.sanitize_id_to_name, 1, 1),
    "find_executable": (python_utils.find_executable, 1, 1),
    "is_wrapper_file": (python_utils.is_wrapper_file, 1, 1),
    "get_wrapper_id": (python_utils.get_wrapper_id, 1, 1),
    "safe_mktemp": (python_utils.safe_mktemp, 1, 2),
}


def main(argv: list[str] | None = None) -> int:
    """Dispatch to the right helper. Returns 0 success / 1 failure.

    Hand-rolled argument parsing instead of argparse so we can return
    exit ``1`` (not ``2``) on bad args, matching the contract the
    hand-rolled dispatcher in ``lib.python_utils`` had for years.
    """
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        return 1
    operation = argv[0]
    if operation not in _DISPATCH:
        return 1
    fn, min_args, max_args = _DISPATCH[operation]
    extra = argv[1:]
    if len(extra) < min_args or len(extra) > max_args:
        return 1
    result = fn(*extra)
    if result is None:
        return 1
    if isinstance(result, bool):
        return 0 if result else 1
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
