# CastraVolt Colab notebook

Open https://colab.research.google.com/ and choose File → Upload notebook, then select `CastraVolt_ML_Training.ipynb`.

1. Run cells in order. The default data mode requests the four CSVs from `data/ML Data` together. Alternatively select Drive mode and set the folder path in the configuration cell.
2. Start with `RUN_MODE = 'smoke'`. It runs all 11 setups with tiny models and two search candidates to check execution. Its scores are not final FYP findings.
3. Set `RUN_MODE = 'full'` for the agreed tree ranges and 30-combination searches. This can take substantial CPU time. Results are saved after each experiment.
4. The final export cell writes a ZIP with data diagnostics, registration summaries, split/fold assignments, scores, predictions, tuning results, chart, version/source metadata and a refitted deployment candidate. Uncomment the download lines at the bottom to download it in Colab.

No source CSVs are modified. State adoption is configurable and off by default until its indicator and date alignment are defensible. Enabling fixed-period context is explicitly retrospective and is not proof of a growth effect. Existing POI counts are permitted only as provisional because their original radius and extraction method remain unverified. The notebook does not query OpenStreetMap or regenerate POIs.

The target uses the authorised assumption that proposed chargers are additions. Displayed counts use ceiling and a configurable default minimum of one. Raw and rounded metrics are reported separately. Saved models are deployment candidates, not proof of optimal charger capacity. A smoke-trained candidate must not be deployed.

Local validation executed every code cell against the four project CSVs in smoke mode. All 11 setups ran for both models and the two baselines. This does not verify the Colab upload/Drive interface or complete full-budget tuning. Identical-coordinate isolation, reproducible assignments, target sums, forbidden-input exclusion and ceiling behaviour were also checked.
