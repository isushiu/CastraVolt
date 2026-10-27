// @vitest-environment jsdom
import {afterEach,expect,test,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import Trends from './Trends';
import fixture from './trends.fixture.json';
vi.mock('./TrendChart',()=>({default:()=> <div>Chart.js monthly chart</div>}));
afterEach(()=>{cleanup();vi.unstubAllGlobals();});

function mockApi(enabled=true){
 const calls:string[]=[];
 vi.stubGlobal('fetch',vi.fn((url:string)=>{
  calls.push(url);
  if(url.endsWith('/auth/csrf'))return Promise.resolve(new Response(JSON.stringify({csrf_token:'test'})));
  if(url.endsWith('/trends/summary'))return Promise.resolve(new Response(JSON.stringify({text:'Only verified monthly figures are described.',model:'fixture',cache_hit:false,generated_at:'2026-10-27T00:00:00Z'})));
  return Promise.resolve(new Response(JSON.stringify({...fixture,summary_enabled:enabled})));
 }));return calls;
}

test('shows calculated totals, explicit coverage and accessible monthly data without automatic AI calls',async()=>{
 const calls=mockApi();render(<Trends/>);
 expect(await screen.findByText('6,401')).toBeTruthy();
 expect(screen.getByText(/2026: January–September/)).toBeTruthy();
 expect(screen.getByRole('button',{name:'Generate summary'})).toBeTruthy();
 expect(calls.some(x=>x.endsWith('/summary'))).toBe(false);
 fireEvent.click(screen.getByText('View monthly data'));
 expect(screen.getByRole('table',{name:'Monthly new registrations'})).toBeTruthy();
});

test('filters submit together and explanation runs only after a click',async()=>{
 const calls=mockApi();render(<Trends/>);await screen.findByText('6,401');
 fireEvent.change(screen.getByLabelText('Chart view'),{target:{value:'year_over_year'}});
 fireEvent.click(screen.getByRole('button',{name:'Apply filters'}));
 await waitFor(()=>expect(calls.some(x=>x.includes('comparison_mode=year_over_year'))).toBe(true));
 await screen.findByRole('button',{name:'Generate summary'});
 fireEvent.click(screen.getByRole('button',{name:'Generate summary'}));
 expect(await screen.findByText('Only verified monthly figures are described.')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Reset filters'}));
 await waitFor(()=>expect(screen.queryByText('Only verified monthly figures are described.')).toBeNull());
});

test('charts remain available when Groq is not configured',async()=>{
 mockApi(false);render(<Trends/>);await screen.findByText('6,401');
 expect((screen.getByRole('button',{name:'Generate summary'}) as HTMLButtonElement).disabled).toBe(true);
 expect(screen.getByText(/AI explanations are not configured/)).toBeTruthy();
 expect(screen.getByText('Chart.js monthly chart')).toBeTruthy();
});


test('yearly changes start with available year pairs rather than an unavailable 2024 comparison',async()=>{
 mockApi();render(<Trends/>);await screen.findByText('6,401');
 expect(screen.getByText('Selangor · 2024 → 2025')).toBeTruthy();
 expect(screen.getByText('Selangor · 2025 → 2026')).toBeTruthy();
 expect(screen.getByText('Kuala Lumpur · 2024 → 2025')).toBeTruthy();
 expect(screen.queryByText('Selangor · 2024',{exact:true})).toBeNull();
 expect(screen.queryByText('Previous-year coverage is unavailable or incomplete.')).toBeNull();
});
