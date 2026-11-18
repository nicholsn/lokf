import { getCollection, type CollectionEntry } from 'astro:content';

/**
 * Helpers over the LOKF bundle: concept IRIs and base-aware site links.
 * Schema relations and JSON-LD come from `lokf export` through graph-data.ts.
 */

export const BASE_IRI = '__KB_BASE_IRI__';

export type Concept = CollectionEntry<'knowledge'>;

/** Join a site-internal path onto Astro's base (works at "/" or "/<repo>"). */
export const href = (path: string) =>
  import.meta.env.BASE_URL.replace(/\/$/, '') + '/' + path.replace(/^\//, '');

/** A concept's IRI: an explicit absolute frontmatter `id`, else base + path. */
export const iriOf = (e: Concept) => {
  const id = (e.data as Record<string, unknown>).id;
  return typeof id === 'string' && /^(https?:|urn:)/.test(id) ? id : BASE_IRI + e.id;
};
export const hrefOf = (e: Concept) => href(e.id);
export const titleOf = (e: Concept) => e.data.title ?? e.id;

let bundlePromise: Promise<{ concepts: Concept[]; byIri: Map<string, Concept> }> | undefined;

export function loadBundle() {
  const read = async () => {
    const concepts = await getCollection('knowledge');
    const byIri = new Map<string, Concept>();
    for (const e of concepts) byIri.set(iriOf(e), e);
    return { concepts, byIri };
  };
  // Production renders every concept page in one build. Reuse the map there;
  // development reads live content after edits.
  if (import.meta.env.DEV) return read();
  return bundlePromise ||= read();
}
