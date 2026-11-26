# Change set run-6891a55c4f04: rules.v2 -> rules.v3

SHA-256 of ruleset_change.json: `6891a55c4f0462151aaa394974bfa376d4cc5becfb95abe40f3d84e21cc23558`

Backtest gate: **FAILED**. Synthetic data; these are regression numbers, not field accuracy.

## Proposed weight changes

- docs_visit: weight 3 -> 2, cap 6 -> 4
- intent_topic_surge: weight 10 -> 14, cap 20 -> 28
- pricing_page_visit: weight 14 -> 9, cap 28 -> 18
- product_signup: weight 15 -> 10, cap 30 -> 20
- webinar_attended: weight 6 -> 4, cap 12 -> 8

## Held-out backtest (time split, hashed before tuning)

| ruleset | AUC | capture top 30% | precision at route | recall at route |
|---|---|---|---|---|
| rules.v2 | 0.8101 | 0.6627 | 0.338 | 0.7833 |
| rules.v3 | 0.8139 | 0.6533 | 0.3613 | 0.7411 |
| naive_raw_conversion | 0.7408 | 0.5818 | 0.2955 | 0.7638 |

v3 AUC gain over v2: 0.0038 (95% bootstrap interval [-0.0184, 0.0258]).

## Lift per signal type (train, inverse-propensity weighted)

| signal | lift | 95% interval | effective n with/without | enough evidence |
|---|---|---|---|---|
| pricing_page_visit | +0.020 | -0.049 to +0.095 | 191.9/339.0 | True |
| demo_page_visit | +0.133 | +0.041 to +0.235 | 99.2/413.9 | True |
| docs_visit | -0.099 | -0.163 to -0.024 | 149.6/353.5 | True |
| blog_visit | -0.107 | -0.171 to -0.033 | 158.2/345.4 | True |
| product_signup | +0.027 | -0.046 to +0.109 | 146.2/393.2 | True |
| product_usage_spike | +0.157 | +0.072 to +0.247 | 132.3/400.4 | True |
| seat_limit_reached | +0.304 | +0.166 to +0.442 | 50.2/473.9 | False |
| intent_topic_surge | +0.181 | +0.101 to +0.263 | 164.9/359.8 | True |
| webinar_attended | -0.096 | -0.161 to -0.014 | 114.1/389.8 | True |
| crm_meeting_booked | +0.201 | +0.078 to +0.337 | 54.9/454.7 | False |
| crm_email_reply | -0.008 | -0.087 to +0.091 | 90.8/414.7 | True |
| hiring_gtm_ops | +0.072 | -0.028 to +0.195 | 64.6/438.7 | True |
| evaluating_alternatives | +0.331 | +0.182 to +0.477 | 42.7/461.0 | False |
| budget_confirmed | +0.331 | +0.149 to +0.508 | 27.1/477.6 | False |

## Routing versus holdout by score band (train)

- 25-40: unproven (routed 0.233, holdout 0.194, n 1200/103)
- 40-60: unproven (routed 0.441, holdout 0.356, n 560/59)
- 60-101: routing_helps (routed 0.772, holdout 0.364, n 145/11)

## Limitations

- synthetic and author-written data
- recency decay is not re-tuned
- marginal lift: co-occurring signals share credit
- rows below threshold that were not explored have no outcome in the export (handled by the explore arm, not by assumption)
