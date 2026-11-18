import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTemporalEvidence, calendarDate } from '../src/lib/temporal.mjs';
import { temporalConfig } from '../src/temporal.config.mjs';

const doc = (id, type, data = {}) => ({ id, title: id, type, href: `/${id}`, data });
const graph = (documents, links) => ({
  nodes: documents.map(d => ({ data: { id: `urn:test:${d.id}`, concept_id: d.id } })),
  edges: links.map(([source, slot, target]) => ({
    data: { source: `urn:test:${source}`, target: `urn:test:${target}`, slot, predicate: `ex:${slot}` },
  })),
});

test('builds a domain-neutral timeline from configured dates and outgoing grouping links', () => {
  const documents = [
    doc('observations/a', 'Observation', { event: { on: '2026-03-04' } }),
    doc('observations/b', 'Observation', { event: { on: '2026-02-11' } }),
    doc('topics/one', 'Topic'), doc('topics/two', 'Topic'),
  ];
  const links = [
    ['observations/a', 'supports', 'topics/one'],
    ['observations/a', 'supports', 'topics/two'],
    ['observations/a', 'supports', 'topics/one'],
    ['observations/b', 'supports', 'topics/one'],
  ];
  const view = buildTemporalEvidence(documents, graph(documents, links), {
    dateFields: [{ path: 'event.on', label: 'Observation date' }],
    groupRelations: [{ relation: 'supports', recordRole: 'source', label: 'Supports' }],
    recordTypes: ['Observation'], groupTypes: ['Topic'], minimumRecords: 2,
  });
  assert.ok(view);
  assert.equal(view.dateField.label, 'Observation date');
  assert.deepEqual(view.periods.map(p => [p.key, p.records.length]), [['2026-03', 1], ['2026-02', 1]]);
  assert.deepEqual(view.groups.map(g => [g.id, g.records.length]), [['topics/one', 2], ['topics/two', 1]]);
  assert.deepEqual(view.records[0].groups.map(g => g.href), ['/topics/one', '/topics/two']);
  assert.equal(view.records[0].href, '/observations/a');
});

test('supports incoming grouping links and picks one date meaning by coverage', () => {
  const documents = [
    doc('entries/a', 'Entry', { created: '2026-01-01', generated: { at: '2026-03-01T12:00:00Z' } }),
    doc('entries/b', 'Entry', { created: '2026-01-02', generated: { at: '2026-03-02T12:00:00Z' } }),
    doc('entries/c', 'Entry', { generated: { at: '2026-03-03T12:00:00Z' } }),
    doc('collections/main', 'Collection'),
  ];
  const links = ['entries/a', 'entries/b', 'entries/c'].map(id => ['collections/main', 'hasPart', id]);
  const view = buildTemporalEvidence(documents, graph(documents, links), {
    dateFields: [
      { path: 'created', label: 'Created' },
      { path: 'generated.at', label: 'Generated' },
    ],
    groupRelations: [{ relation: 'hasPart', recordRole: 'target', label: 'Has part' }],
    minimumRecords: 2,
  });
  assert.equal(view.dateField.path, 'generated.at');
  assert.equal(view.records.length, 3);
  assert.equal(view.groups[0].records.length, 3);
});

test('ignores missing and invalid dates, and hides a view without enough linked records', () => {
  assert.equal(calendarDate('2026-02-30'), '');
  assert.equal(calendarDate(new Date('invalid')), '');
  assert.equal(calendarDate('2026-02-28T12:30:00Z'), '2026-02-28');
  const documents = [
    doc('records/valid', 'Record', { created: '2026-04-01' }),
    doc('records/missing', 'Record'),
    doc('records/invalid', 'Record', { created: '2026-02-30' }),
    doc('groups/one', 'Group'),
  ];
  const withLink = graph(documents, [
    ['records/valid', 'about', 'groups/one'],
    ['records/missing', 'about', 'groups/one'],
    ['records/invalid', 'about', 'groups/one'],
  ]);
  assert.equal(buildTemporalEvidence(documents, withLink, temporalConfig), null);
  assert.equal(buildTemporalEvidence(documents, graph(documents, []), { ...temporalConfig, minimumRecords: 1 }), null);
  const partial = buildTemporalEvidence(documents, withLink, { ...temporalConfig, minimumRecords: 1 });
  assert.deepEqual(partial.records.map(r => r.id), ['records/valid']);
});
