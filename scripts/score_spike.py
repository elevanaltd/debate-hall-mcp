"""Score the 5 spike transcripts against the path_contract harness scorecard."""

import json
import re
from pathlib import Path

DEBATES_DIR = Path("/home/user/debate-hall-mcp/debates/spike-pathcontract")
INVARIANT_ENUM = {"halting", "single_wall_coherence", "re_approval", "per_turn_role_contract"}


def score(path: Path) -> dict:
    data = json.loads(path.read_text())
    name = path.stem.replace("2026-05-03-spike-", "").replace("2026-05-02-spike-", "")
    turns = data["turns"]

    # Wind frame check
    wind = turns[0]["content"] if len(turns) > 0 else ""
    n_frame_headings = len(re.findall(r"PATH_CONTRACT_FRAME\s*\(path_\d+\)", wind))
    n_frame_jsons = len(re.findall(r'"path_id"\s*:\s*"path_\d+"', wind))
    invariants_used = re.findall(r'"hard_invariants_touched"\s*:\s*\[([^\]]*)\]', wind)
    flat_invariants = set()
    for grp in invariants_used:
        for tok in re.findall(r'"([^"]+)"', grp):
            flat_invariants.add(tok)
    off_enum = flat_invariants - INVARIANT_ENUM

    # Wall verdict check
    wall = turns[1]["content"] if len(turns) > 1 else ""
    n_verdict_headings = len(re.findall(r"PATH_CONTRACT_VERDICT\s*\(path_\d+\)", wall))
    n_hard_pass = len(re.findall(r'"status"\s*:\s*"HARD_pass"', wall))
    n_hard_fail = len(re.findall(r'"status"\s*:\s*"HARD_fail"', wall))
    n_soft_disp = len(re.findall(r'"status"\s*:\s*"SOFT_disputed"', wall))
    bogus_status = re.findall(r'"status"\s*:\s*"([^"]+)"', wall)
    off_status = [s for s in bogus_status if s not in {"HARD_pass", "HARD_fail", "SOFT_disputed"}]

    # Find HARD_fail paths
    hard_fail_paths = set()
    # split wall content by path_id, find those containing HARD_fail
    blocks = re.findall(r'"path_id"\s*:\s*"(path_\d+)"[^{]*\{[^}]*"status"\s*:\s*"HARD_fail"', wall, re.DOTALL)
    hard_fail_paths.update(blocks)
    # also catch the looser pattern
    for m in re.finditer(r'"path_id"\s*:\s*"(path_\d+)"(.*?)(?="path_id"|\Z)', wall, re.DOTALL):
        if "HARD_fail" in m.group(2):
            hard_fail_paths.add(m.group(1))

    # Door citation check
    door = turns[2]["content"] if len(turns) > 2 else ""
    door_cites = re.findall(r"\[(path_\d+)\.(accepted|disputed|reframed)\b", door)
    door_cites_per_path = {}
    for p, cat in door_cites:
        door_cites_per_path.setdefault(p, set()).add(cat)
    n_door_cites = len(door_cites)
    door_categories_used = set(c for _, c in door_cites)

    # HARD_fail rule check per path
    hard_fail_satisfied = []
    hard_fail_missed = []
    for p in hard_fail_paths:
        cats = door_cites_per_path.get(p, set())
        if "accepted" in cats or "reframed" in cats:
            hard_fail_satisfied.append(p)
        else:
            hard_fail_missed.append(p)

    return {
        "name": name,
        "wind_frames": n_frame_headings,
        "wind_jsons": n_frame_jsons,
        "wind_invariants": sorted(flat_invariants),
        "wind_off_enum": sorted(off_enum),
        "wall_verdicts": n_verdict_headings,
        "wall_hard_pass": n_hard_pass,
        "wall_hard_fail": n_hard_fail,
        "wall_soft_disp": n_soft_disp,
        "wall_off_status": off_status,
        "hard_fail_paths": sorted(hard_fail_paths),
        "door_citations": n_door_cites,
        "door_categories": sorted(door_categories_used),
        "door_per_path": {p: sorted(cats) for p, cats in door_cites_per_path.items()},
        "hard_fail_rule_satisfied": sorted(hard_fail_satisfied),
        "hard_fail_rule_missed": sorted(hard_fail_missed),
    }


def verdict(s: dict) -> tuple[str, list[str]]:
    issues = []
    if s["wind_frames"] < 3:
        issues.append(f"Wind only emitted {s['wind_frames']}/3 frame headings")
    if s["wind_jsons"] < 3:
        issues.append(f"Wind only emitted {s['wind_jsons']}/3 frame JSON path_ids")
    if s["wind_off_enum"]:
        issues.append(f"Wind used off-enum invariants: {s['wind_off_enum']}")
    if s["wall_verdicts"] < 3:
        issues.append(f"Wall only emitted {s['wall_verdicts']}/3 verdict headings")
    if s["wall_off_status"]:
        issues.append(f"Wall used off-enum status: {s['wall_off_status']}")
    if s["wall_hard_pass"] + s["wall_hard_fail"] + s["wall_soft_disp"] == 0:
        issues.append("Wall emitted no recognized status values")
    if s["door_citations"] == 0:
        issues.append("Door emitted no [path_N.cat: invariant] citations")
    if s["hard_fail_rule_missed"]:
        issues.append(f"Door failed HARD_fail rule for paths: {s['hard_fail_rule_missed']}")
    return ("PASS" if not issues else "FAIL", issues)


print(f"{'='*72}\nSPIKE SCORECARD — RFC-0001 path_contract prompts\n{'='*72}\n")
results = []
for f in sorted(DEBATES_DIR.glob("*.json")):
    s = score(f)
    v, issues = verdict(s)
    results.append((s["name"], v, s, issues))

for name, v, s, issues in results:
    print(f"--- {name} : {v} ---")
    print(f"  Wind: {s['wind_frames']}/3 headings, {s['wind_jsons']}/3 JSON ids, invariants used={s['wind_invariants']}")
    if s["wind_off_enum"]:
        print(f"        OFF-ENUM invariants: {s['wind_off_enum']}")
    print(f"  Wall: {s['wall_verdicts']}/3 verdicts, HARD_pass={s['wall_hard_pass']}, HARD_fail={s['wall_hard_fail']}, SOFT_disputed={s['wall_soft_disp']}")
    if s["wall_off_status"]:
        print(f"        OFF-ENUM status: {s['wall_off_status']}")
    print(f"  Door: {s['door_citations']} citations across {s['door_categories']}")
    print(f"        per-path: {s['door_per_path']}")
    print(f"  HARD_fail paths: {s['hard_fail_paths']}")
    print(f"        Door honored rule for: {s['hard_fail_rule_satisfied']}")
    if s["hard_fail_rule_missed"]:
        print(f"        Door MISSED rule for: {s['hard_fail_rule_missed']}")
    if issues:
        for i in issues:
            print(f"  ! {i}")
    print()

n_pass = sum(1 for _, v, _, _ in results if v == "PASS")
n_total = len(results)
print(f"{'='*72}")
print(f"GATE: {n_pass}/{n_total} pass (need >=4/5 per RFC §11.1 / issue #204)")
print(f"VERDICT: {'GATE PASSED — proceed to build sub-issues' if n_pass >= 4 else 'GATE FAILED — iterate prompts'}")
print(f"{'='*72}")
