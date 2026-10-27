# CastraVolt integration results

27 October 2026. The app now uses the selected evaluated **Random Forest with 1 km POIs, host-site category and state**. It estimates total planned charging points from MEVnet examples. It does not establish an optimal installation size or forecast charging sessions.

## Delivered behaviour

Select a pin, confirm the host category, save the site and prepare its context. The backend derives state, counts mapped facilities within 1,000 metres and supplies exactly ten features to the model. The output appears below the map and is saved with its raw value, rounded total, model identity and extraction provenance. Rounding is nearest whole number, halves upward, minimum one.

Eight POI inputs: malls, petrol stations, hotels, offices, transit stations, universities, hospitals and parking facilities. Category and state complete the ten inputs. EV registration totals are absent from new predictions; 2024–2026 registrations remain available for the future trend dashboard. Existing history retains any legacy adoption context.

Serving artifact: model/verified_poi_state_rf80_cv10/evaluated_pipeline.joblib, SHA256 99ab098d46bdc30e8356c8b7bce7e4be433c577ba244f5b608e0d86e4c10ea20. Version rf80-cv10-1km-99ab098d46bd. RF parameters: 600 trees, maximum depth 5, minimum leaf 10, all features, seed 42. It remains fitted on the evaluated 1,522 training rows; it is not an untested all-data refit.

Startup checks file hashes, sklearn/numpy/pandas versions, fitted parameters, ten saved prediction fixtures and matching 1 km query-rule/snapshot identities. Prediction requests with incompatible map provenance are rejected. The selected serving joblib is explicitly allowed by Git so a copied checkout can include it. Other joblib exports remain ignored. The bundled catalogue itself is unchanged; its catalogue-build identity is distinguished from the 1 km query identity. No fabricated counts or fallback model were added.

## Model evaluation

The full export contains 1,902 prepared sites. The selected 80/20 held-out partition contains 380 sites. Reconstructed RF predictions match every saved held-out prediction within 1.78e-15. All 96 reported evaluation rows were checked against saved outputs.

- Training CV10 MAE: **1.90255**, versus XGBoost **1.93471** in the same protocol. RF won training CV in all six split-plus-CV setups.
- Held-out raw MAE: **2.01239 charging points**; RMSE **3.99264**; R² **0.23809**.
- Rounded MAE: **1.97895**. Exact match **33.4%**; within one point **56.6%**; within two points **80.0%**.
- Actual totals 1–4: 274 sites, MAE **1.25368**. Totals 5–9: 65 sites, MAE **2.06538**. Totals 10+: 41 sites, MAE **6.99880**.

Selection uses training-CV evidence, not the lowest test error. However, experiments and test results were already inspected; this is not a fresh independent final evaluation. XGBoost has lower held-out MAE (1.95357) in the same 80/20+CV10 setup.

## POI contribution and limits

The selected RF is strongly category-dependent. At the same fixed RF settings, category+state without POIs obtains CV MAE **1.89358**, versus **1.90255** with all inputs. POIs alone obtain **2.63013**. Joint held-out POI shuffling over 20 seeds gives RF mean MAE **2.00057**, close to the original **2.01239**; category shuffling worsens it to **3.12530**. These exploratory checks do not demonstrate a useful POI gain for this RF. XGBoost shows more POI dependence (shuffling increases MAE from **1.95357** to **2.11857**).

Therefore the UI says **Research prototype**, with a short note about category dependence and larger-site accuracy. Feature compatibility is verified; capacity accuracy remains limited. Repeated equal outputs may still occur legitimately. Output diversity is not proof of quality. Many host labels are inferred, targets use the agreed existing-plus-additional-proposed interpretation, and KL/Selangor state boundaries do not enforce urban-only coverage.

## Live integration examples

Real backend requests against an isolated temporary app returned:

- KLCC pin (3.1579, 101.7116), category Shopping Mall: raw **14.653614**, displayed **15**.
- Klang pin (3.009127, 101.464577), category Office: raw **3.449319**, displayed **3**.
- Shah Alam pin (3.0738, 101.5183), category Petrol Station: raw **2.125063**, displayed **2**.

These are test inputs with caller-confirmed categories, not independent audits of each host's land use or recommended installation sizes. Each response had radius 1,000 m, ten inputs, matching provenance and the selected RF version. They demonstrate working inference with variable results, not validated optimal capacity.

## Verification

- Final complete backend suite: **80 passed**, including snapshot-mismatch rejection and preserved legacy history.
- Frontend: **27 tests passed across 9 files**; TypeScript and production Vite build passed.
- Six real training-site POI vectors match the live 1 km extractor. All 380 saved held-out model predictions are covered by parity verification.
- Fresh PostgreSQL databases migrated through 0007_optional_adoption; old adoption history remains readable, new records use null adoption columns. Mismatched snapshots, stale edits, nonfinite predictions, unauthorised access and concurrent retry handling are tested.
- Browser flow: internal login → saved map site → Prepare site context → Generate estimate. Verified 1 km text/circle context, output **15** beneath the map, research wording and saved history notice. Screenshot: [verified estimator](tmp/one-km-prediction.png) (local verification artifact, ignored by Git).

Checks used separate ports 8001/5174 and disposable databases. The user's app ports 8000/5173 were left untouched. See BACKLOG.md for remaining deliverables.
