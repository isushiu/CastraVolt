# Future testing: category baseline + POI adjustment

**Recorded:** 28 October 2026 (Asia/Kuala_Lumpur)  
**Status:** Proposed research experiment. No training or app replacement is authorised by this document alone.  
**Purpose:** Keep category as useful context while testing whether POIs can explain meaningful differences between locations within a category.

## 1. What we are trying to fix

The planner selects a pin and confirms the host-site category. CastraVolt should estimate total planned charging points using the site and its surrounding facilities. The concern is that category dominates while different POI environments often lead to the same displayed count.

This is not a request to remove category or force POIs to have an arbitrary percentage of influence. The experiment asks whether an explicit POI adjustment can improve predictions beyond a category baseline. If the data cannot support that adjustment, the correct conclusion is to report the limitation rather than manufacture variation.

The target remains `total_planned_chargers = existing + proposed`, under the project's agreed assumption that proposed means additional chargers. The model learns MEVnet planning examples. This does not establish optimal capacity, charging-session demand, grid feasibility or installation design.

## 2. Current reference model and evidence

The active model is **Random Forest using eight 1 km POI counts + host category**, with nine raw inputs. State is derived to check Selangor/Kuala Lumpur coverage and retained as metadata; it is not a prediction input. Registration/adoption numbers are excluded and remain separate dashboard data.

Current serving directory: `model/verified_poi_category_rf80_cv10`.

Current RF settings:

- 600 trees; maximum depth 5; minimum samples per leaf 10; `max_features=1.0`; random seed 42.
- Evaluated fit uses 1,522 training sites and 380 held-out sites from 1,902 prepared observations.
- Training-CV MAE: **1.902717**.
- Held-out raw MAE: **2.012597**; RMSE: **3.998220**; R²: **0.235960**.
- Held-out rounded MAE: **1.976316**.

It had the lowest training-CV MAE among the POIs + category candidates. It was not the best model across every feature combination: category-only RF achieved CV MAE **1.887726**. Category-only remains a necessary baseline.

Full feature-comparison findings:

- POIs + category RF did not improve on category-only RF. Its CV MAE was approximately 0.015 worse.
- POIs + category XGBoost used POIs more: jointly shuffling its POIs increased held-out MAE by approximately 0.146. However, its gain over category-only XGBoost was small and the reported paired interval included zero.
- POI-only XGBoost CV MAE was approximately 2.606497 and test MAE 2.582736. This was worse than the always-three test MAE of approximately 2.415789.
- The POI-only all-zero vector predicted **3.6626608**, displayed as **4**. That response could not have come from category, because category was excluded from that model.
- Some labels are highly concentrated: 434 of 470 petrol-station records in the prepared data have a total of 2. There are only two Highway records, with targets 3 and 4. Reliable highway-specific conclusions cannot be drawn from two observations.

Rounding can also hide changes. For a diagnostic fixed at Highway, the current RF predicted approximately 4.036 with zero POIs and 4.334 with the screenshot's POI counts. Both round to 4. These are synthetic model probes, not verified capacities for physical sites.

The current RF's shallow trees and minimum leaf size may smooth differences, but the feature-comparison results also suggest limited additional signal in the current POI counts. Neither rounding nor model smoothing alone explains all the observed limitations.

## 3. The proposed method in plain English

Train two connected models with different jobs:

1. **Category baseline:** estimate the typical planned charger total for the host category.
2. **POI adjustment:** predict how much the total should differ from that baseline, using only the surrounding POIs.

Example using an illustrative training observation:

- Actual labelled total: 7 charging points.
- Category model predicts: 4.
- Adjustment target: `7 - 4 = +3`.

For a new pin, the category model might predict 4 and the POI model might predict an adjustment of +1.7. Combine them to get 5.7, then round once to 6.

The +1.7 must be learned from labelled examples. It is not a hand-written bonus for having more facilities. An adjustment can be positive, zero or negative.

This is residual modelling. The approach is a hypothesis to test, not a proven solution or a promise that POIs will become useful.

## 4. Mathematical definition and outputs

Let:

- `C` be the confirmed host-site category.
- `P` be the vector of eight POI counts.
- `y` be the MEVnet labelled total planned charging points.
- `g(C)` be the category baseline.
- `h(P)` be the POI adjustment.

During training, construct residual targets as:

```text
residual_i = actual_total_i - out_of_fold_category_prediction_i
```

At prediction time:

```text
category_baseline = g(category)
poi_adjustment = h(eight_poi_counts)
raw_total = category_baseline + poi_adjustment
displayed_total = max(1, floor(raw_total + 0.5))
```

Rules:

- Combine raw values before rounding. Do not round the baseline or adjustment separately.
- Do not clamp negative residuals or negative adjustments to zero.
- Apply the existing minimum-one display rule only to the final combined prediction. This is a project display policy, not proof that every site needs at least one charger.
- Keep the unclipped raw total and both components in evaluation exports, including negative raw totals if they occur. Report their frequency.
- Do not add a manual POI multiplier just to obtain more varied answers.
- The baseline is not existing installed chargers. It is a model prediction from category. The adjustment is not an estimate of additional chargers to install.

## 5. Data and input scope

Start with the same matching pair:

- `data/ML Data/updated_mevnet.csv`
- `data/ML Data/updated_mevnet_row_groups.csv`

Expected source hashes:

```text
updated_mevnet.csv
 d7bb8091af92f416ca212d35772a75f0e98c088a26ca02b56a0616bf39ea9458
updated_mevnet_row_groups.csv
 d22b39b3b3bb517934090d555add833c51cfbd391533310840c2e2edc4d6f203
```

The baseline receives only category. The adjustment receives only:

- `nearby_mall_count`
- `nearby_petrol_count`
- `nearby_hotel_count`
- `nearby_office_count`
- `nearby_transit_count`
- `nearby_university_count`
- `nearby_hospital_count`
- `nearby_parking_count`

Do not include state, adoption totals, coordinates, IDs, existing/proposed target components, target-derived category statistics or actual charger totals as adjustment inputs. Coordinates and IDs are for grouping, auditing and joining outputs only.

Use the same 1 km radius, extraction rules, deduplication and bundled OSM snapshot as the current dataset. Changes to map definitions belong to a separately versioned experiment.

Preserve the cleaning rules: audit missing/constant/unique columns; reject invalid target/scope rows; convert invalid POI values to missing; fit numeric imputation and feature transformations only within the relevant training subset. Do not remove distinct sites just because their input values are identical.

## 6. Leakage prevention: the essential requirement

Do not train the category model on all observations, predict those same observations and use those in-sample errors to train the POI model. Those residuals may be misleadingly small and are not a fair assessment of what POIs can correct.

Also do not precompute one global residual column before cross-validation. A category model used in that calculation could have seen a later validation fold's labels. Training the adjustment on those residuals would leak information across folds.

### Correct fit procedure for any training subset A

For each proposed combination of baseline and adjustment settings:

1. Use only the rows in subset A.
2. Divide A into five coordinate-group folds for category cross-fitting.
3. For each cross-fitting fold, fit a fresh category pipeline on the other four folds and predict the excluded fold.
4. Assemble one out-of-fold category prediction for every row of A. No row's label may have trained the model predicting that row.
5. Calculate `residual_A = y_A - category_oof_A`.
6. Fit the POI adjustment pipeline on `P_A` and `residual_A`.
7. Fit a fresh category baseline on all of A for later inference.
8. Return the two fitted components as one composite estimator.

Each cross-fitting category pipeline must fit its own preprocessing. Category settings are fixed for that candidate during this fit; any extra tuning must remain inside A. Unknown categories use a documented encoder/fallback learned from A only.

The adjustment is trained against out-of-fold baseline errors but deployed beside a baseline fitted on all of A. That difference is inherent in this design and may cause a mismatch in adjustment size. Evaluation must check whether the combined model is biased or overcorrects; cross-fitting alone does not guarantee success.

### Correct validation of that fit

For a validation subset V, fit the entire procedure above on A, then predict V as `g_A(C_V) + h_A(P_V)`. Score against `y_V`. V must not influence either component, the residual construction, preprocessing or feature selection.

If tuning the adjustment through CV, refit the entire composite procedure inside every CV training fold. Do not create residuals on the full tuning dataset and then cross-validate only the adjustment model. Score the combined total on validation rows, not just residual error.

## 7. Initial experiment protocol

Use the existing source identities and exact saved 80/20 coordinate-group partition:

- Training portion T: 1,522 observations.
- Previously examined holdout H: 380 observations.
- Seed: 42.
- Ten coordinate-group CV folds inside T for model/configuration selection.
- Five coordinate-group cross-fitting folds inside each composite fit to generate category residuals.

The five-fold cross-fitting step and ten-fold tuning step have different jobs. Five-fold cross-fitting builds honest residual targets inside the current fit. Ten-fold tuning compares complete fitted pipelines. They must not share information across their train/validation boundary.

Exactly co-located sites stay together in every split level. Log membership and assert disjoint groups. Nearby locations may still overlap in facilities; this protocol does not remove that limitation.

For each candidate configuration, evaluate the full composite on the same ten tuning folds. Select by mean raw-total MAE. After selection, fit the chosen composite on all of T, generating its residuals by cross-fitting within T, and evaluate H for a descriptive comparison.

The existing holdout has already been inspected repeatedly. Neither its new scores nor selected CV scores should be described as a fresh unbiased final assessment. If results justify further work, freeze the complete procedure and obtain genuinely unseen, reviewed sites for final evaluation. Creating another random split of the same already inspected observations does not make a genuinely unseen final test.

A fully nested outer-validation study can be added later if needed, but the initial ten-fold selection scores should not be relabelled as unbiased nested-validation performance.

## 8. Models to compare

Keep the first round focused:

1. **Always-three and training-median baselines.** Fit medians inside each fold.
2. **Category-only RF.** A direct comparator for whether the POI adjustment adds value.
3. **Current combined RF.** Preserve the frozen serving model as a descriptive reference. For fair fold-by-fold comparisons, refit its pipeline on each fold's training rows; do not score its globally fitted artifact on those validation rows.
4. **Separately tuned combined RF and XGBoost using POIs + category.** This distinguishes a benefit from the two-stage structure from a benefit of retuning the single-stage model.
5. **Category RF baseline + POI RF adjustment.**
6. **Category RF baseline + POI XGBoost adjustment.**

Use the same category-baseline configuration when comparing the category-only and corresponding two-stage candidates. Declare its settings before the experiment, using the prior category-only search as a reference configuration. If baseline settings are retuned, include that choice inside the composite selection process rather than choosing them from holdout performance.

A simple training-category mean/median baseline with a training-only global fallback can be a later diagnostic. Do not immediately train a separate complete model for every category: sparse categories such as Highway have too few examples.

## 9. Tuning and compute plan

Proposed initial configuration, to freeze before running:

- Use seed 42 and mean validation MAE as the primary criterion.
- Start with 20 sampled settings per candidate family. Use the same predeclared budget for comparable direct and residual alternatives; record actual fit counts and elapsed time.
- For RF adjustment, explore 200/400/600 trees, depths 3/5/10/unlimited, minimum leaves 1/2/5/10/20 and feature fractions 0.5/1.0.
- For XGBoost adjustment, explore 100/300/600 trees, depths 2/3/5, learning rates 0.03/0.05/0.1, subsample 0.8/1.0, column sample 0.8/1.0 and lambda 1/5/10.
- These are proposed research ranges, not approved optimal values. Freeze the exact spaces and budgets in run metadata before looking at results.
- Use an ordinary signed regression objective for adjustments. Residuals can be negative, so do not use a nonnegative-count objective for the adjustment target.
- Fit each model with one internal worker and limit parallel search workers to avoid nested CPU overload.
- Save progress after each candidate. Run a clearly labelled smoke mode before full training.

Cross-fitted baseline predictions can be cached for identical source version, training-row membership, baseline settings, grouping and seed. Cache entries must never be reused for a different validation boundary. Do not trade leakage safety for speed.

An optional later shrinkage experiment can scale the learned adjustment toward zero, with the scale selected only through training validation. Do not introduce it as an arbitrary 50/50 blend. If validation chooses an adjustment effectively equal to zero, report that POIs did not add useful predictive value.

## 10. What to measure

### Overall performance

Export raw MAE, RMSE and R²; rounded MAE; exact rounded accuracy; and fractions within one and two charging points. Show CV mean and fold variation separately from holdout metrics. CV standard deviation is not a confidence interval.

### Incremental value of POIs

Compare each residual candidate with its matching category-only baseline and the combined RF on identical evaluation rows. Define MAE gain as baseline error minus candidate error: positive is better.

Use paired coordinate-group bootstrap comparisons for descriptive uncertainty. Report multiple comparisons and the already inspected holdout limitation. An interval including zero is not convincing evidence of a reliable gain.

### Category and capacity breakdowns

Report sample counts and errors by category and by actual total bands 1–4, 5–9 and 10+. Show sparse categories explicitly rather than hiding them in overall averages. Report error direction to identify systematic underestimation of large sites.

Highway has only two currently labelled observations; its category-specific accuracy must remain inconclusive. Do not claim a special highway recommendation was validated.

### Component behaviour

Export, for every evaluated observation:

- Source row/group, actual total and category.
- Category baseline prediction.
- Predicted POI adjustment.
- Combined raw prediction and rounded result.
- Whether display clipping/rounding changed the result.

Report adjustment distributions, near-zero adjustments, negative raw totals and extreme corrections. Examine whether baseline + adjustment systematically overshoots or undershoots across categories.

### Sensitivity probes

For fixed categories, compare genuine low- and high-POI sites with similar training support. Show changes in raw predictions, not only rounded totals. Also test all-zero and single-feature-change vectors as labelled synthetic probes; do not interpret them as physically validated capacities.

Jointly permute the POIs for the fitted composite while keeping category fixed, and report the change in total-prediction error. Also compare against using the baseline alone. Dependence on POIs is necessary for the intended mechanism, but sensitivity or importance alone is not evidence of accuracy or causality.

## 11. Decision criteria

Freeze criteria before running. A proposed practical threshold for discussion is at least **0.10 charging points lower validation MAE** than the matching category baseline. This is a project planning threshold, not an established industry standard; agree it before results and do not change it afterward to select a favourite model.

Advance the two-stage approach only if:

- Leakage checks and source/split checks pass.
- Improvements are reasonably consistent across tuning folds and not driven by one unusual group.
- The adjustment improves accuracy beyond category alone and performs competitively with the current combined RF.
- Larger-site and well-represented category errors do not materially deteriorate. Define any numerical tolerance before the run and show the actual subgroup results.
- POI sensitivity reflects a useful error reduction, rather than merely bigger movements in output.
- Artifact/runtime/parity checks pass.

Keep the current model if the proposed method is worse or gains remain too small/uncertain. A positive gain on the already examined holdout is supporting descriptive evidence, not permission to call it independently validated.

If the method works only for sufficiently represented categories, document that scope and validate any fallback on training data. Do not silently deploy a different rule for sparse categories based on test examples.

## 12. If it does not improve

Do not force the adjustment to be larger, multiply counts to create activity, add synthetic charger labels, or choose an unexplained manual combination.

Investigate whether the current labels contain enough within-category variation and whether that variation corresponds to the measured surroundings. Audit inferred categories and suspicious/repeated planned totals. Counts of facilities are not measures of their size, occupancy or charging activity.

A separate future feature study can consider publicly available mapped information such as facility footprint/area, parking area where mapped, road class/connectivity, nearest-facility distance, and multi-radius counts. Verify availability and meaning, regenerate training and inference features consistently, version the changes and evaluate them separately. More features are not automatically better. Missing public-map information must not be presented as proof that a facility is absent.

If the available POI data cannot explain the labels, document that finding and narrow the product claim rather than suggesting more tuning guarantees a solution.

## 13. Notebook and export deliverables

Create a new notebook, provisionally `notebooks/CastraVolt_Residual_Comparison.ipynb`, without overwriting the existing feature-comparison notebook.

It should include upload, cleaning/audit, shared splits, leakage-safe composite fitting, baselines, tuning, evaluation, component diagnostics, visualisations and a final ZIP download. Use a separate timestamped output folder and label smoke/full mode clearly.

Expected exports:

- `run_metadata.json`: source/extraction hashes, feature schemas, seed, budgets, library versions, selection rule and limitations.
- `data_audit.csv` and `excluded_rows.csv`.
- `holdout_assignments.csv`, `tuning_fold_assignments.csv` and baseline cross-fitting membership sufficient to audit each fit boundary.
- `category_oof_predictions.csv` for the final training fit, with residual targets and source-row identity.
- `search_results_*.csv`, `comparison_summary.csv` and `selected_parameters.json`.
- `component_predictions.csv` for evaluated rows.
- `paired_comparisons.csv`, `per_category_errors.csv` and `errors_by_target_band.csv`.
- `permutation_diagnostics.csv` and `sensitivity_scenarios.csv`.
- Charts showing both error comparisons and baseline/adjustment behaviour.
- A selected composite candidate containing both fitted pipelines and the final display policy, not only the adjustment model.
- Prediction fixtures, output hashes and a results ZIP.

Validate every source-row join and exported metric. Do not export an unrelated fixed default model while labelling it the tuned winner. Smoke output must never become a serving artifact.

## 14. Tests before trusting results

- Outer heldout and validation labels do not enter baseline fitting, residual construction or adjustment fitting for their prediction boundary.
- Every training row receives exactly one cross-fitted baseline prediction from a model that excluded its coordinate group.
- Preprocessing is fold-local and deterministic for fixed inputs/seeds.
- Unknown categories, missing POI values, zero counts, negative adjustments and sparse categories behave as documented.
- Negative adjustments are retained; combination happens before the one final rounding step.
- An adjustment of zero exactly reproduces the category baseline's raw prediction.
- Baselines and candidates share identical evaluation rows and grouping.
- Exported component sums and rounded counts reconcile to exported predictions and metrics.
- Reloaded composite artifacts reproduce fixtures with matching runtimes and map definitions.
- App artifacts/configuration are unchanged during research training.

## 15. Possible app integration, only after review

Do not replace `model/verified_poi_category_rf80_cv10` while experimenting. Keep current site/history flows and both earlier models intact.

If a candidate passes review, introduce a separate verified serving profile containing both components. It still needs category confirmation, the eight genuine 1 km POI counts, coverage validation and exact extraction compatibility. State remains metadata unless a separately approved experiment changes the input scope.

Saved prediction history should identify both component artifacts, baseline, adjustment, combined raw total, rounding/clipping policy, input snapshot and source hashes. The UI can show those components in calculation details and display a raw estimate beside the whole count so rounding is transparent. Explain the baseline/adjustment as statistical model components, not physical charger requirements.

The app must never silently substitute a zero adjustment, a constant charger count or an older incompatible model when a component is missing. Preserve a clear rollback path to the current combined RF.

## 16. Execution stages

1. **Freeze protocol:** confirm sources, split identities, candidate families, budgets, comparison criteria and limitations. Deliver a versioned experiment configuration.
2. **Build notebook and leakage tests:** implement the composite fit and all audit exports. Deliver a smoke run that proves split isolation and component arithmetic.
3. **Run full training:** train all declared comparators and candidates without touching app serving files. Deliver a complete results ZIP.
4. **Review evidence:** assess incremental POI value, subgroup errors, stability and sparse-category limitations. Deliver a written adopt/reject decision with reasons.
5. **Independent assessment:** if promising, freeze the chosen procedure and assess genuinely unseen reviewed sites. Do not relabel repeated test reuse as independent validation.
6. **Integrate only if justified:** verify both component artifacts, update the serving contract/history/UI and test rollback. Deliver verified integration with its remaining limitations stated.

**Next concrete action:** build the leakage-safe comparison notebook and execute its smoke checks. Full training and any serving-model replacement remain separate subsequent actions.
