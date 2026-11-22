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
