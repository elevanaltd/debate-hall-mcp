import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path.cwd() / "src"))

from debate_hall_mcp.tools.init import debate_init
from debate_hall_mcp.tools.turn import debate_turn
from debate_hall_mcp.tools.get import debate_get
from debate_hall_mcp.state import load_debate_state


def main():
    thread_id = "2026-01-08-persistence-test"
    state_dir = Path("debates_test")
    state_dir.mkdir(exist_ok=True)

    print(f"Initializing debate {thread_id} in OCTAVE mode...")
    debate_init(
        thread_id=thread_id,
        topic="Persistence of OCTAVE files",
        state_dir=state_dir,
        octave_mode=True,
    )

    # 2. Add some turns
    print("Adding turns...")
    print("  - Adding Wind...")
    debate_turn(thread_id, "Wind", "What if we stored everything in OCTAVE?", state_dir=state_dir)
    print("  - Adding Wall...")
    debate_turn(thread_id, "Wall", "Yes, but we must verify the hash chain.", state_dir=state_dir)
    print("  - Adding Door...")
    debate_turn(
        thread_id,
        "Door",
        "Therefore: We persist to .oct.md and reconstruct on load.",
        state_dir=state_dir,
    )

    # 3. Verify files on disk
    print("\n--- Files on Disk ---")
    octave_file = state_dir / f"{thread_id}.oct.md"
    json_file = state_dir / f"{thread_id}.json"

    if octave_file.exists():
        print(f"✅ Found {octave_file.name} ({octave_file.stat().st_size} bytes)")
        print("Content Preview:")
        print(octave_file.read_text()[:200] + "...")
    else:
        print(f"❌ Missing {octave_file.name}")

    if json_file.exists():
        print(f"⚠️ Found {json_file.name} (Should NOT exist in pure OCTAVE mode)")
    else:
        print(f"✅ Correctly missing {json_file.name}")

    # 4. Verify reload and hash chain
    print("\n--- Reload Verification ---")
    try:
        room = load_debate_state(thread_id, state_dir)
        print("✅ Reloaded successfully")
        print(f"Turns: {len(room.turns)}")
        print(f"Topic: {room.topic}")

        # Check hashes
        print("\n--- Hash Chain Check ---")
        for i, turn in enumerate(room.turns):
            print(f"Turn {i+1}: {turn.role}")
            print(f"  Hash: {turn.hash[:16]}...")
            print(f"  Prev: {turn.previous_hash[:16] if turn.previous_hash else 'None'}...")

            # Verify linkage
            if i > 0:
                prev = room.turns[i - 1]
                if turn.previous_hash == prev.hash:
                    print("  🔗 Link Valid")
                else:
                    print("  ❌ BROKEN LINK")
    except Exception as e:
        print(f"❌ Failed to reload: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
