import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, FolderOpen, MapPin, Plus, Trash2, X } from 'lucide-react';
import { projectApi } from './api/projects';
import type { Prediction, Project, Site } from './api/projects';

const message=(error: unknown)=>error instanceof Error?error.message:'Unable to complete this request.';
const date=(value:string)=>new Date(value).toLocaleDateString('en-MY',{day:'numeric',month:'short',year:'numeric'});

function ProjectForm({initial, onSave, onCancel}: {initial?:Project; onSave:(name:string,description:string)=>Promise<void>;onCancel:()=>void}) {
  const [name,setName]=useState(initial?.name??''),[description,setDescription]=useState(initial?.description??'');
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{await onSave(name.trim(),description.trim());}catch(err){setError(message(err));}finally{setBusy(false);}}
  return <section className="editor-panel" aria-label={initial?'Edit project':'New project'}><div className="section-heading"><h2>{initial?'Edit project':'New project'}</h2><button className="icon-button" disabled={busy} onClick={onCancel} aria-label="Close project form"><X size={18}/></button></div>
    <form className="workspace-form" onSubmit={submit}><label>Project name<input autoFocus required maxLength={100} value={name} onChange={e=>setName(e.target.value)}/></label><label>Description (optional)<textarea maxLength={2000} rows={3} value={description} onChange={e=>setDescription(e.target.value)}/></label>
      {error&&<p role="alert" className="auth-error">{error}</p>}<div className="form-actions"><button className="button primary" disabled={busy||!name.trim()}>{busy?'Saving…':initial?'Save changes':'Create project'}</button><button type="button" className="button secondary" disabled={busy} onClick={onCancel}>Cancel</button></div></form></section>;
}

export function ProjectsPage(){
  const navigate=useNavigate(); const [projects,setProjects]=useState<Project[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[creating,setCreating]=useState(false),[attempt,setAttempt]=useState(0);
  useEffect(()=>{const controller=new AbortController();setLoading(true);setError('');projectApi<Project[]>('/projects','GET',undefined,controller.signal).then(setProjects).catch(err=>{if(!controller.signal.aborted)setError(message(err));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[attempt]);
  return <><div className="page-heading"><div><div className="eyebrow">YOUR PLANNING WORKSPACE</div><h1>Projects</h1><p>Keep proposed sites and planning decisions together.</p></div><button className="button primary" onClick={()=>setCreating(true)}><Plus size={17}/>New project</button></div>
    {creating&&<ProjectForm onCancel={()=>setCreating(false)} onSave={async(name,description)=>{const result=await projectApi<Project>('/projects','POST',{name,description});navigate(`/projects/${result.id}`);}}/>}
    {loading?<p role="status">Loading your projects…</p>:error?<section className="editor-panel"><p role="alert">{error}</p><button className="button secondary" onClick={()=>setAttempt(n=>n+1)}>Try again</button></section>:projects.length===0?<section className="empty-projects"><div className="empty-icon"><FolderOpen size={28}/></div><h2>No projects yet</h2><p>Create your first project to organise proposed charging sites.</p></section>:<div className="project-grid">{projects.map(project=><Link className="project-card" key={project.id} to={`/projects/${project.id}`}><div className="card-icon"><FolderOpen size={22}/><ArrowRight size={18}/></div><h2>{project.name}</h2><p>{project.description||'Add sites and explore your next location.'}</p><small>Updated {date(project.updated_at)}</small></Link>)}</div>}
    <div className="scope-note"><MapPin size={18}/><p>Study area: Kuala Lumpur and Selangor. Select a site on the map and generate a charging-point estimate.</p></div></>;
}

function SiteHistory({site,onClose}:{site:Site;onClose:()=>void}){
  const [items,setItems]=useState<Prediction[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[attempt,setAttempt]=useState(0);
  useEffect(()=>{const controller=new AbortController();setLoading(true);setError('');projectApi<Prediction[]>(`/sites/${site.id}/predictions`,'GET',undefined,controller.signal).then(setItems).catch(err=>{if(!controller.signal.aborted)setError(message(err));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});return()=>controller.abort();},[site.id,attempt]);
  return <section className="editor-panel"><div className="section-heading"><div><span className="eyebrow">SAVED RESULTS</span><h2>History · {site.name}</h2></div><button className="icon-button" aria-label="Close history" onClick={onClose}><X size={18}/></button></div>
    {loading?<p role="status">Loading history…</p>:error?<><p role="alert">{error}</p><button className="button secondary" onClick={()=>setAttempt(n=>n+1)}>Try again</button></>:items.length===0?<p>No predictions yet. Generate an estimate from this site on the map to add its first result.</p>:items.map(item=><article className="history-item" key={item.id}><h3>{item.displayed_total} total charging points</h3>{item.experimental&&<span className="history-experimental">Research prototype</span>}<p>{date(item.created_at)} · Model {item.model_version}</p><details><summary>View saved inputs and calculation</summary><p>Raw estimate: {item.raw_estimate} · Rounding: {item.rounding_policy}</p>{item.adoption_reference_year!=null&&item.adoption_value!=null&&<p>Legacy adoption context: {item.adoption_reference_year} · {item.adoption_value} registrations</p>}<p>POI rules: {item.extraction_rule_version}</p><pre>{JSON.stringify(item.input_snapshot,null,2)}</pre></details></article>)}
  </section>;
}

export function ProjectWorkspace(){
  const {projectId}=useParams();const navigate=useNavigate();
  const [project,setProject]=useState<Project|null>(null),[sites,setSites]=useState<Site[]>([]);
  const [loading,setLoading]=useState(true),[error,setError]=useState(''),[actionError,setActionError]=useState(''),[busy,setBusy]=useState(false),[attempt,setAttempt]=useState(0);
  const [editingProject,setEditingProject]=useState(false),[history,setHistory]=useState<Site|null>(null);
  const generation=useRef(0);
  useEffect(()=>{const controller=new AbortController();generation.current++;setLoading(true);setError('');setEditingProject(false);setHistory(null);setActionError('');
    Promise.all([projectApi<Project>(`/projects/${projectId}`,'GET',undefined,controller.signal),projectApi<Site[]>(`/projects/${projectId}/sites`,'GET',undefined,controller.signal)])
      .then(([p,s])=>{setProject(p);setSites(s);}).catch(err=>{if(!controller.signal.aborted)setError(message(err));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>{controller.abort();generation.current++;};},[projectId,attempt]);
  async function removeSite(site:Site){if(!window.confirm(`Delete “${site.name}” and all its saved predictions? This cannot be undone.`))return;const current=generation.current;setBusy(true);setActionError('');try{await projectApi(`/sites/${site.id}`,'DELETE');if(current!==generation.current)return;setSites(items=>items.filter(item=>item.id!==site.id));if(history?.id===site.id)setHistory(null);}catch(err){if(current===generation.current)setActionError(message(err));}finally{setBusy(false);}}
  async function removeProject(){if(!project||!window.confirm(`Delete “${project.name}”, all its sites and saved predictions? This cannot be undone.`))return;setBusy(true);setActionError('');const current=generation.current;try{await projectApi(`/projects/${project.id}`,'DELETE');if(current===generation.current)navigate('/');}catch(err){if(current===generation.current)setActionError(message(err));}finally{setBusy(false);}}
  if(loading)return <p role="status">Opening project…</p>;
  if(error||!project)return <section className="editor-panel"><h1>Unable to open project</h1><p role="alert">{error}</p><button className="button secondary" onClick={()=>setAttempt(n=>n+1)}>Try again</button> <Link to="/">Return to projects</Link></section>;
  return <><Link className="back-link" to="/"><ArrowLeft size={16}/>All projects</Link><div className="page-heading"><div><div className="eyebrow">PROJECT WORKSPACE</div><h1>{project.name}</h1><p>{project.description||'Organise the sites you are considering.'}</p></div><div className="form-actions"><button className="button secondary" disabled={busy} onClick={()=>{setEditingProject(true);setHistory(null);}}>Edit project</button><button className="button danger" disabled={busy} onClick={()=>void removeProject()}><Trash2 size={16}/>Delete project</button></div></div>
    {actionError&&<p className="auth-error" role="alert">{actionError}</p>}
    {editingProject&&<ProjectForm key={project.id} initial={project} onCancel={()=>setEditingProject(false)} onSave={async(name,description)=>{setBusy(true);try{const current=generation.current;const result=await projectApi<Project>(`/projects/${project.id}`,'PATCH',{name,description});if(current===generation.current){setProject(result);setEditingProject(false);}}finally{setBusy(false);}}}/>}
    <div className="section-heading"><div><h2>Saved sites <span className="count-pill">{sites.length}</span></h2><p>Proposed locations in this project.</p></div><div className="project-map-actions"><Link className="button primary" to={`/estimator?project=${projectId}`}><MapPin size={17}/>Add site on map</Link></div></div>
    {sites.length===0?<section className="empty-projects"><div className="empty-icon"><MapPin size={27}/></div><h2>No saved sites yet</h2><p>Add a proposed location to start building your project.</p></section>:<div className="project-grid">{sites.map(site=><article className="site-card" key={site.id}><div className="card-icon"><MapPin size={22}/><span className="category-pill">{site.category}</span></div><h3>{site.name}</h3><p>{site.address||'No address added'}</p><p className="coordinates">{site.latitude.toFixed(6)}, {site.longitude.toFixed(6)}</p><small>{site.state??'State pending location validation'}</small><div className="site-actions"><Link className="text-button" to={`/estimator?project=${projectId}&site=${site.id}`}>Open on map</Link><button className="button secondary" disabled={busy} onClick={()=>{setHistory(site);}}>History</button><button className="text-button danger" disabled={busy} onClick={()=>void removeSite(site)}>Delete</button></div></article>)}</div>}
    {history&&<SiteHistory key={history.id} site={history} onClose={()=>setHistory(null)}/>}
    <div className="scope-note"><MapPin size={18}/><p>Select and save sites on the map. Prepare context and generate estimates from each saved site.</p></div></>;
}
