import type { APIRoute } from 'astro';
import { loadGraphData } from '../../lib/graph-data';
import { graphScopes } from '../../lib/graph-scope.mjs';

export async function getStaticPaths() {
  return graphScopes(await loadGraphData()).map(({ scope, graph }) => ({
    params: { scope }, props: { graph },
  }));
}

export const GET: APIRoute = ({ props }) => new Response(
  JSON.stringify(props.graph),
  { headers: { 'Content-Type': 'application/json; charset=utf-8' } },
);
