# Selected evaluated 1 km Random Forest

Restored from the original user-provided poi_category_state_1km_full.zip. This is the tuned RF trained on the saved 1,522 training rows, with 600 trees, depth 5 and minimum leaf 10. It reproduces all 380 saved held-out raw predictions within 1.78e-15 and matches all rounded outputs. It is not the fixed default candidate exported by the notebook.

Ten inputs: eight 1 km POI counts, host category and state. No EV registration input. The manifest binds the model to the bundled OSM snapshot, query rules and locked runtime. Loader checks hashes and ten fixtures before use. The reconstructed serialization has a new file hash; historical saved model versions are preserved.

Keep this entire directory in the repository, including evaluated_pipeline.joblib (explicitly allowed by .gitignore). A checkout without it can prepare POIs but cannot generate estimates. To reconstruct it again, use scripts/restore_verified_model.py with the original trusted Colab ZIP. Restore to a new/absent folder; do not overwrite an existing artifact without preserving it.
