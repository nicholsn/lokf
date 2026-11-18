import type { APIRoute } from 'astro';
import { loadConceptsJsonLd } from '../lib/graph-data';

/** The toolkit's vocabulary-aware JSON-LD projection. */
export const GET: APIRoute = async () => {
  return new Response(JSON.stringify(await loadConceptsJsonLd()), {
    headers: { 'Content-Type': 'application/ld+json; charset=utf-8' },
  });
};
