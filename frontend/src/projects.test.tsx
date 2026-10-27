// @vitest-environment jsdom
import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProjectsPage, ProjectWorkspace } from './projects';

afterEach(()=>{cleanup();vi.unstubAllGlobals();});
const project={id:'project-1',name:'KL pilot',description:'Planning',created_at:'2026-10-27T00:00:00Z',updated_at:'2026-10-27T00:00:00Z'};
function mockApi(initialProjects: unknown[] = []) {
  vi.stubGlobal('fetch',vi.fn(async (url: string,options?: RequestInit)=>{
    const path=String(url);
    if(path.endsWith('/auth/csrf')) return new Response('{"csrf_token":"csrf"}');
    if(path.endsWith('/reference/site-categories')) return new Response('["Office","Unknown"]');
    if(path.endsWith('/projects')&&options?.method==='POST') return new Response(JSON.stringify(project),{status:201});
    if(path.endsWith('/projects')) return new Response(JSON.stringify(initialProjects));
    if(path.endsWith('/sites')) return new Response('[]');
    return new Response(JSON.stringify(project));
  }));
}
test('create a project from empty state and open its workspace',async()=>{
  mockApi();
  render(<MemoryRouter><Routes><Route path="/" element={<ProjectsPage/>}/><Route path="/projects/:projectId" element={<p>Project opened</p>}/></Routes></MemoryRouter>);
  await screen.findByText('No projects yet');
  fireEvent.click(screen.getByRole('button',{name:'New project'}));
  fireEvent.change(screen.getByLabelText('Project name'),{target:{value:'KL pilot'}});
  fireEvent.click(screen.getByRole('button',{name:'Create project'}));
  await screen.findByText('Project opened');
});
test('existing project opens and history has no invented results',async()=>{
  mockApi([project]);
  render(<MemoryRouter initialEntries={['/projects/project-1']}><Routes><Route path="/projects/:projectId" element={<ProjectWorkspace/>}/></Routes></MemoryRouter>);
  await screen.findByRole('heading',{name:'KL pilot'});
  expect(screen.getByText('No saved sites yet')).toBeTruthy();
  expect(screen.queryByText('Estimated charging points')).toBeNull();
});

test('site creation and editing both use the map without a manual add form',async()=>{
  const site={id:'site-1',project_id:project.id,name:'Office entrance',latitude:3.14,longitude:101.69,category:'Office',address:'',state:null,created_at:project.created_at,updated_at:project.updated_at};
  vi.stubGlobal('fetch',vi.fn(async(url:string)=>{
    if(String(url).endsWith('/auth/csrf'))return new Response('{"csrf_token":"csrf"}');
    if(String(url).endsWith('/reference/site-categories'))return new Response('["Office","Unknown"]');
    if(String(url).endsWith('/sites'))return new Response(JSON.stringify([site,{...site,id:'site-2',name:'Other site'}]));
    return new Response(JSON.stringify(project));
  }));
  render(<MemoryRouter initialEntries={['/projects/project-1']}><Routes><Route path="/projects/:projectId" element={<ProjectWorkspace/>}/></Routes></MemoryRouter>);
  await screen.findByText('Office entrance');
  expect(screen.queryByRole('button',{name:'Add site'})).toBeNull();
  expect(screen.getByRole('link',{name:'Add site on map'}).getAttribute('href')).toBe('/estimator?project=project-1');
  expect(screen.getAllByRole('link',{name:'Open on map'})[0].getAttribute('href')).toContain('site=site-1');
  expect(screen.queryByLabelText('Latitude')).toBeNull();
});
