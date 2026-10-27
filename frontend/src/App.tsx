import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, BarChart3, Check, ChevronRight,
  Compass, FolderOpen, Menu, PanelLeftClose, RefreshCw, X } from 'lucide-react';
import { getSystemInfo } from './api/client';
import { AuthPage, AuthProvider, RequireAuth, useAuth } from './auth';
import { ProjectsPage, ProjectWorkspace } from './projects';
import Estimator from './estimator';
const Trends=lazy(()=>import('./Trends'));

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
      <main id="main" className="main-content" tabIndex={-1}><div className="page-content"><Routes><Route path="/" element={<ProjectsPage/>}/><Route path="/projects/:projectId" element={<ProjectWorkspace/>}/><Route path="/estimator" element={<Estimator/>}/><Route path="/trends" element={<Suspense fallback={<p role="status">Loading monthly trends…</p>}><Trends/></Suspense>}/><Route path="*" element={<section className="empty-projects"><h1>Page not found</h1><NavLink to="/" className="button primary">Return to projects <ArrowRight size={16}/></NavLink></section>}/></Routes></div>
      <footer><span>CastraVolt <span className="footer-divider">/</span> Urban EV infrastructure planning</span><Connection/></footer></main>
    </div>
  </div>;
}

export default function App() {
  return <AuthProvider><Routes>
    <Route path="/login" element={<AuthPage mode="login"/>}/>
    <Route path="/register" element={<Navigate to="/login" replace/>}/>
    <Route path="/verify-email" element={<Navigate to="/login" replace/>}/>
    <Route path="/resend-verification" element={<Navigate to="/login" replace/>}/>
    <Route path="/forgot-password" element={<Navigate to="/login" replace/>}/>
    <Route path="/reset-password" element={<Navigate to="/login" replace/>}/>
    <Route path="/*" element={<RequireAuth><Workspace/></RequireAuth>}/>
  </Routes></AuthProvider>;
}
