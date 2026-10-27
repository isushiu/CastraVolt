"""Offline OSM facility catalogue; no remote service or cooldown on normal lookups."""
from functools import lru_cache
from importlib.resources import files
import gzip,hashlib,json,math
from fastapi import HTTPException


def read_snapshot(path,expected_sha):
    try:
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError()
        data=json.loads(gzip.decompress(raw))
        from castravolt.features import RULE_HASH
        if data['rule_sha256']!=RULE_HASH or not isinstance(data['elements'],list):raise ValueError()
        if len(data['coverage_bbox'])!=4:raise ValueError()
        data['_snapshot_sha256']=expected_sha
        return data
    except Exception:raise HTTPException(503,'The local facility snapshot is missing or invalid. Run setup or rebuild the snapshot.') from None


@lru_cache
def load_snapshot():
    try:
        folder=files('castravolt').joinpath('resources')
        manifest=json.loads(folder.joinpath('poi_snapshot_manifest.json').read_text(encoding='utf-8'))
        return read_snapshot(folder.joinpath('poi_snapshot.json.gz'),manifest['snapshot_sha256'])
    except HTTPException:raise
    except Exception:raise HTTPException(503,'The local facility snapshot is not installed. Run setup before preparing site context.') from None


def query_snapshot(snapshot,latitude,longitude):
    from castravolt.features import distance,RADIUS
    west,south,east,north=snapshot['coverage_bbox']
    lat_delta=math.degrees(RADIUS/6371008.8)
    lon_delta=math.degrees(math.asin(math.sin(RADIUS/6371008.8)/math.cos(math.radians(latitude))))
    if not (west<=longitude-lon_delta and longitude+lon_delta<=east and south<=latitude-lat_delta and latitude+lat_delta<=north):
        raise HTTPException(422,'This pin’s full 3 km circle is outside the installed facility snapshot coverage.')
    elements=[]
    for item in snapshot['elements']:
        point=item if item['type']=='node' else item['center']
        if distance((latitude,longitude),(point['lat'],point['lon']))<=RADIUS:elements.append(item)
    return {'version':0.6,'osm3s':{'timestamp_osm_base':snapshot['source_timestamp']},
        'elements':elements+[{'type':'count','tags':{'total':str(len(elements))}}]}
