# EV charger recommendation — working project notes

Updated: 26 October 2026

## Project purpose

Stage 0/1 implementation update: inspected the uploaded Colab export. Its deployment_candidate used defaults, so the selected tuned RF (600 trees, depth 5, minimum leaf size 10) was reconstructed separately using the saved 611/153 split. All saved test predictions matched to 1.78e-15; nearest-half-up MAE is 2.620915. See docs/STAGE_0_HANDOFF.md and model/verified_rf80_cv5/manifest.json. Stage 0 remains pending original POI extraction parity. Stage 1 foundation is implemented with passing application checks; live PostgreSQL migration awaits an available Docker engine. See IMPLEMENTATION_PLAN.md ledger for scope.

Latest project-note decision: the user selected the adoption-enabled full run as the working model. This supersedes earlier notes selecting the no-adoption run or limiting registrations to dashboard trends only. Use the filtered 2024, 2025, and 2026 registration sources for registration analysis and dashboard trends, and supply the configured state-level registration indicator to the adoption-enabled model automatically. The planner does not enter it.

Important distinction: the current notebook defaults to `ADOPTION_MODE = 'fixed_period_context'` and `ADOPTION_REFERENCE_YEAR = 2025`. With `USE_ADOPTION = True`, it uses one 2025 registration total per state as the additional model feature; it does not automatically learn the complete 2024–2026 growth series. All three sources are loaded for trend analysis (2024 and 2025 full years; 2026 January–September). Using all three years as prediction features would require an explicit feature-definition change and retraining.

Selected reported adoption-enabled candidate: Random Forest, 80/20 split with five-fold training CV. Raw MAE approximately 2.62219, RMSE 3.76716, R² 0.41543, and historical ceiling-rounded MAE 2.75817. That rounded metric predates the nearest-integer decision and must not be attributed to the new rule. Ten-fold CV gave identical reported holdout results. The adoption comparison showed negligible change in this setup; do not claim a demonstrated accuracy improvement from adoption. These are user-supplied full-run results.

`PRD.md` has been reconciled with the selected adoption-enabled approach: 11 model inputs and an automatic configured 2025 state-registration lookup, alongside separate 2024–2026 trend analysis.

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
3. The user confirms the existing engineered POIs use a 3 km radius. Recover the original tags, deduplication rules, geometry handling, and extraction date to reproduce the features.
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

Latest radius clarification: the user confirms that the existing MEVnet dataset was already feature-engineered using a 3 km (3,000 metre) radius to gather nearby POIs. Use 3 km for new-pin POI extraction to match training. This supersedes the earlier proposed 1 km radius. Radius provenance is user-confirmed; the original extraction script, exact tags, geometry handling, duplicate matching, and extraction date have not been independently inspected. Retain the existing engineered counts; a radius change is not required. This does not establish that 3 km is an optimal radius.

Agreed duplicate-handling principles (precise matching criteria still need implementation):

- Count each distinct facility once within each POI group.
- Remove repeated OpenStreetMap elements using both element type and ID as the unique key.
- Merge clearly matching representations of the same facility, such as a point and building polygon for one hospital. Define reproducible matching criteria before implementation; do not merge solely on proximity.
- Do not merge different facilities simply because they share coordinates or a building.
- Different groups can count the same complex where it contains distinct qualifying facilities, such as a mall and its parking facility.

Use the user-confirmed 3 km radius and recover the original OpenStreetMap tag mappings, duplicate-handling rules, and counting method used for the current CSV. The agreed duplicate-handling principles must be checked against the original engineering method rather than assumed to have been applied. Use the same tag definitions, geometry/distance handling, radius, and duplicate rules for training and new-pin predictions. Regeneration and retraining are necessary only if matching extraction cannot be reproduced or rules are deliberately changed; the radius clarification alone does not require retraining.

### Agreed prediction rounding

- Preserve raw regression predictions for MAE, RMSE, and R² evaluation.
- Latest agreed displayed-count rule: round to the nearest integer, with fractions below 0.5 rounded down and fractions at or above 0.5 rounded up. Examples: 3.2 becomes 3, 3.5 becomes 4, and 3.9 becomes 4. This supersedes the always-upward ceiling rule.
- Use half-up logic, `floor(raw_prediction + 0.5)`, with the configured minimum applied afterward. Python's built-in `round` uses ties-to-even and is not the agreed rule.
- Minimum-count handling remains to be finalised. The assistant recommended a minimum of one because the derived total target ranges from 1 to 74; the user has not explicitly accepted that minimum. Regardless of rounding, negative displayed counts must not be allowed.
- Also report MAE for rounded recommendations so evaluation reflects the numbers users see.
- Recompute rounded MAE and underestimation frequency from the same saved raw predictions for nearest-half-up and ceiling. No model retraining is needed just to compare rounding rules. Raw MAE, RMSE, and R² remain unchanged. Previously reported ceiling MAE is historical, not the new rule's measured performance.
- This update changes the notes and PRD only. The current notebook still implements ceiling and must be aligned before generating new application-ready counts.

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

1. Match new-pin extraction to the existing user-confirmed 3 km training features; recover exact tags, geometry handling and facility matching. Regenerate and retrain only if the definitions must change or cannot be reproduced.
2. Define the state registration indicator and align its period with site records; calendar-year aggregation alone does not settle this match.
3. Specify fixed model configurations for untuned experiments using the approved ranges as guidance.
4. Finalise minimum displayed-count handling; nearest-integer half-up rounding is agreed, but a minimum of one was only recommended.

Retain the documented interpretation of the total target and report its limitation. These remaining details should be resolved in the preparation stage, not presented as already verified.

### Colab notebook implementation

`notebooks/CastraVolt_ML_Training.ipynb` implements upload/Drive/local loading, source audits, filtered-registration checks and summaries, site preprocessing, all 11 random coordinate-group-preserving setups, Random Forest and XGBoost, both baselines, tuning, metrics, charts and exports. Sources are never overwritten.

Fixed configurations for untuned experiments are implementation defaults: Random Forest uses 300 trees, depth 10, minimum leaf size 2, and all features per split. XGBoost uses 300 rounds, depth 3, learning rate 0.05, row and feature sampling 0.8, and L2 regularisation 1. These are explicit defaults, not claimed optimal settings.

The notebook starts in smoke mode. Local execution on the actual files completed all 11 setups for both models and baselines with reduced tree counts and two search candidates. No full-budget tuning or Colab UI execution has been performed. Those smoke scores are not research findings.

The notebook originally defaults adoption to off; the selected working run instead uses True, as recorded at the top of these notes. Optional fixed-period context and prior-calendar-year modes expose assumptions and reject missing coverage rather than invent zero adoption. Existing POIs were engineered with a 3 km radius per the user's clarification; extraction is not regenerated by this notebook. Its radius configuration/provenance text still refers to the earlier unverified 1 km proposal and must be aligned before subsequent runs or application integration. The configurable minimum displayed count defaults to one as an implementation choice. Target semantics remain documented as an assumption.
<<<<<<< Updated upstream
=======


## Internal prototype and Stage 3 — 27 October 2026

Latest user decision supersedes the public registration flow: shared internal user ID `admin`, password `123`. No registration/email verification/recovery in the active UI; associated endpoints are disabled in default internal mode. All admin users share one persistent workspace. Existing account/session/ownership logic is retained; production rejects demo mode.

Stage 3 delivered: project and site CRUD with confirmed cascading deletion, owner-scoped APIs, persistent coordinates/category/address, prediction-snapshot schema and read-only history. History remains empty until real Stage 6 predictions exist. State is unresolved until trusted map integration; manual coordinates are an interim Stage 3 input. No POI/model/rounding decisions changed.

Verified 30 backend tests, 11 frontend tests and frontend build; isolated browser checks confirmed login → project → saved site → reload → empty history. Next is Stage 4 map/search/pin and 3 km circle. Restart using start.cmd to apply migration 0003. User requested no subagents for further work.


## Stage 4 map workflow — 27 October 2026

Complete locally: Leaflet/OpenStreetMap map, explicit Nominatim search, pin click/drag, 3 km metre-radius circle, coordinate alternative, project-aware saving and reopening, confirmed host-site category, and server-derived study state. Moving the pin invalidates prior location/saved state and address, and requires category reconfirmation. No POI extraction or ML runs during this stage.

State polygons: bundled/hash-checked geoBoundaries Malaysia ADM1 (OSM/Wambacher; 2017 geometry; ODbL 1.0). Reject points outside Selangor/Kuala Lumpur, including Putrajaya. Urban-only coverage remains provisional and visibly labelled; this does not certify current cadastral boundaries. Source metadata and hashes are in src/castravolt/resources.

Geocoder: explicit search only, server-side provider identification, bounded responses/timeouts, successful-result cache and global one-request-per-1.1-second reservation across workers. Public tile/search services are development defaults; suitable providers are needed before wider usage. Migration 0004 adds the cache.

Verification: 35 backend and 17 frontend tests plus build passed. Real browser verified KLCC search and tiles, save, dragging invalidation, update without duplicate, reopening. Temporary QA used only 5174/8001 and a disposable database, then cleaned up. No subagents. Next: Stage 5 feature preparation, still dependent on original POI counting parity.


### Map-only refinement — 27 October 2026

User decision supersedes earlier manual-coordinate alternatives: create and edit sites through the map only. Remove the separate Add site form and inline site editor. Project workspace offers Add site on map and Open on map. Coordinates are displayed read-only; state is derived on the server from the selected pin. Address is reverse-geocoded automatically after the pin settles (1.2 second debounce), or reused from an address search. Name and host-site category remain planner inputs; category is not inferred from nearby facilities.

Reverse lookup shares the existing global provider quota/cache, uses local state polygons rather than the provider's state label, aborts/discards stale responses and can be retried. Save waits for pending address lookup; if lookup fails, address remains optional and the valid pin/state can still be saved. POI/adoption feature extraction remains Stage 5. The observed Not Found response was traced to an older running backend with no location routes; restart once via start.cmd. Local startup now enables source-directory backend reload. User app ports/processes were inspected but not stopped or occupied.


### Pin name refresh — 27 October 2026

Moving or reselecting the pin clears the previous site name and refreshes it from the new search/reverse-geocoding result. No name is carried across locations. A name entered manually while the current pin lookup is pending is preserved. If no name is returned (or lookup fails), show a small indication asking the planner to enter one; saving still requires a nonblank name. Existing saved names are preserved when opening a site until its pin is moved. Regression coverage checks moving between named places and then to an unnamed spot.


## Stage 5 feature preparation — 27 October 2026

After saving a site, Prepare site context explicitly requests server-side facilities within 3,000 metres. The backend reads the owned site's pin/category, derives its state, gathers eight counts (mall, petrol, hotel, office, transit, university, hospital, parking), and appends fixed 2025 registrations (Selangor 560, KL 1,237), category and state: 11 model fields. Registration context is reconciled from the filtered CSV and packaged with source hash/scope. The 2024–2026 series remains available for the later trends dashboard; it is not dynamically substituted into the model lookup.

Counts/provenance are cached by exact location, radius, rule fingerprint and provider. Provider failures/incomplete results are errors, not zero facilities. Changes cancel or clear displayed context, and backend rechecks site revision/session/ownership after extraction. No inference or saved charger prediction happens at this stage.

Original training extraction definitions are still unavailable. New counting rules are explicitly provisional, with inference_eligible=false; they cannot be claimed equivalent to the training POIs. Original rules plus genuine site parity checks, or consistent POI regeneration and retraining, remain necessary. Live provider availability also remains unverified after TLS/timeout failures. See docs/STAGE_5_IMPLEMENTATION.md for exact tags, geometry, deduplication, cache/error behavior and evidence. Stage 5 is pending that dependency, despite the implemented service/UI.


## Provider failure follow-up — 27 October 2026

Reproduced the user's failure: configured Private.coffee status endpoint times out before any POI query. Explicit IPv4 curl also timed out with HTTP 000/no response; the issue was not resolved by IPv4. overpass-api.de failed TLS certificate verification and an OSM-listed alternate status endpoint also timed out. External web status checks timed out too. No certificate validation was disabled and no successful live extraction is claimed.

Implementation now classifies network failures, socket timeouts (504), TLS verification failure, upstream overload and incomplete responses. Return only safe actionable messages; log exception class/status/request ID rather than raw sensitive details. Retry-After propagates to the client and the context button shows a countdown. Cached successes are checked before reservations.

The 35-second in-flight provider lease now has a random ownership token. Completion shortens it to two seconds; connection/timeouts/incomplete responses use a shorter ten-second retry, TLS failure thirty seconds and upstream overload respects the bounded reported delay (minimum thirty seconds). Blocked callers receive the actual remaining wait rather than a fixed 35 seconds. A late response cannot shorten a newer request's lease. Provider service availability remains an external unresolved limitation; these changes do not repair an unreachable endpoint or establish training-feature parity.


## Working local data source — 27 October 2026

Latest implementation supersedes the requirement to wait for public Overpass availability. The default `CASTRAVOLT_POI_SOURCE=local` reads the bundled `resources/poi_snapshot.json.gz`, containing 10,981 genuine OSM facility representations from Geofabrik's 25 October 2026 extract. The compact catalogue is 483,026 bytes; source/checksums/coverage/license are in poi_snapshot_manifest.json. It covers the two state geometries plus a >3 km buffer and rejects circles outside its coverage. Local requests make no provider call and do not use the global Overpass cooldown. Cache keys include the snapshot SHA-256; classification/radius/deduplication remain versioned as before.

The full 252,386,711-byte source PBF stays ignored under data/poi/source. Its published checksum was verified, and its SHA-256 is 92e10b7d3d6b415758fa8e5720411fcb20e431e1f7d7f3e1420a2703289edd23. The compact derived database ships in the application package under ODbL 1.0 with OpenStreetMap/Geofabrik attribution. Source timestamp: 2026-10-25T21:21:21Z. This is a dated snapshot, not a real-time facility inventory; rebuilding/restarting is a deliberate data update.

Way bounding boxes are resolved from source node coordinates. Relation bounds include source members and nested relations. Incomplete geometry affecting study coverage aborts the build; radius uses bounding-box centres, matching the documented provisional method. `scripts/build_local_pois.py` is optional build tooling using the separate poi-build group, not a runtime requirement. Native system TLS via truststore repairs the observed Python-vs-Windows validation mismatch while retaining certificate/hostname checks; optional Overpass and address clients use it. Production data/model parity is not certified by this repair.

Verified real catalogue queries: public KLCC and the user's reported saved pin return counts; the latter prepared in approximately 12 ms in a direct local check. Browser QA on isolated 5174/8001 confirmed Prepare site context displays the real eight counts and 560 Selangor registrations. No ML prediction was generated. Original training POI-rule parity remains pending, so inference_eligible stays false. App startup now defaults to source polling for reliable development reload on Windows drives.

Verification: 54 backend tests passed, 24 frontend tests and production build passed. Tests include source integrity/coverage, way/relation geometry, native TLS verification flags, no remote call for local preparation, and successful cache reuse. A wheel check verifies the snapshot/manifest are shipped. No user app process was stopped or app port occupied; temporary browser QA is cleaned up after verification. Existing user process needs one restart using start.cmd to activate the new source.


## Stage 6 experimental serving — 27 October 2026

User-selected layout: prediction output sits directly beneath the map, with facility inputs on the right. Save site → Prepare site context → Generate experimental estimate. The backend uses the selected verified Random Forest and all 11 server-derived features. Display total planned charging points using nearest-half-up and minimum one; retain raw output. No automatic inference on pin movement and no retraining in the application.

Every saved estimate includes immutable site/features/source/adoption/rule/model provenance and the unverified POI status. Request UUID and site revision prevent duplicate/conflicting retries; database uniqueness and final ownership/session/revision checks cover concurrency. Results clear when the draft changes. Site history retains the experimental label and calculation/input details. Model startup checks exact hash/runtime/features/selected parameters and reproduces ten saved fixtures; missing/incompatible models fail visibly.

Original live/training POI-rule parity remains unresolved. The development action explicitly requests an experimental result; it does not change inference_eligible=false or claim model accuracy for the new counts. Production rejects these unverified inputs. Stage 6 validated completion remains pending that dependency. Experimental local workflow passed 66 backend / 27 frontend tests, build and genuine browser-to-history verification. See docs/STAGE_6_IMPLEMENTATION.md.


### 2026-10-27: repeated 5/10 prediction audit

The serving pipeline calls the verified trained Random Forest; there is no fixed charger-output rule. Nearest-half-up rounding compresses many non-mall raw outputs near 5. Controlled sparse/medium/dense Unknown-category inputs produced 4.959528, 4.845304 and 5.258004; the medium example with Shopping Mall category produced 9.908197.

A diagnostic five-fold shuffled coordinate-group CV (seed 42) on the supplied 764 prepared rows gave MAE: category/state/adoption only 2.8719; POIs only 3.6429; all selected features 2.9441; a more flexible RF (300 trees, depth 10, leaf 2) 3.1320; training-fold median baseline 3.1204. These are exploratory diagnostic results on previously inspected data, not an independent final evaluation. More flexible settings increased output variety but worsened MAE; variety alone is not a valid model-selection criterion.

Five checked original site coordinates had materially different app versus supplied training POIs. At source row 0, supplied counts included 6 petrol stations and 6 offices, whereas the current 3 km app extractor returned 33 petrol stations and 34 offices. This establishes an input consistency problem; it does not establish which radius or historical mapping generated the supplied counts. Do not silently relabel those original counts as matching the app.

Next corrective work: preserve the original dataset; regenerate a versioned training POI dataset at every training-site coordinate using the exact same snapshot, radius, classification and deduplication code as the app. Evaluate category-only, POI-only and combined models with the same folds, checking error and sensitivity. Replace the served artifact only if the rebuilt model supports a useful relationship and passes validation. The current model must not be described as a validated location-specific capacity recommendation.


### Fresh MEVnet export (27 October 2026)

Created data/ML Data/updated_mevnet.csv directly from the official service: 1,911 records (Selangor 1,334; KL 577), comprising 764 Existing and 1,147 Newly Proposed. All 49 source attributes retained, nulls preserved. Prior 764-row prepared dataset only included Existing sites. This new export has no engineered POIs yet and has not replaced the serving model. Provenance and raw response retained under data/updated_mevnet_source/.


### Updated MEVnet POI preparation completed (27 October 2026)

updated_mevnet.csv now contains all 49 official fields plus engineered total_planned_chargers, eight app-identical 3 km OSM POI features, summed POIs, fixed 2025 adoption, per-row provenance and quality flags (70 columns). 1,910 POI extractions complete; one missing-coordinate row has blank POIs. Four source-state/coordinate-state mismatches flagged. 1,906 rows preprocessing-eligible. All source attributes and all charger sums verified after CSV round trip. Missing/nonfinite coordinate checks and genuine site parity with app also checked. Raw source retained separately. Next step is model development/evaluation using this dataset; current served artifact unchanged.


### Agreed radius changed to 1 km; clean matrix rebuilt (27 October 2026)

User requested 1 km and removal of unused columns/observations. Rebuilt all POIs with explicit 1,000 m query and extraction filters. Current output data/ML Data/updated_mevnet_1km.csv (updated_mevnet.csv is Windows-locked and remains 3 km): 1,902 rows, eight POI fields + state adoption + category + state + total target. Nine rows excluded: four state-coordinate mismatches, four zero totals outside positive-capacity scope, one missing coordinate. No missing matrix cells, constant columns or exact site duplicates. Unknown category retained for 1,139 proposed sites; assess missingness/category confounding. All source attributes, charger components and row-coordinate mappings retained outside model matrix. App/model remain on old 3 km until coordinated retraining and serving update. Twelve POI tests passed including explicit 1 km-versus-3 km boundary behaviour.


27 October 2026 filename resolution: file lock released; updated_mevnet.csv now contains the verified 1 km matrix (1,902 observations, 12 columns). updated_mevnet_1km.csv is an identical backup. The preparation manifest now identifies updated_mevnet.csv as the current training file.


27 October category recheck: corrected earlier statement that all proposed sites lacked categories. Actual main-layer nulls: 1,146 Newly Proposed + one Existing; one proposed site is Showroom. Prior 764 rows cannot restore missing categories (the matching old row is already Unknown). Six verified name/state/coordinate matches from dashboard coverage layer restored. Current category-corrected dataset is updated_mevnet_1km.csv because updated_mevnet.csv is locked again; 1,902 rows, 1,133 remaining Unknown. Audit and verified overrides retained under data/updated_mevnet_source/.


27 October host-category enrichment: current data/ML Data/updated_mevnet.csv has 1,902 rows; 1,528 categorised and 374 Unknown (previously 1,133 Unknown). Applied 759 OSM-inferred labels to eligible rows, plus the six earlier official coverage recoveries. Raw-level matcher assigned 761 of 1,141 missing-category sites from real host name/coordinate/footprint evidence. Supplied categories preserved. No arbitrary proximity assignment or forced Others fallback. Per-site evidence, OSM URLs and uncertainty retained under updated_mevnet_source/; inferred labels require review and are distinguished from official labels. Sixteen targeted tests passed. Current model/app unchanged.


27 October extended category review: user explicitly requested analyst deductions from original names/coordinates and additional location evidence. Current updated_mevnet.csv: 1,902 rows, 1,899 categorised, three Unknown (Kebun KL, Virgin Resources, WC Meranti Management). Reduced remaining Unknown from 374 to three using 318 raw explicit-description deductions and 59 researched raw site deductions (371 eligible records). Preserved all official categories, target sums and 1 km POI columns; verified against prior backup. Evidence/source/reasons in category_research_audit.csv and separate overrides. Deduced labels are inferred, not official ground truth. Nineteen targeted tests passed. Serving model/app unchanged.


### POIs + category + state Colab notebook (27 October 2026)

Created notebooks/CastraVolt_POI_Category_State.ipynb using data/ML Data/updated_mevnet.csv and matching updated_mevnet_row_groups.csv. Inputs are eight 1 km POI counts plus category and state; adoption is excluded. Target is total_planned_chargers under the existing-plus-additional-proposed assumption. Seed 42; random coordinate-group-preserving 50/50, 70/30, 80/20, 5/10 CV and the six split-plus-CV setups; Random Forest, XGBoost, always-three and training-median baselines; nearest-half-up minimum-one display rounding. Full mode runs 30 sampled settings per tuned model/setup. Inferred category labels and overlapping nearby-site POIs limit interpretation. Local smoke run executed all 11 setups against 1,902 rows and produced 96 score rows; feature exclusion, grouping, outputs and rounding verified. Full-budget training and actual Colab upload/Drive were not executed; no serving model changed. See notebooks/README.md.


27 October feature cleanup: removed state_ev_registrations from updated_mevnet.csv and its 1 km backup, plus adoption fields from derived audit tables. Current dataset has 1,902 unchanged rows and 11 columns: eight POIs, category, state and total_planned_chargers. Preparation script will not re-add adoption. Updated preparation hash and rebuilt CastraVolt_POI_Category_State.ipynb to accept the revised dataset. Registration source files retained separately for the dashboard.


### Full 1 km result archive audited (27 October 2026)

Both dataset hashes and all saved evaluation metrics verified. Uploaded candidate is default all-data RF, not tuned evaluated model. Recommended RF80/CV10 on training-CV evidence (1.90255 vs XGB 1.93471), with explicit post-hoc selection limitation; reconstructed evaluated artifact under model/verified_poi_state_rf80_cv10 reproduces all 380 saved test predictions. MAE 2.01239, rounded MAE 1.97895, within-two 80%; 10+ target sites MAE 6.9988. Important diagnostic: RF category+state-only CV MAE 1.89358 vs all features 1.90255, so no demonstrated POI benefit in that configuration. XGB shows some POI signal but category dominates both. Original app/model not replaced. See docs/POI_MODEL_HANDOFF.md and artifact diagnostic files.


## Current model integration — 27 October 2026

This decision supersedes earlier 3 km/adoption prediction specifications. The estimator uses eight POI counts within **1 km**, the confirmed host-site category and boundary-derived state. EV registration numbers are excluded from prediction; keep 2024–2026 data for the future monthly trends dashboard.

The selected evaluated Random Forest is `model/verified_poi_state_rf80_cv10` (80/20 with training-only CV10). Results appear below the map, estimate total planned charging points, and use nearest whole number with halves upward and minimum one. Exact model, query-rule and OSM snapshot compatibility is required. New history stores no adoption context; old history is preserved. Research prototype wording reflects measured capacity accuracy limits, not a placeholder model. See BACKLOG.md and RESULTS.md for implementation status and validation.
>>>>>>> Stashed changes
