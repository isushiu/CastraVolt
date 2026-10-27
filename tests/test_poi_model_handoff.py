import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def test_exported_one_km_pipeline_reproduces_saved_held_out_predictions():
    folder = Path('model/verified_poi_state_rf80_cv10')
    manifest = json.loads((folder/'manifest.json').read_text())
    artifact = folder/'evaluated_pipeline.joblib'
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == manifest['model_sha256']
    assert manifest['poi_radius_metres'] == 1000
    assert manifest['use_adoption'] is False
    assert len(manifest['features']) == 10
    assert 'state_ev_registrations' not in manifest['features']
    bundle = joblib.load(artifact)
    data = pd.read_csv('model/poi_category_state_1km_full/prepared_sites.csv')
    saved = pd.read_csv('model/poi_category_state_1km_full/holdout_predictions.csv')
    saved = saved[(saved.experiment=='split_cv_80_10') & (saved.model=='RandomForest')].sort_values('source_row')
    test = data.set_index('_source_row').loc[saved.source_row]
    actual = bundle['pipeline'].predict(test[manifest['features']])
    assert np.allclose(actual, saved.raw_prediction, atol=1e-8, rtol=0)
    for key,value in manifest['selected_parameters'].items():
        assert bundle['pipeline'].get_params()[key] == value
