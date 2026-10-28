import json
from pathlib import Path
import pytest
from castravolt.config import Settings
from castravolt.features import RULES
from castravolt.inference import load_model


def test_poi_category_model_has_nine_inputs_and_matches_export():
    model=load_model(Settings(model_directory=Path('model/verified_poi_category_rf80_cv10')))
    assert model.profile=='poi_category_rf'
    assert list(model.features)==list(RULES)+['category']
    fixtures=json.loads(Path('model/verified_poi_category_rf80_cv10/prediction_fixtures.json').read_text())
    for row in fixtures:
        values={key:row[key] for key in model.features}
        assert model.predict(values)==pytest.approx(row['expected_raw_prediction'],abs=1e-8)
    with pytest.raises(ValueError):model.predict({**values,'state':'SELANGOR'})
    with pytest.raises(ValueError):model.predict({key:value for key,value in values.items() if key!='category'})


from test_accounts import account_settings,client
from test_feature_api import make_site
from test_projects import write
from test_prediction_api import request_data

def test_active_poi_category_contract_requires_category_and_stores_no_state_input(client,account_settings):
    account_settings.poi_source='local'
    sid=make_site(client,account_settings)
    contract=client.get('/api/v1/reference/model-inputs').json()
    assert contract['profile']=='poi_category_rf' and contract['category_required'] is True
    assert contract['features']==list(RULES)+['category']
    response=write(client,'POST',f'/sites/{sid}/predictions',request_data(client,sid))
    assert response.status_code==201,response.text
    values=response.json()['input_snapshot']['features']
    assert len(values)==9 and values['category']=='Shopping Mall' and 'state' not in values
