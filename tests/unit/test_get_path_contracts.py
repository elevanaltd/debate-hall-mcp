"""Regression guard: ``debate_get`` exposes persisted ``path_contracts``
so the orchestrator's #199 ``<PATH_CONTRACTS>`` renderer sees them.

Per RFC-0001 §6 item 1, the orchestrator's ``_format_debate_state``
reads ``debate_state.get("path_contracts")`` and feeds the list to
``render_path_contracts_block``. ``debate_state`` is the dict returned
by :func:`debate_hall_mcp.tools.get.debate_get`. If ``debate_get`` does
not carry the field, the renderer silently emits nothing — a regression
that breaks #199's contract without producing any test failure on the
renderer-side tests (which inject the list directly).

This file pins the contract between the tool layer and the renderer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from debate_hall_mcp.path_contract import FrameRevision, new_path_contract
from debate_hall_mcp.state import DebateMode, DebateRoom, save_debate_state
from debate_hall_mcp.tools.get import debate_get


def _ts() -> datetime:
    return datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)


def test_debate_get_includes_path_contracts_when_present(tmp_path: Path) -> None:
    """A room with path_contracts surfaces them via debate_get()."""
    contract = new_path_contract("p1")
    contract["frame_history"].append(
        FrameRevision(
            rev=0,
            written_at=_ts(),
            written_by="Wind",
            value={
                "assumed_problem": "p",
                "success_criterion": "s",
                "accepted_failure_mode": "f",
                "invariants_touched": ["inv_a"],
            },
        )
    )
    room = DebateRoom(
        thread_id="2026-05-19-get-pc",
        topic="get exposes contracts",
        mode=DebateMode.FIXED,
        path_contracts=[contract],
    )
    state_dir = tmp_path / "debates"
    save_debate_state(room, state_dir)

    result = debate_get("2026-05-19-get-pc", state_dir=state_dir)
    assert "path_contracts" in result
    assert len(result["path_contracts"]) == 1
    assert result["path_contracts"][0]["path_id"] == "p1"
    # Renderer-relevant: latest_frame is reachable through the surfaced shape.
    assert len(result["path_contracts"][0]["frame_history"]) == 1


def test_debate_get_path_contracts_is_empty_list_when_absent(tmp_path: Path) -> None:
    """A room without path_contracts surfaces an empty list (not missing key).

    The renderer treats missing/empty identically (feature-off byte-identity),
    but the contract from the tool layer is to ALWAYS surface the key so
    downstream consumers (analytics, debugging) can rely on its presence.
    """
    room = DebateRoom(
        thread_id="2026-05-19-get-pc-empty",
        topic="empty contracts",
        mode=DebateMode.FIXED,
    )
    state_dir = tmp_path / "debates"
    save_debate_state(room, state_dir)

    result = debate_get("2026-05-19-get-pc-empty", state_dir=state_dir)
    assert result.get("path_contracts") == []
