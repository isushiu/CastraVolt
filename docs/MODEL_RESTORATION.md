# Estimator model restoration

The configured model/verified_poi_state_rf80_cv10 directory was absent. POI preparation still worked, but model loading failed at startup, so inference_eligible remained false and Generate estimate stayed disabled. Restored the selected evaluated Random Forest from the original trusted Colab ZIP using scripts/restore_verified_model.py.

The reconstruction uses the saved 1,522 training rows and selected 600-tree/depth-5/minimum-leaf-10 parameters. All 380 saved held-out raw predictions match within 1.78e-15, and every rounded prediction matches exactly. Six training POI vectors match the bundled 1 km extractor. The model loader validates the snapshot/rules/runtime/checksum and ten parity fixtures. New serialization hash: 1b7bb19365f925c02f59c1287c31c9fc6c96c422da0339aa6f63fa64e5582464. Historical model identities remain intact.

The complete restored directory, including its explicitly Git-allowed joblib, must be retained in commits/copies. Other ignored model exports remain ignored. The recovery command takes an explicitly supplied trusted ZIP path and refuses to overwrite an existing output directory.

Updated blocked-state wording distinguishes a missing model from incompatible map provenance and shows that reason beside the Generate estimate button. Also fixed simultaneous fresh local-context requests: a per-area database transaction lock lets retries share the newly published cache row rather than incorrectly triggering the five-second new-area cooldown.

A backend that already started without the model must be restarted to load it. Refresh the estimator and prepare context again afterward. No guard was bypassed and no fallback model or invented counts were added.

## Trends service verification during this repair

A prior failed request left a temporary summary cooldown. Using the current code and configured key, the complete authenticated summary POST returned 200 and saved real Groq output. An immediate second POST returned 200 with cache_hit=true; GET /trends also returned the saved summary. This successful default-view summary is now in the local project database. Restart the running backend to load the request-header repair for future uncached filters.

## Final verification

Complete backend suite: 102 passed. Frontend suite: 34 passed; TypeScript/Vite build passed. Browser verification: saved site → prepare matched 1 km context → Generate estimate enabled → real RF output 3 saved to history. Temporary ports/database cleaned up; user app processes were not stopped. The existing running backend reported the model unavailable before restart, while a fresh backend loaded the restored model successfully.
