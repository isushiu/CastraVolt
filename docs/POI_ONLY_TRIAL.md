# POI-only estimator trial — 28 October 2026

User requested trying the best POI-only model and disabling category. Source ZIP: model/poi_only_trial_source/feature_comparison_1km_full_20261027_155157UTC.zip (copied from Downloads, original retained).

## Selection and parity

Choose using training CV, not the already examined holdout: POIsOnly XGBoost CV MAE 2.606497; RF 2.620727. XGBoost test MAE 2.582736, RMSE 4.440582, R² 0.057541. The always-three baseline test MAE is 2.415789. Retain this explicit limitation; more varied outputs do not imply better recommendations.

The ZIP contains only the global category-based winner's model file, not the fitted POI-only candidate. Reconstruction uses the exact 1,522 saved training rows and selected XGBoost settings: 100 trees, depth 3, learning rate 0.03, subsample 1, column sample 0.8 and lambda 5; seed 42. A Linux reconstruction matches all 380 saved raw predictions within 1.78e-15 and all rounded predictions exactly. Loading its portable JSON trees into the Windows pipeline retains that parity. A native Windows refit did not match, so it was not used. Six source POI vectors also match the installed snapshot/extraction rules.

Artifact directory: model/verified_poi_only_xgb80_cv10. Model SHA256: 5f2fd29124622e7871326348129a67da3604407d97040637c104c1b164f776a1. The prior RF artifact remains in model/verified_poi_state_rf80_cv10. Both verified profiles load with strict parameter/schema/runtime checks. XGBoost 3.4.1 is locked in the model-validation dependency group.

## Behaviour

The authenticated model-input reference endpoint identifies the active feature contract. During POI-only trial, category is disabled and its confirmation checkbox is hidden. New sites can be saved without category; the database uses Unknown metadata. Editing an older site does not overwrite its existing category. State still derives from the pin for Selangor/KL coverage.

Prepared context retains category/state metadata for old-client and rollback compatibility, but prediction explicitly selects only the verified model's eight feature names. Persisted input_snapshot.features contains exactly those eight numeric POI counts. The model rejects extra category/state inputs. History metadata can still identify site category/state; those are not fed to XGBoost.

The result panel says POI-only trial and explains that category/state are excluded and validation was worse than the simple baseline. Radius remains 1 km and rounding remains nearest whole, halves upward, minimum one. Existing history and current model guards are preserved.

## Start and rollback

Restart the running app after changing profiles. The default and local .env now select model/verified_poi_only_xgb80_cv10. Run setup on another computer before start to install the locked XGBoost dependency. Keep both complete serving artifact directories in the commit/copy.

Rollback: change CASTRAVOLT_MODEL_DIRECTORY to model/verified_poi_state_rf80_cv10 and restart. The model reference endpoint will tell the frontend to require category again. No database migration is needed for this trial.

## Verification

106 backend tests passed, including eight-input snapshot enforcement, strict rejection of extra category/state features, identical predictions after category changes, rollback RF loading, idempotency and stale-edit/history safeguards. 35 frontend tests passed; TypeScript/Vite build passed. Model restoration matched all 380 saved outputs. Browser check and actual map examples recorded after completion below.

Dependency sync encountered a native library locked by the user's running process. Only XGBoost was installed into the current runtime; incomplete charset-normalizer metadata was repaired from the checksum-verified official wheel without replacing a loaded native extension. uv pip check subsequently confirmed that installed packages are compatible. Normal setup with the app stopped follows the updated lockfile.

## Browser outcome

Temporary preview on 8001/5174: saved a KLCC pin without a category, confirmed the category dropdown was disabled and no confirmation checkbox existed, prepared context and generated a saved estimate of 6. Input counts: malls 4, petrol 1, hotels 36, offices 121, transit 7, universities 0, hospitals 0 and parking 88. State was labelled coverage-only. All eight zero counts independently produce raw 3.662660837173462, displayed 4; this demonstrates that excluding category does not imply zero output for a zero-count area. Screenshot: ../tmp/poi-only-trial.png. Temporary preview/database stopped and removed; user ports 8000/5173 left untouched.
