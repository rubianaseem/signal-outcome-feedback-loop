"""Turn the clean synthetic world into messy CRM-style exports. SYNTHETIC DATA ONLY. Deterministic given a seed."""
from __future__ import annotations

import csv
import random
from datetime import timezone
from pathlib import Path

NOTE_TEMPLATES = {
    "meeting_booked": ["Booked a discovery call for Thursday", "Demo scheduled for next week", "Meeting booked via calendar link", "Call set up with their ops lead"],
    "contacted_no_reply": ["Called twice, voicemail, no answer", "Emailed, no response yet", "LinkedIn message sent, nothing back", "Tried to book a meeting but they did not reply"],
    "not_interested": ["Said they are not interested right now", "Declined, already use a competitor", "Asked us to stop contacting them"],
    "wrong_contact": ["Wrong person, left the company", "Not the decision maker, redirected to finance"],
    "deferred": ["Try again in Q1, budget frozen", "Asked to follow up after the holidays"],
    "not_actioned": ["Skipped, too many open tasks", "Did not get to this one", "Deprioritised, covering for a colleague"],
}
ACTED_CODES = ["meeting_booked", "contacted_no_reply", "not_interested", "wrong_contact", "deferred"]


def fmt_ts(rng, ts):
    r = rng.random()
    if r < 0.70:
        return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if r < 0.90:
        return ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")      # naive: documented as UTC
    return str(int(ts.timestamp() * 1000))                                     # epoch milliseconds


def messify(world: dict, seed: int):
    rng = random.Random(seed)
    accounts = world["accounts"]
    actions, acts = [], []
    in_pipe_ids = {}
    for a in world["actions"]:
        arm = {"routed": rng.choice(["routed", "routed", "ROUTED", " Routed"]), "holdout": rng.choice(["holdout", "control", "Holdout"]),
               "explore": rng.choice(["explore", "explore", "Explore"])}[a["arm"]]
        if a["open_opp_at_route"]:
            flag = "true" if rng.random() < 0.7 else ""
        else:
            flag = "false" if rng.random() < 0.9 else ""
        sig = ";".join(f"{t}:{u}" for t, u in a["signals"].items())
        if rng.random() < 0.01:
            sig += ";legacy_pixel:1.0"
        row = {"action_id": a["action_id"], "account_id": a["account_id"], "routed_at": fmt_ts(rng, a["routed_at"]),
               "rules_version": rng.choice([a["rules_version"], a["rules_version"], a["rules_version"].replace("rules.", "")]),
               "score": a["score"], "signals": sig, "icp_tier": a["icp"] if rng.random() > 0.03 else "",
               "owner_id": a["owner_id"], "arm": arm, "p_worked": a["p_worked"], "open_opp_at_route": flag}
        actions.append(row)
        if rng.random() < 0.01:
            actions.append(dict(row))                                             # duplicate export row
    for r in world["activities"]:
        acc = accounts[r["account_id"]]
        row = {"activity_id": "", "action_id": r["action_id"], "account_id": r["account_id"], "contact_email": "", "type": r["type"],
               "ts": r["ts"], "owner_id": r["owner_id"], "status": r["status"], "text": r["text"]}
        if r["type"] == "TASK_COMPLETED" and rng.random() < 0.05:                # blank status, free-text note carries the outcome
            row["type"], row["status"], row["text"] = "TASK_UPDATED", "", rng.choice(NOTE_TEMPLATES[rng.choice(ACTED_CODES)])
        elif r["type"] == "TASK_CLOSED" and rng.random() < 0.3:
            row["type"], row["status"], row["text"] = "TASK_UPDATED", "", rng.choice(NOTE_TEMPLATES["not_actioned"])
        if r.get("pre") or (r["type"] != "OWNER_CHANGED" and rng.random() < 0.15):
            row["action_id"] = ""
        if rng.random() < 0.12:
            row["account_id"] = ""
            dom = rng.choice([acc["domain"], "app." + acc["domain"]] + acc["aliases"])
            row["contact_email"] = (f"user@https://WWW.{dom}./pricing" if rng.random() < 0.15 else f"contact@{dom}")
        elif rng.random() < 0.05:
            row["account_id"] = row["account_id"].upper()
        elif rng.random() < 0.01:
            row["account_id"] = "ACC-9999"
        row["ts"] = fmt_ts(rng, r["ts"]) if not isinstance(r["ts"], str) else r["ts"]
        acts.append(row)
        if rng.random() < 0.03:
            acts.append(dict(row))
    for i, r in enumerate(acts, 1):
        r["activity_id"] = f"act-{seed}-{i:06d}"
    return actions, acts


def write_csv(path, rows, fields):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
