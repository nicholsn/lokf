import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import rewriteLinks from '../remark-lokf-links.mjs';

const file = { path: path.join(process.cwd(), 'knowledge', 'index.md') };

test('rewrites concept links with fragments under a project subpath', () => {
  const link = { type: 'link', url: 'glossary/active-user.md#definition', children: [{ type: 'text', value: 'Active User' }] };
  rewriteLinks({ base: '/my-kb' })({ children: [link] }, file);
  assert.equal(link.url, '/my-kb/glossary/active-user#definition');
});

test('turns active Markdown link and image schemes into plain text', () => {
  const link = { type: 'link', url: '  javascript:alert(1)', children: [{ type: 'text', value: 'Click me' }] };
  const obfuscated = { type: 'link', url: 'java\nscript:alert(1)', children: [{ type: 'text', value: 'Unsafe' }] };
  const image = { type: 'image', url: 'data:text/html,<script>alert(1)</script>', alt: 'Preview' };
  rewriteLinks()({ children: [link, obfuscated, image] }, file);
  assert.equal(link.type, 'text');
  assert.equal(link.value, 'Click me');
  assert.equal(link.url, undefined);
  assert.equal(obfuscated.type, 'text');
  assert.equal(obfuscated.value, 'Unsafe');
  assert.equal(image.type, 'text');
  assert.equal(image.value, 'Preview');
  assert.equal(image.url, undefined);
});

test('turns raw HTML into a text node for escaped rendering', () => {
  const html = { type: 'html', value: '<script>alert(1)</script>' };
  rewriteLinks()({ children: [html] }, file);
  assert.equal(html.type, 'text');
  assert.equal(html.value, '<script>alert(1)</script>');
});
