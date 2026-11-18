import test from 'node:test';
import assert from 'node:assert/strict';
import { graphIndex, graphScopes, MAX_NODES } from '../src/lib/graph-scope.mjs';
import { readView, writeView, validLayout } from '../src/lib/graph-view.mjs';
import { findPath } from '../src/lib/graph-path.mjs';

const node = (id, type = 'Document') => ({ data: { id: `https://graph-test.invalid/${id}`, concept_id: id, label: id, type } });
const edge = (source, target, predicate = 'references') => ({ data: {
  id: `${source}-${predicate}-${target}`, source: `https://graph-test.invalid/${source}`,
  target: `https://graph-test.invalid/${target}`, predicate, slot: predicate,
} });

test('scopes bound large graphs, paginate direct neighbors, and retain typed relations', () => {
  const nodes = [node('hub'), ...Array.from({ length: 125 }, (_, i) => node(`leaf-${String(i).padStart(3, '0')}`)), node('two-hop')];
  const edges = [
    ...nodes.slice(1, -1).map((item) => edge('hub', item.data.concept_id, 'relatesTo')),
    edge('leaf-000', 'two-hop', 'references'),
    edge('hub', 'hub', 'reflectsOn'),
  ];
  const graph = { nodes, edges };
  const original = JSON.stringify(graph);
  const scopes = graphScopes(graph);
  const hub = scopes.filter((entry) => entry.graph.scope.id === 'hub');
  assert.equal(hub.length, 3);
  assert.deepEqual(hub.map(({ graph: { scope } }) => [scope.start, scope.end]), [[1, 60], [61, 120], [121, 125]]);
  assert.ok(scopes.every(({ graph: view }) => view.nodes.length <= MAX_NODES));
  assert.deepEqual(new Set(hub.flatMap(({ graph: view }) => view.nodes.filter((item) => item.data.concept_id.startsWith('leaf-')).map((item) => item.data.concept_id))).size, 125);
  assert.ok(hub[0].graph.edges.some((item) => item.data.predicate === 'references'));
  assert.ok(hub.every(({ graph: view }) => view.edges.some((item) => item.data.predicate === 'reflectsOn')));
  assert.equal(graphIndex(graph).default_focus, 'hub');
  assert.equal(JSON.stringify(graph), original);
});

test('view links round-trip scope, filters, layout, selection, and unrelated query params', () => {
  const url = new URL('https://graph-test.invalid/graph?campaign=kb');
  writeView(url, { focus: 'glossary/a b', page: 3, layout: 'communities', view: 'list', query: 'solar',
    selected: 'glossary/c', hiddenTypes: ['Dataset', 'Document'], hiddenRelations: ['measures'], labels: true });
  const restored = readView(url.searchParams);
  assert.equal(url.searchParams.get('campaign'), 'kb');
  assert.deepEqual(restored, { focus: 'glossary/a b', page: 3, layout: 'communities', view: 'list', query: 'solar',
    selected: 'glossary/c', hiddenTypes: ['Dataset', 'Document'], hiddenRelations: ['measures'], labels: true });
  assert.equal(validLayout('unexpected'), 'fcose');
  assert.equal(readView(new URLSearchParams('page=-4')).page, 1);
});

test('path finder keeps edge predicate and direction and obeys visible filters', () => {
  const graph = { nodes: [node('a'), node('b', 'Dataset'), node('c')], edges: [edge('a', 'b', 'measures'), edge('c', 'b', 'references')] };
  const path = findPath(graph, 'https://graph-test.invalid/a', 'https://graph-test.invalid/c');
  assert.deepEqual(path.steps.map((step) => [step.edge.data.predicate, step.forward]), [['measures', true], ['references', false]]);
  assert.equal(findPath(graph, 'https://graph-test.invalid/a', 'https://graph-test.invalid/c', { directed: true }), null);
  assert.equal(findPath(graph, 'https://graph-test.invalid/a', 'https://graph-test.invalid/c', { hiddenRelations: ['references'] }), null);
  assert.equal(findPath(graph, 'https://graph-test.invalid/a', 'https://graph-test.invalid/c', { hiddenTypes: ['Dataset'] }), null);
});
