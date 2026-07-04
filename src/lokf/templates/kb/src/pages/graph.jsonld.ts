import type { APIRoute } from 'astro';
import { loadBundle, iriOf } from '../lib/lokf';

/** The LOKF JSON-LD context published by the lokf project. */
const CONTEXT =
  'https://raw.githubusercontent.com/nicholsn/lokf/main/lokf.context.jsonld';

/**
 * The whole bundle as one JSON-LD document — this is the LOKF thesis: the
 * concepts' frontmatter, with the published @context attached, IS the RDF
 * graph. Load it with any JSON-LD/RDF tool.
 */
export const GET: APIRoute = async () => {
  const { concepts } = await loadBundle();
  const graph = concepts.map((c) => ({
    id: iriOf(c),
    ...(c.data as Record<string, unknown>),
    ...(c.body ? { body: c.body } : {}),
  }));
  const doc = { '@context': CONTEXT, '@graph': graph };
  return new Response(JSON.stringify(doc, null, 2), {
    headers: { 'Content-Type': 'application/ld+json; charset=utf-8' },
  });
};
