# Change set run-ba327e4178b6: rules.v2 -> rules.v3

SHA-256 of ruleset_change.json: `ba327e4178b681b2dbf266d74ab3cd52f9bfe853ac6f1e62d0010264835c4f3f`

Backtest gate: **PASSED**. Synthetic data; these are regression numbers, not field accuracy.

## Proposed weight changes

- crm_email_reply: weight 9 -> 5, cap 18 -> 10
- docs_visit: weight 3 -> 2, cap 6 -> 4
- intent_topic_surge: weight 10 -> 14, cap 20 -> 28
- pricing_page_visit: weight 14 -> 8, cap 28 -> 16
- webinar_attended: weight 6 -> 4, cap 12 -> 8

## Held-out backtest (time split, hashed before tuning)

| ruleset | AUC | capture top 30% | precision at route | recall at route |
|---|---|---|---|---|
| rules.v2 | 0.7798 | 0.6709 | 0.3522 | 0.758 |
| rules.v3 | 0.8118 | 0.6912 | 0.405 | 0.7406 |
| naive_raw_conversion | 0.7409 | 0.5846 | 0.2965 | 0.8228 |

v3 AUC gain over v2: 0.032 (95% bootstrap interval [0.0108, 0.0542]).

## Lift per signal type (train, inverse-propensity weighted)

| signal | lift | 95% interval | effective n with/without | enough evidence |
|---|---|---|---|---|
| pricing_page_visit | +0.010 | -0.059 to +0.084 | 198.4/309.6 | True |
| demo_page_visit | +0.085 | -0.004 to +0.186 | 98.4/395.0 | True |
| docs_visit | -0.066 | -0.134 to +0.013 | 148.6/335.9 | True |
| blog_visit | -0.077 | -0.144 to -0.000 | 150.0/334.5 | True |
| product_signup | +0.101 | +0.023 to +0.185 | 152.7/370.5 | True |
| product_usage_spike | +0.165 | +0.079 to +0.256 | 132.9/380.7 | True |
| seat_limit_reached | +0.292 | +0.142 to +0.444 | 40.6/452.1 | False |
| intent_topic_surge | +0.196 | +0.114 to +0.280 | 156.6/338.0 | True |
| webinar_attended | -0.073 | -0.142 to +0.014 | 105.8/380.8 | True |
| crm_meeting_booked | +0.280 | +0.145 to +0.419 | 50.5/437.0 | False |
| crm_email_reply | -0.048 | -0.123 to +0.050 | 86.5/402.7 | True |
| hiring_gtm_ops | +0.126 | +0.009 to +0.266 | 51.5/433.7 | False |
| evaluating_alternatives | +0.322 | +0.170 to +0.472 | 40.7/447.3 | False |
| budget_confirmed | +0.426 | +0.275 to +0.559 | 44.9/456.4 | False |

## Routing versus holdout by score band (train)

- 25-40: unproven (routed 0.243, holdout 0.194, n 1167/124)
- 40-60: unproven (routed 0.466, holdout 0.364, n 596/66)
- 60-101: unproven (routed 0.768, holdout 0.909, n 125/11)

## Limitations

- synthetic and author-written data
- recency decay is not re-tuned
- marginal lift: co-occurring signals share credit
- rows below threshold that were not explored have no outcome in the export (handled by the explore arm, not by assumption)
