import math
import pytest


def test_half_up_and_nonfinite_values():
    from castravolt.inference import display_count
    assert [display_count(value) for value in [3.2,3.5,3.9,-1,0,.5]]==[3,4,4,1,1,1]
    for value in [math.nan,math.inf,-math.inf]:
        with pytest.raises(ValueError):display_count(value)


def test_real_verified_model_reproduces_fixtures():
    import json
    from pathlib import Path
    from castravolt.inference import load_model
    from castravolt.config import Settings
    model=load_model(Settings(model_directory=Path('model/verified_poi_state_rf80_cv10')))
    fixtures=json.loads(Path('model/verified_poi_state_rf80_cv10/prediction_fixtures.json').read_text())
    for row in fixtures:
        raw=model.predict({key:row[key] for key in model.features})
        assert raw==pytest.approx(row['expected_raw_prediction'],abs=1e-8)


def test_missing_model_is_not_replaced_with_a_default(tmp_path):
    from castravolt.inference import load_model
    from castravolt.config import Settings
    with pytest.raises(Exception):load_model(Settings(model_directory=tmp_path))


def test_wrong_hash_is_rejected_before_deserialization(tmp_path,monkeypatch):
    import json,joblib
    from pathlib import Path
    from castravolt.inference import load_model
    from castravolt.config import Settings
    manifest=json.loads(Path('model/verified_poi_state_rf80_cv10/manifest.json').read_text())
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    (tmp_path/'prediction_fixtures.json').write_text('[]')
    (tmp_path/'evaluated_pipeline.joblib').write_bytes(b'untrusted file')
    def forbidden(*args):raise AssertionError('Checksum must be checked before loading')
    monkeypatch.setattr(joblib,'load',forbidden)
    with pytest.raises(ValueError,match='checksum'):load_model(Settings(model_directory=tmp_path))
