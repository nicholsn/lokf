import type { APIRoute } from 'astro';
import { loadGraphData } from '../lib/graph-data';
import { graphIndex } from '../lib/graph-scope.mjs';

/** Small navigation index; the explorer fetches a bounded scope on large KBs. */
export const GET: APIRoute = async () => new Response(
  JSON.stringify(graphIndex(await loadGraphData())),
  { headers: { 'Content-Type': 'application/json; charset=utf-8' } },
);
