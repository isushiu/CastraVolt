# Official MEVnet verification

Retrieved and checked on 26 October 2026.

Source chain: https://www.planmalaysia.gov.my/mevnet/ → StoryMap d7a32a04c7494c18953ec94a434e1a53 → dashboard bba366dc3d144510bfd7cda771795f3d → web map 3e8a67dbcc914125b83f3ebcb9f4b1a1 → public feature layer:

https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/MEVnet_EVCB/FeatureServer/0

Downloaded 4,477 official records, including 1,374 Existing and 3,103 Newly Proposed records nationally. Saved the unmodified attributes in official_features.json and supporting configuration/metadata separately.

Both local MEVnet CSVs already contain number_of_existing_ev_charger_s. No restoration or duplicate column was needed, and neither CSV was modified.

All 764 rows in each local file matched official object IDs, location names, states, local authorities, status, and coordinates (tolerance 0.0000001 degrees). Existing and proposed charger counts matched in every row. Dates matched after parsing local day/month/year and official day-month-name-year formats. AC/DC counts matched after treating official nulls as the local zero convention. This verifies count agreement, not that null always semantically means zero.

The *_verified_matches.csv files contain the final per-site checks; verification_summary.json contains totals. The earlier *_comparison.json and *_matches.csv files preserve the initial literal comparison before date/null normalisation, so their differences should not be interpreted as changed charger counts.

Field aliases identify proposed and existing chargers but do not explicitly establish whether proposed values are outstanding additions or earlier planned capacities. Do not automatically add them as a verified total. The user interprets proposed as additional; confirm this interpretation before target construction, including whether proposed chargers have already been installed.

The official StoryMap states that counts represent charging point units with parking bays for simultaneous charging. Its introductory title currently displays a temporary closure notice; the public feature layer was accessible during this check.
