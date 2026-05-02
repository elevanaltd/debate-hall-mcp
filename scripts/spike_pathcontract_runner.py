"""RFC-0001 spike runner — runs the 5 historical-topic debates with the
new path_contract prompts, using the local `claude` CLI provider.

Output: per-debate transcripts under debates/spike-pathcontract/ via the
orchestrator's existing state persistence. Stdout summarises pass/fail
per topic for the #204 gate scoring.
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime, UTC
from pathlib import Path

# Force tier config + state dir for the spike
os.environ["DEBATE_HALL_TIERS_FILE"] = str(Path(__file__).resolve().parent.parent / "tiers.yaml")
SPIKE_STATE_DIR = Path(__file__).resolve().parent.parent / "debates" / "spike-pathcontract"
SPIKE_STATE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["DEBATE_HALL_STATE_DIR"] = str(SPIKE_STATE_DIR)

from debate_hall_mcp.config import load_tier_config  # noqa: E402
from debate_hall_mcp.orchestrator import DebateOrchestrator  # noqa: E402

TOPICS = [
    (
        "rundebate-reliability",
        "How can we make run_debate more reliable and testable? "
        "Consider: provider timeouts, error handling, testing strategies, "
        "and alternative configurations.",
    ),
    (
        "virtualprovider-vs-timebudget",
        "For debate-hall-mcp: Should we implement VirtualProvider or "
        "time-budgeting as NEXT priority?",
    ),
    (
        "cognitive-notary-arch",
        "What is the optimal architecture for debate-hall-mcp going forward?",
    ),
    (
        "decision-governance-tiers",
        "Should every ratified decision in elevana-studio originate from a "
        "GitHub Issue per HestAI-MCP ADR-0060 (ADR↔Issue alignment, every ADR "
        "must have a linked Issue, numbers match), or do we need a tiered "
        "model that distinguishes heavyweight architectural decisions from "
        "lightweight documented choices?",
    ),
    (
        "mythology-in-octave",
        "How should OCTAVE lean into mythological vocabulary? Permission vs "
        "formalization — the Mythological Compression Principle",
    ),
]


async def run_one(slug: str, topic: str, tier_config) -> dict:
    """Run a single debate, return a result summary."""
    started = datetime.now(UTC)
    print(f"\n{'='*72}\n[{started.isoformat()}] STARTING: {slug}\n  Topic: {topic[:80]}{'...' if len(topic) > 80 else ''}\n{'='*72}", flush=True)

    orchestrator = DebateOrchestrator(tier_config=tier_config, state_dir=SPIKE_STATE_DIR)
    today = started.strftime("%Y-%m-%d")
    thread_id = f"{today}-spike-{slug}"

    try:
        result = await orchestrator.run(topic=topic, thread_id=thread_id)
        ended = datetime.now(UTC)
        elapsed = (ended - started).total_seconds()
        print(f"\n[{ended.isoformat()}] FINISHED: {slug}\n  status={result.status} turns={result.turn_count} elapsed={elapsed:.1f}s", flush=True)
        return {
            "slug": slug,
            "thread_id": thread_id,
            "status": result.status,
            "turns": result.turn_count,
            "elapsed_s": elapsed,
            "synthesis_preview": result.synthesis[:200] if result.synthesis else None,
            "error": None,
        }
    except Exception as e:
        ended = datetime.now(UTC)
        elapsed = (ended - started).total_seconds()
        tb = traceback.format_exc()
        print(f"\n[{ended.isoformat()}] FAILED: {slug}\n  elapsed={elapsed:.1f}s\n  error={e!r}\n{tb}", flush=True)
        return {
            "slug": slug,
            "thread_id": thread_id,
            "status": "error",
            "turns": None,
            "elapsed_s": elapsed,
            "synthesis_preview": None,
            "error": f"{type(e).__name__}: {e}",
        }


async def main() -> int:
    tier_config = load_tier_config("spike")
    print(f"Loaded tier config: wind={tier_config.wind.cli}/{tier_config.wind.model} "
          f"wall={tier_config.wall.cli}/{tier_config.wall.model} "
          f"door={tier_config.door.cli}/{tier_config.door.model}", flush=True)
    print(f"State dir: {SPIKE_STATE_DIR}", flush=True)
    print(f"Topics: {len(TOPICS)}", flush=True)

    results = []
    for slug, topic in TOPICS:
        results.append(await run_one(slug, topic, tier_config))

    # Summary
    print("\n" + "="*72)
    print("SPIKE COMPLETE — summary")
    print("="*72)
    for r in results:
        status_marker = "OK" if r["status"] in ("synthesis", "stalemate") else "ERR"
        print(f"  [{status_marker}] {r['slug']:<35} status={r['status']:<10} turns={r['turns']} elapsed={r['elapsed_s']:.1f}s")
        if r["error"]:
            print(f"        error: {r['error']}")
    print(f"\n  successes: {sum(1 for r in results if r['status'] in ('synthesis', 'stalemate'))} / {len(results)}")
    print(f"  state dir: {SPIKE_STATE_DIR}\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
