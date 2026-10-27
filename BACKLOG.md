# CastraVolt backlog

Updated 27 October 2026. Current release scope: integrate the evaluated **1 km POIs + host category + state** model. This is research planning guidance trained on MEVnet totals.

## Completed in this update

- [x] B01 — Serve the selected evaluated RF (80/20 + training CV10), with trusted artifact checksum, runtime, parameter and prediction-fixture checks.
- [x] B02 — Use the same 1,000 m extraction rules and bundled OSM snapshot as training. Six genuine training-site feature vectors match the current extractor. Incompatible provenance blocks prediction.
- [x] B03 — Enforce ten inputs: eight POI counts, confirmed host-site category and derived state. Remove EV registrations from new model inputs and snapshots.
- [x] B04 — Show the 1 km map circle and facility context; retain the prediction output below the map. Replace obsolete unverified-extraction messages with measured model limitations.
- [x] B05 — Preserve old prediction history; allow null adoption columns for new predictions through migration 0007_optional_adoption. Keep ownership, CSRF, stale-edit checks and idempotent retries.
- [x] B06 — Verify application tests (80 backend, 27 frontend), frontend production build and an isolated browser flow. Record model results and real API examples in RESULTS.md.

## Next work, in suggested order

- [ ] B07 — **High: review inferred host categories.** Deliver a reviewed category/evidence audit, prioritising researched and description-derived labels and the three remaining Unknowns. Acceptance: every changed label has evidence and datasets/results are versioned before retraining.
- [ ] B08 — **High: measure useful POI contribution.** Compare separately tuned POI+category+state and category+state baselines under one declared evaluation protocol. Acceptance: report CV results and per-category errors, including cases where POIs do not improve prediction. Never force numerical variety.
- [ ] B09 — **High: independent evaluation.** Reserve genuinely unseen sites before choosing the next model; optionally use geographical groups to assess nearby-site overlap. Acceptance: freeze selection before opening final test results. Current eleven experiments reuse observations and are exploratory.
- [ ] B10 — **High: larger-site reliability.** Inspect 10+ target sites and underestimated extremes. Acceptance: report errors by target band and category; define how the UI communicates low confidence using training-only calibration if intervals are introduced.
- [ ] B11 — **Medium: urban and supply scope.** Add an evidenced urban-area layer if the app must enforce urban-only coverage. KL/Selangor boundaries alone include nonurban places. Sparse existing infrastructure may inform a separate contextual view; the current model does not measure unmet demand.
- [ ] B12 — **Medium: monthly EV trends dashboard.** Reuse filtered fully electric motorkar registration data from 2024–2026 with state and date filters, partial-year labelling and source dates. Keep registrations separate from this predictor.
- [ ] B13 — **Medium: snapshot refresh workflow.** Rebuild and version training features, catalogue hashes, model and parity fixtures together. Acceptance: no refreshed map source silently feeds the old evaluated artifact.
- [ ] B14 — **Before wider deployment: access and operations.** Replace the shared local admin demo with managed individual planner accounts, backup/restore, deployment configuration and operational checks. Research inference remains restricted to development; changing that restriction needs a separate deployment decision.

## Operating note

Restart with `start.cmd` after stopping the old app so startup applies migration 0007 and loads the new default model. If an existing environment explicitly overrides CASTRAVOLT_MODEL_DIRECTORY, point it at model/verified_poi_state_rf80_cv10. Old artifacts are retained for historical reproducibility. No changes were made to the user's running ports 8000/5173.
