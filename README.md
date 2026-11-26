# signal-outcome-feedback-loop

**Routed signals tell you what the rules guessed. Rep outcomes tell you what was true. This repo closes that loop without letting the loop teach itself its own mistakes.**

Built by Rubia Naseem, GTM Engineer (12+ yrs CRM/RevOps, HubSpot & Salesforce).

This is slice 2 of my [revenue-signal-router](https://github.com/rubianaseem/revenue-signal-router). Slice 1 routes signals with versioned weights. This one reads what reps did next, works out which signal types earned their weight, and proposes `rules.v3` as a reviewed diff.

## The problem

Weights get set once during implementation and never revisited. When someone does revisit them, the usual move is "re-weight by raw conversion", and that is circular. Two public write-ups say it plainly:

> "A lead that nobody contacted had a structurally lower chance of converting no matter how good a prospect it was." (Intempt, [lead scoring validation](https://intempt.com/blog/lead-scoring))

> "A lead that never received meaningful follow-up is not a negative label; its outcome is unobserved." (Makin AI, [selection bias in lead scoring](https://makinai.co/insights/en/ai-lead-scoring-sales-contact-selection-bias))

Raw conversion also counts deals already in pipeline, owner changes and holiday delays as if the signal caused them.

## What it does

- Reads routed actions plus messy CRM activity exports (mixed timestamp formats, blank ids, duplicates, email-only references) and attributes each outcome with an attribution window, a holiday extension and named exclusions.
- Estimates lift per signal type with intervals, a minimum-sample rule and inverse-propensity weights, using a random holdout and an explore arm.
- Proposes `rules.v3` as a small, capped diff and backtests it on a time split that was hashed before tuning, against `rules.v2` and a raw-conversion baseline.
- Fixes the slice-1 parse-order bug (`user@https://WWW.iris.example./pricing` became the host `https`) with a 40-case v2 set.
- Pulls activity through a read-only mock HubSpot and Salesforce connector (pagination, 429 and Retry-After, cursor resume, stale-snapshot detection).
- Optional AI step: classify free-text rep notes into outcome codes behind a validator that needs a verbatim quote.

## Where each step runs

1. GitHub stores the code, synthetic data and docs.
2. Your terminal (or Cursor's) runs everything: `python agent.py run`.
3. Optional: if `ANTHROPIC_API_KEY` is set, Claude classifies notes, but only through `sofl/disposition.py`, whose validator decides what is accepted.
4. In real tools, the reviewed output is a rules file a human applies to HubSpot or Salesforce scoring. Nothing here does that for you.
5. Writes: only local files under `outputs/`. There is no CRM write path. The connector has no write verbs.

## Guardrails and human in the loop

- Approval is bound to the SHA-256 of `ruleset_change.json`; editing it or the candidate rules voids the approval.
- A named human is required. Agent, model and service identities are refused. Approvals expire after 48 hours. There is no auto-approve flag.
- A change set that fails the held-out backtest gate cannot be approved. No holdout rows means no proposal.
- Rep notes with instruction-like text are quarantined and never reach a model. The audit trail is hash-chained.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate   # nothing to install for offline mode
python run_demo.py                  # gate fails on shipped data, then a passing synthetic world, approval and release
python run_evals.py                 # every number below (about 30 seconds)
python -m evals.failure_suite       # 25 failure injections
python -m unittest                  # 37 tests
```

## Example output

Shipped held-out split (synthetic): the gate **fails** and the tool says so.

```
run run-6891a55c4f04  gate=FAILED  weights_changed=5
REFUSED: the backtest gate failed for this change set; it cannot be approved
```

| ruleset | AUC | gain vs v2 (95% interval) |
|---|---|---|
| rules.v2 | 0.8101 | |
| rules.v3 | 0.8139 | +0.0038 (-0.0184 to +0.0258) |
| raw-conversion re-weight | 0.7408 | -0.0693 (-0.1097 to -0.0360) |

Across 10 other synthetic worlds: v3 beat v2 in 9 and cleared the gate in 8; raw conversion fell below v2 in 9. With weaker effects the gate cleared in 4 of 10. Over three feedback rounds the raw-conversion loop went 0.839 to 0.807 AUC while this loop went to 0.865. Attribution kept 309 of 337 confounded held-out rows out of training. Details and caveats: [docs/EVALUATION.md](docs/EVALUATION.md).

## How this runs today (and what production would add)

Implemented and tested locally on synthetic, author-written data. The Claude path is tested with a scripted fake model only. The connector talks to a mock. Production would need real read-only OAuth scopes, a real randomised holdout agreed with sales leadership, outcome windows tuned to your cycle length and a PR-based rules release. See [docs/DETAILS.md](docs/DETAILS.md).

## More links

[revenue-signal-router](https://github.com/rubianaseem/revenue-signal-router) (slice 1) | [gtm-agent-eval-harness](https://github.com/rubianaseem/gtm-agent-eval-harness) | [agent-decision-log](https://github.com/rubianaseem/agent-decision-log) | [deal-evidence-engine](https://github.com/rubianaseem/deal-evidence-engine) | [SETUP.md](SETUP.md) | [SOURCES.md](SOURCES.md) | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
