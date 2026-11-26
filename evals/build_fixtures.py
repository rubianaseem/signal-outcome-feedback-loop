"""Build the versioned synthetic fixtures (v1): data/train and data/heldout, plus data/SPLIT.json with SHA-256s of the
held-out files. Run once. The tuner reads data/train only and refuses to backtest if a held-out hash has changed.
    python -m evals.build_fixtures
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from evals.messify import messify, write_csv
from evals.world import SPLIT_DATE, generate, make_accounts
from sofl.rules import load_rules
from sofl.util import sha256_file

ROOT = Path(__file__).resolve().parent.parent
ACTION_FIELDS = ["action_id", "account_id", "routed_at", "rules_version", "score", "signals", "icp_tier", "owner_id", "arm", "p_worked", "open_opp_at_route"]
ACT_FIELDS = ["activity_id", "action_id", "account_id", "contact_email", "type", "ts", "owner_id", "status", "text"]


def build(data_dir, seed=20261126, effect=None, per_week=600):
    """Write train/heldout/accounts/SPLIT.json under data_dir for a synthetic world with this seed."""
    data_dir = Path(data_dir)
    kw = {} if effect is None else {"effect": effect}
    rules = load_rules(ROOT / "config/rules.v2.yaml")
    accounts = make_accounts()
    world = generate(rules, seed=seed, accounts=accounts, per_week=per_week, **kw)
    train_ids = {a["action_id"] for a in world["actions"] if a["routed_at"] < SPLIT_DATE}
    parts = {}
    for name, keep in (("train", lambda i: i in train_ids), ("heldout", lambda i: i not in train_ids)):
        w = {"accounts": accounts, "actions": [a for a in world["actions"] if keep(a["action_id"])]}
        ids = {a["action_id"] for a in w["actions"]}
        w["activities"] = [r for r in world["activities"] if r["action_id"] in ids]
        parts[name] = (w, [g for g in world["gold"] if g["action_id"] in ids])
    for name, (w, gold) in parts.items():
        acts, rows = messify(w, seed=1 if name == "train" else 2)
        d = data_dir / name
        write_csv(d / "actions.csv", acts, ACTION_FIELDS)
        write_csv(d / "activities.csv", rows, ACT_FIELDS)
        write_csv(d / "gold.csv", gold, list(gold[0]))
    acc_rows = [{"account_id": a["account_id"], "domain": a["domain"], "domain_aliases": ";".join(a["aliases"]), "icp_tier": a["icp"], "owner_id": a["owner_id"]} for a in accounts.values()]
    write_csv(data_dir / "accounts.csv", acc_rows, list(acc_rows[0]))
    split = {"split_date": SPLIT_DATE.strftime("%Y-%m-%d"), "unobserved_below_threshold_not_exported": world["unobserved"],
             "heldout_sha256": {f: sha256_file(data_dir / "heldout" / f) for f in ("actions.csv", "activities.csv", "gold.csv")},
             "note": "Hashed when the fixtures were built, before any attribution or re-weighting code read data/train."}
    (data_dir / "SPLIT.json").write_text(json.dumps(split, indent=2, sort_keys=True) + "\n")
    return {k: len(v[0]["actions"]) for k, v in parts.items()}


def main():
    print(json.dumps(build(ROOT / "data")))


if __name__ == "__main__":
    sys.exit(main())
