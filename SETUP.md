# SETUP

## 1. Environment
```bash
python3 --version                       # 3.10 or newer
python3 -m venv .venv && source .venv/bin/activate
python -m unittest                      # 37 tests, about 1 second
```
Offline mode needs no packages and no API key.

## 2. Sample runs
```bash
python agent.py attribute               # 8-row edge-case samples: dead letters, exclusions, holiday window, quarantined note
python agent.py run                     # shipped synthetic fixtures; the gate fails on the held-out split and says so
python agent.py show                    # report plus the hash to approve
python run_demo.py                      # full approve and release flow on a synthetic world that passes the gate
python agent.py sync --flavour salesforce --crash-after-pages 3   # read-only mock connector with 429s and a crash/resume
```
`sample_*.csv` are hand-written synthetic edge cases (comma decimal, unknown signal type, duplicate rows, epoch-ms timestamps,
`user@https://...` email values, an injected note). `data/` holds the larger generated fixtures.

## 3. Optional: Claude for free-text notes
```bash
pip install -r requirements-optional.txt
export ANTHROPIC_API_KEY=...            # never commit it
python agent.py run
```
The model only proposes `{"code", "quote"}` for notes with a blank task status. A code outside the allowed set or a quote that is not in the note is rejected and the rules classifier answers instead. Tested here only with a scripted fake model, not live Claude.

## 4. Real data sources (not done in this repo)
1. Export two tables from HubSpot or Salesforce: routed actions (one row per alert with score, signal units, arm, `p_worked`) and activities (tasks, meetings, opportunity creation, owner changes). Map columns to docs/DATA_CONTRACTS.md.
2. The routing system must log the probability a row was worked (`p_worked`) and keep a random holdout (about 5 to 10 percent of qualifying rows) plus a small explore sample below threshold. Without both, the tool refuses to propose.
3. A real connector needs a private app or connected app with read-only scopes (HubSpot CRM objects read, Salesforce API read). Replace `MockSource` with a class that issues GETs; keep `ReadOnlyClient` and `sync()` as they are.
4. Set `SOFL_PII_SALT`. Put holidays, window length and cycle assumptions in `config/feedback.yaml`, and review them like code.

## 5. Extending with coding agents
Point Cursor, Claude Code, Codex CLI or Grok at AGENTS.md. Good first tasks: a new exclusion rule (add a unit test and a failure-suite case), a new outcome type, a second attribution window per segment. Do not let an agent weaken the approval module.

## 6. Troubleshooting
- `REFUSED: ... changed after the split was hashed`: you edited `data/heldout/`. Restore it from git.
- `gate=FAILED`: the proposal did not beat rules.v2 on the held-out split with a clear margin. That is a valid result.
- `holdout has N eligible rows`: your export has no (or too few) holdout rows.
- Everything lands in `unknown_account` dead letters: `account_id` casing or a different id scheme; see `outputs/*/dead_letters.json`.
- `approval expired`: re-run `approve`; TTL is `approval_ttl_hours` in `config/approvers.json`.
