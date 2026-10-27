"""Execute all notebook cells locally with genuine data and smoke-size models."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path('tmp/ml_validation_packages').resolve()))
os.environ['MPLBACKEND'] = 'Agg'
nb = json.loads(Path('notebooks/CastraVolt_POI_Category_State.ipynb').read_text(encoding='utf-8'))
namespace = {'__name__': '__main__'}
for index, cell in enumerate(nb['cells']):
    if cell['cell_type'] != 'code':
        continue
    source = ''.join(cell['source'])
    if "DATA_SOURCE = 'upload'" in source:
        source = source.replace("DATA_SOURCE = 'upload'", "DATA_SOURCE = 'local'")
        source = source.replace("OUTPUT_DIR = Path('castravolt_poi_category_state_results')",
                                "OUTPUT_DIR = Path('tmp/poi_state_notebook_smoke')")
    print('Executing cell', index, flush=True)
    exec(compile(source, f'cell_{index}', 'exec'), namespace)

assert len(namespace['sites']) == 1902
assert len(namespace['features']) == 10
assert 'state_ev_registrations' not in namespace['X'].columns
assert namespace['displayed_count']([2.0, 2.1, 2.49, 2.5, 2.9, -1]).tolist() == [2, 2, 2, 3, 3, 1]
assert len(namespace['scores'][['experiment','model']].drop_duplicates()) == 44
assert len(namespace['scores']) == 96
for train, test in namespace['holdouts'].values():
    namespace['assert_disjoint'](train, test, namespace['coordinate_groups'])
sample = namespace['X'].iloc[0].to_dict()
assert namespace['predict_prepared_site'](sample)['total_planned_chargers'] >= 1
assert (namespace['run_dir'] / 'summary_metrics.csv').is_file()
assert (namespace['run_dir'] / 'candidate_model.joblib').is_file()
assert Path(namespace['archive']).is_file()
print('PASS: all 11 setups, 10 features, matching coordinate groups, rounding and outputs.')
