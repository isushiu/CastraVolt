import json
from pathlib import Path

path = Path('notebooks/CastraVolt_ML_Training.ipynb')
nb = json.loads(path.read_text(encoding='utf-8'))
assert nb['nbformat'] == 4
code = '\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code')
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        compile(''.join(cell['source']), '<notebook cell>', 'exec')
for term in ['total_planned_chargers', 'vehicles_2026.csv', 'RandomForestRegressor',
             'XGBRegressor', 'RandomizedSearchCV', 'SimpleImputer', 'OneHotEncoder',
             'np.ceil', 'coordinate_groups', 'cv_only', 'split_cv', 'split_only',
             'ALLOW_PROVISIONAL_POI', 'USE_ADOPTION', 'holdout_predictions.csv']:
    assert term in code, term
print(f'PASS: {len(nb["cells"])} cells; all Python compiles; required workflow present')
