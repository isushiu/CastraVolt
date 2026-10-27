import hashlib
import json
from pathlib import Path


def test_notebook_is_self_contained_and_has_the_agreed_contract():
    path = Path('notebooks/CastraVolt_POI_Category_State.ipynb')
    nb = json.loads(path.read_text(encoding='utf-8'))
    assert nb['nbformat'] == 4
    cells = [''.join(cell['source']) for cell in nb['cells'] if cell['cell_type'] == 'code']
    for cell in cells:
        compile(cell, '<colab cell>', 'exec')
    code = '\n'.join(cells)
    for term in ['updated_mevnet.csv', 'updated_mevnet_row_groups.csv', 'coordinate_groups',
                 'RandomForestRegressor', 'XGBRegressor', 'RandomizedSearchCV',
                 'split_only', 'cv_only', 'split_cv', 'np.floor', '0.5', 'holdout_predictions.csv']:
        assert term in code
    assert "numeric_features = POI.copy()" in code
    assert "categorical_features = ['category', 'state']" in code
    assert "numeric_features.append('state_ev_registrations')" not in code
    assert hashlib.sha256(Path('data/ML Data/updated_mevnet.csv').read_bytes()).hexdigest() in code
    assert hashlib.sha256(Path('data/updated_mevnet_source/training_row_provenance_1km.csv').read_bytes()).hexdigest() in code
