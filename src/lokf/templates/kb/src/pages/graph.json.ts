import type { APIRoute } from 'astro';
import { loadBundle, iriOf, hrefOf, titleOf, relationsOf } from '../lib/lokf';

/**
 * The bundle as cytoscape elements — nodes are concepts, edges are the typed
 * relations whose subject AND object both live in this bundle. External
 * targets stay in the JSON-LD projection but are not drawn.
 */
export const GET: APIRoute = async () => {
  const { concepts } = await loadBundle();

  const nodes = concepts.map((c) => ({
    data: {
      id: iriOf(c),
      label: titleOf(c),
      type: c.data.type,
      concept_id: c.id,
      href: hrefOf(c),
    },
  }));

  const known = new Set(nodes.map((n) => n.data.id));
  const edges: { data: Record<string, string> }[] = [];
  for (const c of concepts) {
    const source = iriOf(c);
    for (const { slot, target } of relationsOf(c)) {
      if (!known.has(target) || target === source) continue;
      edges.push({
        data: { id: `${slot}:${source}->${target}`, source, target, predicate: slot },
      });
    }
  }

  return new Response(JSON.stringify({ nodes, edges }, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
