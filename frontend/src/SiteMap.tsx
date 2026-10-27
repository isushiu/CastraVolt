import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export type Point={latitude:number;longitude:number};
export const POI_RADIUS_METRES=3000;
const tileUrl=import.meta.env.VITE_MAP_TILE_URL||'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const tileAttribution=import.meta.env.VITE_MAP_TILE_ATTRIBUTION||'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const pin=L.divIcon({className:'planning-pin',iconSize:[34,44],iconAnchor:[17,43],html:'<svg width="34" height="44" viewBox="0 0 34 44" aria-hidden="true"><path d="M17 42S2 26 2 17a15 15 0 1 1 30 0c0 9-15 25-15 25Z" fill="#6546D7" stroke="white" stroke-width="2"/><circle cx="17" cy="17" r="5" fill="white"/></svg>'});

export default function SiteMap({point,onSelect,disabled=false}:{point:Point|null;onSelect:(point:Point)=>void;disabled?:boolean}){
  const host=useRef<HTMLDivElement>(null),map=useRef<L.Map|null>(null),marker=useRef<L.Marker|null>(null),circle=useRef<L.Circle|null>(null),tiles=useRef<L.TileLayer|null>(null);
  const select=useRef(onSelect),locked=useRef(disabled);select.current=onSelect;locked.current=disabled;
  const [error,setError]=useState(false),[loading,setLoading]=useState(true);
  useEffect(()=>{
    if(!host.current)return;
    const instance=L.map(host.current,{center:[3.139,101.6869],zoom:11,scrollWheelZoom:true});map.current=instance;
    const layer=L.tileLayer(tileUrl,{attribution:tileAttribution,maxZoom:19}).addTo(instance);tiles.current=layer;
    layer.on('tileerror',()=>{setError(true);setLoading(false);});layer.on('load',()=>setLoading(false));
    instance.on('click',(event:L.LeafletMouseEvent)=>{if(!locked.current)select.current({latitude:event.latlng.lat,longitude:event.latlng.lng});});
    const observer=new ResizeObserver(()=>instance.invalidateSize());observer.observe(host.current);
    return()=>{observer.disconnect();instance.remove();map.current=null;marker.current=null;circle.current=null;tiles.current=null;};
  },[]);
  useEffect(()=>{
    const instance=map.current;if(!instance||!point)return;
    const position:L.LatLngTuple=[point.latitude,point.longitude];
    if(!marker.current){
      marker.current=L.marker(position,{icon:pin,draggable:!disabled,title:'Proposed charging site. Drag to move the pin.',keyboard:true}).addTo(instance);
      marker.current.on('dragend',()=>{const location=marker.current!.getLatLng();if(!locked.current)select.current({latitude:location.lat,longitude:location.lng});});
      circle.current=L.circle(position,{radius:POI_RADIUS_METRES,color:'#6546D7',weight:2,fillOpacity:.08,dashArray:'7 6',interactive:false}).addTo(instance);
      marker.current.on('drag',()=>circle.current?.setLatLng(marker.current!.getLatLng()));
    }else{marker.current.setLatLng(position);circle.current?.setLatLng(position);}
    instance.setView(position,Math.max(instance.getZoom(),13));
  },[point?.latitude,point?.longitude]);
  useEffect(()=>{if(disabled)marker.current?.dragging?.disable();else marker.current?.dragging?.enable();},[disabled,point?.latitude,point?.longitude]);
  return <section className="map-panel" aria-label="Proposed site map"><div className="map-toolbar"><span>Click the map to place a pin</span><span className="radius-label">3 km radius</span></div>
    <div ref={host} className="site-map" aria-label="Interactive map of Kuala Lumpur and Selangor"/>
    {loading&&<p className="map-status" role="status">Loading map tiles…</p>}
    {error&&<div className="map-warning" role="alert">Map tiles could not load. Address search is still available. <button className="text-button" onClick={()=>{setError(false);setLoading(true);tiles.current?.redraw();}}>Retry map</button></div>}
    <p className="map-caption">The dashed circle shows 3,000 metres around the pin. <a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noreferrer">Report a map issue</a></p>
  </section>;
}
