# AGENTS.md

Instructions for coding agents (Cursor, Codex CLI, Claude Code, Grok). Same rules as CLAUDE.md:

1. Run `python -m unittest && python -m evals.failure_suite && python run_evals.py` before and after any change.
2. No CRM write path, no auto-approve, no agent approvers. Approvers are named humans in `config/approvers.json`.
3. Never edit `data/heldout/` or `data/SPLIT.json`. Regenerating fixtures changes the hash and must be documented.
4. Keep `ruleset_change.json` deterministic (no timestamps, no random values).
5. New AI behaviour needs a validator, a deterministic fallback and a failure-suite scenario.
6. Docs: no emojis, honest status labels (designed / implemented / tested locally / mocked).
