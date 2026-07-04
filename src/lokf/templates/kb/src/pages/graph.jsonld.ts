import type { APIRoute } from 'astro';
import { loadBundle, iriOf, resolveRef, RELATION_SLOTS } from '../lib/lokf';

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
  const graph = concepts.map((c) => {
    const data = { ...(c.data as Record<string, unknown>) };
    // Resolve bundle-relative relation targets to full IRIs so the RDF edges
    // are unambiguous (mirrors the toolkit); `id` = the concept's own IRI.
    for (const slot of RELATION_SLOTS) {
      const v = data[slot];
      if (v === undefined) continue;
      data[slot] = (Array.isArray(v) ? v : [v]).map((t) =>
        typeof t === 'string' ? resolveRef(t) : t,
      );
    }
    return { ...data, id: iriOf(c), ...(c.body ? { body: c.body } : {}) };
  });
  const doc = { '@context': CONTEXT, '@graph': graph };
  return new Response(JSON.stringify(doc, null, 2), {
    headers: { 'Content-Type': 'application/ld+json; charset=utf-8' },
  });
};
