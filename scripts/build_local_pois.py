"""Build a compact, attributed facility catalogue from a genuine Geofabrik OSM extract."""
import argparse,gzip,hashlib,json
from pathlib import Path
import osmium
from castravolt.features import RULES,CATALOG_RULE_HASH as RULE_HASH
from castravolt.locations import boundaries

ROOT=Path(__file__).resolve().parents[1]


def matches(tags):
    return any(any((tags.get(key) not in {None,'','no','vacant'} if values==['*'] else tags.get(key) in values)
        for key,values in mapping.items()) for mapping in RULES.values())


def combine(boxes):
    if not boxes:return None
    return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]


def intersects(box,coverage):
    return box and box[0]<=coverage[2] and box[2]>=coverage[0] and box[1]<=coverage[3] and box[3]>=coverage[1]


def build(source,coverage,timestamp):
    relations={};roots={};wanted_ways=set();wanted_nodes=set();ways={};positions={};elements=[]
    class Relations(osmium.SimpleHandler):
        def relation(self,r):
            tags=dict(r.tags);members=[(m.type,m.ref) for m in r.members]
            relations[r.id]=members
            if matches(tags):roots[r.id]=tags
    print('Reading relation memberships…',flush=True);Relations().apply_file(str(source))
    visited=set()
    def collect(rid):
        if rid in visited:return
        visited.add(rid)
        for kind,id in relations.get(rid,[]):
            if kind=='w':wanted_ways.add(id)
            elif kind=='n':wanted_nodes.add(id)
            elif kind=='r':collect(id)
    for rid in roots:collect(rid)
    class Ways(osmium.SimpleHandler):
        def way(self,w):
            tags=dict(w.tags)
            if w.id in wanted_ways or matches(tags):
                refs=[n.ref for n in w.nodes];ways[w.id]=(tags,refs);wanted_nodes.update(refs)
    print('Reading facility ways…',flush=True);Ways().apply_file(str(source))
    class ReferencedNodes(osmium.SimpleHandler):
        def node(self,n):
            lon,lat=n.location.lon,n.location.lat
            positions[n.id]=[lon,lat,lon,lat]
    print('Reading referenced coordinates…',flush=True)
    ReferencedNodes().apply_file(str(source),filters=[osmium.filter.EntityFilter(osmium.osm.NODE),osmium.filter.IdFilter(wanted_nodes)])
    class FacilityNodes(osmium.SimpleHandler):
        def node(self,n):
            lon,lat=n.location.lon,n.location.lat
            if coverage[0]<=lon<=coverage[2] and coverage[1]<=lat<=coverage[3]:
                tags=dict(n.tags)
                if matches(tags):elements.append({'type':'node','id':n.id,'lat':lat,'lon':lon,'tags':tags})
    print('Reading tagged facility points…',flush=True)
    keys=sorted({key for mapping in RULES.values() for key in mapping})
    FacilityNodes().apply_file(str(source),filters=[osmium.filter.EntityFilter(osmium.osm.NODE),osmium.filter.KeyFilter(*keys)])
    way_bounds={};incomplete=set()
    for wid,(tags,refs) in ways.items():
        box=combine([positions[n] for n in refs if n in positions]);way_bounds[wid]=box
        if not box or any(n not in positions for n in refs):incomplete.add(('w',wid))
    def centre(kind,id,tags,box,missing):
        if missing and (not box or intersects(box,coverage)):
            raise ValueError(f'Incomplete source geometry near study coverage: {kind} {id}')
        if not box:return
        lon=(box[0]+box[2])/2;lat=(box[1]+box[3])/2
        if coverage[0]<=lon<=coverage[2] and coverage[1]<=lat<=coverage[3]:
            elements.append({'type':kind,'id':id,'center':{'lat':lat,'lon':lon},'tags':tags})
    for wid,(tags,refs) in ways.items():
        if matches(tags):centre('way',wid,tags,way_bounds[wid],('w',wid) in incomplete)
    memo={}
    def relation_box(rid,active):
        if rid in memo:return memo[rid]
        if rid in active:return None,True
        boxes=[];missing=False
        if rid not in relations:return None,True
        for kind,id in relations[rid]:
            if kind=='n':box=positions.get(id);bad=box is None
            elif kind=='w':box=way_bounds.get(id);bad=box is None or ('w',id) in incomplete
            else:box,bad=relation_box(id,active|{rid})
            if box:boxes.append(box)
            missing|=bad
        memo[rid]=(combine(boxes),missing or not boxes);return memo[rid]
    for rid,tags in roots.items():
        box,missing=relation_box(rid,set());centre('relation',rid,tags,box,missing)
    return sorted(elements,key=lambda item:(item['type'],item['id']))


def coverage_for_states():
    points=[]
    for feature in boundaries():
        geometry=feature['geometry'];polygons=[geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
        points.extend(point for polygon in polygons for ring in polygon for point in ring)
    return [min(p[0] for p in points)-.05,min(p[1] for p in points)-.05,max(p[0] for p in points)+.05,max(p[1] for p in points)+.05]


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);args=parser.parse_args()
    with osmium.io.Reader(str(args.source)) as reader:timestamp=reader.header().get('osmosis_replication_timestamp')
    if not timestamp:raise ValueError('Source has no replication timestamp')
    coverage=coverage_for_states();elements=build(args.source,coverage,timestamp)
    sha=hashlib.sha256()
    with args.source.open('rb') as stream:
        while chunk:=stream.read(1048576):sha.update(chunk)
    data={'coverage_bbox':coverage,'rule_sha256':RULE_HASH,'source_timestamp':timestamp,
        'source_url':'https://download.geofabrik.de/asia/'+args.source.name,'source_sha256':sha.hexdigest(),
        'attribution':'© OpenStreetMap contributors, extract by Geofabrik; ODbL 1.0','elements':elements}
    raw=gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0)
    folder=ROOT/'src/castravolt/resources';target=folder/'poi_snapshot.json.gz'
    partial=target.with_suffix('.gz.partial');partial.write_bytes(raw);partial.replace(target)
    manifest={k:v for k,v in data.items() if k!='elements'};manifest.update(snapshot_sha256=hashlib.sha256(raw).hexdigest(),element_count=len(elements),snapshot_bytes=len(raw))
    (folder/'poi_snapshot_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Published {len(elements)} facility representations, {len(raw)} compressed bytes',flush=True)
