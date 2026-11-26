#!/usr/bin/env python3
"""signal-outcome-feedback-loop CLI.  python agent.py run | show | approve | release | verify-audit | attribute | sync | connector-demo"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sofl import approval
from sofl.audit import verify
from sofl.changeset import SplitError, report_md, run as run_change
from sofl.llm import get_client
from sofl.util import parse_dt, read_json

ROOT = Path(__file__).resolve().parent


def _now(a):
    return parse_dt(a.now) if getattr(a, "now", None) else datetime.now(timezone.utc)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run", help="attribute outcomes, estimate lift, propose rules.v3, backtest, write a change set")
    r.add_argument("--out", default="outputs/run")
    r.add_argument("--now")
    r.add_argument("--world-seed", type=int, help="generate a fresh synthetic world with this seed (hash-locked before the run) instead of data/")
    r.add_argument("--effect", type=float, help="synthetic effect-size multiplier for --world-seed (default 1.7; 1.0 is the weak world)")
    for name in ("show", "verify-audit"):
        s = sp.add_parser(name)
        s.add_argument("--out", default="outputs/run")
    a = sp.add_parser("approve", help="a named human approves the exact change-set hash")
    a.add_argument("--out", default="outputs/run")
    a.add_argument("--approver", required=True)
    a.add_argument("--sha256", required=True)
    a.add_argument("--now")
    rel = sp.add_parser("release", help="write rules.v3.yaml locally after verified approval")
    rel.add_argument("--out", default="outputs/run")
    rel.add_argument("--now")
    at = sp.add_parser("attribute", help="attribute a small export and print one row per action (no tuning)")
    at.add_argument("--actions", default="sample_routed_actions.csv")
    at.add_argument("--activities", default="sample_crm_activities.csv")
    at.add_argument("--accounts", default="sample_accounts.csv")
    at.add_argument("--as-of", default="2026-11-12T23:59:00Z")
    sy = sp.add_parser("sync", help="read-only pull of activities from the MOCK HubSpot or Salesforce API into a JSONL file")
    sy.add_argument("--flavour", choices=["hubspot", "salesforce"], default="hubspot")
    sy.add_argument("--out", default="outputs/sync")
    sy.add_argument("--inject-429", type=int, default=2)
    sy.add_argument("--crash-after-pages", type=int, default=0)
    args = ap.parse_args(argv)
    out = ROOT / getattr(args, "out", "outputs/run")
    try:
        if args.cmd == "run":
            client = get_client()
            data_dir = None
            if args.world_seed is not None:
                from evals.build_fixtures import build
                data_dir = out.parent / f"world_{args.world_seed}"
                build(data_dir, args.world_seed, args.effect)
            res = run_change(ROOT, out, _now(args), client=client, data_dir=data_dir)
            c = res["change"]
            print(f"run {res['manifest']['run_id']}  model={res['manifest']['model']}  gate={'PASSED' if c['gate']['passed'] else 'FAILED'}  weights_changed={len(c['diff'])}")
            print(f"change set sha256: {res['manifest']['change_sha256']}")
            print(f"report: {(out / 'change_report.md').relative_to(ROOT)}")
        elif args.cmd == "show":
            m = read_json(out / "manifest.json")
            print((out / "change_report.md").read_text())
            print(f"To approve: python agent.py approve --approver <your id> --sha256 {m['change_sha256']}")
        elif args.cmd == "approve":
            cfg = json.loads((ROOT / "config/approvers.json").read_text())
            rec = approval.approve(out, args.sha256, args.approver, _now(args), cfg)
            print(f"approved by {rec['approver_name']} until {rec['expires_at']}")
        elif args.cmd == "release":
            p = approval.release(out, _now(args))
            print(f"released {p.relative_to(ROOT)} (local file; nothing was written to any CRM)")
        elif args.cmd == "verify-audit":
            for f in ("audit.jsonl", "approvals.jsonl"):
                if (out / f).exists():
                    print(f, *verify(out / f))
        elif args.cmd == "attribute":
            from sofl.pipeline import load_config, load_dataset
            from sofl.rules import load_rules
            cfg = load_config(ROOT)
            r2 = load_rules(ROOT / "config/rules.v2.yaml")
            d = load_dataset(ROOT / args.actions, ROOT / args.activities, ROOT / args.accounts, set(r2["signals"]), parse_dt(args.as_of), cfg=cfg)
            for row in d["rows"]:
                print(f"{row['action_id']:10s} {row['arm']:8s} y={row['y']} excluded={row['excluded_reason'] or '-':20s} acted={row['acted']} holiday={row['holiday']}")
            print("dead letters:", json.dumps(d["dead_letters"], default=str))
            print("stats:", json.dumps(d["stats"], default=str))
        elif args.cmd == "sync":
            from evals.connector_demo import demo
            print(demo(ROOT, out, args.flavour, args.inject_429, args.crash_after_pages))
    except (approval.ApprovalError, SplitError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
