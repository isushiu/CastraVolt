# ML data preparation

Prepared 26 October 2026. Original files in the parent folder are unchanged.

## Contents

- `mevnet_ev_charging_demand_labelled_dataset.csv`: parent-folder MEVnet records with one added derived target column, `total_planned_chargers = number_of_existing_ev_charger_s + number_of_proposed_ev_charger__`. All original columns, values, and row order are preserved. All 764 sums were checked after saving. The parent source file is unchanged.

## Target interpretation

The user authorised the total calculation based on interpreting proposed chargers as additional chargers. This is the selected modelling assumption, not a definition independently established by the official field labels. If proposed values represent historical totals or already installed plans, adding them could double-count. Keep the two source columns for traceability, but do not use either as an input for predicting this target. Installed AC/DC and indoor/outdoor counts should also be excluded as direct capacity components unavailable for a proposed new site.
- `ev_registration2024.csv`: 2,688 retained registration records (Selangor 792; Kuala Lumpur 1,896). Full-year source.
- `ev_registration2025.csv`: 1,797 retained registration records (Selangor 560; Kuala Lumpur 1,237). Full-year source.
- `vehicles_2026.csv`: 1,916 retained registration records (Selangor 606; Kuala Lumpur 1,310). January–September source.

## Exact registration filters

- `fuel = electric`, excluding hybrids and other fuels.
- `state` is exactly `Selangor` or `W.P. Kuala Lumpur`.
- `type = motokar` in all three years, as requested by the user.

This uses the user's narrower scope of the source's `motokar` type. SUVs classified as `jip`, multipurpose vehicles, pickups, window vans, and motorcycles are excluded. These counts therefore do not represent every electric passenger vehicle.

## Handling and limitations

- No records from `ev_registration2026.csv` or its workbook were used.
- `Rakan Niaga` and all other state values are excluded. These files contain records explicitly labelled with the requested states; they should not be interpreted as complete local EV adoption counts without resolving the source's state-field meaning.
- Source columns, values, row order, and repeated records are retained. No deduplication or monthly aggregation was performed.
- These are filtered registration inputs, not an integrated training matrix. State-level registration features still need to be defined and matched to the model data.
- Compare matching periods when assessing growth: 2026 is not a full year.
- Registration outputs were reopened and checked for row counts, electric fuel, permitted states, and car category where available. The MEVnet copy was originally verified byte-for-byte; after adding the target, all original values and row order were verified unchanged and all 764 target sums were checked.


## updated_mevnet.csv (27 October 2026)

Fresh official MEVnet data, filtered to Selangor/KL, now enriched with the exact app OSM 3 km POI extraction method. Contains 1,911 rows, 70 columns, preserved existing/proposed charger counts, derived total target and fixed 2025 state adoption. Of these, 1,906 pass preprocessing checks; one missing-coordinate row and four source/coordinate-state mismatches remain flagged. See ../updated_mevnet_source/README.md and preparation_manifest.json. Current served model is unchanged.


## Current dataset: 1 km (27 October 2026)

Use updated_mevnet_1km.csv: 1,902 rows, 11 inputs and one total target. POIs recalculated at 1 km; nine invalid/out-of-scope observations removed. Original updated_mevnet.csv is locked and remains the old 3 km file. Raw counts, row-coordinate mappings, exclusions and source provenance are under ../updated_mevnet_source/. See that README for full handling, including 1,139 missing categories retained as Unknown.


27 October 2026 filename resolution: file lock released; updated_mevnet.csv now contains the verified 1 km matrix (1,902 observations, 12 columns). updated_mevnet_1km.csv is an identical backup. The preparation manifest now identifies updated_mevnet.csv as the current training file.


27 October category recheck: corrected earlier statement that all proposed sites lacked categories. Actual main-layer nulls: 1,146 Newly Proposed + one Existing; one proposed site is Showroom. Prior 764 rows cannot restore missing categories (the matching old row is already Unknown). Six verified name/state/coordinate matches from dashboard coverage layer restored. Current category-corrected dataset is updated_mevnet_1km.csv because updated_mevnet.csv is locked again; 1,902 rows, 1,133 remaining Unknown. Audit and verified overrides retained under data/updated_mevnet_source/.


27 October host-category enrichment: current data/ML Data/updated_mevnet.csv has 1,902 rows; 1,528 categorised and 374 Unknown (previously 1,133 Unknown). Applied 759 OSM-inferred labels to eligible rows, plus the six earlier official coverage recoveries. Raw-level matcher assigned 761 of 1,141 missing-category sites from real host name/coordinate/footprint evidence. Supplied categories preserved. No arbitrary proximity assignment or forced Others fallback. Per-site evidence, OSM URLs and uncertainty retained under updated_mevnet_source/; inferred labels require review and are distinguished from official labels. Sixteen targeted tests passed. Current model/app unchanged.


27 October extended category review: user explicitly requested analyst deductions from original names/coordinates and additional location evidence. Current updated_mevnet.csv: 1,902 rows, 1,899 categorised, three Unknown (Kebun KL, Virgin Resources, WC Meranti Management). Reduced remaining Unknown from 374 to three using 318 raw explicit-description deductions and 59 researched raw site deductions (371 eligible records). Preserved all official categories, target sums and 1 km POI columns; verified against prior backup. Evidence/source/reasons in category_research_audit.csv and separate overrides. Deduced labels are inferred, not official ground truth. Nineteen targeted tests passed. Serving model/app unchanged.


The POI/category/state Colab notebook also requires updated_mevnet_row_groups.csv, a matching copy of the row provenance that keeps exact same-coordinate sites together when splitting. It is not an ML feature file. Use it together with updated_mevnet.csv; the notebook checks both file hashes.


27 October feature cleanup: removed state_ev_registrations from updated_mevnet.csv and its 1 km backup, plus adoption fields from derived audit tables. Current dataset has 1,902 unchanged rows and 11 columns: eight POIs, category, state and total_planned_chargers. Preparation script will not re-add adoption. Updated preparation hash and rebuilt CastraVolt_POI_Category_State.ipynb to accept the revised dataset. Registration source files retained separately for the dashboard.
