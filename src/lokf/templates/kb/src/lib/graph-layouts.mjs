import { LAYOUTS, validLayout } from './graph-view.mjs';

/** Presentation-only groups. Source graph nodes and edges are never rewritten. */
export function clearGroups(cy) {
  cy.nodes('.concept').move({ parent: null });
  cy.nodes('.layout-group').remove();
}

function groupsFor(elements, mode, excludedRelations) {
  const nodes = elements.nodes();
  if (mode === 'types') {
    return [...new Set(nodes.map((n) => n.data('type')))].sort().map((type) => ({
      label: type, nodes: nodes.filter((n) => n.data('type') === type),
    }));
  }
  const relationships = elements.edges().filter((edge) =>
    !excludedRelations.has(edge.data('slot') || edge.data('predicate')));
  if (!nodes.length) return [];
  const raw = nodes.union(relationships).markovClustering({ expandFactor: 2, inflateFactor: 1.3, maxIterations: 30 });
  const seen = new Set();
  const groups = [];
  for (const cluster of raw.sort((a, b) => b.length - a.length)) {
    const members = cluster.filter((node) => !seen.has(node.id()));
    if (!members.length) continue;
    members.forEach((node) => seen.add(node.id()));
    groups.push(members);
  }
  for (const node of nodes) if (!seen.has(node.id())) groups.push(node.collection());
  const plural = groups.filter((group) => group.length > 1).map((group, i) => ({
    label: `Community ${i + 1}`, nodes: group,
  }));
  const singles = groups.filter((group) => group.length === 1);
  if (singles.length) plural.push({ label: 'Unclustered', nodes: singles.reduce((all, group) => all.union(group), nodes.cy().collection()) });
  return plural;
}

export function prepareLayout(cy, choice, excludedRelations = new Set(['isPartOf', 'hasPart'])) {
  clearGroups(cy);
  const mode = validLayout(choice);
  const nodes = cy.nodes('.concept').not('.hidden');
  const edges = cy.edges().not('.hidden').filter((edge) => nodes.contains(edge.source()) && nodes.contains(edge.target()));
  let elements = nodes.union(edges);
  let groups = [];
  if (mode === 'communities' || mode === 'types') {
    groups = groupsFor(elements, mode, excludedRelations);
    cy.batch(() => {
      groups.forEach((group, i) => {
        const parent = cy.add({ data: { id: `__layout_group_${i}`, label: group.label }, classes: 'layout-group' });
        group.nodes.move({ parent: parent.id() });
        elements = elements.union(parent);
      });
    });
  }
  const common = { animate: false, fit: true, padding: 50 };
  let options;
  if (mode === 'radial') {
    const degrees = new Map(nodes.map((node) => [node.id(), edges.filter((edge) => edge.source().id() === node.id() || edge.target().id() === node.id()).length]));
    const max = Math.max(0, ...degrees.values());
    options = { ...common, name: 'concentric', concentric: (node) => degrees.get(node.id()) || 0,
      levelWidth: () => Math.max(1, Math.ceil(max / 5)), minNodeSpacing: 65,
      avoidOverlap: true, nodeDimensionsIncludeLabels: true };
  } else if (mode === 'cose') {
    options = { ...common, name: 'cose', numIter: 500, nodeRepulsion: () => 14000,
      idealEdgeLength: () => 130, componentSpacing: 120 };
  } else {
    options = { ...common, name: 'fcose', quality: 'default', randomize: true, numIter: 800,
      nodeSeparation: 100, nodeRepulsion: () => 12000,
      idealEdgeLength: () => 120, packComponents: false, tile: true };
  }
  if (nodes.length < 2) options = { ...common, name: 'grid' };
  return { elements, options, groups: groups.length, nodes: nodes.length, description: LAYOUTS[mode].description };
}
