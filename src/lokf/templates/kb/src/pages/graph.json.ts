import type { APIRoute } from 'astro';
import { loadGraphData } from '../lib/graph-data';

/** The toolkit's vocabulary-aware Cytoscape projection, with site URLs. */
export const GET: APIRoute = async () => {
  return new Response(JSON.stringify(await loadGraphData()), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
