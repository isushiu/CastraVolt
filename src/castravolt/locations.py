"""Local state-boundary validation and bounded, explicit address search."""
from datetime import timedelta
from functools import lru_cache
from importlib.resources import files
import json
import hashlib
import math
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from castravolt.account_models import AuthRateLimit, User
from castravolt.auth import current_user, database, digest, now, throttle
from castravolt.location_models import GeocodeCache
from castravolt.network import tls_context

router=APIRouter(prefix='/api/v1/locations',tags=['Locations'])
BOUNDARY_VERSION='MYS-ADM1-15666254-2017'


@lru_cache
def boundaries():
    folder=files('castravolt').joinpath('resources')
    raw=folder.joinpath('study_states.geojson').read_bytes()
    source=json.loads(folder.joinpath('study_states_source.json').read_text(encoding='utf-8'))
    if hashlib.sha256(raw).hexdigest()!=source['bundled_sha256']:
        raise HTTPException(503,'Study-state boundary validation is unavailable.')
    return json.loads(raw)['features']


def ring_status(x,y,ring):
    inside=False
    for (ax,ay),(bx,by) in zip(ring,ring[1:]):
        cross=(x-ax)*(by-ay)-(y-ay)*(bx-ax)
        if abs(cross)<1e-12 and min(ax,bx)-1e-12<=x<=max(ax,bx)+1e-12 and min(ay,by)-1e-12<=y<=max(ay,by)+1e-12:
            return 'boundary'
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax: inside=not inside
    return 'inside' if inside else 'outside'


def contains_polygon(x,y,polygon):
    return ring_status(x,y,polygon[0])=='inside' and all(ring_status(x,y,hole)=='outside' for hole in polygon[1:])


def resolve_state(latitude,longitude):
    if not math.isfinite(latitude) or not math.isfinite(longitude): raise HTTPException(422,'Enter valid coordinates.')
    found=[]
    for feature in boundaries():
        geometry=feature['geometry']
        polygons=[geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
        if any(contains_polygon(longitude,latitude,polygon) for polygon in polygons):
            found.append('SELANGOR' if feature['properties']['shapeName']=='Selangor' else 'W.P. KUALA LUMPUR')
    if len(found)!=1: raise HTTPException(422,'Choose a location inside Selangor or Kuala Lumpur, away from ambiguous state borders.')
    return found[0]


class LocationResult(BaseModel):
    latitude: float
    longitude: float
    state: str
    boundary_version: str=BOUNDARY_VERSION
    urban_coverage: str='provisional'


class SearchResult(LocationResult):
    name: str
    address: str


def reserve_geocoder(db):
    key_global=digest('geocoder:global')
    reservation=insert(AuthRateLimit).values(key=key_global,count=0,expires_at=func.clock_timestamp()+timedelta(seconds=1.1))
    reservation=reservation.on_conflict_do_update(index_elements=['key'],
        set_={'expires_at':func.clock_timestamp()+timedelta(seconds=1.1)},
        where=AuthRateLimit.expires_at<=func.clock_timestamp()).returning(AuthRateLimit.key)
    reserved=db.scalar(reservation); db.commit()
    if not reserved: raise HTTPException(429,'Address lookup is busy. Please retry in a moment.',headers={'Retry-After':'2'})


def fetch_reverse(settings,latitude,longitude):
    params=urlencode({'lat':latitude,'lon':longitude,'format':'jsonv2','zoom':18,'accept-language':'en'})
    request=UrlRequest(settings.geocoder_url.rstrip('/')+'/reverse?'+params,
        headers={'User-Agent':settings.geocoder_user_agent,'Accept':'application/json'})
    with urlopen(request,timeout=8,context=tls_context()) as response: raw=response.read(256001)
    if len(raw)>256000: raise ValueError('Provider response exceeds limit')
    result=json.loads(raw)
    if not isinstance(result,dict) or not result.get('display_name'): raise ValueError('No address returned')
    return result


@router.get('/address',response_model=SearchResult)
def address(request:Request,latitude:float=Query(ge=-90,le=90),longitude:float=Query(ge=-180,le=180),
            user:User=Depends(current_user),db:Session=Depends(database)):
    state=resolve_state(latitude,longitude)
    throttle(request,db,'geocode',str(user.id))
    settings=request.app.state.settings
    key=digest(f'{settings.geocoder_url}:reverse-v1:{BOUNDARY_VERSION}:{latitude:.6f}:{longitude:.6f}')
    cached=db.get(GeocodeCache,key)
    if cached and cached.expires_at>now():
        result=dict(cached.results[0]);result.update(latitude=latitude,longitude=longitude,state=state);db.commit();return result
    reserve_geocoder(db)
    try:
        data=fetch_reverse(settings,latitude,longitude)
        result=SearchResult(latitude=latitude,longitude=longitude,state=state,
            name=str(data.get('name') or '')[:100],address=str(data['display_name'])[:500]).model_dump()
    except Exception:
        raise HTTPException(503,'Address unavailable. Your pin and state are still valid; you can retry the lookup or save without an address.') from None
    db.execute(insert(GeocodeCache).values(key=key,results=[result],expires_at=now()+timedelta(days=7))
        .on_conflict_do_update(index_elements=['key'],set_={'results':[result],'expires_at':now()+timedelta(days=7)}))
    db.execute(delete(GeocodeCache).where(GeocodeCache.expires_at<now()));db.commit()
    return result


@router.get('/validate',response_model=LocationResult)
def validate(latitude:float=Query(ge=-90,le=90),longitude:float=Query(ge=-180,le=180),user:User=Depends(current_user)):
    return LocationResult(latitude=latitude,longitude=longitude,state=resolve_state(latitude,longitude))


def fetch_search(settings,query):
    params=urlencode({'q':query,'format':'jsonv2','limit':8,'countrycodes':'my',
                      'viewbox':'100.7,4.0,102.1,2.5','bounded':1,'accept-language':'en'})
    request=UrlRequest(settings.geocoder_url.rstrip('/')+'/search?'+params,
                       headers={'User-Agent':settings.geocoder_user_agent,'Accept':'application/json'})
    with urlopen(request,timeout=8,context=tls_context()) as response:
        raw=response.read(256001)
    if len(raw)>256000: raise ValueError('Provider response exceeds limit')
    data=json.loads(raw)
    if not isinstance(data,list): raise ValueError('Invalid provider response')
    return data[:8]


@router.get('/search',response_model=list[SearchResult])
def search(request:Request,q:str=Query(min_length=3,max_length=200),user:User=Depends(current_user),db:Session=Depends(database)):
    query=' '.join(q.split())
    if len(query)<3: raise HTTPException(422,'Enter at least three characters.')
    throttle(request,db,'geocode',str(user.id))
    settings=request.app.state.settings
    key=digest(settings.geocoder_url+':search-v1:'+BOUNDARY_VERSION+':'+query.casefold())
    cached=db.get(GeocodeCache,key)
    if cached and cached.expires_at>now():
        result=cached.results; db.commit(); return result
    # Atomic reservation shared by every API worker; no sleeps or per-worker loophole.
    reserve_geocoder(db)
    # Commit above returns the connection before calling the external provider.
    try:
        items=fetch_search(settings,query)
        results=[]
        for item in items:
            latitude,longitude=float(item['lat']),float(item['lon'])
            try: state=resolve_state(latitude,longitude)
            except HTTPException: continue
            results.append(SearchResult(latitude=latitude,longitude=longitude,state=state,
                name=str(item.get('name') or item.get('display_name','Selected location'))[:100],
                address=str(item.get('display_name',''))[:500]).model_dump())
    except Exception:
        raise HTTPException(503,'Address search is temporarily unavailable. Place the pin on the map instead.') from None
    db.execute(insert(GeocodeCache).values(key=key,results=results,expires_at=now()+timedelta(days=7))
        .on_conflict_do_update(index_elements=['key'],set_={'results':results,'expires_at':now()+timedelta(days=7)}))
    db.execute(delete(GeocodeCache).where(GeocodeCache.expires_at<now()));db.commit()
    return results
