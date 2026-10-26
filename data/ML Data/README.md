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
