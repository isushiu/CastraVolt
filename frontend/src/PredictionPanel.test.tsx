import { expect,test } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import PredictionPanel from './PredictionPanel';
import type { Prediction } from './api/projects';

test('estimate is labelled experimental and total rather than additional capacity',()=>{
  const result:Prediction={id:'p1',site_id:'s1',input_snapshot:{validation:{poi_parity_verified:false}},raw_estimate:3.5,displayed_total:4,model_version:'verified-fixture',extraction_rule_version:'provisional',poi_timestamp:'2026-10-25T00:00:00Z',adoption_reference_year:2025,adoption_value:560,rounding_policy:'nearest_half_up_minimum_1',created_at:'2026-10-27T00:00:00Z',experimental:true};
  const html=renderToStaticMarkup(<MemoryRouter><PredictionPanel result={result} ready busy={false} error="" onPredict={()=>{}} projectId="project-1"/></MemoryRouter>);
  expect(html).toContain('Experimental');expect(html).toContain('>4</strong>');expect(html).toContain('total planned');
  expect(html).toContain('3.5000');expect(html).toContain('prediction history');
});
test('no invented output before saved context is ready',()=>{
  const html=renderToStaticMarkup(<MemoryRouter><PredictionPanel result={null} ready={false} busy={false} error="" onPredict={()=>{}} projectId="p1"/></MemoryRouter>);
  expect(html).toContain('disabled');expect(html).not.toContain('prediction-number');expect(html).toContain('prepare its context');
});
