# POI-only trial implementation

The user explicitly authorises a reversible POI-only app trial, not a final accuracy upgrade. Use the latest full feature-comparison ZIP. Choose the POIsOnly learner by training CV MAE: XGBoost, 2.606497 vs RF 2.620727. Preserve the current RF artifact and all history.

- [x] Reconstruct selected POI-only XGBoost using saved parameters/train rows; verify all 380 exported predictions before exporting a separate serving bundle.
- [x] Add locked XGBoost runtime. Support two explicitly verified serving profiles with strict input/parameter/runtime/radius/snapshot checks. Pass and persist exactly the eight model inputs in POI-only mode.
- [x] Expose an authenticated model-input contract. Disable category and remove its confirmation/save requirement for POI-only trial; retain prior categories/history as metadata. State remains coverage metadata, never a trial input.
- [x] Set the local model directory to the trial and document rollback to the preserved RF directory. Keep scientific limitations visible without category-dominance wording for POI-only mode.
- [x] Test parity, category independence, zero-count behaviour, API input snapshots, legacy profile compatibility and browser flow. Do not occupy the user's 8000/5173 ports.

Verification: 106 backend tests, 35 frontend tests, production build and browser workflow passed. Linux reconstruction + portable JSON booster reproduced all 380 Colab predictions on Windows. Current runtime dependency check passed. No accuracy improvement is claimed; source/rollback details are in docs/POI_ONLY_TRIAL.md.
