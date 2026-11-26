# SOURCES

Patterns borrowed, never code or text. Pages were read as search-result excerpts and summaries only (I did not open full pages); LinkedIn was not inspected.

| Source | What I took (pattern) | My change | Licence |
|---|---|---|---|
| Intempt, https://intempt.com/blog/lead-scoring (read 26 Nov 2026, excerpt) | Validation on history is circular: routing decided which leads were ever worked; keep a random holdback of about 5 to 10 percent | Holdout is a first-class arm in the data contract; no holdout rows means no proposal | Not stated; quoted briefly |
| Makin AI, https://makinai.co/insights/en/ai-lead-scoring-sales-contact-selection-bias (excerpt) | Selective labels: no follow-up is not a negative; record eligible / prioritised / served / observable; bounded exploration cohort | Explore arm with logged `p_worked`; `window_open` is excluded, not scored zero | Not stated; quoted briefly |
| automate rev.ops, https://www.automaterevops.ai/post/why-do-you-need-a-holdout-group-for-lead-scoring (16 Nov 2026, excerpt; vendor content) | Random holdout of qualifying accounts, compare worked vs held-out by score band | Band check in every change set; used as a report, not as a promotion rule | Not stated |
| Datasumi, https://www.datasumi.com/blog/advanced-business-ml-closed-loop-decision-systems (excerpt) | Log assignment probability; inverse-propensity weighting | IPW with Kish effective sample size feeding the minimum-sample rule | Not stated |
| PyData Amsterdam 2026 talk abstract, https://pretalx.com/pydata-amsterdam2026/talk/WBBVBF/ | Combining a small holdout with a larger censored set (abstract only) | Not implemented; noted as a next step | n/a |
| X post by @cmyharish, https://x.com/cmyharish/status/2125794174339526898 (26 Nov 2026, text only) | Lead scoring is configured once and then not used | Motivation only | n/a |
| Newcombe (1998), Wilson (1927) intervals; Kish effective sample size | Standard statistics | Implemented from the formulas in `sofl/lift.py` | n/a |
| My own revenue-signal-router (MIT) | identity, audit chain, approval pattern, validator pattern, injection screen | Adapted and extended; parse-order bug fixed | MIT |

GitHub repository searches for signal outcome feedback and lead scoring uplift returned no results via `gh search`; that is not proof none exist.
