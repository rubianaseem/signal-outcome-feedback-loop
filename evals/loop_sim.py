"""Selection-bias simulation: does a closed loop that only learns from what it routed drift, and does the explore arm help?

Each round: generate 8 weeks under the CURRENT rules, re-weight, repeat 3 times. Two loops share the same worlds:
  naive  - raw conversion re-weight, learns only from rows the rules routed (no explore, no holdout, no weights, no exclusions)
  sofl   - this repo's attribution exclusions + IPW lift + explore arm + conservative proposal (no human gate in the simulation)
Scored each round on a fresh unbiased population (no routing) with a known truth. SYNTHETIC and author-written.
"""
from __future__ import annotations

import copy
import statistics

from evals.world import TRUE_BETA, generate, make_accounts, population
from sofl.backtest import wauc
from sofl.lift import per_signal
from sofl.pipeline import load_config
from sofl.reweight import naive_raw_conversion, propose
from sofl.rules import load_rules, score


def spearman(a, b):
    def ranks(x):
        order = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        i = 0
        while i < len(order):
            j = i
            while j < len(order) and x[order[j]] == x[order[i]]:
                j += 1
            for k in range(i, j):
                r[order[k]] = (i + j - 1) / 2
            i = j
        return r
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else 0.0


def rows_from(world, with_exclusions):
    out = []
    for a, g in zip(world["actions"], world["gold"]):
        out.append({"arm": a["arm"], "signals": a["signals"], "icp": a["icp"], "p_worked": a["p_worked"], "y": g["y_opp"],
                    "excluded_reason": g["excluded_reason"] if with_exclusions else ""})
    return out


def run(root, seeds=(1, 2, 3, 4, 5), rounds=3):
    cfg = load_config(root)
    r2 = load_rules(f"{root}/config/rules.v2.yaml")
    types = list(r2["signals"])
    acc = make_accounts()
    res = {"naive": [[] for _ in range(rounds + 1)], "sofl": [[] for _ in range(rounds + 1)]}
    for seed in seeds:
        pop = population(None, 900 + seed, accounts=acc)
        ys, ws = [p["y"] for p in pop], [1.0] * len(pop)
        for name in ("naive", "sofl"):
            rules = copy.deepcopy(r2)
            for rd in range(rounds + 1):
                sc = [score(p["signals"], rules, p["icp"]) for p in pop]
                w = [rules["signals"][t]["weight"] for t in types]
                res[name][rd].append((wauc(sc, ys, ws), spearman(w, [TRUE_BETA[t] for t in types])))
                if rd == rounds:
                    break
                if name == "naive":
                    world = generate(rules, seed * 100 + rd, weeks=8, accounts=acc, p_holdout=0.0, p_explore=0.0, id_prefix="n")
                    rows = rows_from(world, False)
                    rules = naive_raw_conversion(rules, rows, f"rules.naive{rd + 1}")
                else:
                    world = generate(rules, seed * 100 + rd, weeks=8, accounts=acc, id_prefix="s")
                    rows = rows_from(world, True)
                    stats = per_signal(rows, types, min_eff_n=cfg["reweight"]["min_effective_n"])
                    rules, _ = propose(rules, stats, cfg, f"rules.loop{rd + 1}")
    return {n: [{"round": i, "auc": round(statistics.fmean(a for a, _ in v), 4), "spearman_weights_vs_truth": round(statistics.fmean(s for _, s in v), 3)}
                for i, v in enumerate(vs)] for n, vs in res.items()}
