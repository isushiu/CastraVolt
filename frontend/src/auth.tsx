import { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, ArrowLeft, Mail, ShieldCheck, Zap } from 'lucide-react';
import { ApiError } from './api/client';
import type { components } from './api/schema';

export type Planner = components['schemas']['Planner'];
type Context = { user: Planner | null; loading: boolean; unavailable: boolean; refresh: () => Promise<void>;
  signIn: (email: string,password: string) => Promise<void>; signOut: () => Promise<void> };
const AuthContext = createContext<Context | null>(null);

async function read<T>(response: Response): Promise<T> {
  const body = await response.json().catch(()=>null);
  if (!response.ok) throw new ApiError(body?.error?.message ?? 'Unable to complete this request. Please try again.',response.status);
  return body as T;
}

export async function accountAction(path: string,data: Record<string,string> = {}) {
  const csrf = await fetch('/api/v1/auth/csrf',{credentials:'include',cache:'no-store'}).then(read<{csrf_token:string}>);
  return fetch(`/api/v1/auth/${path}`,{method:'POST',credentials:'include',
    headers:{'Content-Type':'application/json','X-CSRF-Token':csrf.csrf_token},body:JSON.stringify(data)}).then(read<{message?: string; user?: Planner}>);
}

export function AuthProvider({children}: {children:ReactNode}) {
  const [user,setUser] = useState<Planner|null>(null);
  const [loading,setLoading] = useState(true);
  const [unavailable,setUnavailable] = useState(false);
  const generation=useRef(0);
  const location=useLocation();
  async function refresh(silent=false) {
    const requestId=++generation.current;
    if(!silent) setLoading(true); setUnavailable(false);
    try { const planner=await fetch('/api/v1/auth/me',{credentials:'include',cache:'no-store'}).then(read<Planner>); if(requestId===generation.current) setUser(planner); }
    catch (error) { if(requestId===generation.current){setUser(null);setUnavailable(!(error instanceof ApiError && error.status===401));} }
    finally { if(requestId===generation.current) setLoading(false); }
  }
  useEffect(()=>{ void refresh(); },[]);
  useEffect(()=>{ if(user) void refresh(true); },[location.pathname]);
  useEffect(()=>{
    const check=()=>{if(document.visibilityState!=='hidden') void refresh(true);};
    const expired=()=>{generation.current++;setUser(null);setLoading(false);};
    window.addEventListener('focus',check);
    window.addEventListener('castravolt:unauthenticated',expired);
    const timer=window.setInterval(check,60000);
    return()=>{window.removeEventListener('focus',check);window.removeEventListener('castravolt:unauthenticated',expired);window.clearInterval(timer);};
  },[]);
  async function signIn(email:string,password:string) {
    generation.current++;
    const result=await accountAction('login',{id:email,password});
    if (!result.user) throw new Error('Unable to start your session.');
    setUnavailable(false); setLoading(false); setUser(result.user);
  }
  async function signOut() { await accountAction('logout'); generation.current++; setLoading(false);setUser(null); }
  return <AuthContext.Provider value={{user,loading,unavailable,refresh,signIn,signOut}}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context=useContext(AuthContext);
  if (!context) throw new Error('Account context is required');
  return context;
}

export function RequireAuth({children}: {children:ReactNode}) {
  const auth=useAuth(); const location=useLocation();
  if (auth.loading) return <main className="session-state" role="status">Opening your workspace…</main>;
  if (auth.unavailable) return <main className="session-state"><h1>Unable to connect</h1><p>Your account service is temporarily unavailable.</p><button className="button primary" onClick={()=>void auth.refresh()}>Try again</button></main>;
  if (!auth.user) return <Navigate to="/login" replace state={{from:location.pathname+location.search}}/>;
  return children;
}

type Mode = 'login'|'register'|'verify-email'|'forgot-password'|'reset-password'|'resend-verification';

function returnPath(from:unknown){
  if(typeof from!=='string')return '/';
  try{
    const origin=typeof window==='undefined'?'http://localhost':window.location.origin;
    const destination=new URL(from,origin);
    const safe=destination.origin===origin&&(/^\/projects\/[a-f0-9-]+$/.test(destination.pathname)||['/','/estimator','/trends'].includes(destination.pathname));
    return safe?destination.pathname+destination.search:'/';
  }catch{return '/';}
}

const copy: Record<Mode,{title:string; description:string; action:string}> = {
  login:{title:'Welcome back.',description:'Sign in to the internal CastraVolt workspace.',action:'Sign in'},
  register:{title:'Make room for better planning.',description:'Create your individual CastraVolt account.',action:'Create account'},
  'verify-email':{title:'One last step.',description:'Confirm your email address to access your workspace.',action:'Verify email'},
  'forgot-password':{title:'Let’s get you back in.',description:'Request a link to reset your password.',action:'Send reset link'},
  'reset-password':{title:'A fresh start.',description:'Choose a new password for your account.',action:'Update password'},
  'resend-verification':{title:'Need another link?',description:'Request a new email verification link.',action:'Send verification link'},
};

export function AuthPage({mode}: {mode:Mode}) {
  const auth=useAuth(); const navigate=useNavigate(); const location=useLocation(); const [params]=useSearchParams();
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[success,setSuccess]=useState('');
  const [email,setEmail]=useState(''),[name,setName]=useState(''),[password,setPassword]=useState('');
  useEffect(()=>{setError('');setSuccess('');setPassword('');setBusy(false);},[mode]);
  const token=params.get('token') ?? '';
  const tokenMode=mode==='verify-email'||mode==='reset-password';
  const needsEmail=['login','register','forgot-password','resend-verification'].includes(mode);
  const needsPassword=['login','register','reset-password'].includes(mode);
  const text=copy[mode];
  const destination=returnPath(location.state?.from);
  if (auth.user && (mode==='login'||mode==='register')) return <Navigate to={destination} replace/>;
  async function submit(event:FormEvent) {
    event.preventDefault();setBusy(true);setError('');
    try {
      if (mode==='login') {
        await auth.signIn(email.trim(),password);
        // Only allow the known internal workspace destinations after authentication.
        navigate(destination, {replace:true});
      } else {
        const data: Record<string,string>={};
        if(needsEmail) data.email=email.trim();
        if(needsPassword) data.password=password;
        if(mode==='register') data.name=name.trim();
        if(tokenMode) data.token=token;
        const result=await accountAction(mode,data);
        if(mode==='reset-password') await auth.refresh();
        setSuccess(result.message ?? 'Request completed.');setPassword('');
        if (tokenMode) navigate(`/${mode}`,{replace:true}); // remove used token from the current URL
      }
    } catch(err) {setError(err instanceof Error ? err.message : 'Please try again.');}
    finally {setBusy(false);}
  }
  return <main className="auth-layout">
    <section className="auth-brand-panel"><Link className="brand" to="/"><span className="brand-symbol"><span/><span/></span><span>CastraVolt<small>EV INFRASTRUCTURE PLANNING</small></span></Link>
      <div className="auth-brand-copy"><span className="section-kicker">BETTER PLACES TO CHARGE</span><h1>Thoughtful planning.<br/>A clearer way forward.</h1><p>A private space to explore locations, understand their surroundings and plan urban EV infrastructure.</p><div className="auth-feature"><ShieldCheck size={18}/> Your account. Your workspace.</div></div>
      <span className="auth-study"><Zap size={15}/> Kuala Lumpur &amp; Selangor</span>
    </section>
    <section className="auth-form-panel"><div className="auth-form-inner"><div className="eyebrow">EV INFRASTRUCTURE PLANNING</div><h2>{text.title}</h2><p className="auth-description">{text.description}</p>
      {success ? <div className="auth-success" role="status"><Mail size={25}/><p>{success}</p><Link className="button primary" to="/login">Back to sign in <ArrowRight size={16}/></Link></div> : <form onSubmit={submit}>
        {mode==='register' && <label>Full name<input name="name" autoComplete="name" value={name} onChange={e=>setName(e.target.value)} required maxLength={100}/></label>}
        {needsEmail && <label>{mode==='login'?'User ID':'Email address'}<input name={mode==='login'?'username':'email'} type={mode==='login'?'text':'email'} autoComplete={mode==='login'?'username':'email'} value={email} onChange={e=>setEmail(e.target.value)} required maxLength={254}/></label>}
        {needsPassword && <label>Password<input name="password" type="password" autoComplete={mode==='login'?'current-password':'new-password'} value={password} onChange={e=>setPassword(e.target.value)} required minLength={mode==='login'?1:12} maxLength={128}/>{mode!=='login'&&<small>Use at least 12 characters.</small>}</label>}
        {tokenMode&&!token&&<p className="auth-error" role="alert">Open the complete link from your email to continue.</p>}
        {error&&<p className="auth-error" role="alert">{error}</p>}
        <button className="button primary auth-submit" disabled={busy||(tokenMode&&!token)}>{busy?'Please wait…':text.action}<ArrowRight size={16}/></button>
      </form>}
      <div className="auth-links">{mode==='login'?<p>Demo access: <strong>admin</strong> / <strong>123</strong></p>:<Link to="/login"><ArrowLeft size={14}/> Back to sign in</Link>}</div>
      <p className="auth-footnote">Planning with context. Built for Kuala Lumpur and Selangor.</p>
    </div></section>
  </main>;
}
