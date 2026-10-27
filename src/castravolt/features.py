"""Versioned feature preparation. Provisional POI rules cannot certify model parity."""
from datetime import datetime,timedelta
from functools import lru_cache
from importlib.resources import files
import hashlib,json,math,logging,secrets,ssl
from uuid import UUID
from urllib.request import Request as UrlRequest,urlopen
from urllib.error import HTTPError,URLError

from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import delete,func,select,update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from castravolt.auth import csrf,current_user,current_session,database,digest,now,throttle
from castravolt.account_models import AuthRateLimit,User
from castravolt.feature_models import PoiCache
from castravolt.locations import BOUNDARY_VERSION,resolve_state
from castravolt.projects import owned_site
from castravolt.network import tls_context

router=APIRouter(prefix='/api/v1/sites',tags=['Feature preparation'])
RADIUS=3000
RULES={
 'nearby_mall_count':{'shop':['mall']},
 'nearby_petrol_count':{'amenity':['fuel']},
 'nearby_hotel_count':{'tourism':['hotel','motel','resort']},
 'nearby_office_count':{'office':['*'],'building':['office']},
 'nearby_transit_count':{'railway':['station','halt'],'public_transport':['station']},
 'nearby_university_count':{'amenity':['university']},
 'nearby_hospital_count':{'amenity':['hospital'],'healthcare':['hospital']},
 'nearby_parking_count':{'amenity':['parking']}}
RULE_VERSION='provisional-centres-wikidata50m-v1'
RULE_HASH=digest(json.dumps({'tags':RULES,'method':RULE_VERSION,'radius':RADIUS},sort_keys=True))
logger=logging.getLogger('castravolt')


def provider_failure(error):
    reason=error.reason if isinstance(error,URLError) else error
    if isinstance(error,HTTPError):
        if error.code in {429,503}:
            raw=error.headers.get('Retry-After','30') if error.headers else '30'
            delay=max(30,min(300,int(raw))) if raw.isdigit() else 30
            return 503,'The facilities provider is overloaded. Please try again after the retry wait.',delay
        return 503,'The facilities provider rejected the request. Please try again later.',30
    if isinstance(reason,TimeoutError):
        return 504,'The facilities provider timed out. Please try again shortly.',10
    if isinstance(reason,ssl.SSLError):
        return 503,'A secure connection to the facilities provider could not be verified. The provider connection needs attention.',30
    if isinstance(error,(URLError,ConnectionError,OSError)):
        return 503,'Cannot connect to the facilities provider. Please check the network or try again later.',10
    if isinstance(error,HTTPException):
        return error.status_code,'The facilities provider returned an incomplete response. Please try again.',10
    return 503,'The facilities provider returned an unreadable response. Please try again.',10


def finish_reservation(db,token,delay):
    # Only the request owning this lease may shorten it; a late response cannot release a newer lookup.
    db.execute(update(AuthRateLimit).where(AuthRateLimit.key==digest('overpass:global'),AuthRateLimit.count==token)
               .values(expires_at=func.clock_timestamp()+timedelta(seconds=delay)))
    db.commit()


@lru_cache
def adoption_manifest():
    try:
        data=json.loads(files('castravolt').joinpath('resources/adoption_2025.json').read_text(encoding='utf-8'))
        if data['reference_year']!=2025 or data['counts']!={'SELANGOR':560,'W.P. KUALA LUMPUR':1237}: raise ValueError()
        return data
    except Exception: raise HTTPException(503,'The evaluated adoption context is missing or invalid.') from None


def adoption_context(state):
    data=adoption_manifest()
    if state not in data['counts']: raise HTTPException(422,'No evaluated adoption context exists for this state.')
    return {'reference_year':2025,'value':data['counts'][state],'version':data['version'],'source_sha256':data['source_sha256'],'measure':data['measure']}


def distance(a,b):
    lat1,lon1,lat2,lon2=map(math.radians,(*a,*b))
    value=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371008.8*2*math.asin(min(1,math.sqrt(value)))


def extract_counts(data,latitude,longitude,*,radius_metres=RADIUS):
    try:
        if data.get('remark') or not isinstance(data.get('elements'),list): raise ValueError()
        timestamp=datetime.fromisoformat(data['osm3s']['timestamp_osm_base'].replace('Z','+00:00'))
        if timestamp.tzinfo is None: raise ValueError()
        elements=data['elements']
        if not elements or elements[-1].get('type')!='count': raise ValueError()
        if int(elements[-1]['tags']['total'])!=len(elements)-1 or len(elements)>20001: raise ValueError()
        items={}
        for item in elements[:-1]:
            kind=item['type'];identifier=item['id'];tags=item.get('tags',{})
            if kind not in {'node','way','relation'} or type(identifier) is not int or not isinstance(tags,dict): raise ValueError()
            if any(not isinstance(k,str) or not isinstance(v,str) for k,v in tags.items()): raise ValueError()
            position=item if kind=='node' else item['center']
            lat,lon=float(position['lat']),float(position['lon'])
            if not math.isfinite(lat) or not math.isfinite(lon) or abs(lat)>90 or abs(lon)>180: raise ValueError()
            if distance((latitude,longitude),(lat,lon))<=radius_metres:
                items[(kind,identifier)]={'tags':tags,'point':(lat,lon),'type':kind}
        counts={}
        for feature,mapping in RULES.items():
            facilities=[]
            identity_index={}
            for key,item in sorted(items.items()):
                tags=item['tags']
                if not any((tags.get(k) not in {None,'','no','vacant'} if values==['*'] else tags.get(k) in values) for k,values in mapping.items()): continue
                name=' '.join(tags.get('name','').casefold().split());identity=tags.get('wikidata','')
                candidates=identity_index.get((identity,name),[]) if identity and name else []
                match=next((f for f in candidates if item['type'] not in f['types'] and distance(item['point'],f['point'])<=50),None)
                if match: match['types'].add(item['type'])
                else:
                    facility={'identity':identity,'name':name,'point':item['point'],'types':{item['type']}}
                    facilities.append(facility)
                    if identity and name: identity_index.setdefault((identity,name),[]).append(facility)
            counts[feature]=len(facilities)
        return counts
    except (KeyError,ValueError,TypeError,AttributeError,IndexError,OverflowError):
        raise HTTPException(503,'POI provider returned incomplete or invalid data. Counts were not filled with zeros.') from None


def build_query(latitude,longitude):
    if not all(math.isfinite(v) for v in [latitude,longitude]): raise HTTPException(422,'Invalid coordinates')
    selectors=set()
    for mapping in RULES.values():
        for key,values in mapping.items():
            if values==['*']: selectors.add(f'nwr(around:{RADIUS},{latitude:.8f},{longitude:.8f})["{key}"];')
            else:
                for value in values: selectors.add(f'nwr(around:{RADIUS},{latitude:.8f},{longitude:.8f})["{key}"="{value}"];')
    return '[out:json][timeout:20][maxsize:33554432];('+''.join(sorted(selectors))+');out body center;out count;'


def fetch_overpass(settings,latitude,longitude):
    request=UrlRequest(settings.overpass_url,data=build_query(latitude,longitude).encode(),method='POST',
        headers={'Content-Type':'text/plain; charset=utf-8','Accept':'application/json','User-Agent':'CastraVolt/0.1 (EV site context research)'})
    with urlopen(request,timeout=25,context=tls_context()) as response: raw=response.read(4000001)
    if len(raw)>4000000: raise ValueError('POI response exceeds 4 MB')
    return json.loads(raw)


class ModelFeatures(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    nearby_mall_count:int=Field(ge=0)
    nearby_petrol_count:int=Field(ge=0)
    nearby_hotel_count:int=Field(ge=0)
    nearby_office_count:int=Field(ge=0)
    nearby_transit_count:int=Field(ge=0)
    nearby_university_count:int=Field(ge=0)
    nearby_hospital_count:int=Field(ge=0)
    nearby_parking_count:int=Field(ge=0)
    state_ev_registrations:int=Field(ge=0)
    category:str
    state:str


class AdoptionContext(BaseModel):
    reference_year:int
    value:int
    version:str
    source_sha256:str
    measure:str


class PoiProvenance(BaseModel):
    provider:str
    osm_base_timestamp:str
    response_sha256:str
    geometry:str
    deduplication:str
    attribution:str
    source_url:str|None=None
    source_snapshot_sha256:str|None=None


class PreparedContext(BaseModel):
    site_id:str
    site_updated_at:datetime
    features:ModelFeatures
    radius_metres:int=RADIUS
    extraction_rule_version:str=RULE_VERSION
    rule_sha256:str=RULE_HASH
    boundary_version:str=BOUNDARY_VERSION
    extracted_at:datetime
    cache_hit:bool
    provenance:PoiProvenance
    adoption:AdoptionContext
    inference_eligible:bool=False
    limitation:str='Live POI counting rules are provisional; equivalence to the training features is not verified.'


@router.post('/{site_id}/features',response_model=PreparedContext,dependencies=[Depends(csrf)])
def prepare_features(site_id:UUID,request:Request,user:User=Depends(current_user),db:Session=Depends(database)):
    site=owned_site(db,user,site_id)
    snapshot={'latitude':site.latitude,'longitude':site.longitude,'category':site.category,'updated_at':site.updated_at}
    state=resolve_state(site.latitude,site.longitude);adoption=adoption_context(state)
    throttle(request,db,'features',str(user.id))
    settings=request.app.state.settings
    local=None
    if settings.poi_source=='local':
        from castravolt.local_pois import load_snapshot
        local=load_snapshot()
    source='local-osm:'+local['_snapshot_sha256'] if local is not None else settings.overpass_url
    key=digest(json.dumps([snapshot['latitude'],snapshot['longitude'],RADIUS,RULE_HASH,source]))
    cached=db.get(PoiCache,key);hit=bool(cached and cached.expires_at>now())
    if hit:
        counts=cached.counts;provenance=cached.provenance;extracted=cached.extracted_at;db.commit()
    else:
        if local is not None:
            from castravolt.local_pois import query_snapshot
            db.commit()
            data=query_snapshot(local,snapshot['latitude'],snapshot['longitude'])
            counts=extract_counts(data,snapshot['latitude'],snapshot['longitude'])
        else:
            token=secrets.randbelow(2**30)+1
            reservation=insert(AuthRateLimit).values(key=digest('overpass:global'),count=token,expires_at=func.clock_timestamp()+timedelta(seconds=35))
            reservation=reservation.on_conflict_do_update(index_elements=['key'],set_={'count':token,'expires_at':func.clock_timestamp()+timedelta(seconds=35)},where=AuthRateLimit.expires_at<=func.clock_timestamp()).returning(AuthRateLimit.key)
            reserved=db.scalar(reservation);db.commit()
            if not reserved:
                remaining=db.scalar(select(func.extract('epoch',AuthRateLimit.expires_at-func.clock_timestamp())).where(AuthRateLimit.key==digest('overpass:global')))
                delay=max(1,math.ceil(remaining or 1));db.commit()
                raise HTTPException(429,f'Another area lookup or its retry wait is active. Try again in {delay} seconds.',headers={'Retry-After':str(delay)})
            try:
                data=fetch_overpass(settings,snapshot['latitude'],snapshot['longitude'])
                counts=extract_counts(data,snapshot['latitude'],snapshot['longitude'])
            except Exception as error:
                status,message,delay=provider_failure(error)
                finish_reservation(db,token,delay)
                logger.warning('poi_provider_failure kind=%s status=%s request_id=%s',type(error).__name__,status,getattr(request.state,'request_id','unknown'))
                raise HTTPException(status,message,headers={'Retry-After':str(delay)}) from None
            finish_reservation(db,token,2)
        extracted=now()
        provenance={'provider':'Local Geofabrik OSM snapshot' if local is not None else settings.overpass_url,'osm_base_timestamp':data['osm3s']['timestamp_osm_base'],
            'response_sha256':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),
            'geometry':'node coordinates or bounding-box centre; geodesic radius filter','deduplication':RULE_VERSION,
            'attribution':'© OpenStreetMap contributors (ODbL)'}
        if local is not None:provenance.update(source_url=local['source_url'],source_snapshot_sha256=local['_snapshot_sha256'])
        db.execute(insert(PoiCache).values(key=key,counts=counts,provenance=provenance,extracted_at=extracted,expires_at=extracted+timedelta(hours=settings.poi_cache_hours))
            .on_conflict_do_update(index_elements=['key'],set_={'counts':counts,'provenance':provenance,'extracted_at':extracted,'expires_at':extracted+timedelta(hours=settings.poi_cache_hours)}))
        db.execute(delete(PoiCache).where(PoiCache.expires_at<now()));db.commit()
    # A remote query must not authorise a stale site or an expired/revoked session.
    if not current_session(request,db): raise HTTPException(401,'Please sign in to continue.')
    db.expire_all();current=owned_site(db,user,site_id)
    if current.updated_at!=snapshot['updated_at']: raise HTTPException(409,'This site changed during lookup. Save the current selection and prepare again.')
    return PreparedContext(site_id=str(site_id),site_updated_at=snapshot['updated_at'],features=ModelFeatures(**counts,
        state_ev_registrations=adoption['value'],category=snapshot['category'],state=state),
        extracted_at=extracted,cache_hit=hit,provenance=provenance,adoption=adoption)
