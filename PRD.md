# CastraVolt Product Requirements Document


> Current internal scope (27 October 2026): shared demo login `admin` / `123`; no public registration, verification or password recovery. Everyone using this account shares its projects, sites and history. Database ownership/session/CSRF checks remain. Earlier individual-account requirements below describe retained future capability and are superseded for this prototype. Demo access is development-only; production rejects it.

Status: Prototype specification

Updated: 27 October 2026

## 1. Purpose

Help infrastructure planners estimate the total number of charging points for a proposed new site in urban Selangor or Kuala Lumpur.

The planner selects a location. CastraVolt gathers surrounding facilities, accepts the site's category, looks up the configured EV registration count for the site's state, and returns an estimated total planned charging-point count. EV registration trends also provide background information in a separate dashboard view.

This is an FYP decision-support prototype. The prediction represents patterns in a constructed MEVnet planning target, not independently measured optimal demand or a guarantee of waiting times.

## 2. Users and scope

Primary user: a planner evaluating a proposed new EV charging site.

The internal prototype uses the shared admin account described above. Login opens its persistent Projects workspace. Individually provisioned accounts can be added later if planners require separate workspaces.

Supported states: Selangor and W.P. Kuala Lumpur. The study concerns urban sites; support for every coordinate in these states is not implied. An urban-area boundary or explicit urban study extent must be selected before enforcing an urban-only location check.

Primary tasks:

- Select a proposed site and obtain an estimated total charging-point count.
- Inspect the surrounding POI information used for the estimate.
- View monthly EV registration trends for the two states.

Out of scope for the initial prototype:

- Automatically finding the best site or optimising an entire charging network.
- Recommending additional chargers for an existing site.
- Separately recommending AC/DC equipment, power ratings, or connector types.
- Live charger availability, bookings, navigation, pricing, installation costs, and grid-capacity assessment.
- Predicting local EV ownership from state registration totals.
- Learning the complete 2024–2026 adoption growth series or forecasting its effect from the current fixed-state registration feature.

## 3. Product decisions

- Use the adoption-enabled full-run model, as selected by the user. The adoption comparison showed negligible improvement in the strongest reported setup; do not claim a demonstrated accuracy gain.
- Use all three registration sources for trends. The model's additional feature uses the configured 2025 state total, not the complete 2024–2026 series.
- Prediction features: eight nearby POI counts, site category, state, and `state_ev_registrations` (11 features).
- POI radius: 3,000 metres (3 km), matching the existing engineered dataset as confirmed by the project owner. This supersedes the earlier 1 km proposal. Reproduce the original geometry/distance handling.
- Use all 23 MEVnet site categories, with Unknown as a missing-data fallback.
- Selected model candidate: Random Forest, 80/20 random split with five-fold training CV. Ten-fold CV produced the same reported holdout scores; five-fold is less expensive.
- Round displayed counts to the nearest integer, with exact halves upward. Use a configurable minimum of one as the initial implementation default; record this as a product rule rather than a validated demand threshold.

## 4. Planner experience

1. Open the site-estimation view.
2. Search for an address or place a pin on the map.
3. Confirm the site's category. The application may suggest a category when reliable matching information is available, but the planner can correct it.
4. Request an estimate.
5. The application validates the location, derives the state, gathers the eight nearby POI counts, looks up that state's configured registration total, prepares features, and obtains a prediction.
6. Show the estimated total charging points, site category, location, POI radius, POI counts used, and registration indicator's state and reference year.

Moving the pin or changing category invalidates the previous recommendation. A new estimate must be requested. Show loading and retry states while gathering POIs and predicting.

The planner does not manually enter POI counts, state registration figures, or existing onsite charger counts. This flow is intended for new sites.

## 5. Prediction inputs and output

### User inputs

- Latitude/longitude through map selection or address search.
- Confirmed site category.

### Automatically prepared model features

- `nearby_mall_count`
- `nearby_petrol_count`
- `nearby_hotel_count`
- `nearby_office_count`
- `nearby_transit_count`
- `nearby_university_count`
- `nearby_hospital_count`
- `nearby_parking_count`
- `category`
- `state`
- `state_ev_registrations`

Coordinates identify the state and POI search area; they are not direct model features in the selected experiment. Do not supply IDs, existing/proposed counts, installed AC/DC counts, indoor/outdoor counts, or nearby total POI count as extra inputs to the exported pipeline.

The registration lookup uses `ADOPTION_MODE = fixed_period_context` and `ADOPTION_REFERENCE_YEAR = 2025`, consistent with the current adoption-enabled notebook configuration. From the filtered 2025 CSV, use 560 new electric motokar registrations for SELANGOR and 1,237 for W.P. KUALA LUMPUR. Validate these values against the deployed model's source hashes and configuration before integration; changes require a versioned data/model update. These are filtered new registrations, not complete fleet estimates. The same state value is repeated for all sites in that state.

The user does not enter or edit the indicator. Missing or unsupported lookup values produce an error, not a zero or an automatic switch to another year. This retrospective state-context feature does not establish neighbourhood adoption or a causal growth effect.

### Output

Primary label: **Estimated total charging points**.

Display `max(1, floor(raw_prediction + 0.5))` using the initial configurable minimum. Fractions below 0.5 round down; fractions at or above 0.5 round up: 3.2 becomes 3, 3.5 becomes 4, and 3.9 becomes 4. Do not use ties-to-even rounding. Retain the raw estimate internally for traceability. The output is total site capacity, not a number of additional chargers or a recommendation for a particular charging speed.

Explain briefly that the estimate is based on surrounding facilities and MEVnet planning records. Do not label it verified optimal capacity or display an invented confidence percentage. Any uncertainty interval would require separate calibration and validation.

## 6. Site categories

Use these source labels consistently in training, selection controls, and prediction:

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

Unknown is an explicit fallback for missing information. Do not silently assign a category based on proximity alone.

## 7. POI extraction requirements

Source: OpenStreetMap data, queried through Overpass API or a compatible managed Overpass service that preserves the agreed feature definitions.

The frontend displays an OpenStreetMap-based map through a map rendering library and an appropriate tile provider. A planner can drop or move a pin and see a circle with a 3 km ground-distance radius centred on that pin. The displayed circle represents the search area; displaying map tiles or drawing a circle does not retrieve POIs.

On an explicit estimate request, the frontend sends the selected site's coordinates/category to FastAPI through the owned-site workflow. The backend queries Overpass around those coordinates with radius 3,000 metres, maps returned facilities into the eight POI groups, deduplicates them, and combines counts with the derived state, confirmed site category, and configured adoption lookup before inference. Do not issue a full extraction on every map movement.

Results represent qualifying facilities mapped in OpenStreetMap, not a guaranteed complete inventory of real-world facilities. Explain this coverage limitation where the POI inputs are presented. Distinguish map tile, address search/geocoding, and POI data services; they may use separate providers and are not interchangeable.

- Count the eight facility groups within 3 km of the selected pin, matching the original engineering method. Confirm its exact geometry/distance handling rather than changing it silently.
- Define explicit tag mappings, geometry/distance rules, and facility-matching criteria before implementation.
- Remove repeated elements using OpenStreetMap element type plus ID.
- Count each distinct facility once within a group. Merge clearly matching point/polygon representations of the same facility under reproducible rules.
- Do not merge different facilities solely because they share coordinates or a building.
- A complex can contribute distinct qualifying facilities to different groups, such as a mall and its parking facility.
- Use identical extraction code and rules for training features and application predictions.
- Preserve extraction time and rule version with prediction diagnostics.
- Honour the data provider's attribution and service usage requirements.
- Cache validated successful POI lookups with their location, radius, extraction-rule version and timestamp. Apply request limits and provider-aware timeouts/retries for multiple planners. Public map tile and Overpass services have separate usage policies and availability constraints; choose services appropriate to expected demand.

The project owner confirms the supplied training POIs were already engineered using a 3 km radius. Preserve those counts and use 3 km for application extraction. This resolves the earlier unknown-radius issue; the original script, tag mappings, geometry handling, duplicate rules, and extraction date still need to be recovered or checked for reproducibility. Do not claim they have been independently verified. The radius clarification alone does not require regeneration or retraining. If counting definitions change or cannot be reproduced, regenerate consistent training features and retrain before claiming matching live estimates. The notebook's earlier 1 km configuration and unknown-radius wording must also be updated before subsequent runs or integration.

An unsuccessful POI request is not a count of zero. Show an error and retry option. Valid zero counts are acceptable only after a successful response.

## 8. EV registration trend dashboard

Provide a dedicated **EV adoption trends** dashboard using monthly new electric motokar registrations as the adoption indicator. Explain the indicator in the dashboard: it measures filtered new registrations, not total EV ownership.

Use the filtered CSVs in `data/ML Data`:

- `ev_registration2024.csv`: January–December 2024.
- `ev_registration2025.csv`: January–December 2025.
- `vehicles_2026.csv`: January–September 2026.

Scope: `fuel = electric`, `type = motokar`, state Selangor or W.P. Kuala Lumpur. Rakan Niaga and other states are excluded. SUVs classified as jip and all other vehicle types are excluded.

Requirements:

- Default view: both states, all available months from January 2024 through September 2026, monthly aggregation.
- State filter: both states, Selangor only, or Kuala Lumpur only. When both are selected, show separate labelled series rather than silently combining them.
- Year filter: all available years, 2024, 2025, or 2026. Support selecting multiple years for comparison.
- Month-range filter: inclusive start/end months within the selected available coverage. Reject reversed ranges and clearly show the active period.
- Comparison mode: chronological timeline or year-over-year comparison aligned by calendar month, with series labelled by state and year. In year-over-year mode, apply the same month window to each selected year.
- Reset filters action restores the default view. State, year, and period filters update the chart and summaries together.
- Summary metrics: new registrations in the selected period, average per covered calendar month, and percentage change versus the same months of the previous year when that complete comparable period exists.
- Calculate averages over covered months, including genuine zero-count months. Never treat months outside source coverage as zero. Suppress percentage growth when the comparison period is missing, incomplete, or has a zero denominator, and explain why it is unavailable.
- If filters produce no covered months, show a clear empty state; do not display fabricated zero totals or growth.
- Show source scope and coverage near the chart: 2024/2025 full years, 2026 January–September. Do not plot October–December 2026 as zero registrations.
- The chart must label month and new registrations (vehicles), show a series legend, and support inspecting exact monthly counts. Provide an accessible monthly data view.
- Filters operate on pre-aggregated monthly records derived from the existing CSVs; the application does not need to repeatedly upload or process raw vehicle records.

- Show monthly new registrations, with separate state series and a state filter.
- Show the selected period and source coverage clearly.
- Label 2026 as year-to-date through September, not a full-year total.
- Use matching month ranges for year-over-year growth comparisons.
- Describe the metric as new electric motokar registrations, not total EV fleet or neighbourhood adoption.
- Explain that records labelled Rakan Niaga are excluded, limiting geographical coverage.
- Preserve repeated registration records; do not deduplicate them simply because their attributes match.
- Keep the trend view separate from the prediction lookup. The service consumes only the fixed configured 2025 state total; chart filters and other years do not alter it. Do not imply that the model learns the entire monthly growth series.

## 9. Model and evaluation

### Target

`total_planned_chargers = number_of_existing_ev_charger_s + number_of_proposed_ev_charger__`.

This uses the project owner's authorised interpretation that proposed counts represent additional chargers. Official field aliases alone do not independently establish that interpretation. If the field instead represents historical totals or realised proposals, revisit the target and retrain; do not silently change its meaning.

MEVnet describes its count units as charging points with parking bays representing simultaneous charging.

### Reported selected experiment with adoption

Random Forest, 80/20 split with five-fold training CV:

- Raw MAE: approximately 2.62219 charging points.
- RMSE: approximately 3.76716 charging points.
- R²: approximately 0.41543.
- Historical ceiling-rounded MAE: approximately 2.7582 charging points.
- Nearest-half-up rounded MAE: approximately 2.62092 charging points, verified locally against all 153 saved test predictions after reconstructing the selected tuned pipeline. This is not a fresh independent test set.

Re-evaluate the same saved raw predictions under nearest-half-up and ceiling, reporting rounded MAE and underestimation frequency. No retraining is required for this comparison. Raw metrics are unaffected by the display rounding change. The notebook currently implements ceiling and needs to be aligned with this PRD before new application-ready exports.

These are user-supplied full-run results, not a fresh independently reproduced evaluation. CV-only results were weaker; report all experiments in the FYP rather than only the strongest holdout. Do not turn an observed best test score into a claim of unbiased final-model selection.

### Deployment artifact

Use the selected adoption-enabled Random Forest pipeline and its exact preprocessing/feature schema. Retrieve the selected hyperparameters from the corresponding full-run search results and preserve evaluation metadata, including adoption mode, reference year, and state lookup values. Set `USE_ADOPTION = True` when reproducing this run; the notebook's current default is False.

The current notebook's `deployment_candidate.joblib` is a separately refitted candidate using configured parameters; it does not automatically preserve the winning tuned configuration. Before integration, export the evaluated tuned pipeline or explicitly refit a deployment candidate with its chosen parameters and record that its evaluation refers to the earlier held-out experiment. Retraining on all sites does not provide a new independent test score.

Keep models server-side. Version the model, feature schema, extraction rules, rounding policy, and source-data hashes. Include those versions in prediction diagnostics.

## 10. Functional acceptance criteria

- A planner can select a supported location, choose a category, and request an estimate.
- State is derived from the selected location; unsupported states produce a clear message.
- Each prediction receives exactly the selected model's eleven feature columns, with compatible types and training preprocessing.
- POI radius and counting rules agree with the training feature definition, or the interface explicitly identifies the result as provisional.
- The map displays a 3 km circle centred on the selected pin. Only an explicit estimate request triggers backend POI gathering; visual map rendering alone never supplies or implies validated POI counts.
- Duplicate OpenStreetMap representations do not inflate a facility count under the implemented rules.
- Unavailable POI data cannot silently become zeros or a successful prediction.
- Successful output is an integer produced by the nearest-half-up/minimum policy. Verify examples 3.2 → 3, 3.5 → 4, and 3.9 → 4, plus configured minimum handling.
- Changing location or category cannot leave an old recommendation presented as current.
- Registration charts reproduce the filtered source counts, distinguish states, and clearly label 2026 coverage.
- State/year/month-range filters and comparison mode update monthly charts and summary metrics consistently. Same-period growth is calculated only from complete comparable coverage, and unavailable 2026 months are not zero-filled.
- The correct 2025 registration value is supplied automatically for the derived state. Trend filters cannot alter the lookup, and missing values cannot silently become zero.
- The prediction service loads the intended adoption-enabled model artifact, not an accidental no-adoption model, smoke model, or default refit.
- The result identifies an estimate of planned capacity and makes no claim of verified optimal charger demand.

## 11. Data, errors, and traceability

- Keep raw and filtered source datasets unchanged by the application.
- Provide friendly errors for geocoding failure, unsupported locations, POI timeout, model unavailability, and invalid input.
- Record model and feature versions, selected category, extracted counts, registration value/reference year, raw estimate, rounded count, and extraction timestamp for debugging. Do not introduce persistent user-location logging without a defined need and retention policy.
- Test the application with recorded feature fixtures as well as real POI responses so external service failures can be distinguished from prediction failures.
- Require individual planner authentication for projects, sites and saved predictions. Enforce ownership in the backend so planners cannot access another account's records. Technical requirements are in TRD.md.

## 12. Implementation order and outstanding details

1. Recover the selected adoption-enabled full-run model parameters/artifact and verify the eleven-input pipeline and configured 2025 state registration lookup.
2. Reproduce the original POI tags, geometry handling and duplicate matching at the user-confirmed 3 km radius. Keep the existing engineered features unless definitions must change or cannot be reproduced; in that case regenerate and retrain.
3. Select the urban study boundary, map/geocoding provider, POI service, application framework, and hosting environment.
4. Implement the estimator flow and result states.
5. Implement registration summaries and trend view separately from prediction.
6. Validate the acceptance criteria and document modelling limitations in the FYP.

No additional hyperparameter search is a prerequisite for developing the interface. Data-rule compatibility and correct model export are prerequisites for claiming that live application estimates reproduce the selected experiment.


## Stage 4 implementation — 27 October 2026

The active estimator uses Leaflet 1.9.4 with OpenStreetMap tiles and visible attribution. Project workspace offers Add site on map and Open on map; the sidebar estimator starts with a project chooser. Planners can submit an address search, click the map, drag the pin or use numeric coordinates. A 3,000 metre Leaflet Circle follows the pin. Confirm the host-site category before saving; nearby POIs do not determine that category. Saving creates or updates an owned site without running ML.

State is derived server-side from bundled, hash-checked Selangor/Kuala Lumpur state polygons (geoBoundaries MYS ADM1, OSM/Wambacher, 2017, ODbL 1.0). Unsupported/ambiguous boundary points are rejected, including Putrajaya. This is a reproducible research boundary with provisional urban-only coverage, not current cadastral verification. User-supplied state fields are forbidden. Moving the pin invalidates prior validation/saved state, clears the stale address, and requests category reconfirmation.

Address search uses a configurable server-side Nominatim endpoint, explicit submission only, bounded time/response size, provider identification, seven-day successful-result caching and a PostgreSQL global 1.1-second reservation. No autocomplete, searches on every keystroke, or POI/inference on map movement. Search/map failures expose retry/manual alternatives. Browser generation/abort guards prevent late responses replacing current selections. Standard tile requests retain provider attribution, browser caching and origin referrers.

Public OSM/Nominatim endpoints are low-volume development defaults, not a production capacity promise. Configure suitable providers for wider use. Provider details, source hashes, licensing and checks are recorded in docs/STAGE_4_IMPLEMENTATION.md. Existing-site records with unresolved state remain unchanged until a coordinate update; Stage 5/6 must independently validate state before using adoption context.


### Map-only refinement — 27 October 2026

User decision supersedes earlier manual-coordinate alternatives: create and edit sites through the map only. Remove the separate Add site form and inline site editor. Project workspace offers Add site on map and Open on map. Coordinates are displayed read-only; state is derived on the server from the selected pin. Address is reverse-geocoded automatically after the pin settles (1.2 second debounce), or reused from an address search. Name and host-site category remain planner inputs; category is not inferred from nearby facilities.

Reverse lookup shares the existing global provider quota/cache, uses local state polygons rather than the provider's state label, aborts/discards stale responses and can be retried. Save waits for pending address lookup; if lookup fails, address remains optional and the valid pin/state can still be saved. POI/adoption feature extraction remains Stage 5. The observed Not Found response was traced to an older running backend with no location routes; restart once via start.cmd. Local startup now enables source-directory backend reload. User app ports/processes were inspected but not stopped or occupied.


## Stage 5 feature preparation — 27 October 2026

After saving a site, Prepare site context explicitly requests server-side facilities within 3,000 metres. The backend reads the owned site's pin/category, derives its state, gathers eight counts (mall, petrol, hotel, office, transit, university, hospital, parking), and appends fixed 2025 registrations (Selangor 560, KL 1,237), category and state: 11 model fields. Registration context is reconciled from the filtered CSV and packaged with source hash/scope. The 2024–2026 series remains available for the later trends dashboard; it is not dynamically substituted into the model lookup.

Counts/provenance are cached by exact location, radius, rule fingerprint and provider. Provider failures/incomplete results are errors, not zero facilities. Changes cancel or clear displayed context, and backend rechecks site revision/session/ownership after extraction. No inference or saved charger prediction happens at this stage.

Original training extraction definitions are still unavailable. New counting rules are explicitly provisional, with inference_eligible=false; they cannot be claimed equivalent to the training POIs. Original rules plus genuine site parity checks, or consistent POI regeneration and retraining, remain necessary. Live provider availability also remains unverified after TLS/timeout failures. See docs/STAGE_5_IMPLEMENTATION.md for exact tags, geometry, deduplication, cache/error behavior and evidence. Stage 5 is pending that dependency, despite the implemented service/UI.


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
