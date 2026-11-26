"""Load, score with, diff and serialise a rules file. Scoring here is the slice-1 formula on recorded signal units.

Each routed action records, per signal type, the recency-decayed event count at routing time (`signals`). Re-scoring a
past action under another ruleset is therefore exact: score = min(100, icp_mult * sum(min(weight * units, cap))).
Recency decay itself is not re-tuned by this repo (documented limitation).
"""
from __future__ import annotations

from pathlib import Path

from .miniyaml import loads as yaml_loads
from .util import sha256_text


def load_rules(path) -> dict:
    return yaml_loads(Path(path).read_text(encoding="utf-8"))


def score(signals: dict[str, float], rules: dict, icp: str = "A") -> float:
    tot = 0.0
    for t, units in signals.items():
        s = rules["signals"].get(t)
        if s and units > 0:
            tot += min(s["weight"] * units, s["cap"])
    return round(min(rules.get("account_cap", 100), tot * rules.get("icp_multiplier", {}).get(icp, 1.0)), 4)


def qualifies(signals: dict[str, float], rules: dict, icp: str = "A") -> bool:
    n = sum(1 for t, u in signals.items() if u > 0 and t in rules["signals"] and rules["signals"][t]["weight"] > 0)
    return n >= rules.get("min_distinct_signal_types", 2) and score(signals, rules, icp) >= rules["thresholds"]["route"]


def dump_rules(rules: dict, header: str = "") -> str:
    out = [f"# {l}" for l in header.splitlines()] if header else []
    out.append(f"version: {rules['version']}")
    out.append("thresholds:\n  route: %s\n  high: %s" % (rules["thresholds"]["route"], rules["thresholds"]["high"]))
    out.append(f"min_distinct_signal_types: {rules.get('min_distinct_signal_types', 2)}")
    out.append(f"account_cap: {rules.get('account_cap', 100)}")
    m = rules.get("icp_multiplier", {})
    out.append("icp_multiplier: {" + ", ".join(f"{k}: {v}" for k, v in m.items()) + "}")
    out.append("signals:")
    for t, s in rules["signals"].items():
        out.append(f"  {t}: {{weight: {s['weight']}, cap: {s['cap']}}}")
    return "\n".join(out) + "\n"


def rules_sha(rules: dict) -> str:
    return sha256_text(dump_rules(rules))


def diff_rules(old: dict, new: dict) -> list[dict]:
    d = []
    for t in sorted(set(old["signals"]) | set(new["signals"])):
        a, b = old["signals"].get(t), new["signals"].get(t)
        if a != b:
            d.append({"signal": t, "old": a, "new": b})
    return d
