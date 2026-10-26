"""Verify the trusted user-provided model export and recover the evaluated RF pipeline.

Run with uv run --group model-validation python scripts/verify_model_handoff.py.
Never load untrusted joblib files. Does not change the original Colab export.
"""
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

root = Path(__file__).resolve().parents[1]
source = root / 'model/PROVISIONAL_full_adoption'
output = root / 'model/verified_rf80_cv5'
metadata = json.loads((source / 'run_metadata.json').read_text())
if sklearn.__version__ != metadata['versions']['sklearn']:
    raise RuntimeError('Use the exact exported scikit-learn version for reconstruction')
bundle = joblib.load(source / 'deployment_candidate.joblib')
features = bundle['features']
assert metadata['use_adoption'] is True and metadata['adoption_reference_year'] == 2025
assert len(features) == 11 and 'state_ev_registrations' in features
selected = pd.read_csv(source / 'selected_hyperparameters.csv')
row = selected[(selected.experiment == 'split_cv_80_5') & (selected.model == 'RandomForest')].iloc[0]
params = json.loads(row.parameters)
original_params = bundle['pipeline'].named_steps['model'].get_params()
original_matches = all(original_params[key.removeprefix('model__')] == value for key,value in params.items())
data = pd.read_csv(source / 'prepared_sites.csv')
assignments = pd.read_csv(source / 'holdout_assignments.csv')
assignment = assignments[np.isclose(assignments.train_fraction, 0.8)]
assert assignment.source_row.is_unique and data._source_row.is_unique
train = data._source_row.isin(assignment[assignment.partition == 'train'].source_row)
test = data._source_row.isin(assignment[assignment.partition == 'test'].source_row)
assert (train | test).all() and not (train & test).any()
assert not set(data.loc[train,'_coordinate_group']) & set(data.loc[test,'_coordinate_group'])
assert (data.total_planned_chargers == data.number_of_existing_ev_charger_s + data.number_of_proposed_ev_charger__).all()
pipeline = clone(bundle['pipeline']).set_params(**params)
pipeline.fit(data.loc[train,features],data.loc[train,'total_planned_chargers'])
actual = data.loc[test,'total_planned_chargers'].to_numpy()
predictions = pipeline.predict(data.loc[test,features])
saved = pd.read_csv(source / 'holdout_predictions.csv')
saved = saved[(saved.experiment == 'split_cv_80_5') & (saved.model == 'RandomForest')]
expected = saved.set_index('source_row').loc[data.loc[test,'_source_row'],'raw_prediction'].to_numpy()
if not np.allclose(predictions, expected, rtol=1e-7, atol=1e-7):
    raise RuntimeError(f'Reconstructed predictions differ: max abs {np.max(np.abs(predictions-expected))}')
output.mkdir(exist_ok=True)
fixture = data.loc[test,['_source_row',*features]].head(10).copy()
fixture['expected_raw_prediction'] = predictions[:10]
fixture['expected_half_up_count'] = np.maximum(1,np.floor(predictions[:10]+0.5)).astype(int)
fixture.to_json(output / 'prediction_fixtures.json',orient='records',indent=2)
joblib.dump({'pipeline':pipeline,'features':features,'metadata':{
    **metadata,'rounding':'nearest_half_up','planned_poi_radius_metres':3000,
    'poi_provenance':'3 km radius confirmed by owner; original tag/deduplication parity still pending',
    'artifact_role':'reconstructed evaluated 80-percent-training fitted pipeline',
}},output / 'evaluated_pipeline.joblib')
source_hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [
    source/'deployment_candidate.joblib',source/'prepared_sites.csv',source/'holdout_predictions.csv']}
manifest = {'status':'prediction_parity_verified','original_candidate_matches_selected_parameters':original_matches,
    'selected_parameters':params,'features':features,'train_sites':int(train.sum()),'test_sites':int(test.sum()),
    'maximum_prediction_difference':float(np.max(np.abs(predictions-expected))),
    'metrics':{'MAE':float(mean_absolute_error(actual,predictions)),
    'RMSE':float(np.sqrt(mean_squared_error(actual,predictions))), 'R2':float(r2_score(actual,predictions)),
    'nearest_half_up_MAE':float(mean_absolute_error(actual,np.maximum(1,np.floor(predictions+0.5))))},
    'source_hashes':source_hashes,'model_sha256':hashlib.sha256((output/'evaluated_pipeline.joblib').read_bytes()).hexdigest(),
    'runtime':{'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__},
    'remaining':['Original POI tag/geometry/deduplication implementation required for live feature parity.',
                 'Total target retains owner-authorised additional-chargers assumption.',
                 'Selected experiment was chosen after inspecting test results; not fresh independent model selection.']}
(output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
