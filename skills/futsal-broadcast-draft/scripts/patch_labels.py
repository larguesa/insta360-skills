"""Patch zone labels without re-analysis: hold lateral zone at confirmed goals; centre on dead-ball windows.

Reads a labels JSON (from label_zones.py), applies ranges from a patch JSON, writes labels_v2.json.

Patch JSON schema:
{
  "goals": [{"t": 316.0, "zone": 1, "hold_before": 3.0, "hold_after": 3.0}, ...],
  "centres": [[120.0, 167.5], ...]
}
Times are source-video seconds (same timeline as labels t0 + i*step).

python patch_labels.py --labels 1T_labels.json --patch 1T_patch.json --out 1T_labels_v2.json
"""
import argparse, json, shutil
from pathlib import Path

def idx(t0, st, t):
    return int(round((t - t0) / st))

def set_range(z, t0, st, t_a, t_b, zone):
    i0 = max(0, idx(t0, st, t_a)); i1 = min(len(z) - 1, idx(t0, st, t_b))
    for i in range(i0, i1 + 1):
        z[i] = zone
    return i0, i1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--patch", required=True, help="JSON with goals[] and centres[]")
    ap.add_argument("--out", required=True)
    ap.add_argument("--bak-suffix", default=".bak_pre_patch")
    a = ap.parse_args()
    L = json.load(open(a.labels, encoding="utf-8"))
    P = json.load(open(a.patch, encoding="utf-8"))
    shutil.copy(a.labels, a.labels + a.bak_suffix)
    z = list(L["zones"]); t0 = L["t0"]; st = L["step"]
    changes = []
    for pair in P.get("centres", []):
        ta, tb = pair[0], pair[1]
        i0, i1 = set_range(z, t0, st, ta, tb, 2)
        changes.append({"kind": "centre_dead", "src": [ta, tb], "idx": [i0, i1], "zone": 2})
    for g in P.get("goals", []):
        gsrc = float(g["t"]); side = int(g["zone"])
        hb = float(g.get("hold_before", 3.0)); ha = float(g.get("hold_after", 3.0))
        i0, i1 = set_range(z, t0, st, gsrc - hb, gsrc + ha, side)
        changes.append({"kind": "goal_hold", "goal_src": gsrc, "src": [gsrc - hb, gsrc + ha], "idx": [i0, i1], "zone": side})
    out = dict(L); out["zones"] = z; out["patch_changes"] = changes
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"))
    nchg = sum(1 for x, y in zip(L["zones"], z) if x != y)
    print(a.labels, "->", a.out, "labels_changed", nchg, "of", len(z))

if __name__ == "__main__":
    main()
