/** Only schema-defined class edges; never infer a TBox from record co-occurrence. */
export function schemaGraph(model) {
  const names = new Set(model.classes.map(c => c.name));
  const nodes = model.classes.map(c => ({data: {id: c.name, label: c.name, local: c.local, abstract: c.abstract}}));
  const edges = [];
  const add = (source, target, label, kind) => {
    if (names.has(target)) edges.push({data: {id: `e${edges.length}`, source, target, label, kind}});
  };
  for (const c of model.classes) {
    if (c.is_a) add(c.name, c.is_a, 'is a', 'inheritance');
    for (const m of c.mixins) add(c.name, m, 'mixin', 'inheritance');
    for (const s of c.slots) {
      // Inherited links remain available when focused on a class, but don't flood the overview.
      for (const target of new Set([s.range, ...s.any_of])) add(c.name, target, s.name, s.declared_here || s.overridden_here ? 'slot' : 'inherited-slot');
    }
  }
  return {nodes, edges};
}
export function schemaScope(graph, focus = '', limit = 70) {
  const selected = new Set();
  if (focus) {
    selected.add(focus);
    for (const e of graph.edges) if (e.data.source === focus || e.data.target === focus) {
      for (const id of [e.data.source, e.data.target]) if (selected.size < limit) selected.add(id);
    }
  } else {
    const local = graph.nodes.filter(n => n.data.local);
    for (const n of (local.length ? local : graph.nodes)) if (selected.size < limit) selected.add(n.data.id);
    for (const e of graph.edges) if (e.data.kind !== 'inherited-slot' && selected.has(e.data.source) && selected.size < limit) selected.add(e.data.target);
  }
  const edges = graph.edges.filter(e => selected.has(e.data.source) && selected.has(e.data.target) && (focus ? (e.data.source === focus || e.data.target === focus) : e.data.kind !== 'inherited-slot'));
  return {nodes: graph.nodes.filter(n => selected.has(n.data.id)), edges, omitted: graph.nodes.length - selected.size};
}
