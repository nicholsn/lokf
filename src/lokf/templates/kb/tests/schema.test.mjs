import test from 'node:test';
import assert from 'node:assert/strict';
import {schemaGraph,schemaScope} from '../src/lib/schema-graph.mjs';
test('schema graph includes inheritance, overrides and unused types with bounded scopes',()=>{
 const classes=Array.from({length:150},(_,i)=>({name:`C${i}`,local:i>0,is_a:i?'C0':null,mixins:[],slots:i?[{name:'rel',range:`C${(i+1)%150}`,any_of:[],declared_here:true}]:[]}));
 const graph=schemaGraph({classes});
 assert.equal(graph.nodes.length,150);
 assert(graph.edges.some(e=>e.data.source==='C1' && e.data.target==='C0' && e.data.kind==='inheritance'));
 const overview=schemaScope(graph);
 assert(overview.nodes.length<=70);assert(overview.omitted>0);
 const focus=schemaScope(graph,'C100');
 assert(focus.nodes.some(n=>n.data.id==='C100'));
 assert(focus.nodes.some(n=>n.data.id==='C0'));
 assert(focus.nodes.some(n=>n.data.id==='C101'));
 for(const e of focus.edges) assert(focus.nodes.some(n=>n.data.id===e.data.target));
});

import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { checkSchemaRoutes, schemaPath, slotCardinality } from '../src/lib/schema-browser.ts';

test('schema paths distinguish case and punctuation and protect emitted pages', t => {
  const model = { classes: [{name: 'Gene'}, {name: 'gene'}, {name: 'β chain'}, {name: 'Note'}], slots: [], types: [], enums: [] };
  const paths = model.classes.map(term => schemaPath(model, 'classes', term.name));
  assert.equal(new Set(paths.map(path => path.toLowerCase())).size, 4);
  assert.equal(paths[3], 'schema/classes/Note');

  const assets = mkdtempSync(join(tmpdir(), 'lokf-schema-assets-'));
  t.after(() => rmSync(assets, {recursive: true, force: true}));
  assert.throws(() => checkSchemaRoutes(model, [{id: 'schema'}], [], assets), /route collision/);
  assert.throws(() => checkSchemaRoutes(model, [], ['Schema/classes/Note'], assets), /route collision/);
  mkdirSync(join(assets, paths[3]), {recursive: true});
  writeFileSync(join(assets, 'schema', 'legend.svg'), 'site asset');
  assert.doesNotThrow(() => checkSchemaRoutes(model, [], [], assets));
  writeFileSync(join(assets, paths[3], 'index.html'), 'custom page');
  assert.throws(() => checkSchemaRoutes(model, [], [], assets), /schema\/classes\/Note.*collides with/);
});

test('slot cardinality renders effective inclusive bounds, including zero', () => {
  assert.equal(slotCardinality({}), '0..1');
  assert.equal(slotCardinality({required: true, multivalued: true}), '1..*');
  assert.equal(slotCardinality({multivalued: true, minimum_cardinality: 2, maximum_cardinality: 5}), '2..5');
  assert.equal(slotCardinality({multivalued: true, exact_cardinality: 2}), '2..2');
  assert.equal(slotCardinality({multivalued: true, maximum_cardinality: 0}), '0..0');
});
