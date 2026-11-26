#!/usr/bin/env python3
"""Reproduce every number in the README and docs/EVALUATION.md.   python run_evals.py   (about 1 minute, no API key, stdlib only)
Writes outputs/eval_report.md and outputs/eval_results.json. All data is synthetic and author-written."""
from __future__ import annotations

import csv
import json
import statistics
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from evals import loop_sim
from evals.build_fixtures import build
from evals.identity_cases_v2 import CASES
from evals.notes_heldout_v1 import NOTES, NOTES_B
from evals.scripted_model import FakeModel
from evals.v1_parse import norm_host_v1
from evals.world import TRUE_BETA
from sofl import disposition
from sofl.attribution import naive_label
from sofl.changeset import run as run_change
from sofl.identity import norm_host
from sofl.lift import eligible, per_signal
from sofl.pipeline import AS_OF_DEFAULT, load_config, load_dataset
from sofl.rules import load_rules
from sofl.util import parse_dt

ROOT = Path(__file__).resolve().parent
NOW = datetime(2026, 11, 26, 18, 0, tzinfo=timezone.utc)


def gold_of(split):
    return {r["action_id"]: r for r in csv.DictReader(open(ROOT / "data" / split / "gold.csv"))}


def attribution_eval(cfg, r2):
    out = {}
    for split in ("train", "heldout"):
        d = load_dataset(ROOT / f"data/{split}/actions.csv", ROOT / f"data/{split}/activities.csv", ROOT / "data/accounts.csv", set(r2["signals"]), parse_dt(AS_OF_DEFAULT), cfg=cfg)
        g = gold_of(split)
        rows = d["rows"]
        conf = [r for r in rows if g[r["action_id"]]["excluded_reason"] in ("already_in_pipeline", "owner_changed")]
        caught = [r for r in conf if r["excluded_reason"] in ("already_in_pipeline", "owner_changed")]
        clean = [r for r in rows if not g[r["action_id"]]["excluded_reason"]]
        false_ex = [r for r in clean if r["excluded_reason"]]
        both = [r for r in clean if not r["excluded_reason"]]
        lab_ok = sum(r["y"] == int(g[r["action_id"]]["y_opp"]) for r in both)
        nv = naive_label(d["actions"], d["activities"], cfg["attribution"]["window_days"])
        gold_el = [r for r in nv if not g[r["action_id"]]["excluded_reason"]]
        nv_ok = sum(r["y"] == int(g[r["action_id"]]["y_opp"]) for r in gold_el)
        nv_leak = sum(1 for r in nv if g[r["action_id"]]["excluded_reason"] in ("already_in_pipeline", "owner_changed", "window_open"))
        acted_rows = [r for r in rows if r["arm"] != "holdout" and r["acted"] is not None]
        acted_ok = sum(int(r["acted"]) == int(g[r["action_id"]]["acted"]) for r in acted_rows)
        out[split] = {"rows": len(rows), "confounded_rows_in_gold": len(conf), "confounders_excluded": len(caught), "clean_rows": len(clean),
                      "clean_rows_wrongly_excluded": len(false_ex), "label_agreement": f"{lab_ok}/{len(both)}",
                      "naive_label_agreement_on_gold_eligible": f"{nv_ok}/{len(gold_el)}", "naive_confounded_or_immature_rows_kept_as_training_rows": nv_leak,
                      "rep_action_known": f"{len(acted_rows)}/{sum(1 for r in rows if r['arm'] != 'holdout')}", "rep_action_correct_when_known": f"{acted_ok}/{len(acted_rows)}",
                      "dead_letters": len(d["dead_letters"]), "notes_classified": d["stats"]["attribution"]["notes_classified"]}
    return out


def estimator_eval(cfg, r2):
    """Rank agreement (Spearman) of estimated per-type lift with the known true effect, train split, plus mean absolute error vs best-fit scale."""
    d = load_dataset(ROOT / "data/train/actions.csv", ROOT / "data/train/activities.csv", ROOT / "data/accounts.csv", set(r2["signals"]), parse_dt(AS_OF_DEFAULT), cfg=cfg)
    types = list(r2["signals"])
    truth = [TRUE_BETA[t] for t in types]
    res = {}
    variants = {"v3 estimator (exclusions + IPW)": per_signal(d["rows"], types, min_eff_n=0), "exclusions, no IPW": per_signal(d["rows"], types, min_eff_n=0, weighted=False),
                "IPW, no exclusions": per_signal([dict(r, excluded_reason="") for r in d["rows"]], types, min_eff_n=0)}
    for name, st in variants.items():
        res[name] = round(loop_sim.spearman([s["delta"] for s in st], truth), 3)
    nv = [r for r in naive_label(d["actions"], d["activities"]) if r["arm"] == "routed"]
    rate = []
    for t in types:
        sub = [r for r in nv if r["signals"].get(t, 0) > 0]
        rate.append(sum(r["y"] for r in sub) / len(sub))
    res["naive raw conversion rate"] = round(loop_sim.spearman(rate, truth), 3)
    res["v2 weights (for reference)"] = round(loop_sim.spearman([r2["signals"][t]["weight"] for t in types], truth), 3)
    return res


def multi_seed(effect, seeds=range(1, 11)):
    rows = []
    for s in seeds:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            build(td / "w", s, effect)
            c = run_change(ROOT, td / "o", NOW, data_dir=td / "w")["change"]
            b = c["backtest_heldout"]
            rows.append({"seed": s, "gate": c["gate"]["passed"], "weights_changed": len(c["diff"]), "auc_v2": b["rules.v2"]["auc"], "auc_v3": b["rules.v3"]["auc"],
                         "auc_naive": b["naive_raw_conversion"]["auc"], "gain_ci_low": b["rules.v3"]["auc_gain_ci95"][0]})
    return {"effect": effect, "worlds": len(rows), "gate_passed": sum(r["gate"] for r in rows), "v3_beats_v2": sum(r["auc_v3"] > r["auc_v2"] for r in rows),
            "naive_below_v2": sum(r["auc_naive"] < r["auc_v2"] for r in rows), "v3_beats_naive": sum(r["auc_v3"] > r["auc_naive"] for r in rows),
            "median_auc_gain_v3_vs_v2": round(statistics.median(r["auc_v3"] - r["auc_v2"] for r in rows), 4),
            "median_auc_gain_naive_vs_v2": round(statistics.median(r["auc_naive"] - r["auc_v2"] for r in rows), 4), "per_world": rows}


def disposition_eval():
    out = {}
    for label, notes in (("held-out A (written before the classifier)", NOTES), ("probe B (written after, unseen phrasings)", NOTES_B)):
        ok = ok_kw = wrong_confident = 0
        for n, g in notes:
            r = disposition.classify(n)
            p = "injection" if r["source"] == "quarantine" else r["code"]
            ok += p == g
            wrong_confident += (p != g and p != "unclear")
            ok_kw += disposition.keyword_baseline(n) == g and g != "injection"
        out[label] = {"notes": len(notes), "rules_correct": ok, "rules_wrong_but_confident": wrong_confident, "keyword_baseline_correct": ok_kw}
    fm = FakeModel()
    src = {}
    for n, g in NOTES + NOTES_B:
        r = disposition.classify(n, client=fm, sleep=lambda s: None)
        src[r["source"]] = src.get(r["source"], 0) + 1
    out["scripted model run over all 42 notes"] = {"sources": src, "model_calls": len(fm.calls), "injection_notes_sent_to_model": sum("nstruction" in c or "SYSTEM" in c for c in fm.calls)}
    return out


def main():
    cfg, r2 = load_config(ROOT), load_rules(ROOT / "config/rules.v2.yaml")
    R = {}
    R["identity_parse"] = {"cases": len(CASES), "slice1_v1_pass": sum(norm_host_v1(v) == e for v, e in CASES), "v2_pass": sum(norm_host(v) == e for v, e in CASES),
                           "v2_failures": [v for v, e in CASES if norm_host(v) != e]}
    R["attribution"] = attribution_eval(cfg, r2)
    R["estimator_rank_agreement_with_truth"] = estimator_eval(cfg, r2)
    res = run_change(ROOT, ROOT / "outputs/run", NOW)
    c = res["change"]
    R["shipped_heldout_backtest"] = {"gate_passed": c["gate"]["passed"], "weights_changed": [d["signal"] for d in c["diff"]], **c["backtest_heldout"],
                                      "routing_vs_holdout_train": c["routing_vs_holdout_by_score_band"]}
    R["multi_world_effect_1.7"] = multi_seed(1.7)
    R["multi_world_effect_1.0_weak"] = multi_seed(1.0)
    R["selection_bias_loop_sim"] = loop_sim.run(ROOT)
    R["disposition"] = disposition_eval()
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs/eval_results.json").write_text(json.dumps(R, indent=2, sort_keys=True, default=str) + "\n")
    L = ["# Eval report (synthetic, author-written data; regression checks, not field accuracy)", "", "```json", json.dumps(R, indent=1, sort_keys=True, default=str), "```", ""]
    (ROOT / "outputs/eval_report.md").write_text("\n".join(L))
    ip = R["identity_parse"]
    print(f"identity parse: slice-1 {ip['slice1_v1_pass']}/{ip['cases']}, v2 {ip['v2_pass']}/{ip['cases']}")
    for s, a in R["attribution"].items():
        print(f"attribution {s}: confounders excluded {a['confounders_excluded']}/{a['confounded_rows_in_gold']}, clean wrongly excluded {a['clean_rows_wrongly_excluded']}/{a['clean_rows']}, label agreement {a['label_agreement']} (naive {a['naive_label_agreement_on_gold_eligible']})")
    print("estimator Spearman vs truth:", R["estimator_rank_agreement_with_truth"])
    h = R["shipped_heldout_backtest"]
    print("shipped held-out:", {k: h[k] for k in ("rules.v2", "rules.v3", "naive_raw_conversion")}, "gate", h["gate_passed"])
    for k in ("multi_world_effect_1.7", "multi_world_effect_1.0_weak"):
        m = R[k]
        print(k, {x: m[x] for x in m if x != "per_world"})
    print("loop sim:", json.dumps(R["selection_bias_loop_sim"]))
    print("disposition:", json.dumps(R["disposition"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
