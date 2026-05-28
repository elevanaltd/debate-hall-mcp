"""Thread-id filesystem safety validation (cycle-break helper).

This module is a deliberate leaf in the dependency tree. It exists solely
to host ``_validate_thread_id_for_filesystem`` (and its companion constant
``PATH_UNSAFE_PATTERNS``) so both ``state.py`` and ``events.py`` can
import the helper without forming a cycle through one another.

Background (CRS #2 on PR #224 / RFC-0001 validator-wiring):
---------------------------------------------------------

Before this module existed, ``_validate_thread_id_for_filesystem`` lived
in ``state.py`` and ``events.py`` imported it from there. The path-
contract validator (``path_contract_validator``) needed to emit
``VALIDATOR_FAILURE`` events on rejection, which forced it to import
``events.append_event`` — and ``state.DebateRoom.append_diff_revision``
needed to invoke the validator, which would have closed a cycle:

    state → path_contract_validator → events → state

That cycle was previously broken with **lazy imports inside**
``append_diff_revision`` and a ``list[Any]`` annotation on
``PathContractValidationError.failures`` (the validator's
``ValidatorFailure`` type could not be referenced at module load). Both
were symptoms of the same root: ``state.py`` owned a helper that did not
belong to its concern (filesystem-safety pre-check on ``thread_id``).

The fix is structural: extract the helper into this dedicated module so
the dependency tree becomes:

    state → path_contract_validator → events → _thread_id
    state → _thread_id  (re-export for backward compatibility)

The cycle is broken at the root. The lazy imports in
``append_diff_revision`` and the ``list[Any]`` workaround on
``PathContractValidationError`` are both retired.

Compliance:

- PROD::I4 (VERIFIABLE_EVENT_LEDGER) — preserved; the audit emission
  path is now reachable from a stable import graph.
- SYS::I3 (ENFORCEMENT_PROTOCOLS) — structural breach (the cycle) is
  remediated by upgrading the dependency graph rather than guarding
  symptoms.

Note: ``state.py`` re-exports ``_validate_thread_id_for_filesystem`` (and
``PATH_UNSAFE_PATTERNS``) for backward compatibility with any existing
caller that imports the private name from ``state``.
"""

from __future__ import annotations

# Security: Patterns that indicate path traversal or directory separator
# injection in a ``thread_id``. Used by every code path that turns a
# ``thread_id`` into a filesystem name (state files, event files, lock
# files). The list is intentionally minimal — we reject any of these
# unconditionally rather than try to enumerate safe characters.
PATH_UNSAFE_PATTERNS: list[str] = ["..", "/", "\\"]


def _validate_thread_id_for_filesystem(thread_id: str) -> None:
    """Validate that ``thread_id`` is safe to embed in a filesystem path.

    Rejects path-traversal sequences and directory separators to prevent
    filesystem injection on every code path that builds a file name from
    a ``thread_id`` (state persistence, event log, lock file).

    Args:
        thread_id: Thread identifier supplied by an external caller.

    Raises:
        ValueError: If ``thread_id`` contains any path-unsafe character
            from :data:`PATH_UNSAFE_PATTERNS`.
    """
    for pattern in PATH_UNSAFE_PATTERNS:
        if pattern in thread_id:
            raise ValueError(f"Invalid thread_id '{thread_id}': contains path-unsafe characters")


__all__ = [
    "PATH_UNSAFE_PATTERNS",
    "_validate_thread_id_for_filesystem",
]
