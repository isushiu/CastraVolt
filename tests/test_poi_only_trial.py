import json
from pathlib import Path
import pytest
from castravolt.config import Settings
from castravolt.inference import load_model
from castravolt.features import RULES


def test_poi_only_model_reproduces_saved_fixture_outputs_and_rejects_category():
    model=load_model(Settings(model_directory=Path('model/verified_poi_only_xgb80_cv10')))
    assert list(model.features)==list(RULES)
    assert len(model.features)==8 and model.profile=='poi_only_xgb'
    fixtures=json.loads(Path('model/verified_poi_only_xgb80_cv10/prediction_fixtures.json').read_text())
    for row in fixtures:
        values={k:row[k] for k in model.features}
        assert model.predict(values)==pytest.approx(row['expected_raw_prediction'],abs=1e-7)
    with pytest.raises(ValueError):model.predict({**values,'category':'Highway'})
    with pytest.raises(ValueError):model.predict({**values,'state':'SELANGOR'})
    assert model.predict({key:0 for key in model.features})>=0


def test_original_rf_remains_loadable_for_rollback():
    model=load_model(Settings(model_directory=Path('model/verified_poi_state_rf80_cv10')))
    assert len(model.features)==10 and model.profile=='poi_category_state_rf'


from test_accounts import account_settings,client
from test_projects import write
from test_feature_api import make_site
from test_prediction_api import request_data


def test_trial_api_stores_eight_inputs_and_category_changes_do_not_change_estimate(client,account_settings):
    account_settings.poi_source='local'
    client.app.state.prediction_model=load_model(Settings(model_directory=Path('model/verified_poi_only_xgb80_cv10')))
    sid=make_site(client,account_settings)
    contract=client.get('/api/v1/reference/model-inputs').json()
    assert contract['category_required'] is False and len(contract['features'])==8
    first=write(client,'POST',f'/sites/{sid}/predictions',request_data(client,sid))
    assert first.status_code==201,first.text
    features=first.json()['input_snapshot']['features']
    assert set(features)==set(RULES)
    assert 'category' not in features and 'state' not in features
    assert first.json()['model_version'].startswith('xgb-poi-only-')
    assert write(client,'PATCH',f'/sites/{sid}',{'category':'Highway'}).status_code==200
    second=write(client,'POST',f'/sites/{sid}/predictions',request_data(client,sid))
    assert second.status_code==201,second.text
    assert second.json()['raw_estimate']==first.json()['raw_estimate']
