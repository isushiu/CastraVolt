import pytest
from fastapi import HTTPException


def element(kind,id,tags,lat=3.1579,lon=101.7116):
    return {'type':kind,'id':id,'tags':tags,**({'lat':lat,'lon':lon} if kind=='node' else {'center':{'lat':lat,'lon':lon}})}


def payload(elements):
    return {'version':0.6,'osm3s':{'timestamp_osm_base':'2026-10-27T00:00:00Z'},'elements':elements+[{'type':'count','tags':{'total':str(len(elements))}}]}


def test_grouping_radius_and_conservative_duplicates():
    from castravolt.features import extract_counts
    hospital={'amenity':'hospital','wikidata':'Q123','name':'City Hospital'}
    data=payload([element('node',1,hospital),element('node',1,hospital),element('way',2,hospital),
        element('node',3,{'amenity':'hospital','name':'Other hospital'}),element('node',4,{'shop':'mall'}),
        element('way',5,{'amenity':'parking'}),element('node',6,{'amenity':'fuel'},lat=4),
        element('node',7,{'tourism':'hotel'}),element('node',8,{'office':'company'}),
        element('node',9,{'railway':'station','public_transport':'station'}),element('node',10,{'amenity':'university'})])
    counts=extract_counts(data,3.1579,101.7116)
    assert list(counts.values())==[1,0,1,1,1,1,2,1]


@pytest.mark.parametrize('data',[{}, {'elements':[]},payload([])|{'remark':'runtime error: timed out'},payload([{'type':'way','id':1,'tags':{'shop':'mall'}}])])
def test_incomplete_or_malformed_provider_results_fail(data):
    from castravolt.features import extract_counts
    with pytest.raises(HTTPException): extract_counts(data,3.1579,101.7116)


def test_complete_empty_query_is_zero_and_adoption_is_verified():
    from castravolt.features import extract_counts, adoption_context
    assert set(extract_counts(payload([]),3.1579,101.7116).values())=={0}
    assert adoption_context('SELANGOR')['value']==560
    assert adoption_context('W.P. KUALA LUMPUR')['value']==1237
    with pytest.raises(HTTPException): adoption_context('JOHOR')


def test_feature_order_matches_the_evaluated_model_manifest():
    import json
    from pathlib import Path
    from castravolt.features import ModelFeatures
    manifest=json.loads((Path(__file__).resolve().parents[1]/'model/verified_rf80_cv5/manifest.json').read_text())
    assert list(ModelFeatures.model_fields)==manifest['features']


def test_provider_overload_preserves_backoff_without_exposing_raw_errors():
    from urllib.error import HTTPError
    from castravolt.features import provider_failure
    status,message,delay=provider_failure(HTTPError('https://provider.invalid',429,'raw error',{'Retry-After':'75'},None))
    assert status==503 and delay==75
    assert 'overloaded' in message and 'raw error' not in message
