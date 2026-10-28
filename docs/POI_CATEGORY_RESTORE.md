# Restore POIs + category — 28 October 2026

The user chose to end the POI-only trial and restore category. The active model now uses exactly nine inputs: eight 1 km POI counts + category. State remains derived for coverage and saved metadata, not prediction.

Random Forest is selected because training CV MAE 1.902717 is lower than XGBoost 1.934889 within POIsCategory. The test MAE is 2.012597. The chosen RF reproduces all 380 saved raw predictions within 1.78e-15 and all displayed counts exactly. It was reconstructed using saved parameters (600 trees, depth 5, minimum leaf 10, max_features 1, seed 42) and the original 1,522 training rows; no new split or all-data refit was used.

Active directory: model/verified_poi_category_rf80_cv10. Previous directories model/verified_poi_only_xgb80_cv10 and model/verified_poi_state_rf80_cv10 remain intact. Local .env, example configuration and portable default now select the nine-input model. Frontend reads its model-input reference contract and restores the category dropdown, confirmation checkbox and save requirement. Existing history keeps each original model identity. State is absent from the nine-input prediction snapshot; category is required by the model.

The POI-only zero-count response was 3.662660837173462, rounded to 4. That response did not come from category, since category was excluded. Restoring category improves prediction accuracy on this dataset but does not establish optimal site capacity, a minimum physical requirement or a reliable POI contribution beyond category.

Restart the running app to load the active model, then refresh and prepare site context again. No database migration is needed. Keep the full active artifact directory in any commit/copy. The user app ports were not stopped or occupied during verification.

Verification: 108 backend tests and 35 frontend tests passed, along with the production build. Browser verification confirmed category selection and confirmation restored, context preparation, and a saved KLCC estimate of 15 from the nine-input model. Screenshot: ../tmp/poi-category-restored.png. Temporary preview/database cleaned up. Both earlier model artifacts remain available.
