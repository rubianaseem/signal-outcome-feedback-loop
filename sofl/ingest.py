"""Parse messy exports into normalised records. Nothing is silently dropped: every rejected row goes to a dead letter
list with a reason, and every normalisation that changed a value is counted."""
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone

from .identity import Resolver, norm_host
from .util import parse_dt

ARM_ALIASES = {"routed": "routed", "holdout": "holdout", "control": "holdout", "hold-out": "holdout", "explore": "explore", "exploration": "explore"}
KNOWN_SIGNALS = None  # set from the rules file by the pipeline; unknown signal types are counted and dropped


def parse_ts(value):
    """ISO with Z or offset, naive ISO / 'YYYY-MM-DD HH:MM:SS' (documented as UTC), or epoch seconds/milliseconds."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if re.fullmatch(r"\d{10}", s):
        return datetime.fromtimestamp(int(s), tz=timezone.utc)
    if re.fullmatch(r"\d{13}", s):
        return datetime.fromtimestamp(int(s) / 1000, tz=timezone.utc)
    return parse_dt(s.replace(" ", "T", 1) if re.match(r"\d{4}-\d{2}-\d{2} ", s) else s)


def read_csv(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        out = []
        for row in csv.DictReader(fh):
            extra = row.pop(None, None)          # more fields than headers, e.g. an unquoted decimal comma
            rec = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
            if extra:
                rec["_column_mismatch"] = "1"
            out.append(rec)
        return out


def load_accounts(path) -> dict[str, dict]:
    out = {}
    for r in read_csv(path):
        r["account_id"] = r["account_id"].lower()
        r["aliases"] = [a for a in (norm_host(x) for x in r.get("domain_aliases", "").split(";")) if a]
        out[r["account_id"]] = r
    return out


def parse_signals(text: str, known) -> tuple[dict, list[str], str]:
    sigs, unknown = {}, []
    for part in [p for p in (text or "").split(";") if p.strip()]:
        name, _, units = part.partition(":")
        name = name.strip()
        try:
            u = float(units.strip().replace(",", "."))
        except ValueError:
            return {}, unknown, f"bad_units:{name}"
        if u < 0:
            return {}, unknown, f"negative_units:{name}"
        if known is not None and name not in known:
            unknown.append(name)
            continue
        sigs[name] = sigs.get(name, 0.0) + u
    return sigs, unknown, ""


def ingest_actions(rows, accounts, known_signals) -> tuple[list[dict], list[dict], dict]:
    out, dead, seen = [], [], {}
    stats = {"rows": len(rows), "duplicates_dropped": 0, "arm_normalised": 0, "unknown_signal_types_dropped": 0, "version_normalised": 0}
    for r in rows:
        aid = r.get("action_id", "")
        if r.get("_column_mismatch"):
            dead.append({"row": aid or "?", "reason": "column_count_mismatch"})
            continue
        if not aid:
            dead.append({"row": r, "reason": "missing_action_id"})
            continue
        acct = r.get("account_id", "").lower()
        if acct not in accounts:
            dead.append({"row": aid, "reason": "unknown_account"})
            continue
        arm = ARM_ALIASES.get(r.get("arm", "").strip().lower())
        if not arm:
            dead.append({"row": aid, "reason": "unknown_arm"})
            continue
        if arm != r.get("arm"):
            stats["arm_normalised"] += 1
        ts = parse_ts(r.get("routed_at"))
        if not ts:
            dead.append({"row": aid, "reason": "bad_routed_at"})
            continue
        sigs, unknown, err = parse_signals(r.get("signals", ""), known_signals)
        if err:
            dead.append({"row": aid, "reason": err})
            continue
        stats["unknown_signal_types_dropped"] += len(unknown)
        try:
            p = float(r.get("p_worked") or "")
        except ValueError:
            dead.append({"row": aid, "reason": "missing_p_worked"})
            continue
        if not 0 < p <= 1:
            dead.append({"row": aid, "reason": "bad_p_worked"})
            continue
        ver = r.get("rules_version", "")
        if ver and not ver.startswith("rules."):
            ver, _ = "rules." + ver, stats.__setitem__("version_normalised", stats["version_normalised"] + 1)
        flag = r.get("open_opp_at_route", "").lower()
        rec = {"action_id": aid, "account_id": acct, "routed_at": ts, "rules_version": ver, "signals": sigs,
               "icp": r.get("icp_tier") or accounts[acct].get("icp_tier") or "B", "owner_id": r.get("owner_id", ""), "arm": arm,
               "p_worked": p, "open_opp_flag": {"true": True, "false": False}.get(flag), "score": float(r.get("score") or 0)}
        if aid in seen:
            if seen[aid] == rec:
                stats["duplicates_dropped"] += 1
            else:
                dead.append({"row": aid, "reason": "conflicting_duplicate"})
            continue
        seen[aid] = rec
        out.append(rec)
    return out, dead, stats


def ingest_activities(rows, resolver: Resolver, as_of=None) -> tuple[list[dict], list[dict], dict]:
    out, dead, seen = [], [], set()
    stats = {"rows": len(rows), "duplicates_dropped": 0, "resolved_by": {}, "future_dated_rejected": 0}
    for r in rows:
        key = (r.get("account_id", "").lower(), r.get("contact_email"), r.get("action_id"), r.get("type"), r.get("ts"), r.get("status"), r.get("text"), r.get("owner_id"))
        if key in seen:
            stats["duplicates_dropped"] += 1
            continue
        seen.add(key)
        if r.get("_column_mismatch"):
            dead.append({"row": r.get("activity_id"), "reason": "column_count_mismatch"})
            continue
        ts = parse_ts(r.get("ts"))
        if not ts:
            dead.append({"row": r.get("activity_id"), "reason": "bad_ts"})
            continue
        if as_of and ts > as_of:
            stats["future_dated_rejected"] += 1
            dead.append({"row": r.get("activity_id"), "reason": "future_dated"})
            continue
        res = resolver.resolve({"account_id": r.get("account_id"), "email": r.get("contact_email")})
        if not res["account_id"]:
            dead.append({"row": r.get("activity_id"), "reason": "unresolved:" + res.get("reason", "?")})
            continue
        stats["resolved_by"][res["method"]] = stats["resolved_by"].get(res["method"], 0) + 1
        out.append({"activity_id": r.get("activity_id", ""), "action_id": r.get("action_id", ""), "account_id": res["account_id"],
                    "type": r.get("type", "").upper(), "ts": ts, "owner_id": r.get("owner_id", ""), "status": r.get("status", "").strip().lower(),
                    "text": r.get("text", ""), "email": r.get("contact_email", "")})
    return out, dead, stats
