"""Execute the delivered notebook cells with local input and temporary outputs."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path('tmp/ml_validation_packages').resolve()))
os.environ['MPLBACKEND'] = 'Agg'
nb = json.loads(Path('notebooks/CastraVolt_ML_Training.ipynb').read_text(encoding='utf-8'))
namespace = {'__name__': '__main__'}
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] != 'code':
        continue
    source = ''.join(cell['source'])
    if "DATA_SOURCE = 'upload'" in source:
        source = source.replace("DATA_SOURCE = 'upload'", "DATA_SOURCE = 'local'")
        source = source.replace("OUTPUT_DIR = Path('castravolt_results')", "OUTPUT_DIR = Path('tmp/notebook_smoke')")
    print('EXECUTING CELL', i, flush=True)
    exec(compile(source, f'cell_{i}', 'exec'), namespace)

np = namespace['np']
groups = np.array(['a','a','b','c','d','e','f','g','h','i','j','k'])
for ratio in [0.5,0.7,0.8]:
    train, test = namespace['random_group_holdout'](groups, 1-ratio)
    namespace['assert_disjoint'](train,test,groups)
    assert np.array_equal(test, namespace['random_group_holdout'](groups,1-ratio)[1])
for k in [5,10]:
    folds = namespace['random_group_folds'](groups,k)
    tested = []
    for train,test in folds:
        namespace['assert_disjoint'](train,test,groups)
        tested.extend(test)
    assert sorted(tested) == list(range(len(groups)))
assert namespace['displayed_count']([2.0,2.1,2.9,-1]).tolist() == [2,3,3,1]
sites = namespace['sites']
assert (sites[namespace['TARGET']] == sites[namespace['EXISTING']] + sites[namespace['PROPOSED']]).all()
assert not set([namespace['TARGET'],namespace['EXISTING'],namespace['PROPOSED'],'type_ac','type_dc','indoor','outdoor','objectid']) & set(namespace['features'])
assert len(namespace['scores'][['experiment','model']].drop_duplicates()) == 44
assert len(namespace['scores']) == 96
print('PASS: all 11 setups executed for both models and baselines; grouping, rounding, target and input checks passed')
