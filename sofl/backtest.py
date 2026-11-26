"""Backtest rulesets on a held-out time split. Metrics are population-weighted: routed and holdout rows weigh 1,
explore rows weigh 1 / p_worked so the below-threshold population is represented."""
from __future__ import annotations

import random

from .rules import qualifies, score


def weights(rows):
    return [(1.0 / r["p_worked"]) if r["arm"] == "explore" else 1.0 for r in rows]


def wauc(scores, ys, ws) -> float:
    """Weighted AUC with mid-rank tie handling. Returns 0.5 if one class is empty."""
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    pos = sum(w for w, y in zip(ws, ys) if y)
    neg = sum(ws) - pos
    if pos <= 0 or neg <= 0:
        return 0.5
    acc, cum_neg, i = 0.0, 0.0, 0
    while i < len(order):
        j = i
        while j < len(order) and scores[order[j]] == scores[order[i]]:
            j += 1
        grp = order[i:j]
        gp = sum(ws[g] for g in grp if ys[g])
        gn = sum(ws[g] for g in grp if not ys[g])
        acc += gp * (cum_neg + gn / 2)
        cum_neg += gn
        i = j
    return acc / (pos * neg)


def capture(scores, ys, ws, top=0.30) -> float:
    """Share of weighted opportunities that sit in the top `top` of the weighted population by score."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    total_w, tot_pos = sum(ws), sum(w for w, y in zip(ws, ys) if y)
    if tot_pos <= 0:
        return 0.0
    got, cum = 0.0, 0.0
    for i in order:
        frac = min(ws[i], max(0.0, top * total_w - cum))
        if frac <= 0:
            break
        got += frac * ys[i]
        cum += frac
    return got / tot_pos


def evaluate(rows, rules, n_boot=300, seed=5, ref=None):
    """rows: eligible attributed rows. Returns metrics for `rules`; if `ref` rules given, adds paired AUC gain interval."""
    ws, ys = weights(rows), [r["y"] for r in rows]
    sc = [score(r["signals"], rules, r["icp"]) for r in rows]
    out = {"auc": round(wauc(sc, ys, ws), 4), "capture_top30": round(capture(sc, ys, ws), 4)}
    q = [qualifies(r["signals"], rules, r["icp"]) for r in rows]
    pw = sum(w for w, k in zip(ws, q) if k)
    out["route_precision"] = round(sum(w * y for w, y, k in zip(ws, ys, q) if k) / pw, 4) if pw else 0.0
    tp = sum(w for w, y in zip(ws, ys) if y)
    out["route_recall"] = round(sum(w * y for w, y, k in zip(ws, ys, q) if k) / tp, 4) if tp else 0.0
    out["routed_share"] = round(pw / sum(ws), 4)
    if ref is not None:
        rs = [score(r["signals"], ref, r["icp"]) for r in rows]
        rng, n, diffs = random.Random(seed), len(rows), []
        for _ in range(n_boot):
            idx = [rng.randrange(n) for _ in range(n)]
            a = wauc([sc[i] for i in idx], [ys[i] for i in idx], [ws[i] for i in idx])
            b = wauc([rs[i] for i in idx], [ys[i] for i in idx], [ws[i] for i in idx])
            diffs.append(a - b)
        diffs.sort()
        out["auc_gain_vs_ref"] = round(out["auc"] - wauc(rs, ys, ws), 4)
        out["auc_gain_ci95"] = [round(diffs[int(0.025 * n_boot)], 4), round(diffs[int(0.975 * n_boot) - 1], 4)]
    return out
