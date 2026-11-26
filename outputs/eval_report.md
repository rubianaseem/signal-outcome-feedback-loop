# Eval report (synthetic, author-written data; regression checks, not field accuracy)

```json
{
 "attribution": {
  "heldout": {
   "clean_rows": 762,
   "clean_rows_wrongly_excluded": 16,
   "confounded_rows_in_gold": 337,
   "confounders_excluded": 309,
   "dead_letters": 58,
   "label_agreement": "734/746",
   "naive_confounded_or_immature_rows_kept_as_training_rows": 527,
   "naive_label_agreement_on_gold_eligible": "708/762",
   "notes_classified": 110,
   "rep_action_correct_when_known": "1129/1129",
   "rep_action_known": "1129/1195",
   "rows": 1289
  },
  "train": {
   "clean_rows": 2284,
   "clean_rows_wrongly_excluded": 46,
   "confounded_rows_in_gold": 633,
   "confounders_excluded": 596,
   "dead_letters": 51,
   "label_agreement": "2218/2238",
   "naive_confounded_or_immature_rows_kept_as_training_rows": 633,
   "naive_label_agreement_on_gold_eligible": "2162/2284",
   "notes_classified": 226,
   "rep_action_correct_when_known": "2545/2545",
   "rep_action_known": "2545/2704",
   "rows": 2917
  }
 },
 "disposition": {
  "held-out A (written before the classifier)": {
   "keyword_baseline_correct": 14,
   "notes": 32,
   "rules_correct": 32,
   "rules_wrong_but_confident": 0
  },
  "probe B (written after, unseen phrasings)": {
   "keyword_baseline_correct": 2,
   "notes": 10,
   "rules_correct": 2,
   "rules_wrong_but_confident": 2
  },
  "scripted model run over all 42 notes": {
   "injection_notes_sent_to_model": 0,
   "model_calls": 47,
   "sources": {
    "fallback": 28,
    "model": 10,
    "quarantine": 4
   }
  }
 },
 "estimator_rank_agreement_with_truth": {
  "IPW, no exclusions": 0.933,
  "exclusions, no IPW": 0.924,
  "naive raw conversion rate": 0.959,
  "v2 weights (for reference)": 0.922,
  "v3 estimator (exclusions + IPW)": 0.97
 },
 "identity_parse": {
  "cases": 40,
  "slice1_v1_pass": 23,
  "v2_failures": [],
  "v2_pass": 40
 },
 "multi_world_effect_1.0_weak": {
  "effect": 1.0,
  "gate_passed": 4,
  "median_auc_gain_naive_vs_v2": -0.0405,
  "median_auc_gain_v3_vs_v2": 0.0133,
  "naive_below_v2": 8,
  "per_world": [
   {
    "auc_naive": 0.7302,
    "auc_v2": 0.703,
    "auc_v3": 0.7239,
    "gain_ci_low": -0.014,
    "gate": false,
    "seed": 1,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.689,
    "auc_v2": 0.7231,
    "auc_v3": 0.7386,
    "gain_ci_low": -0.005,
    "gate": false,
    "seed": 2,
    "weights_changed": 2
   },
   {
    "auc_naive": 0.7281,
    "auc_v2": 0.772,
    "auc_v3": 0.7976,
    "gain_ci_low": 0.0047,
    "gate": true,
    "seed": 3,
    "weights_changed": 3
   },
   {
    "auc_naive": 0.6412,
    "auc_v2": 0.6261,
    "auc_v3": 0.6477,
    "gain_ci_low": -0.011,
    "gate": false,
    "seed": 4,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.6297,
    "auc_v2": 0.6908,
    "auc_v3": 0.7018,
    "gain_ci_low": -0.0016,
    "gate": true,
    "seed": 5,
    "weights_changed": 4
   },
   {
    "auc_naive": 0.791,
    "auc_v2": 0.8599,
    "auc_v3": 0.8651,
    "gain_ci_low": -0.0128,
    "gate": false,
    "seed": 6,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.7789,
    "auc_v2": 0.832,
    "auc_v3": 0.8383,
    "gain_ci_low": -0.0027,
    "gate": true,
    "seed": 7,
    "weights_changed": 6
   },
   {
    "auc_naive": 0.6889,
    "auc_v2": 0.755,
    "auc_v3": 0.7707,
    "gain_ci_low": -0.0032,
    "gate": true,
    "seed": 8,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.7622,
    "auc_v2": 0.7993,
    "auc_v3": 0.8057,
    "gain_ci_low": -0.0207,
    "gate": false,
    "seed": 9,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.714,
    "auc_v2": 0.7293,
    "auc_v3": 0.7286,
    "gain_ci_low": -0.0297,
    "gate": false,
    "seed": 10,
    "weights_changed": 5
   }
  ],
  "v3_beats_naive": 9,
  "v3_beats_v2": 9,
  "worlds": 10
 },
 "multi_world_effect_1.7": {
  "effect": 1.7,
  "gate_passed": 8,
  "median_auc_gain_naive_vs_v2": -0.0517,
  "median_auc_gain_v3_vs_v2": 0.0126,
  "naive_below_v2": 9,
  "per_world": [
   {
    "auc_naive": 0.7418,
    "auc_v2": 0.7738,
    "auc_v3": 0.7788,
    "gain_ci_low": -0.024,
    "gate": false,
    "seed": 1,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.7409,
    "auc_v2": 0.7798,
    "auc_v3": 0.8118,
    "gain_ci_low": 0.0108,
    "gate": true,
    "seed": 2,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.6488,
    "auc_v2": 0.7424,
    "auc_v3": 0.7734,
    "gain_ci_low": 0.0136,
    "gate": true,
    "seed": 3,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.7807,
    "auc_v2": 0.8223,
    "auc_v3": 0.8307,
    "gain_ci_low": -0.004,
    "gate": true,
    "seed": 4,
    "weights_changed": 4
   },
   {
    "auc_naive": 0.747,
    "auc_v2": 0.7455,
    "auc_v3": 0.7554,
    "gain_ci_low": -0.0026,
    "gate": true,
    "seed": 5,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.7503,
    "auc_v2": 0.8211,
    "auc_v3": 0.8446,
    "gain_ci_low": 0.0065,
    "gate": true,
    "seed": 6,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.84,
    "auc_v2": 0.8948,
    "auc_v3": 0.907,
    "gain_ci_low": -0.0015,
    "gate": true,
    "seed": 7,
    "weights_changed": 5
   },
   {
    "auc_naive": 0.7308,
    "auc_v2": 0.7988,
    "auc_v3": 0.8117,
    "gain_ci_low": 0.0005,
    "gate": true,
    "seed": 8,
    "weights_changed": 6
   },
   {
    "auc_naive": 0.7913,
    "auc_v2": 0.8571,
    "auc_v3": 0.8529,
    "gain_ci_low": -0.0247,
    "gate": false,
    "seed": 9,
    "weights_changed": 4
   },
   {
    "auc_naive": 0.7551,
    "auc_v2": 0.8036,
    "auc_v3": 0.8317,
    "gain_ci_low": 0.0093,
    "gate": true,
    "seed": 10,
    "weights_changed": 5
   }
  ],
  "v3_beats_naive": 10,
  "v3_beats_v2": 9,
  "worlds": 10
 },
 "selection_bias_loop_sim": {
  "naive": [
   {
    "auc": 0.8388,
    "round": 0,
    "spearman_weights_vs_truth": 0.922
   },
   {
    "auc": 0.797,
    "round": 1,
    "spearman_weights_vs_truth": 0.921
   },
   {
    "auc": 0.8089,
    "round": 2,
    "spearman_weights_vs_truth": 0.984
   },
   {
    "auc": 0.8073,
    "round": 3,
    "spearman_weights_vs_truth": 0.978
   }
  ],
  "sofl": [
   {
    "auc": 0.8388,
    "round": 0,
    "spearman_weights_vs_truth": 0.922
   },
   {
    "auc": 0.8535,
    "round": 1,
    "spearman_weights_vs_truth": 0.918
   },
   {
    "auc": 0.8642,
    "round": 2,
    "spearman_weights_vs_truth": 0.919
   },
   {
    "auc": 0.865,
    "round": 3,
    "spearman_weights_vs_truth": 0.918
   }
  ]
 },
 "shipped_heldout_backtest": {
  "gate_passed": false,
  "naive_raw_conversion": {
   "auc": 0.7408,
   "auc_gain_ci95": [
    -0.1097,
    -0.036
   ],
   "auc_gain_vs_ref": -0.0693,
   "capture_top30": 0.5818,
   "route_precision": 0.2955,
   "route_recall": 0.7638,
   "routed_share": 0.4783
  },
  "routing_vs_holdout_train": [
   {
    "band": "25-40",
    "diff": 0.038,
    "hi": 0.108,
    "holdout_rate": 0.194,
    "lo": -0.051,
    "n_holdout": 103,
    "n_routed": 1200,
    "routed_rate": 0.233,
    "verdict": "unproven"
   },
   {
    "band": "40-60",
    "diff": 0.085,
    "hi": 0.203,
    "holdout_rate": 0.356,
    "lo": -0.049,
    "n_holdout": 59,
    "n_routed": 560,
    "routed_rate": 0.441,
    "verdict": "unproven"
   },
   {
    "band": "60-101",
    "diff": 0.409,
    "hi": 0.629,
    "holdout_rate": 0.364,
    "lo": 0.116,
    "n_holdout": 11,
    "n_routed": 145,
    "routed_rate": 0.772,
    "verdict": "routing_helps"
   }
  ],
  "rules.v2": {
   "auc": 0.8101,
   "capture_top30": 0.6627,
   "route_precision": 0.338,
   "route_recall": 0.7833,
   "routed_share": 0.4287
  },
  "rules.v3": {
   "auc": 0.8139,
   "auc_gain_ci95": [
    -0.0184,
    0.0258
   ],
   "auc_gain_vs_ref": 0.0038,
   "capture_top30": 0.6533,
   "route_precision": 0.3613,
   "route_recall": 0.7411,
   "routed_share": 0.3794
  },
  "weights_changed": [
   "docs_visit",
   "intent_topic_surge",
   "pricing_page_visit",
   "product_signup",
   "webinar_attended"
  ]
 }
}
```
