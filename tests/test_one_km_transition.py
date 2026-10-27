import csv
import json
from pathlib import Path


def test_current_model_contract_is_one_km_without_registration():
    from castravolt.features import ModelFeatures, RADIUS
    from castravolt.config import Settings
    from castravolt.inference import load_model
    assert RADIUS == 1000
    assert len(ModelFeatures.model_fields) == 10
    assert 'state_ev_registrations' not in ModelFeatures.model_fields
    model = load_model(Settings())
    assert model.radius_metres == 1000
    assert model.version.startswith('rf80-cv10-1km-')


def test_default_extraction_reproduces_training_pois_for_real_locations():
    from castravolt.features import extract_counts, RULES
    from castravolt.local_pois import load_snapshot, query_snapshot
    with Path('data/ML Data/updated_mevnet.csv').open(encoding='utf-8-sig', newline='') as f:
        training = list(csv.DictReader(f))
    with Path('data/ML Data/updated_mevnet_row_groups.csv').open(encoding='utf-8-sig', newline='') as f:
        provenance = list(csv.DictReader(f))
    snapshot = load_snapshot()
    for index in [0, 50, 150, 800, 1100, 1800]:
        lat, lon = float(provenance[index]['latitude']), float(provenance[index]['longitude'])
        actual = extract_counts(query_snapshot(snapshot, lat, lon), lat, lon)
        assert actual == {key: int(training[index][key]) for key in RULES}
