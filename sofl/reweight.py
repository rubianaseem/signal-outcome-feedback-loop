"""Propose rules.v3 from per-signal lift. Deterministic, versioned, and conservative.

For each signal type with enough evidence (effective n on both sides >= min_effective_n):
  1. delta_s = IPW opportunity rate with the signal minus without it (marginal lift, with a Newcombe interval).
  2. The old weight implies a lift of w_s * k, where k converts weight units to rate units so that the evidence-set
     weights keep their total mass (the route threshold stays comparable). k = sum(max(delta_s, 0)) / sum(w_s).
  3. The weight changes only if the old implied lift lies OUTSIDE the `change_z` interval around delta_s. Otherwise: unchanged, "within noise".
  4. A changing weight moves `shrink` of the way to delta_s / k, is limited to +/- max_relative_step, and at most
     max_changes weights change per release (largest evidence-gap first).
Caps keep their old cap/weight ratio. Types without enough evidence are untouched and named in the change set.
"""
from __future__ import annotations

import copy

from .lift import newcombe
from .rules import diff_rules


def propose(rules_v2: dict, stats: list[dict], cfg: dict, new_version="rules.v3") -> tuple[dict, list[dict]]:
    rc = cfg["reweight"]
    ev = [s for s in stats if s["sufficient"] and rules_v2["signals"][s["signal"]]["weight"] > 0]
    tot_w = sum(rules_v2["signals"][s["signal"]]["weight"] for s in ev)
    k = (sum(max(s["delta"], 0.0) for s in ev) / tot_w) if tot_w else 0.0
    notes, cands = [], []
    for s in stats:
        t = s["signal"]
        w = rules_v2["signals"][t]["weight"]
        if not s["sufficient"]:
            notes.append({"signal": t, "decision": "insufficient_evidence", "n_eff_with": s["n_eff_with"], "n_eff_without": s["n_eff_without"]})
            continue
        if k <= 0:
            notes.append({"signal": t, "decision": "no_positive_lift_in_data"})
            continue
        implied = w * k
        _, lo_c, hi_c = newcombe(s["rate_with"], s["n_eff_with"], s["rate_without"], s["n_eff_without"], rc.get("change_z", rc["z"]))
        if lo_c <= implied <= hi_c:
            notes.append({"signal": t, "decision": "unchanged_within_noise", "delta": s["delta"], "old_implied_delta": round(implied, 4)})
            continue
        target = max(0.0, s["delta"]) / k
        new_w = w + rc["shrink"] * (target - w)
        lo_w, hi_w = w * (1 - rc["max_relative_step"]), w * (1 + rc["max_relative_step"])
        new_w = min(hi_w, max(lo_w, new_w))
        cands.append({"signal": t, "w": w, "new_w": new_w, "gap": abs(s["delta"] - implied), "delta": s["delta"], "implied": implied})
    cands.sort(key=lambda c: (-c["gap"], c["signal"]))
    rules = copy.deepcopy(rules_v2)
    rules["version"] = new_version
    for i, c in enumerate(cands):
        t = c["signal"]
        if i >= rc["max_changes"]:
            notes.append({"signal": t, "decision": "deferred_max_changes"})
            continue
        old = rules_v2["signals"][t]
        nw = max(1, round(c["new_w"])) if c["new_w"] > 0.5 else 0
        if nw == old["weight"]:
            notes.append({"signal": t, "decision": "unchanged_rounding"})
            continue
        ratio = old["cap"] / old["weight"] if old["weight"] else 1
        rules["signals"][t] = {"weight": nw, "cap": max(nw, round(nw * ratio))}
        notes.append({"signal": t, "decision": "reweight", "old_weight": old["weight"], "new_weight": nw, "delta": round(c["delta"], 4), "old_implied_delta": round(c["implied"], 4)})
    return rules, notes


def naive_raw_conversion(rules_v2: dict, naive_rows: list[dict], new_version="rules.naive") -> dict:
    """Baseline: weight proportional to raw conversion of routed rows that contain the signal. No exclusions, no
    holdout, no weighting, no interval, no minimum sample, every type replaced. Total weight mass preserved."""
    routed = [r for r in naive_rows if r["arm"] == "routed"]
    rate = {}
    for t in rules_v2["signals"]:
        sub = [r for r in routed if r["signals"].get(t, 0) > 0]
        rate[t] = sum(r["y"] for r in sub) / len(sub) if sub else 0.0
    tot_old = sum(s["weight"] for s in rules_v2["signals"].values())
    tot_rate = sum(rate.values()) or 1.0
    rules = copy.deepcopy(rules_v2)
    rules["version"] = new_version
    for t, s in rules_v2["signals"].items():
        nw = max(1, round(tot_old * rate[t] / tot_rate))
        ratio = s["cap"] / s["weight"]
        rules["signals"][t] = {"weight": nw, "cap": max(nw, round(nw * ratio))}
    return rules
