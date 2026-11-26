# CLAUDE.md

signal-outcome-feedback-loop: closed-loop outcome feedback for signal routing (slice 2 of revenue-signal-router). Python standard library only. Synthetic data only.

## Commands
- `python run_demo.py` end-to-end demo; `python run_evals.py`; `python -m evals.failure_suite`; `python -m unittest`
- `python agent.py run | show | approve | release | verify-audit | attribute | sync`

## Rules you must keep
- Nothing in this repo writes to a CRM. Do not add a write path, a write verb to `ReadOnlyClient`, or a flag that skips approval.
- `ruleset_change.json` is hashed; approvals bind to that hash. Do not make its content depend on time or randomness.
- `data/heldout/*` is hash-locked in `data/SPLIT.json`. Never tune on it. Change thresholds only by looking at `data/train` (or a dev cut inside it) and record the change in docs/EVALUATION.md.
- Report only numbers that `run_evals.py`, `evals/failure_suite.py` or the tests print. Say "synthetic" and "scripted fake model" where true.
- No emojis in code, docs or commit messages. README stays under 900 words (target about 700).
- AI is used only in `sofl/disposition.py`, behind `validate()` (code in the allowed set, quote is a verbatim span). Keep injection screening before any model call.
