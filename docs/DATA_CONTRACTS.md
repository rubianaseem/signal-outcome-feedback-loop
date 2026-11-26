# DATA CONTRACTS

All shipped data is SYNTHETIC. Headers are fixed; unknown extra columns are ignored; a row with more fields than headers is dead-lettered (`column_count_mismatch`).

## routed_actions.csv (one row per alert the router produced or withheld)
| column | type | rules |
|---|---|---|
| action_id | string | required; identical duplicates are dropped, conflicting duplicates dead-lettered |
| account_id | string | must exist in accounts.csv (case-insensitive) |
| routed_at | timestamp | ISO with Z or offset, naive `YYYY-MM-DD HH:MM:SS` (read as UTC), epoch seconds or milliseconds |
| rules_version | string | `rules.v2` or `v2`; normalised and counted |
| score | number | score at routing time |
| signals | string | `type:units;type:units`, units are recency-decayed counts at routing time; comma decimals allowed; unknown types dropped and counted; negative or non-numeric rejects the row |
| icp_tier | A/B/C | blank falls back to accounts.csv |
| owner_id | string | blank for holdout rows |
| arm | routed / holdout / explore | `control` is read as holdout; case and spaces ignored; anything else dead-lettered |
| p_worked | number in (0, 1] | probability this row would be worked; required for weighting |
| open_opp_at_route | true / false / blank | blank is unknown, not false |

## crm_activities.csv (HubSpot engagement or Salesforce activity export, normalised)
`activity_id, action_id, account_id, contact_email, type, ts, owner_id, status, text`
- `type`: TASK_COMPLETED, TASK_CLOSED, TASK_UPDATED, MEETING_BOOKED, OPP_CREATED, OWNER_CHANGED.
- A row needs `account_id` or `contact_email`. Email values may be wrapped (`Name <a@b>`, `mailto:`, `a@https://host/path`); the host is parsed with the v2 parser. Personal-domain and unknown-domain references are dead-lettered, never guessed.
- `action_id` may be blank: the row then links to the latest action on the same account routed at or before it.
- `status` spellings are case-insensitive; a blank status with a note goes to the disposition classifier.
- Future-dated rows (after `as_of`) are dead-lettered. A row dated before its action is ignored for labelling and counted.

## accounts.csv
`account_id, domain, domain_aliases (semicolon list), icp_tier, owner_id`

## Attributed row (internal)
`action_id, account_id, arm, signals, icp, routed_at, p_worked, excluded_reason, y, acted, holiday`
`excluded_reason`: empty, `already_in_pipeline`, `owner_changed`, `window_open`. `y` is opportunity created within the window. `acted` is true, false or unknown.

## ruleset_change.json (the approved artifact)
`from_version, to_version, diff[], decisions[], evidence, lift[], routing_vs_holdout_by_score_band[], backtest_heldout, gate{passed,rule,problems}, candidate_rules_sha256, base_rules_sha256, feedback_config_sha256, as_of, heldout_sha256, limitations[]`. Contains no timestamps or random values, so two runs on the same inputs give the same SHA-256.

## Outcome codes (notes)
meeting_booked, contacted_no_reply, not_interested, wrong_contact, deferred, not_actioned, unclear.
