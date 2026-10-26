# Stage 0 model/data handoff

Inspected the trusted user-supplied `model/PROVISIONAL_full_adoption` export on 26 October 2026.

The uploaded `deployment_candidate.joblib` is adoption-enabled but uses the notebook defaults (300 trees, depth 10, minimum leaf size 2). It is not the selected tuned RF configuration (600 trees, depth 5, minimum leaf size 10, all features per split).

`scripts/verify_model_handoff.py` preserves that original export and reconstructs the selected 80/20 + five-fold-CV Random Forest from its saved prepared data, exact split and selected hyperparameters. It uses scikit-learn 1.6.1, NumPy 2.1.3 and pandas 2.2.3, matching those exported library versions. The 611 training sites and 153 test sites have disjoint coordinate groups.

The reconstructed fitted pipeline reproduced all 153 saved raw predictions within a maximum absolute difference of 1.78e-15. Original metrics were reproduced: MAE 2.6221909, RMSE 3.7671622, R² 0.4154254. Nearest-integer half-up rounding with a minimum of one yields MAE 2.6209150, replacing the previous ceiling metric for this rule.

Outputs are in `model/verified_rf80_cv5/`: evaluated_pipeline.joblib, manifest.json, and ten prediction fixtures. The artifact remains fitted on the evaluated 80% training subset, not automatically refitted on all sites. It is reconstructed from the selected experiment, not newly independently evaluated model selection.

**Status: partial handoff verified; Stage 0 is still pending original POI extraction parity.** The owner confirms a 3 km radius, but exact tag mappings, geometry handling and duplicate-merging implementation are not supplied. Do not invent these and claim they match the engineered counts. Registration-summary/lookup source hashes must remain tied to the deployed configuration. The authorised existing-plus-proposed target assumption is unchanged.

Reproduce with `uv sync --group model-validation`, then `uv run --group model-validation python scripts/verify_model_handoff.py`. Only load model files from trusted sources. The original Colab files are unchanged.
