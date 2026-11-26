"""Per-signal-type outcome lift with intervals, minimum-sample rules and selection-bias handling.

Estimator: inverse-propensity weighted opportunity rate on rows a rep was asked to work (arms routed + explore),
weight = 1 / p_worked as logged at routing time. Explore rows (random sample of below-threshold signals routed anyway)
carry large weights so the below-threshold population is represented; without them every estimate is conditioned on the
old rules' own routing decision. Uncertainty uses the Kish effective sample size and a Newcombe-Wilson interval for the
difference of two proportions. Holdout rows (random 8 percent of qualifying rows withheld) give the incremental check.
"""
from __future__ import annotations

import math


def wilson(p: float, n: float, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 1.0
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - r) / d), min(1.0, (c + r) / d)


def newcombe(p1, n1, p2, n2, z=1.96) -> tuple[float, float, float]:
    l1, u1 = wilson(p1, n1, z)
    l2, u2 = wilson(p2, n2, z)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def wstats(rows, key=lambda r: r["y"], w=lambda r: 1.0 / r["p_worked"]):
    sw = sum(w(r) for r in rows)
    sw2 = sum(w(r) ** 2 for r in rows)
    if sw <= 0:
        return 0.0, 0.0
    return sum(w(r) * key(r) for r in rows) / sw, (sw * sw) / sw2


def eligible(rows):
    return [r for r in rows if not r["excluded_reason"]]


def per_signal(rows, signal_types, z=1.96, min_eff_n=60, weighted=True) -> list[dict]:
    """Rows: attributed rows. Returns one stats dict per signal type."""
    worked = [r for r in eligible(rows) if r["arm"] in ("routed", "explore")]
    w = (lambda r: 1.0 / r["p_worked"]) if weighted else (lambda r: 1.0)
    base, base_n = wstats(worked, w=w)
    out = []
    for s in signal_types:
        with_s = [r for r in worked if r["signals"].get(s, 0) > 0]
        wo = [r for r in worked if r["signals"].get(s, 0) <= 0]
        p1, n1 = wstats(with_s, w=w)
        p0, n0 = wstats(wo, w=w)
        d, lo, hi = newcombe(p1, n1, p0, n0, z)
        hold_w = [r for r in eligible(rows) if r["arm"] == "holdout" and r["signals"].get(s, 0) > 0]
        rout_w = [r for r in eligible(rows) if r["arm"] == "routed" and r["signals"].get(s, 0) > 0]
        inc = None
        if hold_w and rout_w:
            ph, nh = sum(r["y"] for r in hold_w) / len(hold_w), len(hold_w)
            pr, nr = sum(r["y"] for r in rout_w) / len(rout_w), len(rout_w)
            di, li, ui = newcombe(pr, nr, ph, nh, z)
            inc = {"routed_rate": round(pr, 4), "holdout_rate": round(ph, 4), "n_routed": nr, "n_holdout": nh, "diff": round(di, 4), "lo": round(li, 4), "hi": round(ui, 4)}
        out.append({"signal": s, "rate_with": round(p1, 4), "rate_without": round(p0, 4), "delta": round(d, 4), "lo": round(lo, 4), "hi": round(hi, 4),
                    "n_eff_with": round(n1, 1), "n_eff_without": round(n0, 1), "n_rows_with": len(with_s),
                    "sufficient": n1 >= min_eff_n and n0 >= min_eff_n, "incremental_vs_holdout": inc})
    return out


def band_check(rows, bands=((25, 40), (40, 60), (60, 101)), score_of=lambda r: r["score"]) -> list[dict]:
    """Routed vs holdout opportunity rate by score band: does acting on a band beat leaving it alone?"""
    res = []
    el = eligible(rows)
    for lo_s, hi_s in bands:
        r_ = [r for r in el if r["arm"] == "routed" and lo_s <= score_of(r) < hi_s]
        h_ = [r for r in el if r["arm"] == "holdout" and lo_s <= score_of(r) < hi_s]
        if not r_ or not h_:
            res.append({"band": f"{lo_s}-{hi_s}", "n_routed": len(r_), "n_holdout": len(h_), "verdict": "no_data"})
            continue
        pr, ph = sum(r["y"] for r in r_) / len(r_), sum(r["y"] for r in h_) / len(h_)
        d, lo, hi = newcombe(pr, len(r_), ph, len(h_))
        res.append({"band": f"{lo_s}-{hi_s}", "n_routed": len(r_), "n_holdout": len(h_), "routed_rate": round(pr, 3), "holdout_rate": round(ph, 3),
                    "diff": round(d, 3), "lo": round(lo, 3), "hi": round(hi, 3), "verdict": "routing_helps" if lo > 0 else ("unproven" if hi > 0 else "routing_hurts")})
    return res
