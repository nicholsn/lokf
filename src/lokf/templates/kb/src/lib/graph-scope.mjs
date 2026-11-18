/** Bounded, deterministic views over a complete LOKF graph export.
 *
 * Every concept gets an addressable one-hop neighborhood. A page contains at
 * most PAGE_SIZE direct neighbors, then fills remaining space with two-hop
 * context. The complete graph remains available separately as graph.json.
 */
export const PAGE_SIZE = 60;
export const MAX_NODES = 180;

const labelOf = (node) => String(node.data.label || node.data.concept_id || node.data.id);
const byLabel = (a, b) => labelOf(a).localeCompare(labelOf(b)) || String(a.data.id).localeCompare(String(b.data.id));

export function graphIndex(graph) {
  const nodes = new Map(graph.nodes.map((node) => [node.data.id, node]));
  const degree = new Map([...nodes.keys()].map((id) => [id, 0]));
  for (const { data: edge } of graph.edges) {
    if (!nodes.has(edge.source) || !nodes.has(edge.target) || edge.source === edge.target) continue;
    degree.set(edge.source, degree.get(edge.source) + 1);
    degree.set(edge.target, degree.get(edge.target) + 1);
  }
  const choices = [...nodes.values()].sort(byLabel).map(({ data }) => ({
    id: data.id, concept_id: data.concept_id, label: data.label,
    type: data.type, href: data.href, degree: degree.get(data.id),
  }));
  const defaultNode = [...choices].sort((a, b) => b.degree - a.degree || a.label.localeCompare(b.label) || a.id.localeCompare(b.id))[0];
  return { count: choices.length, default_focus: defaultNode?.concept_id || '', nodes: choices };
}

export function graphScopes(graph, { pageSize = PAGE_SIZE, maxNodes = MAX_NODES } = {}) {
  if (!Number.isSafeInteger(pageSize) || pageSize < 1 || !Number.isSafeInteger(maxNodes) || maxNodes <= pageSize) {
    throw new RangeError('maxNodes must exceed a positive pageSize');
  }
  const nodes = new Map(graph.nodes.map((node) => [node.data.id, node]));
  const adjacent = new Map([...nodes.keys()].map((id) => [id, new Set()]));
  const incident = new Map([...nodes.keys()].map((id) => [id, []]));
  const edges = [...new Map(graph.edges.map((edge) => [edge.data.id, edge])).values()].filter(({ data }) =>
    nodes.has(data.source) && nodes.has(data.target));
  for (const { data } of edges) {
    if (data.source === data.target) continue;
    adjacent.get(data.source).add(data.target);
    adjacent.get(data.target).add(data.source);
  }
  for (const edge of edges) {
    incident.get(edge.data.source).push(edge);
    incident.get(edge.data.target).push(edge);
  }
  const results = [];
  for (const center of [...nodes.values()].sort(byLabel)) {
    const id = center.data.id;
    const related = [...adjacent.get(id)].map((target) => nodes.get(target)).sort(byLabel);
    const pages = Math.max(1, Math.ceil(related.length / pageSize));
    for (let page = 1; page <= pages; page++) {
      const direct = related.slice((page - 1) * pageSize, page * pageSize);
      const selected = new Set([id, ...direct.map((node) => node.data.id)]);
      const secondHop = new Map();
      for (const node of direct) {
        for (const target of adjacent.get(node.data.id)) {
          if (selected.has(target)) continue;
          secondHop.set(target, (secondHop.get(target) || 0) + 1);
        }
      }
      const context = [...secondHop.keys()].sort((a, b) =>
        secondHop.get(b) - secondHop.get(a) || byLabel(nodes.get(a), nodes.get(b)));
      const room = maxNodes - selected.size;
      for (const target of context.slice(0, room)) selected.add(target);
      const viewEdges = new Map();
      for (const key of selected) {
        for (const edge of incident.get(key)) {
          if (selected.has(edge.data.source) && selected.has(edge.data.target)) {
            viewEdges.set(edge.data.id, edge);
          }
        }
      }
      const view = {
        nodes: [...selected].map((key) => nodes.get(key)),
        edges: [...viewEdges.values()],
        scope: {
          id: center.data.concept_id, title: labelOf(center), type: center.data.type,
          page, pages, total: related.length,
          start: related.length ? (page - 1) * pageSize + 1 : 0,
          end: Math.min(page * pageSize, related.length),
          context_omitted: Math.max(0, context.length - room),
        },
      };
      results.push({ scope: `${center.data.concept_id}/${page}`, graph: view });
    }
  }
  return results;
}
