// @vitest-environment jsdom
import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Estimator from './estimator';

vi.mock('./SiteMap',()=>({default:({onSelect}:{onSelect:(point:{latitude:number;longitude:number})=>void})=><div><button onClick={()=>onSelect({latitude:3.1579,longitude:101.7116})}>Choose KL pin</button><button onClick={()=>onSelect({latitude:3.0738,longitude:101.5183})}>Choose Selangor pin</button></div>}));
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
const project={id:'p1',name:'KL pilot',description:'',created_at:'2026-10-27',updated_at:'2026-10-27'};
const site={id:'s1',project_id:'p1',name:'New site',category:'Office',latitude:3.1579,longitude:101.7116,state:'W.P. KUALA LUMPUR',address:'',created_at:'2026-10-27',updated_at:'2026-10-27'};
function setup(extra?:(path:string,options?:RequestInit)=>Promise<Response>|undefined){
  const fetcher=vi.fn(async(url:string,options?:RequestInit)=>{
    const path=String(url),override=extra?.(path,options);if(override)return override;
    if(path.endsWith('/auth/csrf'))return new Response('{"csrf_token":"csrf"}');
    if(path.endsWith('/reference/site-categories'))return new Response('["Office","Unknown"]');
    if(path.endsWith('/projects/p1/sites')||path.endsWith('/sites/s1'))return new Response(JSON.stringify(site));
    if(path.includes('/locations/address'))return new Response(JSON.stringify({latitude:3.1579,longitude:101.7116,state:'W.P. KUALA LUMPUR',name:'KLCC',address:'KLCC, Malaysia'}));
    if(path.includes('/locations/validate'))return new Response(JSON.stringify({latitude:3.1579,longitude:101.7116,state:path.includes('3.0738')?'SELANGOR':'W.P. KUALA LUMPUR',boundary_version:'fixture',urban_coverage:'provisional'}));
    if(path.endsWith('/projects'))return new Response(JSON.stringify([project]));
    return new Response(JSON.stringify(project));
  });vi.stubGlobal('fetch',fetcher);
  render(<MemoryRouter initialEntries={['/estimator?project=p1']}><Estimator/></MemoryRouter>);return fetcher;
}
async function chooseAndComplete(){
  await screen.findByRole('heading',{name:'Site estimator'});
  fireEvent.click(screen.getByRole('button',{name:'Choose KL pin'}));
  await screen.findByText('W.P. KUALA LUMPUR');
  fireEvent.change(screen.getByLabelText('Site name'),{target:{value:'New site'}});
  fireEvent.change(screen.getByLabelText('Host-site category'),{target:{value:'Office'}});
  fireEvent.click(screen.getByLabelText('I confirm the host-site category.'));
}
test('save validated pin into selected project, then update the same site',async()=>{
  const fetcher=setup();await chooseAndComplete();
  expect(screen.queryByLabelText('Latitude')).toBeNull();
  expect(screen.queryByRole('button',{name:'Use coordinates'})).toBeNull();
  await waitFor(()=>expect((screen.getByRole('button',{name:'Save proposed site'}) as HTMLButtonElement).disabled).toBe(false),{timeout:3000});
  fireEvent.click(screen.getByRole('button',{name:'Save proposed site'}));
  await screen.findByText('Site saved to KL pilot.');
  const create=fetcher.mock.calls.find(([path,options])=>String(path).endsWith('/projects/p1/sites')&&options?.method==='POST');
  expect(JSON.parse(create![1]!.body as string)).toEqual({name:'New site',address:'KLCC, Malaysia',category:'Office',latitude:3.1579,longitude:101.7116});
  fireEvent.change(screen.getByLabelText('Site name'),{target:{value:'Renamed'}});
  await waitFor(()=>expect((screen.getByRole('button',{name:'Save proposed site'}) as HTMLButtonElement).disabled).toBe(false),{timeout:3000});
  fireEvent.click(screen.getByRole('button',{name:'Save proposed site'}));
  await screen.findByText('Site saved to KL pilot.');
  expect(fetcher.mock.calls.some(([path,options])=>String(path).endsWith('/sites/s1')&&options?.method==='PATCH')).toBe(true);
  expect(fetcher.mock.calls.some(([path])=>String(path).includes('/predictions')||String(path).includes('overpass'))).toBe(false);
});
test('unsupported location cannot be saved',async()=>{
  setup(path=>path.includes('/locations/validate')?Promise.resolve(new Response('{"error":{"message":"Unsupported location"}}',{status:422})):undefined);
  await screen.findByRole('heading',{name:'Site estimator'});fireEvent.click(screen.getByText('Choose KL pin'));
  await screen.findByText('Unsupported location');
  expect((screen.getByRole('button',{name:'Save proposed site'}) as HTMLButtonElement).disabled).toBe(true);
});
test('late state validation cannot overwrite a newer pin',async()=>{
  let finish:((value:Response)=>void)|undefined;
  setup(path=>path.includes('/locations/validate')&&path.includes('3.1579')?new Promise(resolve=>{finish=resolve;}):undefined);
  await screen.findByRole('heading',{name:'Site estimator'});fireEvent.click(screen.getByText('Choose KL pin'));
  await waitFor(()=>expect(finish).toBeDefined());fireEvent.click(screen.getByText('Choose Selangor pin'));
  await screen.findByText('SELANGOR');finish!(new Response('{"state":"W.P. KUALA LUMPUR"}'));
  await waitFor(()=>expect(screen.queryByText('W.P. KUALA LUMPUR')).toBeNull());
});
test('late address search cannot overwrite the map selection',async()=>{
  let finish:((value:Response)=>void)|undefined;
  setup(path=>path.includes('/locations/search')?new Promise(resolve=>{finish=resolve;}):undefined);
  await screen.findByRole('heading',{name:'Site estimator'});
  fireEvent.change(screen.getByLabelText('Find an address or place'),{target:{value:'KLCC'}});
  fireEvent.click(screen.getByRole('button',{name:'Search'}));await waitFor(()=>expect(finish).toBeDefined());
  fireEvent.click(screen.getByText('Choose Selangor pin'));await screen.findByText('SELANGOR');
  finish!(new Response('[{"name":"Stale result","latitude":3.1,"longitude":101.7,"state":"W.P. KUALA LUMPUR"}]'));
  await waitFor(()=>expect(screen.queryByText('Stale result')).toBeNull());
});

test('moving the pin clears the old name and fills the new place name',async()=>{
  setup(path=>path.includes('/locations/address')&&path.includes('3.0738')?Promise.resolve(new Response(JSON.stringify({name:'Shah Alam Library',address:'Shah Alam, Selangor'}))):undefined);
  await screen.findByRole('heading',{name:'Site estimator'});
  fireEvent.click(screen.getByText('Choose KL pin'));
  await screen.findByDisplayValue('KLCC',{}, {timeout:3000});
  fireEvent.click(screen.getByText('Choose Selangor pin'));
  expect((screen.getByLabelText('Site name') as HTMLInputElement).value).toBe('');
  await screen.findByDisplayValue('Shah Alam Library',{}, {timeout:3000});
});

test('an unnamed new pin clears the previous name and asks for a manual name',async()=>{
  setup(path=>path.includes('/locations/address')&&path.includes('3.0738')?Promise.resolve(new Response(JSON.stringify({name:'',address:'Unnamed road, Selangor'}))):undefined);
  await screen.findByRole('heading',{name:'Site estimator'});
  fireEvent.click(screen.getByText('Choose KL pin'));
  await screen.findByDisplayValue('KLCC',{}, {timeout:3000});
  fireEvent.click(screen.getByText('Choose Selangor pin'));
  await screen.findByText('No place name found for this spot. Please enter a site name.',{}, {timeout:3000});
  expect((screen.getByLabelText('Site name') as HTMLInputElement).value).toBe('');
  expect((screen.getByRole('button',{name:'Save proposed site'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText('Site name'),{target:{value:'My planned site'}});
  expect(screen.queryByText('No place name found for this spot. Please enter a site name.')).toBeNull();
});

test('site context is prepared only on request and is cleared when the pin moves',async()=>{
  const fetcher=setup(path=>path.endsWith('/features')?Promise.resolve(new Response(JSON.stringify({features:{nearby_mall_count:2,nearby_petrol_count:1,nearby_hotel_count:3,nearby_office_count:4,nearby_transit_count:5,nearby_university_count:0,nearby_hospital_count:1,nearby_parking_count:8,state_ev_registrations:1237,state:'W.P. KUALA LUMPUR',category:'Office'},adoption:{reference_year:2025},provenance:{osm_base_timestamp:'2026-10-27'},extracted_at:'2026-10-27T00:00:00Z',extraction_rule_version:'provisional',cache_hit:false}))):undefined);
  await chooseAndComplete();
  await waitFor(()=>expect((screen.getByRole('button',{name:'Save proposed site'}) as HTMLButtonElement).disabled).toBe(false),{timeout:3000});
  fireEvent.click(screen.getByRole('button',{name:'Save proposed site'}));await screen.findByText('Site saved to KL pilot.');
  expect(fetcher.mock.calls.some(([path])=>String(path).endsWith('/features'))).toBe(false);
  fireEvent.click(screen.getByRole('button',{name:'Prepare site context'}));
  await screen.findByText('1,237 new EV car registrations');
  fireEvent.click(screen.getByRole('button',{name:'Choose Selangor pin'}));
  expect(screen.queryByText('1,237 new EV car registrations')).toBeNull();
  expect((screen.getByRole('button',{name:'Prepare site context'}) as HTMLButtonElement).disabled).toBe(true);
});
