import type { APIRoute } from 'astro';
import { loadBundle, hrefOf, titleOf } from '../lib/lokf';
import { loadGraphData } from '../lib/graph-data';
import { buildIndex, searchableText } from '../lib/search.mjs';

function contentDate(data: Record<string, unknown>): string {
  const generated = data.generated as { at?: unknown } | undefined;
  const value = generated?.at ?? data.created ?? data.timestamp;
  const text = value instanceof Date ? value.toISOString() : String(value ?? '');
  return /^\d{4}-\d{2}-\d{2}/.test(text) ? text.slice(0, 10) : '';
}

/** Build once with Astro; the browser fetches the index only when search is used. */
export const GET: APIRoute = async () => {
  const [{ concepts }, graph] = await Promise.all([loadBundle(), loadGraphData()]);
  const graphNodes = new Map(graph.nodes.map(node => [node.data.concept_id, node.data]));
  const documents = concepts.map(c => {
    const data = c.data as Record<string, unknown>;
    const node = graphNodes.get(c.id);
    return {
      title: titleOf(c),
      type: c.data.type,
      concept_id: c.id,
      href: hrefOf(c),
      tags: Array.isArray(data.tags) ? data.tags.filter((tag): tag is string => typeof tag === 'string') : [],
      status: String(node?.status ?? data.status ?? ''),
      genre: typeof data.genre === 'string' ? data.genre : '',
      trust_tier: String(node?.trust_tier ?? ''),
      stale: Boolean(node?.stale),
      description: String(data.description ?? ''),
      text: searchableText([data.claim, data.thesis, data.summary, c.body].filter(Boolean).join('\n')),
      date: contentDate(data),
    };
  });
  return new Response(JSON.stringify(buildIndex(documents)), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
