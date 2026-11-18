import test from 'node:test';
import assert from 'node:assert/strict';
import { buildIndex, searchIndex, searchableText, snippetFor, terms } from '../src/lib/search.mjs';

const documents = [
  {
    title: 'Résumé of data systems', type: 'Document', concept_id: 'docs/resume',
    href: '/docs/resume', tags: ['science'], status: 'stable', genre: 'reference',
    description: 'A summary of the platform', text: 'Source material on energy systems', date: '2026-06-01',
    trust_tier: 'verified', stale: false,
  },
  {
    title: 'Energy systems', type: 'GlossaryTerm', concept_id: 'glossary/energy',
    href: '/glossary/energy', tags: ['compute'], status: 'draft', genre: 'explanation',
    description: 'A term about power', text: 'The platform needs energy', date: '2026-07-01',
    trust_tier: 'generated', stale: true,
  },
  {
    title: 'Old platform note', type: 'Document', concept_id: 'docs/old',
    href: '/docs/old', tags: ['science'], status: 'deprecated', genre: 'reference',
    description: 'A note about energy', text: 'Archived platform documentation', date: '2025-01-01',
    trust_tier: 'unverified', stale: false,
  },
];
const index = buildIndex(documents);
const titles = ids => ids.map(id => index.documents[id].title);

test('normalizes accents and matches all words with final-word prefix', () => {
  assert.deepEqual(terms('Résumé A/B'), ['resume', 'a', 'b']);
  assert.deepEqual(titles(searchIndex(index, 'resume plat')), ['Résumé of data systems']);
  assert.deepEqual(titles(searchIndex(index, 'platform energy')),
    ['Old platform note', 'Energy systems', 'Résumé of data systems']);
  assert.deepEqual(searchIndex(index, 'platform absent'), []);
});

test('ranks title before body and applies portable facets', () => {
  assert.equal(titles(searchIndex(index, 'energy'))[0], 'Energy systems');
  assert.deepEqual(titles(searchIndex(index, 'energy', {type:'Document',tag:'science',status:'stable',genre:'reference',trust:'verified',freshness:'current',from:'2026-01-01'})),
    ['Résumé of data systems']);
  assert.deepEqual(titles(searchIndex(index, 'energy', {freshness:'stale'})), ['Energy systems']);
  assert.deepEqual(titles(searchIndex(index, '', {sort:'newest'})),
    ['Energy systems', 'Résumé of data systems', 'Old platform note']);
});

test('keeps body words searchable while presenting readable snippets', () => {
  const body = searchableText('# Heading\nA [linked phrase](https://example.invalid) about **solar** energy.');
  assert.match(body, /linked phrase about solar energy/);
  assert.deepEqual(terms(body).slice(-2), ['solar', 'energy']);
  assert.match(snippetFor({description:'',text:body}, 'solar'), /solar energy/);
});
