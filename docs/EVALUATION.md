# EVALUATION

Reproduce: `python run_evals.py` (about 30 s), `python -m evals.failure_suite` (about 15 s), `python -m unittest`. Raw output: `outputs/eval_results.json`.
No API key, no network. **All data is synthetic and author-written, including the world that produces the outcomes.** These are regression checks that show the machinery recovers a known signal under confounding. They are not field accuracy and say nothing about any real account.

## What the synthetic world is
`evals/world.py` simulates 16 weeks of 600 signal bundles a week, 8,000 accounts. Each signal type has a true effect (`TRUE_BETA`). Rules v2 gets several wrong on purpose: `pricing_page_visit`, `crm_email_reply` and `webinar_attended` too high, `intent_topic_surge` too low, `docs_visit` scored though useless. Confounders: 30 percent of CRM-signal rows (3 percent of others) are already in pipeline, plus any account with an opportunity in the last 60 days; 6 percent change owner; two holiday windows delay reps by a week; some rows are too recent to have an outcome. Arms: 8 percent holdout, 6 percent explore. `evals/messify.py` then adds mixed timestamp formats, blank ids, email-only references (3 of 20 with a URL in the email field), duplicates, status spellings and blank-status notes.

## Splits and what was tuned on what
- `data/train` is weeks 1 to 11, `data/heldout` is weeks 12 to 16 (split date 2026-09-28). SHA-256 of the three held-out files are in `data/SPLIT.json`; `agent.py run` refuses to backtest if they change.
- Fixture history (honest): I rebuilt the fixtures six times while developing the generator (account pool size, repeat-account handling, effect size, base rate). Each rebuild happened before any attribution, lift or re-weighting result had been read from the held-out split. After the first weaker world gave a dev gain inside the noise, I raised the effect size (`EFFECT = 1.7`). The weak world (1.0) is kept as a sensitivity run below, so the choice is visible.
- Re-weighting settings (`change_z` 1.28, shrink 0.5, step cap 40 percent, 6 changes) were chosen on a dev cut inside train (fit on weeks 1 to 7, validate on weeks 8 to 11). The shipped held-out split was then evaluated with the frozen design. It failed the gate on that first look, and I did not change the design afterwards (later edits were the connector, tests and docs). I have re-run it several times since; the output is identical.
- Notes for the disposition classifier: set A (32 notes) was written before the classifier; set B (10 notes) after, to probe it. Same author, so neither is blind.

## Results

### 1. Parse-order bug (identity)
| | cases passed |
|---|---|
| slice-1 `norm_host` | 23 / 40 |
| v2 `norm_host` | 40 / 40 |
The 40 cases are author-written; the first 8 are the known failure and near neighbours, so the slice-1 score is expected to be low. Sample `user@https://WWW.iris.example./pricing` now resolves to `iris.example`.

### 2. Attribution against the gold file
| | train | held-out |
|---|---|---|
| confounded rows (in pipeline, owner change) kept out | 596 / 633 | 309 / 337 |
| clean rows wrongly excluded | 46 / 2284 | 16 / 762 |
| label agreement on rows both treat as eligible | 2218 / 2238 | 734 / 746 |
| naive baseline label agreement (fixed window, exact join, no exclusions) | 2162 / 2284 | 708 / 762 |
| naive rows that are confounded or immature yet kept for training | 633 | 527 |
| rep action known / correct when known | 2545 of 2704 / 2545 | 1129 of 1195 / 1129 |
Rep-action correctness is 100 percent partly because the dev note templates are the same family as the classifier rules; see section 7.
The 46 false exclusions are mostly the 60-day look-back catching a genuinely earlier opportunity on a repeat account that the generator did not mark.

### 3. Lift estimator versus the known truth (train, Spearman of estimated lift against true effect)
exclusions + IPW 0.970; exclusions without IPW 0.924; IPW without exclusions 0.933; naive raw conversion 0.959; v2 weights for reference 0.922. This is a small separation and I would not claim more than "no worse". The AUC results below are more discriminating.

### 4. Held-out backtest on the shipped split (weighted AUC; explore rows weigh 1/p_worked)
| ruleset | AUC | capture of opportunities in top 30 percent | precision at route threshold | recall at route threshold |
|---|---|---|---|---|
| rules.v2 | 0.8101 | 0.6627 | 0.3380 | 0.7833 |
| rules.v3 (5 weights changed) | 0.8139 | 0.6533 | 0.3613 | 0.7411 |
| raw-conversion re-weight | 0.7408 | 0.5818 | 0.2955 | 0.7638 |
v3 minus v2 AUC: +0.0038, 95 percent paired bootstrap interval -0.0184 to +0.0258. **The gate failed**, so this change set cannot be approved. Raw conversion minus v2: -0.0693 (-0.1097 to -0.0360).
Routed versus holdout by v2 score band (train): 25 to 40 unproven (n 1200 / 103), 40 to 60 unproven (560 / 59), 60 and above routing helps (145 / 11, small holdout).

### 5. Ten other synthetic worlds (seeds 1 to 10, fixed before looking), same code and settings
| effect size | gate passed | v3 beats v2 | v3 beats raw conversion | raw conversion below v2 | median AUC gain v3 vs v2 | median AUC gain raw vs v2 |
|---|---|---|---|---|---|---|
| 1.7 (shipped) | 8 / 10 | 9 / 10 | 10 / 10 | 9 / 10 | +0.0126 | -0.0517 |
| 1.0 (weak) | 4 / 10 | 9 / 10 | 9 / 10 | 8 / 10 | +0.0133 | -0.0405 |
Reading: the gain over v2 is small and often inside noise; the gate is doing its job (it refused 2 of 10 strong worlds and 6 of 10 weak ones). The consistent result is that re-weighting by raw conversion hurts. Per-world numbers are in `outputs/eval_results.json`. The shipped fixture (seed 20261126) is one of the failing draws, which is why it is the default demo.

### 6. Feedback-loop simulation (5 seeds, 3 rounds, fresh unbiased population, AUC)
| round | raw-conversion loop (no explore, no holdout) | this loop (exclusions, IPW, explore) |
|---|---|---|
| 0 (rules.v2) | 0.8388 | 0.8388 |
| 1 | 0.7970 | 0.8535 |
| 2 | 0.8089 | 0.8642 |
| 3 | 0.8073 | 0.8650 |
Weight rank agreement with truth was 0.92 for v2 and stays between 0.92 and 0.98 for both loops, so it does not discriminate; AUC does. This simulation has no human gate: it shows what the estimator does when every proposal is accepted.

### 7. Free-text note classifier (the only AI step)
| set | notes | rules classifier correct | wrong but confident | keyword baseline correct |
|---|---|---|---|---|
| A, written before the classifier (includes 3 injected notes) | 32 | 32 | 0 | 14 |
| B, unseen phrasings, written after | 10 | 2 | 2 | 2 |
Set B shows the rules classifier misses paraphrases (it answers unclear for most, which is safe: the row's rep-action stays unknown). Two answers were wrong and confident ("Firm no from the VP, will not revisit" came back deferred; "Voicemail left, then they emailed back to book a slot on Monday" came back contacted_no_reply). That gap is what a model is for, behind the validator.
Scripted fake model over all 42 notes (modes rotate: valid, fabricated quote, code not allowed, prose, timeout): 10 accepted from the model, 28 fell back to rules, 4 injected notes quarantined, 0 injected notes sent to the model. This is a scripted double, not Claude.

### 8. Failure suite and unit tests
25 / 25 failure scenarios and 37 / 37 unit tests pass (`outputs/failure_suite_report.md`). Scenarios cover 429 Retry-After, 5xx backoff, crash and resume (byte-identical), a half-written page, stale snapshot once and twice, write attempts, malformed pages, agent and unknown approvers, wrong and short hashes, edited change set, edited candidate rules, expired TTL, tampered approvals log, gate-failed approval, edited held-out file, missing holdout, minimum sample, prompt injection, fabricated quotes, 429 from the model, dead letters, audit tamper and determinism.

## Limitations
- The simulation knows the truth because I wrote it. Real signals interact, decay and drift in ways it does not model.
- Marginal lift: when signals co-occur they share credit. A joint model would be sharper and I did not build one.
- Held-out holdout is small (55 eligible rows), so the routed-versus-holdout band check is weak, especially above score 60.
- The gain of v3 over v2 is modest and inside noise in several worlds. The tool is conservative by design; it is not a lift machine.
- Recency decay, thresholds and capacity are not re-tuned. Threshold changes would be a separate change set.
