import test from 'node:test';
import assert from 'node:assert/strict';
import { fieldsOf, fieldValues, incomingTitle, readable, relationTitle, typeTitle } from '../src/lib/labels.mjs';
import { PALETTE, TYPE_COLORS, typeColors } from '../src/lib/graph-colors.mjs';

const vocabulary = {
  types: { DataStage: { title: 'Data stage' } },
  relations: { unlocks: { title: 'Unlocks', inverse_title: 'Unlocked by' }, modality: { title: 'Modality' } },
  fields: { DataStage: [{ name: 'formats', title: 'Formats', multivalued: true }] },
};

test('names types and relations as the schema titles them', () => {
  assert.equal(typeTitle(vocabulary, 'DataStage'), 'Data stage');
  assert.equal(relationTitle(vocabulary, 'unlocks'), 'Unlocks');
  assert.deepEqual(fieldsOf(vocabulary, 'DataStage').map((field) => field.name), ['formats']);
  assert.deepEqual(fieldsOf(vocabulary, 'Modality'), []);
});

test('reads a relation from its target with the inverse title, else an arrow', () => {
  assert.equal(incomingTitle(vocabulary, 'unlocks'), 'Unlocked by');
  // no inverse title: the forward title, marked as pointing at this concept
  assert.equal(incomingTitle(vocabulary, 'modality'), '← Modality');
});

test('falls back to readable names for a graph exported without a vocabulary', () => {
  assert.equal(readable('ScientificCapability'), 'Scientific capability');
  assert.equal(readable('processing_step'), 'Processing step');
  assert.equal(readable('URLField'), 'URL field');
  assert.equal(typeTitle(undefined, 'GlossaryTerm'), 'Glossary term');
  assert.equal(incomingTitle({}, 'derivedFrom'), '← Derived from');
});

test('shows field values as text and skips nested objects', () => {
  assert.deepEqual(fieldValues(['CRAM', 'BAM']), ['CRAM', 'BAM']);
  assert.deepEqual(fieldValues(5), ['5']);
  assert.deepEqual(fieldValues(new Date('2026-01-02')), ['2026-01-02']);
  assert.deepEqual(fieldValues([{ nested: true }, '', null]), []);
  assert.deepEqual(fieldValues(undefined), []);
});

test('gives every type in a graph its own color', () => {
  const types = ['CurationProcess', 'CurationType', 'DataStage', 'Explanation', 'GlossaryTerm',
    'HierarchyLevel', 'Modality', 'ProcessingLevel', 'Reference', 'ScientificCapability',
    ...Array.from({ length: 12 }, (_, i) => `Extra${i}`)];
  const colors = typeColors(types);
  assert.equal(new Set(Object.values(colors)).size, types.length);
  assert.equal(colors.GlossaryTerm, TYPE_COLORS.GlossaryTerm);
  // Reference's usual color is GlossaryTerm's too, so it takes a spare one
  assert.notEqual(colors.Reference, colors.GlossaryTerm);
  assert.ok(PALETTE.includes(colors.CurationProcess));
});
