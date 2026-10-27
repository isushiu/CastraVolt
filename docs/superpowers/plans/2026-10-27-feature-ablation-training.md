# Feature-comparison Colab handoff

User clarified that the deliverable is a whole notebook to run in Colab, not local full training. Supersedes the earlier local-training plan. No subagents. Current app model unchanged.

- [x] Created CastraVolt_Feature_Comparison.ipynb and its builder.
- [x] All seven nonempty POI/category/state block combinations; separate RF/XGBoost tuning plus always-three/training-median baselines.
- [x] Exact current dataset/group hashes and coordinate-only grouping; same 80/20 split and ten CV folds as the original export.
- [x] Full mode default, 30 candidates, honest selection/test limitations, diagnostic exports and ZIP download.
- [x] All cells executed in smoke mode; 14 candidates + 2 baselines and 6,080 held-out prediction rows verified. Serving artifact checksum unchanged.
- [ ] User runs full training in Colab and returns ZIP for interpretation.
