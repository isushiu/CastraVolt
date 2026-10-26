import { expect, test, vi, afterEach } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { accountAction, AuthPage, AuthProvider, RequireAuth } from './auth';

afterEach(()=>vi.unstubAllGlobals());
test('registration has labelled fields and password guidance',()=>{
  const html=renderToStaticMarkup(<MemoryRouter><AuthProvider><AuthPage mode="register"/></AuthProvider></MemoryRouter>);
  expect(html).toContain('Full name');expect(html).toContain('Email address');
  expect(html).toContain('minLength="12"');expect(html).not.toContain('localStorage');
});
test('verification requires a real token and explicit action',()=>{
  const html=renderToStaticMarkup(<MemoryRouter initialEntries={['/verify-email']}><AuthProvider><AuthPage mode="verify-email"/></AuthProvider></MemoryRouter>);
  expect(html).toContain('Open the complete link');expect(html).toContain('disabled');
});
test('protected content is not rendered while checking session',()=>{
  const html=renderToStaticMarkup(<MemoryRouter><AuthProvider><RequireAuth><p>Private content</p></RequireAuth></AuthProvider></MemoryRouter>);
  expect(html).toContain('Opening your workspace');expect(html).not.toContain('Private content');
});
test('writes bootstrap CSRF then send a credentialed JSON request',async()=>{
  const fetcher=vi.fn().mockResolvedValueOnce(new Response('{"csrf_token":"test-csrf"}'))
    .mockResolvedValueOnce(new Response('{"message":"ok"}'));
  vi.stubGlobal('fetch',fetcher);
  await accountAction('logout');
  expect(fetcher).toHaveBeenNthCalledWith(2,'/api/v1/auth/logout',expect.objectContaining({
    credentials:'include',method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':'test-csrf'},
  }));
});
