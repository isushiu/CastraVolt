import { useEffect, useRef, useState } from 'react';
import { NavLink, Route, Routes } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, BarChart3, Check, ChevronRight, CircleHelp,
  Compass, FolderOpen, Layers3, MapPin, Menu, PanelLeftClose, RefreshCw, ShieldCheck, X, Zap } from 'lucide-react';
import { getSystemInfo } from './api/client';
import { AuthPage, AuthProvider, RequireAuth, useAuth } from './auth';

function Projects() {
  return <>
    <div className="page-heading"><div><div className="eyebrow">YOUR PLANNING WORKSPACE</div>
      <h1>Projects</h1><p>A considered place to plan what comes next.</p></div>
      <span className="preview-badge"><span /> Planner workspace</span></div>
    <section className="welcome-panel" aria-labelledby="welcome-heading">
      <div className="welcome-copy"><span className="section-kicker">BETTER PLACES TO CHARGE</span>
        <h2 id="welcome-heading">Turn a location into<br />a planning decision.</h2>
        <p>Explore the surroundings. Understand the context.<br className="desktop-break" /> Plan EV infrastructure with a clearer picture.</p>
        <a className="button primary" href="#planning-workflow">Explore the workflow <ArrowRight size={16}/></a>
        <div className="welcome-footnote"><MapPin size={14}/> Kuala Lumpur &amp; Selangor</div></div>
      <div className="location-illustration" aria-hidden="true">
        <svg viewBox="0 0 410 310" role="presentation">
          <defs><pattern id="map-grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M 32 0 L 0 0 0 32" fill="none" stroke="#E3DDF2" strokeWidth="0.7"/></pattern></defs>
          <rect x="0" y="0" width="410" height="310" fill="url(#map-grid)"/>
          <path d="M0 245L130 195L230 225L410 145M65 0L125 100L115 310M0 110L185 90L410 30M285 0L255 130L345 310" className="illustration-road"/>
          <circle cx="221" cy="148" r="99" fill="#6546D7" fillOpacity="0.035" stroke="#6546D7" strokeDasharray="5 6"/>
          <circle cx="221" cy="148" r="65" fill="#6546D7" fillOpacity="0.04"/>
          <circle cx="148" cy="112" r="6" fill="#B7A7EC"/><circle cx="278" cy="192" r="6" fill="#B7A7EC"/>
          <circle cx="251" cy="77" r="5" fill="#B7A7EC"/><circle cx="173" cy="205" r="5" fill="#B7A7EC"/>
          <path d="M221 163s-21-22-21-36a21 21 0 0142 0c0 14-21 36-21 36z" fill="#6546D7"/>
          <circle cx="221" cy="127" r="7" fill="white"/>
        </svg>
        <div className="illustration-note"><span className="note-icon"><Zap size={15}/></span><div>One location. More context.<small>Site category · Nearby facilities · EV adoption</small></div></div>
        <span className="illustration-caption">Illustration · not a geographic map</span>
      </div>
    </section>
    <div className="section-heading"><div><h2>Your projects</h2><p>Your sites and estimates will stay together here.</p></div><span className="quiet-label"><ShieldCheck size={14}/> Private by design</span></div>
    <section className="empty-projects" aria-labelledby="private-workspace-heading">
      <div className="empty-icon"><FolderOpen size={27} strokeWidth={1.5}/></div>
      <h3 id="private-workspace-heading">A space for your next project</h3>
      <p>Your account is ready.<br />Project creation and saved sites are coming next.</p>
      <span className="upcoming-tag">Project creation coming soon</span>
    </section>
    <section className="workflow" id="planning-workflow" aria-labelledby="workflow-heading">
      <div className="section-heading"><div><span className="eyebrow">FROM PLACE TO POSSIBILITY</span><h2 id="workflow-heading">A clear path to your estimate</h2></div><span className="quiet-label">The planning workflow</span></div>
      <div className="workflow-grid">{[
        { icon: MapPin, number: '01', title: 'Choose a location', text: 'Find a proposed site on the map and confirm the type of place.' },
        { icon: Layers3, number: '02', title: 'Understand the area', text: 'Bring together mapped facilities within 3 km and state EV registration context.' },
        { icon: Zap, number: '03', title: 'Review your estimate', text: 'See estimated total charging points, with the inputs behind the result.' },
      ].map(item => <article className="workflow-item" key={item.number}><div className="workflow-top"><item.icon size={20} strokeWidth={1.6}/><span>{item.number}</span></div><h3>{item.title}</h3><p>{item.text}</p></article>)}</div>
    </section>
    <div className="scope-note"><CircleHelp size={17}/><p>Planning estimates support a decision; they do not replace a site assessment, grid-capacity check or installation design.</p></div>
  </>;
}

function RoadmapPage({ trends = false }: { trends?: boolean }) {
  return <><div className="eyebrow">{trends ? 'REGISTRATION CONTEXT' : 'PROJECT TOOLS'}</div><h1>{trends ? 'EV adoption trends' : 'Site estimator'}</h1>
    <section className="empty-projects"><div className="empty-icon">{trends ? <BarChart3/> : <MapPin/>}</div><h2>{trends ? 'Monthly context, clearly presented' : 'Start with a proposed location'}</h2><p>{trends ? 'The monthly dashboard will bring together filtered 2024–2026 registrations with state and period comparisons.' : 'The estimator will connect a selected site, surrounding facilities and a planning estimate within your project.'}</p><span className="upcoming-tag">Coming in a later stage</span></section></>;
}

function Connection() {
  const [state, setState] = useState<'loading'|'online'|'offline'>('loading');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState('loading');
    getSystemInfo(controller.signal).then(() => setState('online')).catch(() => {
      if (!controller.signal.aborted) setState('offline');
    });
    return () => controller.abort();
  }, [attempt]);
  return <div className={`connection ${state}`} role="status"><span className="status-dot"/>
    {state === 'online' ? 'Service connected' : state === 'loading' ? 'Connecting…' : 'Service unavailable'}
    {state === 'offline' && <button onClick={() => setAttempt(n=>n+1)} aria-label="Retry connection"><RefreshCw size={13}/></button>}</div>;
}

export function Workspace() {
  const auth=useAuth();
  const [logoutError,setLogoutError]=useState('');
  const [menuOpen,setMenuOpen] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const media = window.matchMedia('(max-width:900px)');
    const resized = () => { if (!media.matches) setMenuOpen(false); };
    media.addEventListener('change', resized);
    return () => media.removeEventListener('change', resized);
  }, []);
  useEffect(() => {
    if (!menuOpen || !window.matchMedia('(max-width:900px)').matches) return;
    const previous = document.activeElement;
    const controls = Array.from(sidebarRef.current?.querySelectorAll<HTMLElement>('a,button') ?? []);
    controls[0]?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); setMenuOpen(false); }
      if (event.key !== 'Tab' || !controls.length) return;
      const first = controls[0], last = controls[controls.length-1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown',keydown);
    return () => {
      document.removeEventListener('keydown',keydown);
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, [menuOpen]);
  return <div className="app-shell"><a className="skip-link" href="#main">Skip to content</a>
    {menuOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={()=>setMenuOpen(false)}/>}
    <aside ref={sidebarRef} className={`sidebar ${menuOpen ? 'is-open' : ''}`} aria-label="Main navigation">
      <NavLink to="/" className="brand" onClick={()=>setMenuOpen(false)}><span className="brand-symbol"><span/><span/></span><span>CastraVolt<small>EV INFRASTRUCTURE PLANNING</small></span></NavLink>
      <button className="mobile-close" aria-label="Close navigation" onClick={()=>setMenuOpen(false)}><X size={20}/></button>
      <div className="nav-label">WORKSPACE</div><nav>
        <NavLink to="/" end onClick={()=>setMenuOpen(false)}><FolderOpen size={18}/>Projects<ChevronRight className="active-chevron" size={14}/></NavLink>
        <NavLink to="/estimator" onClick={()=>setMenuOpen(false)}><Compass size={18}/>Site estimator</NavLink>
        <NavLink to="/trends" onClick={()=>setMenuOpen(false)}><BarChart3 size={18}/>EV adoption trends</NavLink>
      </nav>
      <div className="sidebar-bottom"><div className="study-label"><span className="small-dot"/> STUDY AREA</div><p>Kuala Lumpur<br />&amp; Selangor</p><div className="sidebar-rule"/><span className="prototype-label">FYP research prototype <ArrowUpRight size={13}/></span><button className="signout" onClick={()=>{setLogoutError('');void auth.signOut().catch(()=>setLogoutError('Unable to sign out. Please retry.'));}}>Sign out</button>{logoutError&&<p role="alert">{logoutError}</p>}</div>
    </aside>
    <div className="main-shell"><header className="utility-bar"><div className="breadcrumb"><button className="mobile-menu" aria-label="Open navigation" aria-expanded={menuOpen} onClick={()=>setMenuOpen(true)}><Menu size={20}/></button><PanelLeftClose size={17} className="desktop-panel-icon"/><span>Workspace</span><ChevronRight size={13}/><span className="breadcrumb-current">CastraVolt</span></div><div className="utility-right"><span className="prototype-label header-prototype"><Check size={13}/> {auth.user?.name}</span><span className="avatar" aria-label="Your account">{auth.user?.name.slice(0,2).toUpperCase()}</span></div></header>
      <main id="main" className="main-content" tabIndex={-1}><Routes><Route path="/" element={<Projects/>}/><Route path="/estimator" element={<RoadmapPage/>}/><Route path="/trends" element={<RoadmapPage trends/>}/><Route path="*" element={<section className="empty-projects"><h1>Page not found</h1><NavLink to="/" className="button primary">Return to projects <ArrowRight size={16}/></NavLink></section>}/></Routes>
      <footer><span>CastraVolt <span className="footer-divider">/</span> Urban EV infrastructure planning</span><Connection/></footer></main>
    </div>
  </div>;
}

export default function App() {
  return <AuthProvider><Routes>
    <Route path="/login" element={<AuthPage mode="login"/>}/>
    <Route path="/register" element={<AuthPage mode="register"/>}/>
    <Route path="/verify-email" element={<AuthPage mode="verify-email"/>}/>
    <Route path="/resend-verification" element={<AuthPage mode="resend-verification"/>}/>
    <Route path="/forgot-password" element={<AuthPage mode="forgot-password"/>}/>
    <Route path="/reset-password" element={<AuthPage mode="reset-password"/>}/>
    <Route path="/*" element={<RequireAuth><Workspace/></RequireAuth>}/>
  </Routes></AuthProvider>;
}
