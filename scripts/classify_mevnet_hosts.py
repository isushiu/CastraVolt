"""Conservative host-site classification from spatial/name matches to genuine OSM objects."""
import csv
import gzip
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from castravolt.features import distance
from castravolt.locations import contains_polygon

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'data/updated_mevnet_source'
KEYS=['name','amenity','shop','office','building','tourism','leisure','aeroway','highway']


def category_from_tags(t):
    a=t.get('amenity');shop=t.get('shop');b=t.get('building');tour=t.get('tourism');leisure=t.get('leisure')
    if t.get('highway') in {'services','rest_area'}:return 'R&R'
    if a=='fuel':return 'Petrol Station'
    if shop=='mall':return 'Galleria' if 'galleria' in t.get('name','').lower() else 'Shopping Mall'
    if shop in {'car','motorcycle'}:return 'Showroom'
    if a=='hospital' or t.get('healthcare')=='hospital':return 'Hospital'
    if a=='university':return 'University'
    if a=='place_of_worship':return 'Prayer Hall'
    if a=='library':return 'Library'
    if a in {'conference_centre','events_venue'}:return 'Convention Center'
    if a in {'restaurant','cafe','fast_food','food_court','bar','pub','ice_cream'}:return 'F&B'
    if a in {'cinema','theatre','nightclub'}:return 'Entertainment'
    if tour in {'hotel','motel','resort','guest_house','hostel'} or b=='hotel':return 'Hotel & Resort'
    if tour=='theme_park':return 'Theme Park'
    if t.get('aeroway') in {'aerodrome','terminal'}:return 'Airport'
    if leisure in {'sports_centre','golf_course','fitness_centre','recreation_ground','swimming_pool','water_park'}:return 'Recreation Center'
    if t.get('office') not in {None,'','no','vacant'} or b=='office' or a in {'townhall','courthouse'}:return 'Office'
    if b in {'apartments','condominium'}:return 'Strata'
    if b in {'house','detached','terrace','semidetached_house','residential'}:return 'Residences'
    if a in {'bank','post_office','car_wash','vehicle_inspection','police','fire_station'} or shop in {'car_repair','laundry','dry_cleaning'}:return 'Services'
    if shop in {'supermarket','department_store','convenience','wholesale','hardware','furniture','electronics'}:return 'Others'
    return None


def normalise(value):
    value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()
    value=value.replace('&',' and ').replace("'",'')
    return ' '.join(re.findall(r'[a-z0-9]+',value))


def similarity(site_name,tags):
    names=[tags.get(k,'') for k in ['name','name:en','official_name','alt_name','brand','operator']]
    site=normalise(site_name)
    scores=[]
    for name in names:
        name=normalise(name)
        if not name or not site:continue
        score=SequenceMatcher(None,site,name).ratio()
        if site==name:score=1
        elif len(name)>=5 and (site.startswith(name+' ') or site.endswith(' '+name)):score=max(score,.88)
        scores.append(score)
    return max(scores,default=0)


def explicit_host_category(name):
    text=normalise(name)
    rules=[('Petrol Station',r'\b(shell|petronas|petron|caltex|bhp|bhpetrol|petrol|fuel|five|5petrol)\b'),
           ('Shopping Mall',r'\b(mall|shopping centre|shopping center)\b'),
           ('Hotel & Resort',r'\b(hotel|resort|chalet)\b'),('University',r'\b(university|universiti)\b'),
           ('Hospital',r'\b(hospital)\b'),('Library',r'\b(library|perpustakaan|ppas)\b'),
           ('Prayer Hall',r'\b(mosque|masjid|surau|balai islam|temple|church)\b'),
           ('F&B',r'\b(kfc|mcdonalds|restaurant|restoran|cafe|starbucks|food court)\b'),
           ('R&R',r'\b(r and r|rest area|rest stop|rest and service)\b'),
           ('Theme Park',r'\b(theme park|escape)\b'),
           ('Recreation Center',r'\b(golf|stadium|sports centre|sports center|country club)\b')]
    categories={category for category,pattern in rules if re.search(pattern,text)}
    return next(iter(categories)) if len(categories)==1 else None


def match_host(site,candidates):
    lat,lon=site.get('latitude'),site.get('longitude')
    if lat is None or lon is None or not all(math.isfinite(v) for v in [lat,lon]):
        return {'category':None,'reason':'invalid_coordinates','candidates':[]}
    matches=[]
    explicit=explicit_host_category(site['location'])
    for item in candidates:
        tags=item['tags'];category=category_from_tags(tags)
        if category is None:continue
        if explicit and category!=explicit:continue
        metres=distance((lat,lon),(item['lat'],item['lon']))
        ring=item.get('ring');inside=bool(ring and contains_polygon(lon,lat,[ring]))
        name_score=similarity(site['location'],tags)
        # Proximity alone never identifies a host. A containing typed polygon is
        # evidence, but name-supported matches take priority over broad enclosing sites.
        if name_score>=.82 and metres<=250:score=.9+.1*name_score-min(metres,250)/5000
        elif inside and name_score>=.5:score=.88+.05*name_score
        elif inside and explicit==category:score=.80
        else:continue
        matches.append({'category':category,'score':round(score,5),'distance_metres':round(metres,2),
                        'inside_polygon':inside,'name_score':round(name_score,4),
                        'osm_url':f"https://www.openstreetmap.org/{item['type']}/{item['id']}",
                        'osm_name':tags.get('name',''),'tags':tags})
    matches.sort(key=lambda x:x['score'],reverse=True)
    if not matches:return {'category':None,'reason':'no_supported_host_match','candidates':[]}
    best=matches[0]
    if any(x['category']!=best['category'] and best['score']-x['score']<.08 for x in matches[1:]):
        return {'category':None,'reason':'conflicting_host_matches','candidates':matches[:5]}
    return {'category':best['category'],'reason':'osm_name_and_location' if best['name_score']>=.82 else 'osm_containing_host_polygon',
            'evidence':best,'candidates':matches[:5]}


def build_catalogue():
    import osmium
    source=ROOT/'data/poi/source/malaysia-singapore-brunei-261025.osm.pbf'
    data=[];bbox=[100.70,2.49,102.08,3.98]
    class Handler(osmium.SimpleHandler):
        def node(self,n):
            if not n.location.valid():return
            lat,lon=n.location.lat,n.location.lon
            if not (bbox[0]<=lon<=bbox[2] and bbox[1]<=lat<=bbox[3]):return
            tags=dict(n.tags)
            if category_from_tags(tags):data.append({'type':'node','id':n.id,'lat':lat,'lon':lon,'tags':tags})
        def way(self,w):
            tags=dict(w.tags)
            if not category_from_tags(tags):return
            if not w.nodes or any(not n.location.valid() for n in w.nodes):return
            points=[(n.lon,n.lat) for n in w.nodes]
            west=min(p[0] for p in points);east=max(p[0] for p in points)
            south=min(p[1] for p in points);north=max(p[1] for p in points)
            if not (west<=bbox[2] and east>=bbox[0] and south<=bbox[3] and north>=bbox[1]):return
            item={'type':'way','id':w.id,'lat':(south+north)/2,'lon':(west+east)/2,'tags':tags}
            if len(points)>=4 and points[0]==points[-1]:item['ring']=points
            data.append(item)
    print('Reading named and typed OSM host objects and building footprints…',flush=True)
    Handler().apply_file(str(source),locations=True,idx='flex_mem',
                        filters=[osmium.filter.KeyFilter(*KEYS)])
    payload={'source':source.name,'source_date':'2026-10-25','attribution':'OpenStreetMap contributors; Geofabrik; ODbL 1.0',
             'limitations':'Node and way evidence only; multipolygon relations and unmapped venues can remain unresolved.',
             'objects':data}
    (FOLDER/'host_osm_catalogue.json.gz').write_bytes(gzip.compress(json.dumps(payload).encode(),mtime=0))
    print(f'Indexed {len(data)} OSM host objects',flush=True)
    return payload


def main():
    path=FOLDER/'host_osm_catalogue.json.gz'
    catalogue=json.loads(gzip.decompress(path.read_bytes())) if path.exists() else build_catalogue()
    grid=defaultdict(list);step=.005
    for item in catalogue['objects']:
        ring=item.get('ring')
        xs=[p[0] for p in ring] if ring else [item['lon']]
        ys=[p[1] for p in ring] if ring else [item['lat']]
        for x in range(math.floor(min(xs)/step),math.floor(max(xs)/step)+1):
            for y in range(math.floor(min(ys)/step),math.floor(max(ys)/step)+1):grid[x,y].append(item)
    sources=[x['attributes'] for x in json.loads((FOLDER/'features.json').read_text(encoding='utf-8'))]
    overrides=json.loads((FOLDER/'verified_category_overrides.json').read_text(encoding='utf-8'))
    # Re-evaluate inferred matches on every run; do not silently freeze old rules.
    overrides={key:value for key,value in overrides.items() if not value.get('source','').startswith('OSM')}
    reviews=[];added=0
    for site in sources:
        if site.get('category') or str(site['objectid']) in overrides:continue
        lat,lon=site.get('latitude'),site.get('longitude');candidates={}
        if lat is not None and lon is not None:
            gx,gy=math.floor(lon/step),math.floor(lat/step)
            for x in range(gx-1,gx+2):
                for y in range(gy-1,gy+2):
                    for item in grid[x,y]:candidates[item['type'],item['id']]=item
        result=match_host(site,list(candidates.values()))
        review={'objectid':site['objectid'],'location':site['location'],'state':site['state'],
                'latitude':lat,'longitude':lon,**result}
        reviews.append(review)
        if result['category']:
            overrides[str(site['objectid'])]={'category':result['category'],
                **{key:site[key] for key in ['location','state','latitude','longitude']},
                'source':'OSM inferred host category (not official MEVnet)',
                'source_url':result['evidence']['osm_url'],'matching':result['reason'],
                'evidence':result['evidence'],'osm_snapshot_date':catalogue['source_date']}
            added+=1
    (FOLDER/'verified_category_overrides.json').write_text(json.dumps(overrides,indent=2),encoding='utf-8')
    (FOLDER/'host_category_evidence.json').write_text(json.dumps(reviews,indent=2),encoding='utf-8')
    with (FOLDER/'host_category_review.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        fields=['objectid','location','state','latitude','longitude','category','reason','osm_url','osm_name']
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in reviews:
            writer.writerow({**{key:row.get(key) for key in fields[:7]},
                'osm_url':row.get('evidence',{}).get('osm_url',''),'osm_name':row.get('evidence',{}).get('osm_name','')})
    print(json.dumps({'checked':len(reviews),'assigned':added,'unresolved':len(reviews)-added,
                      'assigned_categories':dict(Counter(x['category'] for x in reviews if x['category']))},indent=2))


if __name__=='__main__':main()
