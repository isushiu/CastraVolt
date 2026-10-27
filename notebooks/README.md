# Current 1 km POI + category + state notebook

Open `CastraVolt_POI_Category_State.ipynb` in Google Colab and run its cells in order. The upload cell requires two files selected together from `data/ML Data`: `updated_mevnet.csv` and `updated_mevnet_row_groups.csv`. The row-groups file keeps identical site coordinates together during splitting; coordinates and IDs are not model inputs. The pair is hash-checked against the dataset used to build this notebook. If you regenerate the dataset, rebuild the notebook with `python notebooks/build_poi_state_notebook.py` and use its newly matched files.

The notebook uses eight POI counts (1 km), site category and state. Registration numbers are excluded. The target is the existing-plus-proposed total under the documented additional-proposed assumption. Missing categories include inferred labels. `RUN_MODE = 'smoke'` tests the 11 setups with small models; set `RUN_MODE = 'full'` to run the agreed full models and tuning. Full tuning may take substantial time. It compares Random Forest, XGBoost, always-three and training-median baselines; shows MAE, RMSE, R², rounded MAE and prediction-distribution plots; and saves a ZIP with predictions, split assignments, metadata and a refitted candidate. In the last cell, uncomment the `files.download(archive)` lines to download the results.

Local verification ran all cells in smoke mode on 1,902 rows, all 11 setups and four models/baselines; the matching files, ten model inputs, grouped split, rounding, saved candidate and ZIP were verified. Full-budget training and Colab upload/Drive were not executed. The candidate is not automatically installed in the app; the current app still uses a 3 km model/feature contract. The earlier notebook below remains available for the original experiments.

---

# CastraVolt Colab notebook

Open https://colab.research.google.com/ and choose File → Upload notebook, then select `CastraVolt_ML_Training.ipynb`.

1. Run cells in order. The default data mode requests the four CSVs from `data/ML Data` together. Alternatively select Drive mode and set the folder path in the configuration cell.
2. Start with `RUN_MODE = 'smoke'`. It runs all 11 setups with tiny models and two search candidates to check execution. Its scores are not final FYP findings.
3. Set `RUN_MODE = 'full'` for the agreed tree ranges and 30-combination searches. This can take substantial CPU time. Results are saved after each experiment.
4. The final export cell writes a ZIP with data diagnostics, registration summaries, split/fold assignments, scores, predictions, tuning results, chart, version/source metadata and a refitted deployment candidate. Uncomment the download lines at the bottom to download it in Colab.

No source CSVs are modified. State adoption is configurable and off by default until its indicator and date alignment are defensible. Enabling fixed-period context is explicitly retrospective and is not proof of a growth effect. Existing POI counts are permitted only as provisional because their original radius and extraction method remain unverified. The notebook does not query OpenStreetMap or regenerate POIs.

The target uses the authorised assumption that proposed chargers are additions. Displayed counts use ceiling and a configurable default minimum of one. Raw and rounded metrics are reported separately. Saved models are deployment candidates, not proof of optimal charger capacity. A smoke-trained candidate must not be deployed.

Local validation executed every code cell against the four project CSVs in smoke mode. All 11 setups ran for both models and the two baselines. This does not verify the Colab upload/Drive interface or complete full-budget tuning. Identical-coordinate isolation, reproducible assignments, target sums, forbidden-input exclusion and ceiling behaviour were also checked.


## Feature comparison notebook

Open `CastraVolt_Feature_Comparison.ipynb` in Google Colab. It compares all seven nonempty combinations of POIs (the eight counts as one block), site category and state, using separately tuned RF and XGBoost models plus two simple baselines. EV registration data is excluded.

Upload the same `updated_mevnet.csv` and `updated_mevnet_row_groups.csv` together. Hash and row-alignment checks protect the pairing; coordinates are only for splits. Defaults: full mode, 80/20 holdout, ten training CV folds, seed 42, 30 sampled settings per candidate. The 4,200 validation fits can take a substantial session; GPU is unnecessary. Optional extra train fractions increase the workload. This is a feature-ablation comparison rather than every combination of the earlier eleven protocols.

Run all cells, then return the downloaded ZIP. It includes `comparison_summary.csv`, `feature_added_value.csv`, `permutation_diagnostics.csv`, predictions, source/fold assignments, searches, target-band errors, zero-POI scenarios, metadata and the training-CV-selected candidate. Each settings run uses a timestamped output directory so different runs do not mix. A final download cell can also archive partial results after interruption; partial or smoke results are not final findings.

The app's current model is not changed. Existing held-out sites have already been inspected, so these comparisons remain exploratory. Rebuild the notebook with `python notebooks/build_feature_comparison_notebook.py`; workflow verification is `python tests/run_feature_comparison_smoke.py` with the model-validation/XGBoost environment available.
