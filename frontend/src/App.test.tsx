import { expect, test } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

test('foundation never pretends to have private projects, accounts or working predictions', () => {
  const html = renderToStaticMarkup(<MemoryRouter><App/></MemoryRouter>);
  expect(html).toContain('Workspace preview');
  expect(html).toContain('Project creation coming soon');
  expect(html).toContain('3 km');
  expect(html).toContain('Illustration · not a geographic map');
  expect(html).not.toContain('Sign out');
});

test('unknown routes provide an accessible return path', () => {
  const html = renderToStaticMarkup(<MemoryRouter initialEntries={['/missing']}><App/></MemoryRouter>);
  expect(html).toContain('Page not found');
  expect(html).toContain('Return to projects');
});
