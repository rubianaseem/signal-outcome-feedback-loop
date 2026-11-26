"""Enforced human approval of a rules change set, bound to the SHA-256 of ruleset_change.json.

Enforced in code (each rule has a unit test or failure-suite scenario):
  - The approver is a named human in config/approvers.json. Agent, model and service identities are refused.
  - The approver gives the full 64-character SHA-256 of ruleset_change.json; it must match the file on disk and the hash
    the run recorded in manifest.json. Editing the change set (or the candidate rules file it pins) voids the approval.
  - A change set whose backtest gate failed can never be approved or released.
  - Approvals expire after approval_ttl_hours and live in a hash-chained approvals.jsonl.
  - release() is the only code that writes a rules file, and only after verify_approval() passes. There is no auto-approve flag,
    and nothing in this repository writes to a CRM.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from .audit import AuditLog, verify
from .util import iso, parse_dt, read_json, sha256_file, sha256_text


class ApprovalError(Exception):
    pass


def is_agent(approver_id: str, blocked: list[str]) -> bool:
    toks = set(re.split(r"[^a-z0-9]+", (approver_id or "").lower()))
    return not (approver_id or "").strip() or bool(toks & {b.lower() for b in blocked})


def _check_artifacts(run_dir: Path, m: dict) -> str:
    cs = run_dir / "ruleset_change.json"
    current = sha256_file(cs)
    if current != m["change_sha256"]:
        raise ApprovalError("ruleset_change.json differs from what this run generated; re-run instead of editing outputs")
    cand = run_dir / "rules.v3.candidate.yaml"
    if sha256_file(cand) != read_json(cs)["candidate_rules_sha256"]:
        raise ApprovalError("rules.v3.candidate.yaml differs from the file the change set pins; re-run instead of editing outputs")
    return current


def approve(run_dir, sha256: str, approver_id: str, now: datetime, approvers: dict) -> dict:
    run_dir = Path(run_dir)
    m = read_json(run_dir / "manifest.json")
    if is_agent(approver_id, approvers.get("blocked_identities", [])):
        raise ApprovalError(f"'{approver_id}' is an agent, model or service identity and can never approve")
    who = approvers.get("approvers", {}).get(approver_id)
    if not who:
        raise ApprovalError(f"unknown approver '{approver_id}'; approvers are named humans in config/approvers.json")
    if not re.fullmatch(r"[0-9a-f]{64}", sha256 or ""):
        raise ApprovalError("approval needs the full 64-character SHA-256 printed by `python agent.py show`")
    current = sha256_file(run_dir / "ruleset_change.json")
    if sha256 != current:
        raise ApprovalError("hash does not match ruleset_change.json on disk; review the current change set and use its hash")
    _check_artifacts(run_dir, m)
    if not read_json(run_dir / "ruleset_change.json")["gate"]["passed"]:
        raise ApprovalError("the backtest gate failed for this change set; it cannot be approved")
    log = AuditLog(run_dir / "approvals.jsonl", clock=lambda: now)
    return log.append({"event": "approved", "change_sha256": sha256, "approver": approver_id, "approver_name": who["name"],
                       "run_id": m["run_id"], "expires_at": iso(now + timedelta(hours=approvers.get("approval_ttl_hours", 48)))})


def verify_approval(run_dir, now: datetime) -> dict:
    run_dir = Path(run_dir)
    m = read_json(run_dir / "manifest.json")
    ap = run_dir / "approvals.jsonl"
    if not ap.exists():
        raise ApprovalError("not approved: run `python agent.py approve` with a named approver and the change-set hash")
    ok, why = verify(ap)
    if not ok:
        raise ApprovalError(f"approvals log failed verification: {why}")
    recs = [json.loads(x) for x in ap.read_text().splitlines() if x.strip()]
    mine = [r for r in recs if r.get("event") == "approved"]
    if not mine:
        raise ApprovalError("not approved")
    last = mine[-1]
    try:
        current = _check_artifacts(run_dir, m)
    except ApprovalError:
        raise ApprovalError("change set changed after approval; approval is void")
    if current != last["change_sha256"]:
        raise ApprovalError("change set changed after approval; approval is void")
    if now > parse_dt(last["expires_at"]):
        raise ApprovalError("approval expired; review and approve again")
    return last


def release(run_dir, now: datetime) -> Path:
    run_dir = Path(run_dir)
    last = verify_approval(run_dir, now)
    cs = read_json(run_dir / "ruleset_change.json")
    text = (run_dir / "rules.v3.candidate.yaml").read_text(encoding="utf-8")
    if sha256_text(text) != cs["candidate_rules_sha256"]:
        raise ApprovalError("candidate rules hash mismatch")
    out = run_dir / "released" / f"{cs['to_version']}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    AuditLog(run_dir / "audit.jsonl", clock=lambda: now).append(
        {"event": "released", "to_version": cs["to_version"], "rules_sha256": cs["candidate_rules_sha256"], "approver": last["approver"],
         "change_sha256": last["change_sha256"], "writes_to_crm": 0})
    return out
