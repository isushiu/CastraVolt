# EV charger recommendation — working project notes

Updated: 26 October 2026

## Project purpose

Latest target decision (26 October 2026): the user authorised adding `total_planned_chargers = number_of_existing_ev_charger_s + number_of_proposed_ev_charger__` to the ML Data copy. This is now the selected training target, based on the user's interpretation that proposed counts are additional chargers. Earlier sections describing the proposed column alone as the target are superseded. The official field labels do not independently establish this interpretation; if proposals are historical totals or already realised, the sum could double-count. Preserve both original columns and exclude them, plus any direct capacity components such as installed AC/DC and indoor/outdoor counts, from model inputs that would reveal the target or be unavailable at a new site. The parent-folder source CSV remains unchanged.

Official dashboard verification: both local MEVnet files still contain `number_of_existing_ev_charger_s`. All 764 sites matched official IDs, names, states, local authorities, status, and coordinates; both existing and proposed counts agreed for every site. Dates agree after formatting normalisation. No dataset edits were needed. Evidence is saved in `data/mevnet_verification/`. Official aliases alone did not confirm the additional-versus-total meaning. The official StoryMap describes counts as simultaneous charging points with parking bays.

Help a planner estimate the total number of charging points to install at a proposed new site in an urban area of Selangor or Kuala Lumpur.

The planner chooses the location. The system recommends the site's charging-point count; it does not currently choose the best location automatically.

A charging point should be defined as capacity to charge one vehicle simultaneously. Confirm that MEVnet counts use this definition.

## What the machine learning model learns

Learn relationships between the characteristics of existing recorded sites and their MEVnet proposed charger counts.

Each training row represents one site. Candidate inputs are:

- Nearby mall, petrol station, hotel, office, transit, university, hospital, and parking counts.
- Site category, such as office or shopping mall.
- Location information, such as coordinates and state, if evaluation supports using them.
- A prepared state-level EV registration indicator, supplied automatically for Selangor or Kuala Lumpur. Treat this as a candidate feature and compare performance with and without it.

The nearby total POI count is already the sum of the eight individual POI counts. It is not an independent source of information.

Candidate models: Random Forest regressor and XGBoost regressor.

## What the model predicts

Intended output: estimated total charging points recommended for the selected new site.

Preferred training target: `number_of_proposed_ev_charger__` from the MEVnet dataset.

The user confirms that these proposed counts originate from MEVnet. Still confirm the field's meaning: total site capacity versus additional chargers. This is a semantic check, not a question about whether the source is authentic.

The prediction learns MEVnet proposal patterns. Agreement with those proposals does not by itself prove optimal capacity, actual charging demand, or acceptable waiting times.

## What the planner enters

1. A proposed location, selected by dropping a pin or searching for an address.
2. A site category, confirmed or selected if automatic identification is unreliable.
3. A request to estimate the charging-point count.

The planner should not need to count nearby facilities or supply EV registration figures manually.

## What the application gathers automatically

- Latitude and longitude from the selected pin.
- State and supported-area membership from the location.
- Nearby POI counts from OpenStreetMap using the same radius, categories, counting rules, and processing used for training.
- A stored EV registration indicator selected by the pin's state. The planner does not enter this value. Use the same indicator definition and preparation method in training and prediction.

The existing CSV contains previously gathered POI counts. Gathering equivalent counts for a new pin requires implementing the lookup; it is not already provided by the CSV.

## EV adoption data: current decision

Include a prepared state-level EV registration indicator as a candidate model input, supplied behind the scenes by a lookup for Selangor or Kuala Lumpur. Also show registration growth as research background and dashboard context where useful. No numerical lookup values have been finalised yet.

The supplied registrations do not establish neighbourhood-level EV adoption around a pin. A state-level lookup would give every location in that state the same value. One fixed adoption value for each of two states adds little information beyond the state itself.

Compare models with and without this input before deciding whether to retain it. Two fixed state values do not establish how adoption growth affects required charger counts. Updating the stored figures later does not guarantee that the model can forecast the effect of growth, particularly beyond the training values.

Using growth as a training feature would require a defensible match between registration periods and dated proposal records. New registrations are additions over a period, not the full EV fleet.

Most electric registration records have `Rakan Niaga` in the state field. Verify the source definition before treating a filter on named states as a reliable measure of local adoption.

## Available datasets

- `data/mevnet_ev_charging_demand_labelled_dataset.csv`: 764 sites; 418 Selangor and 346 Kuala Lumpur. All marked existing. Contains site attributes, POI counts, existing charger counts, and proposed charger counts.
- `data/ev_registration2024.csv`: full-year registration records; includes multiple fuels and vehicle types.
- `data/ev_registration2025.csv`: full-year registration records; includes multiple fuels and vehicle types.
- `data/ev_registration2026.csv`: January–May 2026; contains extra empty columns and a summary alongside raw records.
- `data/ev_registration2026.xlsx`: registration workbook with a separate summary sheet. Only sample records and sheet structure were inspected; full equality with the CSV has not been verified.
- `data/vehicles_2026.csv`: January–September 2026; includes car, motorcycle, and other vehicle categories. Overlaps the other 2026 records, so do not append both sources without reconciling coverage.

The user selected the narrower `type = motokar` scope for EV registration inputs. Filtered copies in `data/ML Data` retain only `fuel = electric`, `type = motokar`, and states `Selangor` or `W.P. Kuala Lumpur`. Use `vehicles_2026.csv` for 2026, not `ev_registration2026.csv`. SUVs classified as `jip`, multipurpose vehicles, pickups, window vans, and motorcycles are excluded. The resulting counts represent this selected type, not all electric passenger vehicles. Originals remain unchanged; preparation details are in `data/ML Data/README.md`.

## Inputs to exclude or handle carefully

- Do not use the target column as an input.
- Do not require installed onsite charger counts for a proposed new site.
- Installed `type_ac` and `type_dc` counts sum exactly to existing charger count in all 764 records. They would reveal that target if existing count were predicted, and are not independently available at a new site.
- Exclude identifiers such as `objectid` and empty export columns.
- Do not automatically remove identical registration rows: multiple vehicles can share all recorded attributes.
- Keep spatially overlapping sites together during evaluation where appropriate. Two dataset entries share coordinates and may represent distinct facilities at one location.

## Evaluation

Compare Random Forest and XGBoost using MAE, RMSE, and R² on held-out sites. Use geographically separated evaluation to assess performance beyond immediately neighbouring training sites.

Include simple baselines: always predict three charging points, and predict the training-set median. These comparisons assess agreement with MEVnet proposal counts; they do not demonstrate reduced queues or lower operating costs.

Compare otherwise equivalent models with and without the state-level registration indicator, using the same held-out sites. Retain it only if the evidence and interpretation support its use.

Define how non-integer or negative model outputs become valid displayed counts before evaluating the final recommendation behaviour.

## Application flow

Planner selects pin and confirms site category
→ application gathers matching nearby POI features
→ application looks up the prepared state-level EV registration indicator, if retained in the model
→ trained model estimates proposed total charger count
→ dashboard displays the estimate and explains its basis and limitations.

## Details to confirm before training

1. Does MEVnet's proposed-count field represent total chargers at the site or additional chargers?
2. Does the field count devices, connectors, bays, or simultaneous charging points?
3. What POI radius, tags, deduplication rules, and extraction date produced the current dataset?
4. What does `data_as` represent, and when were the proposals made?
5. Should the output distinguish AC and DC capacity? A raw count alone does not specify charging speed.
6. Are private or access-restricted sites suitable training examples for the intended public-facing planning use case?
7. Which registration indicator and reference period should be used for each state, how should `Rakan Niaga` records be handled, and how can the indicator be aligned with proposal dates without using future information?

## Scope of this note

This records the discussion and a read-only inspection of the local datasets. No model has been trained, no source records have been changed, and no external service has been connected.

## Training experiment plan discussed

The user requested recording the following discussion. This is an experiment plan, not a report of completed training. The 11 evaluation setups below replace the earlier suggestion to use only one 80/20 experiment. The user approved the proposed tuning ranges and search budget and selected random splitting rather than geographical grouping. The latest split decision below supersedes earlier geographical recommendations.

### Target and features

- Preferred target: `number_of_proposed_ev_charger__`. Intended interpretation: total proposed charging points at a site. Confirm the source field definition before interpreting results as total recommended capacity.
- Core candidate features: eight individual nearby POI counts, site category, and state.
- Test a prepared state-level EV registration indicator as an additional feature, comparing otherwise equivalent models with and without it.
- Coordinates can be tested as optional features. Assess whether they improve generalisation rather than memorisation of neighbouring sites.
- Exclude object identifiers, target values, and installed onsite charger counts from the new-site input requirements.
- The user supplies a pin and confirms site category. The application converts these into the model's required feature columns, including state lookup and POI extraction. The model does not consume the map pin directly.

### Registration integration

The application supplies the stored registration indicator automatically based on Selangor or Kuala Lumpur. The planner does not enter adoption figures.

The exact indicator, reference period, and treatment of `Rakan Niaga` remain unresolved. Match registrations to proposal dates where defensible; do not use later registrations to explain earlier proposals. Two fixed state figures supply broad context but do not demonstrate how growth changes required charger capacity.

### Eleven evaluation setups

Run each setup for both Random Forest and XGBoost. Ratios below mean training/test proportions.

1. 50/50 split only.
2. 70/30 split only.
3. 80/20 split only.
4. Five-fold cross-validation only.
5. Ten-fold cross-validation only.
6. 50/50 split with five-fold CV inside the training portion.
7. 50/50 split with ten-fold CV inside the training portion.
8. 70/30 split with five-fold CV inside the training portion.
9. 70/30 split with ten-fold CV inside the training portion.
10. 80/20 split with five-fold CV inside the training portion.
11. 80/20 split with ten-fold CV inside the training portion.

Split-only experiments use predefined hyperparameters and evaluate on the held-out test portion. The exact fixed configurations still need selection.

CV-only experiments use predefined hyperparameters and report held-out fold scores, their mean, and variability. If hyperparameters are tuned in these experiments, use nested CV for an unbiased assessment rather than reporting the same scores used for selection.

Split-plus-CV experiments reserve the test portion first. Tune hyperparameters using CV only within the training portion, select using lowest mean validation MAE, refit on the whole training portion, and evaluate once on the untouched test portion.

### Fair comparison and reproducibility

- Random seed: 42 wherever randomisation is used and supported. Record actual splits and folds for reproducibility.
- Use the same held-out sites and CV folds for both models and for comparisons with and without registration features.
- Recommended: geographical grouping for splits and CV, keeping colocated sites together. Finalise how groups are formed and confirm there are enough groups for ten-fold CV within the smallest training portion. Grouped ratios may only approximate requested percentages.
- Fit imputation, categorical encoding, feature selection, and any other learned preprocessing only on the relevant training partition or fold.
- Report actual training/test sizes, MAE, RMSE, and R². For CV, report fold variability as well as average performance.
- Treat the setups as a sensitivity study of training size and evaluation strategy. Do not select the highest-scoring split as proof of the best model: test sets differ in difficulty.
- If selecting a final model after comparing many setups, make that selection process explicit. Repeatedly inspecting test results makes those sets part of model selection; use a separate final holdout or nested evaluation for a fresh final-performance claim.

### Proposed hyperparameter search

These ranges and the search budget were approved by the user. They are not validated optimal settings. Fixed configurations for experiments without tuning still need to be specified.

Random Forest:

- Number of trees: 300 or 600.
- Maximum depth: 5, 10, or unrestricted.
- Minimum samples per leaf: 2, 5, or 10.
- Features considered at each split: square root or all features.

XGBoost:

- Number of boosting rounds: 100, 300, or 600.
- Maximum depth: 2, 3, or 5.
- Learning rate: 0.03, 0.05, or 0.1.
- Row sampling fraction: 0.8 or 1.0.
- Feature sampling fraction per tree: 0.8 or 1.0.
- L2 regularisation: 1 or 5.

Agreed budget: 30 sampled hyperparameter combinations per model per split-plus-CV setup. Use identical folds and the same selection metric. This is additional computation beyond simply fitting each of the 22 model/setup combinations. CV-only tuning would require a separately defined nested search.

### Baseline benchmarks

Random Forest and XGBoost are the main competing models. Also evaluate simple benchmarks to establish whether they add predictive value:

- Always predict three charging points.
- Always predict the training partition's median proposed charger count. In CV, calculate the median independently inside each training fold.

Baseline comparisons measure agreement with MEVnet proposals, not demonstrated reductions in waiting times or costs.

### Site category and POI extraction rules

Agreed: retain all 23 MEVnet site categories for the selected site's category input:

- Strata
- Shopping Mall
- Office
- Showroom
- Hotel & Resort
- Others
- F&B
- Petrol Station
- Recreation Center
- Hospital
- Galleria
- Petrol Station - Highway
- Prayer Hall
- University
- Convention Center
- Airport
- Highway
- R&R
- Entertainment
- Library
- Residences
- Theme Park
- Services

These describe the proposed site itself. The application may suggest a category from location information where reliable; the planner confirms or corrects it. Automatic mapping to all MEVnet categories is not yet implemented or guaranteed.

Handle the missing site category during cleaning: inspect the site to identify it if possible, otherwise use an explicit Unknown value rather than guess. Unknown is a missing-data fallback, not a replacement for the 23 source categories.

Nearby facilities are separate inputs. Retain the eight existing POI groups: malls, petrol stations, hotels, offices, transit, universities, hospitals, and parking. Do not automatically expand the nearby counts to all 23 site categories. That would require new feature extraction and training data.

Agreed starting radius: 1 km straight-line distance from the selected pin. This is not a verified original extraction setting or a proven optimal radius. The user explicitly agreed to the 23 site categories, this starting radius, and the duplicate-handling principles below.

Agreed duplicate-handling principles (precise matching criteria still need implementation):

- Count each distinct facility once within each POI group.
- Remove repeated OpenStreetMap elements using both element type and ID as the unique key.
- Merge clearly matching representations of the same facility, such as a point and building polygon for one hospital. Define reproducible matching criteria before implementation; do not merge solely on proximity.
- Do not merge different facilities simply because they share coordinates or a building.
- Different groups can count the same complex where it contains distinct qualifying facilities, such as a mall and its parking facility.

Recover the original radius, OpenStreetMap tag mappings, duplicate-handling rules, and counting method used for the current CSV. If adopting the proposed rules or if the originals cannot be recovered, regenerate POI counts for every training site consistently. Use the same tag definitions, geometry/distance handling, radius, and duplicate rules for training and new-pin predictions. Do not apply 1 km only in the application while retaining training counts generated under unknown or different rules.

### Agreed prediction rounding

- Preserve raw regression predictions for MAE, RMSE, and R² evaluation.
- For displayed counts, always round upward using ceiling: 2.0 becomes 2, 2.1 becomes 3, and 2.9 becomes 3. This supersedes the earlier nearest-integer proposal.
- Minimum-count handling remains to be finalised. The assistant recommended a minimum of one because the derived total target ranges from 1 to 74; the user has not explicitly accepted that minimum. Regardless of rounding, negative displayed counts must not be allowed.
- Also report MAE for rounded recommendations so evaluation reflects the numbers users see.

### Next steps before execution

Confirm the proposed-count definition, recover the existing POI extraction settings or approve and regenerate using consistent new settings, define geographical groups and fixed model configurations, and settle the registration indicator/reference period. Then prepare the feature matrix and run the documented experiments. No training has been started.

### Latest agreement and remaining choices

- Registration aggregation: use 1 January–31 December for complete years 2024 and 2025. The selected 2026 source currently covers 1 January–30 September, so label it year-to-date. Continue excluding `Rakan Niaga` and retaining only electric `motokar` registrations explicitly recorded in Selangor or Kuala Lumpur.
- This defines the aggregation periods, but not which year's indicator is attached to each site. Temporal alignment with proposal records remains unresolved.
- The random-versus-geographical choice applies to all 50/50, 70/30, and 80/20 train/test splits and to fold construction in the CV experiments. Ratios specify how much data is allocated; grouping specifies which sites stay together. If geographical grouping is selected, define the grouping method and scale and verify ten-fold feasibility.
- Other remaining implementation details: fixed untuned model configurations, exact POI tag and facility-matching rules, recovery or consistent regeneration of existing POI features, and minimum displayed count. Do not describe splitting as the only unresolved detail.
- The selected total target is authorised under the user's additional-chargers interpretation; its source-semantic limitation remains documented rather than blocking the authorised target creation.

### Final split decision: random splitting

The user selected the simpler random approach for all 11 experiment setups.

- Random 50/50, 70/30, and 80/20 train/test allocations, using seed 42.
- Shuffled five-fold and ten-fold CV, also using seed 42 where supported.
- Give Random Forest, XGBoost, baselines, and feature comparisons identical site assignments.
- For split-plus-CV, construct CV folds only within the training portion. Keep the test portion untouched during tuning.
- Keep records at identical coordinates together in every split and fold. Implement this as random allocation of coordinate groups, not geographical grid grouping. Ratios may be approximate. For CV, shuffle and balance coordinate groups across folds; ordinary row-level KFold alone would not preserve this requirement.
- State the evaluation limitation: nearby but distinct sites can have overlapping POI features, so results may be more optimistic than performance in wholly unseen neighbourhoods. This is not a geographically independent evaluation.
- Do not implement the previously discussed 5 km grid or 2 km spatial buffer as the selected approach.

### Plan readiness

The overall workflow and evaluation design are established. No training has started. Before execution, finish these preparation details:

1. Recover or regenerate training POIs with the agreed 1 km extraction rules and define exact tags and facility matching.
2. Define the state registration indicator and align its period with site records; calendar-year aggregation alone does not settle this match.
3. Specify fixed model configurations for untuned experiments using the approved ranges as guidance.
4. Finalise minimum displayed-count handling; upward rounding is agreed, but a minimum of one was only recommended.

Retain the documented interpretation of the total target and report its limitation. These remaining details should be resolved in the preparation stage, not presented as already verified.

### Colab notebook implementation

`notebooks/CastraVolt_ML_Training.ipynb` implements upload/Drive/local loading, source audits, filtered-registration checks and summaries, site preprocessing, all 11 random coordinate-group-preserving setups, Random Forest and XGBoost, both baselines, tuning, metrics, charts and exports. Sources are never overwritten.

Fixed configurations for untuned experiments are implementation defaults: Random Forest uses 300 trees, depth 10, minimum leaf size 2, and all features per split. XGBoost uses 300 rounds, depth 3, learning rate 0.05, row and feature sampling 0.8, and L2 regularisation 1. These are explicit defaults, not claimed optimal settings.

The notebook starts in smoke mode. Local execution on the actual files completed all 11 setups for both models and baselines with reduced tree counts and two search candidates. No full-budget tuning or Colab UI execution has been performed. Those smoke scores are not research findings.

Adoption is off by default pending a justified period match. Optional fixed-period context and prior-calendar-year modes expose the assumptions and reject missing coverage rather than invent zero adoption. Existing POI counts remain labelled provisional; extraction is not regenerated by this notebook. The configurable minimum displayed count defaults to one as an implementation choice. Target semantics remain documented as an assumption.
