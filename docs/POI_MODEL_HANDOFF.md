# Full 1 km POI/category/state model handoff audit

Checked the user-provided poi_category_state_1km_full.zip on 27 October 2026. Original export retained under model/poi_category_state_1km_full. Both source file hashes match the current dataset and coordinate file. Prepared rows, targets, grouping, rounded predictions and all 96 evaluation score rows were checked against the saved predictions. All training-CV rows belong to the corresponding training split. The model uses 8 POI counts + category + state, with no EV registration feature, radius 1,000 m and nearest-half-up rounding, minimum 1.

## Model selection and export

Within the 80/20 + CV10 protocol, Random Forest training-CV MAE is 1.90255 and XGBoost 1.93471. RF has lower training-CV MAE in all six split-plus-CV setups. RF is therefore the recommended comparison candidate on training-CV evidence, although XGBoost has lower 80/20 test error. This is a post-hoc choice among already inspected experiments, not a fresh unbiased final evaluation.

The uploaded candidate_model.joblib is the all-data fixed RF (300 trees, depth 10, minimum leaf 2), not the tuned evaluated RF. Reconstructed and exported the selected evaluated RF to model/verified_poi_state_rf80_cv10/evaluated_pipeline.joblib: 600 trees, depth 5, minimum leaf 10, all features at each split. It was fitted on the saved 1,522 training rows and matches all 380 saved held-out raw predictions within 1.78e-15. Ten parity fixtures, source/model hashes and manifest are alongside it. A test checks every saved held-out prediction and fitted parameters. This artifact is not the full-data refit and is now the default serving model after the coordinated 1 km integration.

Selected RF held-out results: raw MAE 2.01239, RMSE 3.99264, R2 0.23809; rounded MAE 1.97895. Exact rounded match 33.4%; within 1 point 56.6%; within 2 points 80.0%. Actual-target bands: 1–4 points (274 sites) MAE 1.25368; 5–9 (65 sites) MAE 2.06538; 10+ (41 sites) MAE 6.99880. Rounded outputs range 2–14, with 136 of 380 predictions equal to 4. Larger totals are poorly estimated.

## Does the model use location POIs?

Additional descriptive checks used the same saved 80% training partition and its 10 tuning folds. At the selected RF settings, category+state without POIs gives mean-fold MAE 1.89358, versus 1.90255 for all inputs; POIs alone 2.63013. These fixed-setting ablations are exploratory and not independently tuned alternatives, but show no demonstrated gain from POIs in this RF configuration.

Repeated joint shuffling of all eight held-out POI columns over 20 deterministic seeds gives RF mean MAE 2.00057 versus unshuffled 2.01239. Category shuffling increases it to 3.12530; state shuffling changes little. For the separately reconstructed tuned XGBoost (verified against saved predictions), POI shuffling increases MAE from 1.95357 to 2.11857, and category shuffling to 3.06315. Thus XGBoost has more detectable POI dependence, but both models remain category-dominated. Permutation results are descriptive: correlated inputs, limited sample and inferred category labels affect interpretation.

See heldout_site_errors.csv, training_feature_ablation.csv and poi_signal_diagnostic.json inside the verified artifact directory. Source targets are MEVnet planned totals under the additional-proposed assumption; these results do not establish optimal charging demand. Many host categories were inferred during preparation and require review.

## Integration status — 27 October 2026

The app now defaults to the selected evaluated RF in `model/verified_poi_state_rf80_cv10`. The map and extraction use 1 km. Ten inputs are enforced; adoption is absent from new feature responses and prediction snapshots. Startup verifies model/runtime/fixtures plus the query-rule and bundled OSM snapshot hashes. A mismatched source cannot authorise a prediction. Legacy adoption history remains readable through migration `0007_optional_adoption`.

POI feature compatibility is verified; optimal capacity is not established. The UI therefore labels results Research prototype and explains category dependence and larger-site error. See RESULTS.md and BACKLOG.md for checks and remaining work.
