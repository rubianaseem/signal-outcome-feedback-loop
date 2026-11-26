"""Synthetic world generator for the signal-outcome feedback loop. EVERYTHING HERE IS SYNTHETIC AND AUTHOR-WRITTEN.

The generator knows the true effect of each signal type (TRUE_BETA). Rules v2 deliberately gets several wrong
(pricing_page_visit and crm_email_reply too high, intent_topic_surge too low, docs_visit useless but scored).
It then emits the messy exports a CRM would hold (routed actions + activities) and a gold file with the truth.
Because the author wrote both the world and the system, results show whether the machinery recovers a known
signal under confounding. They are regression checks, not field evidence.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from sofl.rules import qualifies, score

TRUE_BETA = {"pricing_page_visit": 0.45, "demo_page_visit": 1.2, "docs_visit": 0.0, "blog_visit": -0.1,
             "product_signup": 0.7, "product_usage_spike": 1.4, "seat_limit_reached": 1.8, "intent_topic_surge": 1.1,
             "webinar_attended": 0.1, "crm_meeting_booked": 1.5, "crm_email_reply": 0.25, "hiring_gtm_ops": 0.9,
             "evaluating_alternatives": 1.5, "budget_confirmed": 1.7}
FREQ = {"pricing_page_visit": 14, "demo_page_visit": 6, "docs_visit": 16, "blog_visit": 18, "product_signup": 8,
        "product_usage_spike": 7, "seat_limit_reached": 2, "intent_topic_surge": 12, "webinar_attended": 10,
        "crm_meeting_booked": 4, "crm_email_reply": 9, "hiring_gtm_ops": 5, "evaluating_alternatives": 3,
        "budget_confirmed": 2}
B0, WORK_BOOST, ICP_EFFECT = -4.3, 0.6, {"A": 0.3, "B": 0.0, "C": -0.3}
START = datetime(2026, 7, 13, tzinfo=timezone.utc)
AS_OF = datetime(2026, 11, 12, 23, 59, tzinfo=timezone.utc)
SPLIT_DATE = datetime(2026, 9, 28, tzinfo=timezone.utc)
HOLIDAYS = [("2026-08-31", "2026-09-01"), ("2026-10-26", "2026-10-30")]
WINDOW, HOL_EXT = 14, 7
REPS = [f"rep_{n}" for n in "amara farid dev lena omar sana tomas yuki".split()]


def sig(x):
    return 1 / (1 + math.exp(-x))


def in_holiday(ts: datetime) -> bool:
    d = ts.strftime("%Y-%m-%d")
    return any(a <= d <= b for a, b in HOLIDAYS)


EFFECT = 1.7   # fixtures v1 effect-size multiplier; 1.0 is the weaker first world (kept as a sensitivity run)


def true_logit(signals: dict, icp: str, effect: float = EFFECT) -> float:
    return B0 - 1.7 * (effect - 1) + effect * sum(TRUE_BETA[t] * min(u, 1.5) for t, u in signals.items()) + ICP_EFFECT[icp]


def make_accounts(n=8000, seed=7):
    rng = random.Random(seed)
    out = {}
    for i in range(1, n + 1):
        aid = f"acc-{i:04d}"
        out[aid] = {"account_id": aid, "name": f"Synthetic Co {i}", "domain": f"synco{i}.example",
                    "aliases": [f"synco{i}-group.example"] if i % 9 == 0 else [],
                    "icp": rng.choices("ABC", [30, 45, 25])[0], "owner_id": rng.choice(REPS)}
    return out


def bundle(rng):
    k = rng.choices([1, 2, 3, 4], [25, 35, 25, 15])[0]
    types, pool = [], dict(FREQ)
    for _ in range(k):
        t = rng.choices(list(pool), list(pool.values()))[0]
        types.append(t)
        pool.pop(t)
    return {t: round(rng.uniform(0.4, 2.4), 2) for t in types}


def generate(rules: dict, seed: int, weeks: int = 16, start=START, as_of=AS_OF, per_week: int = 600,
             p_holdout: float = 0.08, p_explore: float = 0.06, accounts=None, id_prefix: str = "a", effect: float = EFFECT):
    """Return dict(actions, activities, gold, unobserved). One bundle = one account-week of signals."""
    rng = random.Random(seed)
    accounts = accounts or make_accounts()
    ids = list(accounts)
    actions, acts, gold, unobserved = [], [], [], 0
    n = 0
    last_opp: dict[str, datetime] = {}
    for w in range(weeks):
        wk0 = start + timedelta(days=7 * w)
        for aid in rng.sample(ids, per_week):
            acc = accounts[aid]
            sigs = bundle(rng)
            t0 = wk0 + timedelta(days=rng.choices(range(7), [20, 20, 20, 20, 20, 2, 1])[0], hours=rng.randint(8, 17),
                                 minutes=rng.randint(0, 59))
            q = qualifies(sigs, rules, acc["icp"])
            if q:
                arm, p_w = ("holdout" if rng.random() < p_holdout else "routed"), 1 - p_holdout
            elif p_explore > 0 and rng.random() < p_explore:
                arm, p_w = "explore", p_explore
            else:
                unobserved += 1
                continue
            n += 1
            action_id = f"{id_prefix}-{n:06d}"
            crm_sig = "crm_meeting_booked" in sigs or "crm_email_reply" in sigs
            in_pipe = rng.random() < (0.30 if crm_sig else 0.03)
            if aid in last_opp and t0 - timedelta(days=60) <= last_opp[aid] < t0:
                in_pipe = True                      # an earlier opportunity on this account is still recent
            owner = acc["owner_id"]
            owner_changed = arm != "holdout" and rng.random() < 0.06
            hol = in_holiday(t0)
            z = true_logit(sigs, acc["icp"], effect)
            acted = False
            if arm in ("routed", "explore"):
                acted = rng.random() < (0.55 if hol else 0.82)
            if acted:
                z += WORK_BOOST
            if owner_changed:
                z -= 0.7
            opp = rng.random() < (0.5 if in_pipe else sig(z))
            lag = min(40, 1 + int(rng.expovariate(1 / 6)))
            if hol:
                lag += 7
            opp_ts = t0 + timedelta(days=lag, hours=rng.randint(0, 8)) if opp else None
            if opp_ts:
                last_opp[aid] = max(opp_ts, last_opp.get(aid, opp_ts))
            win = WINDOW + (HOL_EXT if hol else 0)
            matured = as_of >= t0 + timedelta(days=win)
            reason = ""
            if in_pipe:
                reason = "already_in_pipeline"
            elif owner_changed:
                reason = "owner_changed"
            elif not matured:
                reason = "window_open"
            y = int(bool(opp and lag <= win))
            gold.append({"action_id": action_id, "arm": arm, "excluded_reason": reason, "y_opp": y, "acted": int(acted),
                         "holiday": int(hol), "true_p": round(sig(true_logit(sigs, acc["icp"], effect)), 4)})
            actions.append({"action_id": action_id, "account_id": aid, "routed_at": t0, "rules_version": rules["version"],
                            "signals": sigs, "icp": acc["icp"], "owner_id": owner if arm != "holdout" else "",
                            "arm": arm, "p_worked": p_w, "open_opp_at_route": in_pipe, "score": score(sigs, rules, acc["icp"])})
            # ----- activity export rows (messy) -----
            def add(typ, ts, **kw):
                acts.append({"action_id": action_id, "account_id": aid, "type": typ, "ts": ts, "owner_id": owner, "status": "", "text": "", **kw})
            if in_pipe and rng.random() < 0.6:
                add("OPP_CREATED", t0 - timedelta(days=rng.randint(5, 50)), owner_id="", pre=True)
            if arm != "holdout":
                if acted:
                    add("TASK_COMPLETED", t0 + timedelta(hours=rng.randint(1, 100)), status=rng.choice(["done", "Done", "COMPLETED", "completed"]))
                elif rng.random() < 0.75:
                    add("TASK_CLOSED", t0 + timedelta(days=rng.randint(7, 14)), status=rng.choice(["ignored", "Expired", "skipped", "no action"]))
                if owner_changed:
                    add("OWNER_CHANGED", t0 + timedelta(days=rng.randint(1, 6)), text="owner reassigned")
            if opp:
                add("OPP_CREATED", opp_ts)
                if acted and rng.random() < 0.6:
                    add("MEETING_BOOKED", opp_ts - timedelta(days=rng.randint(0, 3)))
    # messiness is applied by evals.messify so that the clean truth stays inspectable
    return {"actions": actions, "activities": acts, "gold": gold, "unobserved": unobserved, "accounts": accounts}


def population(rules_unused, seed: int, n: int = 6000, accounts=None, effect: float = EFFECT):
    """Unbiased fresh population for the feedback-loop simulation: signal bundle + realised outcome, no routing."""
    rng = random.Random(seed)
    accounts = accounts or make_accounts()
    ids = list(accounts)
    out = []
    for _ in range(n):
        acc = accounts[rng.choice(ids)]
        s = bundle(rng)
        out.append({"signals": s, "icp": acc["icp"], "y": int(rng.random() < sig(true_logit(s, acc["icp"], effect)))})
    return out
