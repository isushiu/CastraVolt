# Colab Training Implementation Plan

**Goal:** Deliver a self-contained Colab notebook loading the four ML Data CSVs, auditing and preparing data, training Random Forest and XGBoost, and evaluating the 11 agreed setups.

**Spec:** PROJECT_NOTES.md. User authorised notebook implementation after planning.

**Architecture:** Notebook cells contain all execution code. A local builder emits standard notebook JSON. Colab supports Drive or direct multi-file upload. Artifacts include diagnostics, split assignments, metrics, predictions, models and metadata.

**Constraints:** seed 42; random coordinate-group-preserving splits; untouched test portions during tuning; 30 search combinations; raw and ceiling metrics; preserve source data; no claim of verified optimal demand; no invented POI radius provenance or adoption temporal match.

- [x] Create notebook validation covering required files, safe preprocessing, grouped splits, rounding, and all 11 setups.
- [x] Implement loading, schema checks, source audit, target construction verification and optional adoption lookup.
- [x] Implement leakage-safe preprocessing, fixed models, grouped CV, tuning and baseline comparisons.
- [x] Add outputs, charts, export and deployment example using prepared feature values.
- [x] Validate notebook structure and compile all Python cells; execute smoke experiments if dependencies can be installed. Report limitations candidly.

Rulings: use a configurable minimum displayed count of one (clearly labelled default); adoption disabled by default until period definition is defensible; existing POIs allowed only as explicitly provisional. Full runs are opt-in. No remote publication or real training results are implied by notebook creation.
