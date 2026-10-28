# Active POIs + category Random Forest

Nine inputs: eight 1 km POI counts and confirmed host-site category. State is coverage metadata, not a model input. Selected by the lowest training-CV MAE among the POIsCategory candidates: RF 1.902717 versus XGBoost 1.934889. RF test MAE is 2.012597. This selection did not choose the lowest test score.

Reconstructed from feature_comparison_1km_full_20261027_155157UTC.zip on the same 1,522 training rows. All 380 saved holdout raw predictions match within 1.78e-15 and rounded outputs match exactly. The manifest binds source identity, runtime, parameters, extraction rules and snapshot. This is not an all-data refit.

The prior POI-only XGBoost and original ten-feature RF are retained separately. Keep this complete serving directory, including the explicitly Git-allowed joblib, manifest and fixtures. No additional database migration is required to change profiles.

Category remains dominant. This candidate is more accurate than the POI-only model but adding POIs has not demonstrated a reliable gain over category alone; the recommendation is research planning guidance, not verified optimal capacity.
