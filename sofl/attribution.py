"""Deterministic outcome attribution: routed action + CRM activities -> one labelled row per action.

Join: an activity with a known action_id links to that action; one without links to the LATEST action on the same
resolved account that was routed at or before the activity. Activities before their action are ignored (negative lag).
Label y = an OPP_CREATED activity within `window_days` after routing (+ `holiday_extension_days` if routing fell in a
holiday window). Exclusions, first match wins, each counted and named:
  already_in_pipeline  CRM flag true, or an opportunity created in the `pre_existing_lookback_days` before routing
  owner_changed        an OWNER_CHANGED activity linked to the action
  window_open          the attribution window had not closed by as_of (no outcome yet: unobserved, not a negative)
`acted` (did the rep act) comes from task status, or from a classified note when the status is blank; None if unknown.
It is reported, not used as a label: conditioning on rep action would bias the lift (intention to treat).
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import timedelta

from .disposition import ACTED, classify
from .util import parse_dt

DONE = {"done", "completed", "complete", "closed - completed", "finished"}
IGNORED = {"ignored", "expired", "skipped", "no action", "dismissed", "not started"}


def in_holiday(ts, holidays) -> bool:
    d = ts.strftime("%Y-%m-%d")
    return any(str(h["start"]) <= d <= str(h["end"]) for h in holidays)


def attribute(actions, activities, cfg, as_of, client=None, log=None) -> tuple[list[dict], dict]:
    a_cfg, holidays = cfg["attribution"], cfg.get("holidays", [])
    by_id = {a["action_id"]: a for a in actions}
    by_acct: dict[str, list] = {}
    for a in actions:
        by_acct.setdefault(a["account_id"], []).append(a)
    for v in by_acct.values():
        v.sort(key=lambda a: a["routed_at"])
    starts = {k: [a["routed_at"] for a in v] for k, v in by_acct.items()}
    linked: dict[str, list] = {a["action_id"]: [] for a in actions}
    opps_by_acct: dict[str, list] = {}
    stats = {"linked_by_id": 0, "linked_by_account": 0, "unlinked": 0, "negative_lag_ignored": 0, "notes_classified": 0, "note_sources": {}}
    for ac in activities:
        if ac["type"] == "OPP_CREATED":
            opps_by_acct.setdefault(ac["account_id"], []).append(ac["ts"])
        tgt = by_id.get(ac["action_id"]) if ac["action_id"] else None
        if tgt is not None:
            stats["linked_by_id"] += 1
        else:
            i = bisect_right(starts.get(ac["account_id"], []), ac["ts"]) - 1
            tgt = by_acct[ac["account_id"]][i] if i >= 0 else None
            stats["linked_by_account" if tgt else "unlinked"] += 1
        if tgt is None:
            continue
        if ac["ts"] < tgt["routed_at"]:
            stats["negative_lag_ignored"] += 1
            continue
        linked[tgt["action_id"]].append(ac)
    rows = []
    for a in actions:
        t0 = a["routed_at"]
        hol = in_holiday(t0, holidays)
        win = a_cfg["window_days"] + (a_cfg["holiday_extension_days"] if hol else 0)
        acts = linked[a["action_id"]]
        reason = ""
        pre = any(t0 - timedelta(days=a_cfg["pre_existing_lookback_days"]) <= o < t0 for o in opps_by_acct.get(a["account_id"], []))
        if a["open_opp_flag"] or pre:
            reason = "already_in_pipeline"
        elif any(x["type"] == "OWNER_CHANGED" for x in acts):
            reason = "owner_changed"
        elif as_of < t0 + timedelta(days=win + a_cfg.get("maturity_days", 0)):
            reason = "window_open"
        y = int(any(x["type"] == "OPP_CREATED" and x["ts"] <= t0 + timedelta(days=win) for x in acts))
        acted = None
        if a["arm"] != "holdout":
            for x in acts:
                if x["type"] in ("TASK_COMPLETED", "TASK_CLOSED", "TASK_UPDATED"):
                    if x["status"] in DONE:
                        acted = True
                    elif x["status"] in IGNORED and acted is None:
                        acted = False
                    elif not x["status"] and x["text"]:
                        r = classify(x["text"], client=client, log=log)
                        stats["notes_classified"] += 1
                        stats["note_sources"][r["source"]] = stats["note_sources"].get(r["source"], 0) + 1
                        if r["code"] in ACTED:
                            acted = True
                        elif r["code"] == "not_actioned" and acted is None:
                            acted = False
        rows.append({"action_id": a["action_id"], "account_id": a["account_id"], "arm": a["arm"], "signals": a["signals"], "icp": a["icp"],
                     "routed_at": t0, "p_worked": a["p_worked"], "excluded_reason": reason, "y": y, "acted": acted, "holiday": hol})
    return rows, stats


def naive_label(actions, activities, window_days=14) -> list[dict]:
    """Evaluation baseline: join on explicit action_id or an exact account_id only, fixed window, no exclusions of any kind."""
    by_id = {a["action_id"]: a for a in actions}
    opp: dict[str, list] = {}
    for ac in activities:
        if ac["type"] == "OPP_CREATED" and ac["action_id"] in by_id:
            opp.setdefault(ac["action_id"], []).append(ac["ts"])
    return [{"action_id": a["action_id"], "arm": a["arm"], "signals": a["signals"], "icp": a["icp"], "excluded_reason": "",
             "y": int(any(a["routed_at"] <= t <= a["routed_at"] + timedelta(days=window_days) for t in opp.get(a["action_id"], []))),
             "p_worked": a["p_worked"]} for a in actions]
