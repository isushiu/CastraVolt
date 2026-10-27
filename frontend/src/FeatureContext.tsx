import type { components } from './api/schema';
import { useEffect,useState } from 'react';

export type PreparedContext=components['schemas']['PreparedContext'];
const groups=[['nearby_mall_count','Malls'],['nearby_petrol_count','Petrol stations'],['nearby_hotel_count','Hotels'],
  ['nearby_office_count','Offices'],['nearby_transit_count','Transit stations'],['nearby_university_count','Universities'],
  ['nearby_hospital_count','Hospitals'],['nearby_parking_count','Parking facilities']] as const;

export default function FeatureContext({context,busy,error,ready,onPrepare,retryAt=null}:{context:PreparedContext|null;busy:boolean;error:string;ready:boolean;onPrepare:()=>void;retryAt?:number|null}){
  const [clock,setClock]=useState(Date.now);
  useEffect(()=>{setClock(Date.now());if(!retryAt||retryAt<=Date.now())return;const timer=window.setInterval(()=>{setClock(Date.now());if(Date.now()>=retryAt)window.clearInterval(timer);},1000);return()=>window.clearInterval(timer);},[retryAt]);
  const remaining=retryAt?Math.max(0,Math.ceil((retryAt-clock)/1000)):0;
  return <section className="feature-context" aria-label="Site context"><h3>Surrounding area</h3><p>Gather mapped facilities within 3 km and the state’s EV registration context for this saved location.</p>
    {!ready&&<p className="context-help">Save the current site and category before preparing its context.</p>}
    <button type="button" className="button secondary" disabled={!ready||busy||remaining>0} onClick={onPrepare}>{busy?'Gathering facilities…':remaining>0?`Try again in ${remaining}s`:'Prepare site context'}</button>
    {busy&&<p role="status">Checking mapped facilities. This may take a little time.</p>}
    {error&&<p className="auth-error" role="alert">{error}</p>}
    {context&&<div className="prepared-context"><h4>Mapped facilities within 3 km</h4><dl className="facility-counts">{groups.map(([key,label])=><div key={key}><dt>{label}</dt><dd>{context.features[key]}</dd></div>)}</dl>
      <div className="adoption-context"><strong>{context.features.state_ev_registrations.toLocaleString()} new EV car registrations</strong><span>{context.features.state} · {context.adoption.reference_year} · electric motokar</span></div>
      <p className="context-warning" role="status">Research preview: these POI counting rules have not yet been verified against the training data.</p>
      <p className="context-help">Source: {context.provenance.provider} · map data dated {context.provenance.osm_base_timestamp.slice(0,10)}</p><details><summary>Sources and preparation details</summary><p>Prepared {new Date(context.extracted_at).toLocaleString()}{context.cache_hit?' · Reused cached extraction':''}</p><p>© OpenStreetMap contributors · ODbL</p><p>OSM source timestamp: {context.provenance.osm_base_timestamp}</p><p>Counting rules: {context.extraction_rule_version}</p><p>EV context: fixed 2025 new registrations, not fleet stock.</p></details>
    </div>}
  </section>;
}
