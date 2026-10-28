# POI-only XGBoost trial

Active trial profile: poi_only_xgb. Eight 1 km POI counts are model inputs. Category and state are excluded. State remains a coverage check and old site categories remain history metadata.

Selected by the lowest training-CV MAE among the POIsOnly candidates in feature_comparison_1km_full_20261027_155157UTC.zip: XGBoost 2.606497 vs RF 2.620727. Test MAE is 2.582736, worse than the always-three baseline at 2.415789. This is an explicitly requested behaviour trial, not a demonstrated accuracy improvement.

The ZIP exported only the overall category-based winner, so the POI-only model was reconstructed from its saved training rows and selected parameters. Windows-native fitting produced different trees. A disposable official Python Linux container reproduced all 380 Colab predictions within 1.78e-15. Its portable JSON booster was then imported into the Windows serving pipeline; all 380 raw and rounded outputs still match. The manifest includes archive and booster hashes. The verified booster is preserved alongside the serving joblib, manifest and fixtures.

Keep this full directory with the project. The joblib is explicitly allowed by .gitignore. The app verifies its eight-feature schema, model type, selected settings, runtime, map/rule hashes and ten fixtures before use. No false zero-count assumptions or default prediction were added.

To roll back, set CASTRAVOLT_MODEL_DIRECTORY=model/verified_poi_state_rf80_cv10 in .env and restart. The UI reads the model input contract and will restore category confirmation for that profile. Existing saved prediction histories retain their original model versions.
