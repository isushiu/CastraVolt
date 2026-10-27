import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Check, MapPin, Search } from 'lucide-react';
import { projectApi } from './api/projects';
import { ApiError } from './api/client';
import type { Project, Site } from './api/projects';
import type { components } from './api/schema';
import SiteMap from './SiteMap';
import type { Point } from './SiteMap';

type Location=components['schemas']['LocationResult'];
type SearchResult=components['schemas']['SearchResult'];
const errorMessage=(error:unknown)=>error instanceof Error?error.message:'Unable to complete this request.';

export default function Estimator(){
  const [params,setParams]=useSearchParams();const projectId=params.get('project')??'',siteId=params.get('site')??'';
  // Route identity resets every draft, request and save state on project/site changes.
  return <EstimatorEditor key={`${projectId}:${siteId}`} projectId={projectId} siteId={siteId} chooseProject={id=>setParams({project:id})}/>;
}

function EstimatorEditor({projectId,siteId,chooseProject}:{projectId:string;siteId:string;chooseProject:(id:string)=>void}){
  const [projects,setProjects]=useState<Project[]>([]),[categories,setCategories]=useState<string[]>([]),[project,setProject]=useState<Project|null>(null);
  const [loading,setLoading]=useState(true),[initialError,setInitialError]=useState(''),[attempt,setAttempt]=useState(0);
  const [point,setPoint]=useState<Point|null>(null);
  const [name,setName]=useState(''),[address,setAddress]=useState(''),[category,setCategory]=useState('Unknown'),[confirmed,setConfirmed]=useState(false);
  const [validation,setValidation]=useState<Location|null>(null),[validating,setValidating]=useState(false),[locationError,setLocationError]=useState('');
  const [query,setQuery]=useState(''),[results,setResults]=useState<SearchResult[]>([]),[searching,setSearching]=useState(false),[searched,setSearched]=useState(false),[searchError,setSearchError]=useState('');
  const [saving,setSaving]=useState(false),[saveError,setSaveError]=useState(''),[saved,setSaved]=useState<Site|null>(null);
  const [persistedId,setPersistedId]=useState(siteId);
  const [addressLoading,setAddressLoading]=useState(false),[addressError,setAddressError]=useState(''),[addressAttempt,setAddressAttempt]=useState(0);
  const alive=useRef(true),revision=useRef(0),pinGeneration=useRef(0),searchGeneration=useRef(0),searchAbort=useRef<AbortController|null>(null),validationAbort=useRef<AbortController|null>(null);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;searchAbort.current?.abort();validationAbort.current?.abort();};},[]);
  useEffect(()=>{const controller=new AbortController();setLoading(true);setInitialError('');
    Promise.all([projectApi<Project[]>('/projects','GET',undefined,controller.signal),projectApi<string[]>('/reference/site-categories','GET',undefined,controller.signal),
      projectId?projectApi<Project>(`/projects/${projectId}`,'GET',undefined,controller.signal):Promise.resolve(null),siteId?projectApi<Site>(`/sites/${siteId}`,'GET',undefined,controller.signal):Promise.resolve(null)])
      .then(([all,cats,p,site])=>{if(controller.signal.aborted)return;if(site&&site.project_id!==projectId)throw new Error('This site does not belong to the selected project.');setProjects(all);setCategories(cats);setProject(p);
        if(site){setPoint({latitude:site.latitude,longitude:site.longitude});setName(site.name);setAddress(site.address??'');setCategory(site.category);setConfirmed(true);}})
      .catch(err=>{if(!controller.signal.aborted)setInitialError(errorMessage(err));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[projectId,siteId,attempt]);
  function invalidate(){revision.current++;setSaved(null);setSaveError('');}
  function selectPoint(next:Point,selected?:SearchResult){
    pinGeneration.current++;
    searchAbort.current?.abort();searchGeneration.current++;setSearching(false);setResults([]);setSearched(false);
    validationAbort.current?.abort();invalidate();setValidation(null);setLocationError('');setPoint(next);setAddress(selected?.address??'');
    setConfirmed(false);
    if(selected&&!name.trim())setName(selected.name);
  }
  useEffect(()=>{
    if(!point)return;const controller=new AbortController();validationAbort.current?.abort();validationAbort.current=controller;
    setValidating(true);setValidation(null);setLocationError('');
    projectApi<Location>(`/locations/validate?latitude=${point.latitude}&longitude=${point.longitude}`,'GET',undefined,controller.signal)
      .then(result=>{if(!controller.signal.aborted)setValidation(result);})
      .catch(err=>{if(!controller.signal.aborted)setLocationError(err instanceof ApiError&&err.status===404?'The running backend is out of date. Stop CastraVolt and run start.cmd again, then retry.':errorMessage(err));})
      .finally(()=>{if(!controller.signal.aborted)setValidating(false);});
    return()=>controller.abort();
  },[point]);
  useEffect(()=>{
    setAddressError('');
    if(!point||!validation||address){setAddressLoading(false);return;}
    const controller=new AbortController();const currentPin=pinGeneration.current;setAddressLoading(true);
    // Resolve only the final pin, after interaction settles; share the provider's global quota.
    const timer=window.setTimeout(()=>{
      projectApi<SearchResult>(`/locations/address?latitude=${point.latitude}&longitude=${point.longitude}`,'GET',undefined,controller.signal)
        .then(result=>{if(!controller.signal.aborted&&currentPin===pinGeneration.current){setAddress(result.address);setName(current=>current.trim()?current:result.name);}})
        .catch(err=>{if(!controller.signal.aborted)setAddressError(errorMessage(err));})
        .finally(()=>{if(!controller.signal.aborted)setAddressLoading(false);});
    },1200);
    return()=>{window.clearTimeout(timer);controller.abort();};
  },[point,validation,address,addressAttempt]);
  async function search(e:FormEvent){
    e.preventDefault();searchAbort.current?.abort();const controller=new AbortController();searchAbort.current=controller;
    const generation=++searchGeneration.current;setSearching(true);setSearchError('');setResults([]);setSearched(false);
    try{const matches=await projectApi<SearchResult[]>(`/locations/search?q=${encodeURIComponent(query.trim())}`,'GET',undefined,controller.signal);if(!controller.signal.aborted&&generation===searchGeneration.current){setResults(matches);setSearched(true);}}
    catch(err){if(!controller.signal.aborted&&generation===searchGeneration.current)setSearchError(errorMessage(err));}
    finally{if(!controller.signal.aborted&&generation===searchGeneration.current)setSearching(false);}
  }
  async function save(e:FormEvent){e.preventDefault();if(!point||!validation||!project||!confirmed||addressLoading)return;
    setSaving(true);setSaveError('');const current=revision.current;
    try{const result=await projectApi<Site>(persistedId?`/sites/${persistedId}`:`/projects/${project.id}/sites`,persistedId?'PATCH':'POST',{name:name.trim(),address:address.trim(),category,latitude:point.latitude,longitude:point.longitude});
      if(alive.current&&current===revision.current){setPersistedId(result.id);setSaved(result);}
    }catch(err){if(alive.current&&current===revision.current)setSaveError(errorMessage(err));}
    finally{if(alive.current)setSaving(false);}
  }
  if(loading)return <p role="status">Opening site estimator…</p>;
  if(initialError)return <section className="editor-panel"><h1>Unable to open estimator</h1><p role="alert">{initialError}</p><button className="button secondary" onClick={()=>setAttempt(n=>n+1)}>Try again</button><Link to="/">Return to projects</Link></section>;
  if(!projectId)return <><div className="page-heading"><div><div className="eyebrow">PROJECT TOOLS</div><h1>Site estimator</h1><p>Choose the project for your proposed charging site.</p></div></div><section className="editor-panel"><h2>Start with a project</h2>{projects.length===0?<p>Create a project before saving a site. <Link to="/">Go to Projects</Link></p>:<div className="project-picker">{projects.map(item=><button key={item.id} className="project-choice" onClick={()=>chooseProject(item.id)}><MapPin size={19}/><span>{item.name}</span><span>Open estimator →</span></button>)}</div>}</section></>;
  return <><Link className="back-link" to={`/projects/${projectId}`}><ArrowLeft size={16}/>Back to {project?.name}</Link><div className="page-heading"><div><div className="eyebrow">PROPOSED CHARGING SITE</div><h1>Site estimator</h1><p>Choose a location and confirm the type of place hosting the chargers.</p></div><span className="category-pill">{siteId?'Edit saved site':'New proposed site'}</span></div>
    <div className="estimator-layout"><div className="estimator-map-column"><section className="search-panel"><form className="address-search" onSubmit={search}><label className="search-label">Find an address or place<input type="search" required minLength={3} maxLength={200} value={query} disabled={saving} placeholder="e.g. KLCC or Shah Alam" onChange={e=>{searchAbort.current?.abort();searchGeneration.current++;setSearching(false);setResults([]);setSearched(false);setSearchError('');setQuery(e.target.value);}}/></label><button className="button primary" disabled={saving||searching||query.trim().length<3}><Search size={16}/>{searching?'Searching…':'Search'}</button></form>
      {searchError&&<p role="alert" className="auth-error">{searchError}</p>}{searched&&results.length===0&&<p role="status">No matching places inside Selangor or Kuala Lumpur. Try a more specific place or use the map.</p>}
      {results.length>0&&<ul className="search-results" aria-label="Address search results">{results.map((item,index)=><li key={`${item.latitude}:${item.longitude}:${index}`}><button disabled={saving} onClick={()=>selectPoint(item,item)}><strong>{item.name}</strong><span>{item.address}</span></button></li>)}</ul>}
      <p className="provider-note">Search uses Nominatim · © OpenStreetMap contributors. Searches run only when submitted.</p></section>
      <SiteMap point={point} onSelect={selectPoint} disabled={saving}/>
    </div><section className="selection-panel"><div className="eyebrow">SELECTED LOCATION</div><h2>{point?'Your proposed site':'Choose a location'}</h2><p className="selection-description">Place a pin or choose a search result. Location details are derived from the pin.</p>
      <form onSubmit={save} className="workspace-form"><fieldset disabled={saving} className="site-fieldset"><dl className="coordinate-summary"><div><dt>Latitude</dt><dd>{point?point.latitude.toFixed(6):'—'}</dd></div><div><dt>Longitude</dt><dd>{point?point.longitude.toFixed(6):'—'}</dd></div></dl>
        {validating&&<p role="status">Checking study-state boundary…</p>}{locationError&&<div role="alert" className="auth-error">{locationError}{point&&<button type="button" className="text-button" onClick={()=>setPoint({...point})}>Retry location check</button>}</div>}
        {validation&&<div className="location-summary"><Check size={16}/><div><strong>{validation.state}</strong><span>Inside the supported state boundary</span></div></div>}
        <label>Site name<input required maxLength={100} value={name} onChange={e=>{invalidate();setName(e.target.value);}} placeholder="Name this proposed site"/></label>
        <div className="derived-address"><span>Address from pin</span><p>{addressLoading?'Looking up this location…':address||'No address available yet'}</p>{addressError&&<div role="status">{addressError}<button type="button" className="text-button" onClick={()=>setAddressAttempt(value=>value+1)}>Retry address</button></div>}</div>
        <label>Host-site category<select aria-label="Host-site category" aria-describedby="host-category-help" value={category} onChange={e=>{invalidate();setCategory(e.target.value);setConfirmed(false);}}>{categories.map(item=><option key={item}>{item}</option>)}</select><small id="host-category-help">The place hosting the chargers, rather than nearby facilities.</small></label>
        <label className="category-confirm"><input type="checkbox" checked={confirmed} onChange={e=>{invalidate();setConfirmed(e.target.checked);}}/>I confirm the host-site category.</label>
        <button className="button primary" disabled={!point||!validation||!name.trim()||!confirmed||saving||addressLoading||!!saved}>{saving?'Saving…':saved?'Site saved':siteId?'Save site changes':'Save proposed site'}</button></fieldset>
        {saveError&&<p role="alert" className="auth-error">{saveError}</p>}{saved&&<div className="saved-site-message" role="status"><Check size={18}/><div>Site saved to {project?.name}.<Link to={`/projects/${projectId}`}>View project and site history →</Link></div></div>}
      </form><div className="estimator-limitation"><strong>Study coverage</strong><p>State boundaries are checked using OSM-derived geoBoundaries (2017). Urban-only coverage is provisional. The 3 km circle is a preview; POI gathering and ML estimates come in later stages.</p><a href="https://www.geoboundaries.org/" target="_blank" rel="noreferrer">Boundary source and attribution</a></div>
    </section></div></>;
}
