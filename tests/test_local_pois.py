import json,gzip,hashlib
import pytest
from fastapi import HTTPException


def test_local_snapshot_returns_real_types_and_rejects_incomplete_coverage(tmp_path):
    from castravolt.local_pois import read_snapshot,query_snapshot
    from castravolt.features import RULE_HASH,extract_counts
    data={'coverage_bbox':[100.5,2.3,102.3,4.1],'rule_sha256':RULE_HASH,'source_timestamp':'2026-10-25T21:21:21Z',
        'source_url':'https://download.geofabrik.de/source.osm.pbf','elements':[
        {'type':'node','id':1,'lat':3.1579,'lon':101.7116,'tags':{'shop':'mall'}},
        {'type':'way','id':2,'center':{'lat':3.1579,'lon':101.7116},'tags':{'amenity':'hospital'}},
        {'type':'node','id':3,'lat':4,'lon':102,'tags':{'shop':'mall'}}]}
    path=tmp_path/'snapshot.json.gz';path.write_bytes(gzip.compress(json.dumps(data).encode()))
    snapshot=read_snapshot(path,hashlib.sha256(path.read_bytes()).hexdigest())
    counts=extract_counts(query_snapshot(snapshot,3.1579,101.7116),3.1579,101.7116)
    assert counts['nearby_mall_count']==1 and counts['nearby_hospital_count']==1
    with pytest.raises(HTTPException):query_snapshot(snapshot,4.09,102.29)
    with pytest.raises(HTTPException):read_snapshot(path,'incorrect')


def test_builder_resolves_way_and_relation_centres_from_source_nodes(tmp_path):
    pytest.importorskip('osmium')
    from scripts.build_local_pois import build
    source=tmp_path/'fixture.osm'
    source.write_text('''<osm version="0.6"><node id="1" lat="3.15" lon="101.70"><tag k="shop" v="mall"/></node>
    <node id="2" lat="3.16" lon="101.72"/><node id="3" lat="3.17" lon="101.74"/>
    <way id="10"><nd ref="2"/><nd ref="3"/><tag k="amenity" v="hospital"/></way>
    <relation id="20"><member type="way" ref="10" role="outer"/><tag k="amenity" v="university"/></relation></osm>''',encoding='utf-8')
    result=build(source,[101,2,102,4],'2026-10-25T21:21:21Z')
    assert len(result)==3
    assert next(x for x in result if x['type']=='way')['center']==pytest.approx({'lat':3.165,'lon':101.73})
    assert next(x for x in result if x['type']=='relation')['center']==pytest.approx({'lat':3.165,'lon':101.73})


def test_tls_uses_native_store_with_verification_enabled():
    import ssl
    from castravolt.network import tls_context
    context=tls_context()
    assert context.verify_mode==ssl.CERT_REQUIRED
    assert context.check_hostname is True
