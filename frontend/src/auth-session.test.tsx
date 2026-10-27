// @vitest-environment jsdom
import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { AuthPage, AuthProvider, RequireAuth } from './auth';

afterEach(()=>{cleanup();vi.unstubAllGlobals();});
function Protected() {
  return <MemoryRouter><AuthProvider><Routes><Route path="/" element={<RequireAuth><p>Private workspace</p></RequireAuth>}/><Route path="/login" element={<p>Sign in required</p>}/></Routes></AuthProvider></MemoryRouter>;
}
const planner={id:'planner-1',name:'Afina',email:'planner@example.com'};

test('session revoked in another tab is cleared on focus',async()=>{
  const fetcher=vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(planner)))
    .mockResolvedValue(new Response('{"error":{"message":"Sign in"}}',{status:401}));
  vi.stubGlobal('fetch',fetcher);
  render(<Protected/>);
  await screen.findByText('Private workspace');
  fireEvent(window,new Event('focus'));
  await screen.findByText('Sign in required');
  expect(screen.queryByText('Private workspace')).toBeNull();
});

test('an API expiry event immediately removes private content',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify(planner))));
  render(<Protected/>);
  await screen.findByText('Private workspace');
  fireEvent(window,new Event('castravolt:unauthenticated'));
  await waitFor(()=>expect(screen.queryByText('Private workspace')).toBeNull());
});

test.each([
  ['/estimator?project=p1&site=s1','Opened /estimator?project=p1&site=s1'],
  ['https://other.example/estimator?project=p1','Opened /'],
])('login resumes only a trusted internal map destination: %s',async(from,expected)=>{
  let signedIn=false;
  vi.stubGlobal('fetch',vi.fn(async(url:string)=>{
    if(String(url).endsWith('/csrf'))return new Response('{"csrf_token":"csrf"}');
    if(String(url).endsWith('/login')){signedIn=true;return new Response(JSON.stringify({user:planner}));}
    return signedIn?new Response(JSON.stringify(planner)):new Response('{"error":{"message":"Sign in"}}',{status:401});
  }));
  function Destination(){const location=useLocation();return <p>Opened {location.pathname+location.search}</p>;}
  render(<MemoryRouter initialEntries={[{pathname:'/login',state:{from}}]}><AuthProvider><Routes>
    <Route path="/login" element={<AuthPage mode="login"/>}/><Route path="*" element={<Destination/>}/>
  </Routes></AuthProvider></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('User ID'),{target:{value:'admin'}});
  fireEvent.change(screen.getByLabelText('Password'),{target:{value:'123'}});
  fireEvent.click(screen.getByRole('button',{name:'Sign in'}));
  await screen.findByText(expected);
});
