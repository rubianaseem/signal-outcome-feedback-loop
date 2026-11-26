"""Build the reviewable change set: lift evidence, rules diff, backtest on the hash-locked held-out split, gate."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from .attribution import naive_label
from .audit import AuditLog
from .backtest import evaluate
from .lift import band_check, eligible, per_signal
from .pipeline import AS_OF_DEFAULT, load_config, load_dataset
from .reweight import naive_raw_conversion, propose
from .rules import diff_rules, dump_rules, load_rules, rules_sha
from .util import parse_dt, pii_hash, sha256_file, sha256_text, write_json


class SplitError(Exception):
    pass


def verify_split(data_dir: Path) -> dict:
    root = data_dir
    split = json.loads((root / "SPLIT.json").read_text())
    for f, h in split["heldout_sha256"].items():
        if sha256_file(root / "heldout" / f) != h:
            raise SplitError(f"heldout/{f} changed after the split was hashed; refusing to backtest on it")
    return split


def run(root, out_dir, now: datetime, client=None, data_dir=None, check_split=True) -> dict:
    root, out_dir = Path(root), Path(out_dir)
    data_dir = Path(data_dir) if data_dir else root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in ("audit.jsonl", "approvals.jsonl"):
        (out_dir / f).unlink(missing_ok=True)
    shutil.rmtree(out_dir / "released", ignore_errors=True)
    cfg = load_config(root)
    r2 = load_rules(root / "config/rules.v2.yaml")
    as_of = parse_dt(AS_OF_DEFAULT)
    split = verify_split(data_dir) if check_split else {}
    log = AuditLog(out_dir / "audit.jsonl", clock=lambda: now)
    known = set(r2["signals"])
    acc_csv = data_dir / "accounts.csv"
    tr = load_dataset(data_dir / "train/actions.csv", data_dir / "train/activities.csv", acc_csv, known, as_of, client=client, log=log.append, cfg=cfg)
    ho = load_dataset(data_dir / "heldout/actions.csv", data_dir / "heldout/activities.csv", acc_csv, known, as_of, client=client, log=log.append, cfg=cfg)
    rc = cfg["reweight"]
    hold_rows = [r for r in eligible(tr["rows"]) if r["arm"] == "holdout"]
    stats = per_signal(tr["rows"], list(r2["signals"]), z=rc["z"], min_eff_n=rc["min_effective_n"])
    bands = band_check([dict(r, score=_score(r, r2)) for r in tr["rows"]])
    problems = []
    if len(hold_rows) < rc["min_holdout_rows"]:
        problems.append(f"holdout has {len(hold_rows)} eligible rows, below min_holdout_rows={rc['min_holdout_rows']}; no proposal")
        r3, notes = r2, [{"decision": "refused_no_holdout"}]
    else:
        r3, notes = propose(r2, stats, cfg)
    naive_tr = naive_raw_conversion(r2, naive_label(tr["actions"], tr["activities"], cfg["attribution"]["window_days"]))
    ho_rows = eligible(ho["rows"])
    ev = {"rules.v2": evaluate(ho_rows, r2), "rules.v3": evaluate(ho_rows, r3, ref=r2),
          "naive_raw_conversion": evaluate(ho_rows, naive_tr, ref=r2)}
    g = cfg["gate"]
    v3 = ev["rules.v3"]
    gate_ok = (not problems) and bool(diff_rules(r2, r3)) and v3["auc_gain_vs_ref"] > g["min_auc_gain"] and \
        (not g["require_ci_not_negative"] or v3["auc_gain_ci95"][0] > -0.005)
    cand_text = dump_rules(r3, header="rules.v3 CANDIDATE. Not live. Released only by `python agent.py release` after named human approval.\nSynthetic-data run: do not use these weights on a real account.")
    (out_dir / "rules.v3.candidate.yaml").write_text(cand_text, encoding="utf-8")
    change = {"from_version": r2["version"], "to_version": r3["version"], "diff": diff_rules(r2, r3), "decisions": notes,
              "evidence": {"train_rows": len(tr["rows"]), "eligible": len(eligible(tr["rows"])), "holdout_eligible": len(hold_rows),
                           "excluded": _count(tr["rows"], "excluded_reason")},
              "lift": stats, "routing_vs_holdout_by_score_band": bands, "backtest_heldout": ev,
              "gate": {"passed": bool(gate_ok), "rule": g, "problems": problems},
              "candidate_rules_sha256": sha256_text(cand_text), "base_rules_sha256": rules_sha(r2),
              "feedback_config_sha256": sha256_file(root / "config/feedback.yaml"), "as_of": AS_OF_DEFAULT,
              "heldout_sha256": split.get("heldout_sha256", {}),
              "limitations": ["synthetic and author-written data", "recency decay is not re-tuned", "marginal lift: co-occurring signals share credit",
                              "rows below threshold that were not explored have no outcome in the export (handled by the explore arm, not by assumption)"]}
    write_json(out_dir / "ruleset_change.json", change)
    chash = sha256_file(out_dir / "ruleset_change.json")
    manifest = {"run_id": "run-" + chash[:12], "change_sha256": chash, "inputs": {"train_actions": sha256_file(data_dir / "train/actions.csv"),
                "train_activities": sha256_file(data_dir / "train/activities.csv")}, "model": getattr(client, "name", "none (deterministic rules)")}
    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "dead_letters.json", [_scrub(d) for d in tr["dead_letters"] + ho["dead_letters"]])
    write_json(out_dir / "ingest_stats.json", {"train": tr["stats"], "heldout": ho["stats"]})
    log.append({"event": "run_complete", "run_id": manifest["run_id"], "change_sha256": chash, "gate_passed": bool(gate_ok),
                "weights_changed": len(change["diff"]), "dead_letters": len(tr["dead_letters"]) + len(ho["dead_letters"]), "writes_to_crm": 0})
    (out_dir / "change_report.md").write_text(report_md(change, manifest), encoding="utf-8")
    return {"manifest": manifest, "change": change, "train": tr, "heldout": ho}


def _score(r, rules):
    from .rules import score
    return score(r["signals"], rules, r["icp"])


def _count(rows, key):
    out = {}
    for r in rows:
        k = r[key] or "eligible"
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def _scrub(d: dict) -> dict:
    row = d["row"]
    if isinstance(row, dict):
        row = {k: (pii_hash(v) if "email" in k else v) for k, v in row.items()}
    return {"row": row, "reason": d["reason"]}


def report_md(c: dict, m: dict) -> str:
    L = [f"# Change set {m['run_id']}: {c['from_version']} -> {c['to_version']}", "", f"SHA-256 of ruleset_change.json: `{m['change_sha256']}`", "",
         f"Backtest gate: **{'PASSED' if c['gate']['passed'] else 'FAILED'}**. Synthetic data; these are regression numbers, not field accuracy.", "", "## Proposed weight changes", ""]
    L += [f"- {d['signal']}: weight {d['old']['weight']} -> {d['new']['weight']}, cap {d['old']['cap']} -> {d['new']['cap']}" for d in c["diff"]] or ["- none"]
    L += ["", "## Held-out backtest (time split, hashed before tuning)", "", "| ruleset | AUC | capture top 30% | precision at route | recall at route |", "|---|---|---|---|---|"]
    for k, v in c["backtest_heldout"].items():
        L.append(f"| {k} | {v['auc']} | {v['capture_top30']} | {v['route_precision']} | {v['route_recall']} |")
    v3 = c["backtest_heldout"]["rules.v3"]
    L += ["", f"v3 AUC gain over v2: {v3['auc_gain_vs_ref']} (95% bootstrap interval {v3['auc_gain_ci95']}).", "", "## Lift per signal type (train, inverse-propensity weighted)", "",
          "| signal | lift | 95% interval | effective n with/without | enough evidence |", "|---|---|---|---|---|"]
    for s in c["lift"]:
        L.append(f"| {s['signal']} | {s['delta']:+.3f} | {s['lo']:+.3f} to {s['hi']:+.3f} | {s['n_eff_with']}/{s['n_eff_without']} | {s['sufficient']} |")
    L += ["", "## Routing versus holdout by score band (train)", ""] + [f"- {b['band']}: {b['verdict']} (routed {b.get('routed_rate')}, holdout {b.get('holdout_rate')}, n {b['n_routed']}/{b['n_holdout']})" for b in c["routing_vs_holdout_by_score_band"]]
    L += ["", "## Limitations", ""] + [f"- {x}" for x in c["limitations"]]
    return "\n".join(L) + "\n"
