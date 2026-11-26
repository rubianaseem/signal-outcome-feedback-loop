# DETAILS

## API-cost assumptions (no account or billing access was used)
Only the optional note classifier calls a model, and only for notes whose task status is blank. I have not looked at any billing page, so I give token arithmetic, not prices.
- One call is about 150 input tokens (instruction plus note) and about 40 output tokens: roughly 190 tokens.
- In the synthetic fixtures 336 notes needed classification across train and held-out (226 and 110), so about 64,000 tokens per full run.
- Cost = tokens x your model's current per-million-token price (check the provider's pricing page). Retries multiply cost; the retry budget is 3 attempts.
- Without a key the cost is zero and the rules classifier answers.
Everything else is local Python.

## Stack-swap table
| Piece | Here | Swap to |
|---|---|---|
| Source | MOCK HubSpot/Salesforce class | read-only HubSpot CRM API or Salesforce REST/SOQL; keep `ReadOnlyClient` and `sync()` |
| Warehouse | CSV files | tables in BigQuery, Snowflake or DuckDB with the same columns (docs/DATA_CONTRACTS.md) |
| Orchestration | CLI | n8n, Airflow or a scheduled job that runs `run` and posts the report |
| Review | terminal `show` and `approve` | pull request on the rules file, with the SHA-256 in the PR description |
| Model | optional Claude via `sofl/llm.py` | any client with `complete(system, user)` |
| Approval store | `approvals.jsonl` | your ticketing or change-management system, keeping the hash binding |

## Customise for your stack
1. Map your export to the two contracts; write the mapping in a small adapter that outputs the CSV headers.
2. Make the router log `arm` and `p_worked`. This is the one change that cannot be faked afterwards.
3. Set `window_days` to about your median time from first signal to opportunity; set holidays; decide whether a CRM-flag-only pre-existing check is enough.
4. Add exclusions that matter to you (lead-source changes, territory reassignments, campaign blackout) in `sofl/attribution.py` with a unit test each.
5. Start `max_changes` and `shrink` low. Let two cycles pass before widening.

## What production would add (honest gaps)
- Real connector: OAuth, scopes review, field-level security, incremental sync by modified date, schema drift detection, real rate-limit headers per vendor. Only the mock is tested.
- A randomised holdout and explore sample agreed with sales leadership, with a plain statement of the cost (a few withheld qualifying accounts per quarter).
- Per-segment windows and a joint (multivariable) model; today lift is marginal.
- Outcome definitions beyond opportunity creation (stage progression, pipeline value, closed-won) with longer maturity windows.
- Drift monitoring on the weights and on rep ignore rates; scheduled re-runs; rollback to rules.v2 as a one-file revert.
- PII handling review: logs here hold ids and pseudonymous hashes, not raw emails (`pii_hash` with your own salt), but I have not done a legal review.
- Concurrency and multi-tenant isolation. The CLI is single-user.
- Live testing of the Claude path. It is only exercised with a scripted fake model.
