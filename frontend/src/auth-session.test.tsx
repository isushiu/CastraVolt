// @vitest-environment jsdom
import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider, RequireAuth } from './auth';

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
