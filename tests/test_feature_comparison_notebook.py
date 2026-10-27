import json
from pathlib import Path


def test_feature_comparison_notebook_is_complete_and_safe_to_run():
    notebook=json.loads(Path('notebooks/CastraVolt_Feature_Comparison.ipynb').read_text(encoding='utf-8'))
    code='\n'.join(''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code')
    for index,cell in enumerate(notebook['cells']):
        if cell['cell_type']=='code':compile(''.join(cell['source']),f'cell-{index}','exec')
    assert "RUN_MODE = 'full'" in code
    for variant in ['POIsOnly','CategoryOnly','StateOnly','POIsCategory','POIsState','CategoryState','POIsCategoryState']:assert variant in code
    assert 'RandomizedSearchCV' in code and 'DummyRegressor' in code
    assert 'state_ev_registrations' not in code
    assert 'verified_poi_state_rf80_cv10' not in code
    assert 'feature_added_value.csv' in code and 'run_metadata.json' in code
