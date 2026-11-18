/** Shortest visible path. A step retains the original edge and traversal direction. */
export function findPath(graph, from, to, { hiddenTypes = [], hiddenRelations = [], directed = false } = {}) {
  const excludedTypes = new Set(hiddenTypes);
  const excludedRelations = new Set(hiddenRelations);
  const nodes = new Map(graph.nodes.filter(({ data }) => !excludedTypes.has(String(data.type || '')))
    .map((node) => [node.data.id, node]));
  if (!nodes.has(from) || !nodes.has(to)) return null;
  if (from === to) return { nodes: [nodes.get(from)], steps: [] };
  const adjacency = new Map([...nodes.keys()].map((id) => [id, []]));
  for (const edge of graph.edges) {
    const { source, target, predicate } = edge.data;
    if (!nodes.has(source) || !nodes.has(target) || excludedRelations.has(String(predicate || ''))) continue;
    adjacency.get(source).push({ next: target, edge, forward: true });
    if (!directed) adjacency.get(target).push({ next: source, edge, forward: false });
  }
  const visited = new Set([from]);
  const parents = new Map();
  const queue = [from];
  for (let i = 0; i < queue.length; i++) {
    const current = queue[i];
    for (const step of adjacency.get(current)) {
      if (visited.has(step.next)) continue;
      visited.add(step.next);
      parents.set(step.next, { previous: current, edge: step.edge, forward: step.forward });
      if (step.next === to) {
        const steps = [];
        let cursor = to;
        while (cursor !== from) {
          const parent = parents.get(cursor);
          steps.unshift({ from: nodes.get(parent.previous), to: nodes.get(cursor), edge: parent.edge, forward: parent.forward });
          cursor = parent.previous;
        }
        return { nodes: [nodes.get(from), ...steps.map((item) => item.to)], steps };
      }
      queue.push(step.next);
    }
  }
  return null;
}
