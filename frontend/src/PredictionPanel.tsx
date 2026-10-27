import { ArrowRight,Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Prediction } from './api/projects';

export default function PredictionPanel({result,ready,busy,error,onPredict,projectId}:{result:Prediction|null;ready:boolean;busy:boolean;error:string;onPredict:()=>void;projectId:string}){
  return <section className="prediction-panel" aria-label="Charging-point estimate"><div className="prediction-heading"><div><span className="eyebrow">PLANNING OUTPUT</span><h2>Charging-point estimate</h2></div><span className="experimental-badge">Experimental</span></div>
    <p className="prediction-warning">The model is verified against its saved test outputs. The current POI counting rules have not yet been verified against its training data, so this result is an experimental estimate.</p>
    {result?<div className="prediction-result" role="status"><div className="prediction-number"><Zap size={26}/><strong>{result.displayed_total}</strong><span>total planned<br/>charging points</span></div><p>Saved to this site’s prediction history.</p><details><summary>Calculation and saved inputs</summary><p>Raw model estimate: {result.raw_estimate.toFixed(4)}. Rounded to the nearest whole number, halves upward, with a minimum of one.</p><p>Model: {result.model_version}</p><p>Estimated {new Date(result.created_at).toLocaleString()}</p><pre>{JSON.stringify(result.input_snapshot,null,2)}</pre></details><Link className="back-link" to={`/projects/${projectId}`}>View site history <ArrowRight size={15}/></Link></div>:<div className="prediction-empty"><Zap size={24}/><p>{ready?'Your saved site context is ready. Generate an experimental estimate when you’re ready.':'Save your site and prepare its context to enable an estimate.'}</p></div>}
    {error&&<p role="alert" className="auth-error">{error}</p>}
    <button className="button primary" disabled={!ready||busy} onClick={onPredict}>{busy?'Generating estimate…':result?'Generate another experimental estimate':'Generate experimental estimate'}<ArrowRight size={16}/></button>
    <p className="prediction-footnote">This estimates total site capacity. Installation design and grid capacity require separate assessment.</p>
  </section>;
}
