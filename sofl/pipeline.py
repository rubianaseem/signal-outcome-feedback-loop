"""Orchestration: load exports -> ingest -> attribute -> lift -> propose rules.v3 -> backtest -> change set."""
from __future__ import annotations

from pathlib import Path

from .attribution import attribute
from .identity import Resolver
from .ingest import ingest_actions, ingest_activities, load_accounts, read_csv
from .miniyaml import load_file

AS_OF_DEFAULT = "2026-11-12T23:59:00Z"


def load_config(root) -> dict:
    return load_file(Path(root) / "config/feedback.yaml")


def load_dataset(actions_csv, activities_csv, accounts_csv, known_signals, as_of, client=None, log=None, cfg=None, activity_rows=None):
    accounts = load_accounts(accounts_csv)
    res = Resolver(accounts)
    actions, dead_a, st_a = ingest_actions(read_csv(actions_csv), accounts, known_signals)
    act_rows = activity_rows if activity_rows is not None else read_csv(activities_csv)
    acts, dead_b, st_b = ingest_activities(act_rows, res, as_of=as_of)
    rows, st_att = attribute(actions, acts, cfg, as_of, client=client, log=log)
    return {"rows": rows, "actions": actions, "activities": acts, "dead_letters": dead_a + dead_b,
            "stats": {"actions": st_a, "activities": st_b, "attribution": st_att}}
