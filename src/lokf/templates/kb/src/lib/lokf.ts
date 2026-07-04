import { getCollection, type CollectionEntry } from 'astro:content';

/**
 * Helpers over the LOKF bundle: resolve concept IRIs, build base-aware links,
 * and project concepts to schema.org JSON-LD. The concept IRI is
 * BASE_IRI + the concept's path id (the LOKF default).
 */

export const BASE_IRI = '__KB_BASE_IRI__';

export type Concept = CollectionEntry<'knowledge'>;

/** LOKF's typed-relation slots — each becomes an edge in the graph. */
export const RELATION_SLOTS = [
  'isPartOf', 'hasPart', 'references', 'dependsOn', 'derivedFrom',
  'about', 'sameAs', 'relatedTo', 'definedBy', 'source',
  'measures', 'memberOf', 'holder',
] as const;

export const REL_LABEL: Record<string, string> = {
  isPartOf: 'Part of', hasPart: 'Has part', references: 'References',
  dependsOn: 'Depends on', derivedFrom: 'Derived from', about: 'About',
  sameAs: 'Same as', relatedTo: 'Related to', definedBy: 'Defined by',
  source: 'Source', measures: 'Measures', memberOf: 'Member of',
  holder: 'Held by',
};

/** Join a site-internal path onto Astro's base (works at "/" or "/<repo>"). */
export const href = (path: string) =>
  import.meta.env.BASE_URL.replace(/\/$/, '') + '/' + path.replace(/^\//, '');

/**
 * Resolve a relation target to a full IRI — mirrors the toolkit's
 * `Bundle.resolve`: absolute IRIs (http(s)/urn) pass through; a bundle-relative
 * Concept ID (`glossary/active-user` or `/glossary/active-user`) hangs off the
 * base IRI so it matches the concept's own `iriOf`.
 */
export const resolveRef = (ref: string) =>
  /^(https?:|urn:)/.test(ref) ? ref : BASE_IRI + ref.replace(/^\//, '');

/** A concept's IRI: an explicit absolute frontmatter `id`, else base + path. */
export const iriOf = (e: Concept) => {
  const id = (e.data as Record<string, unknown>).id;
  return typeof id === 'string' && /^(https?:|urn:)/.test(id) ? id : BASE_IRI + e.id;
};
export const hrefOf = (e: Concept) => href(e.id);
export const titleOf = (e: Concept) => e.data.title ?? e.id;

export async function loadBundle() {
  const concepts = await getCollection('knowledge');
  const byIri = new Map<string, Concept>();
  for (const e of concepts) byIri.set(iriOf(e), e);
  return { concepts, byIri };
}

/** Every typed relation on a concept as {slot, target} pairs. */
export function relationsOf(e: Concept): { slot: string; target: string }[] {
  const d = e.data as Record<string, unknown>;
  const out: { slot: string; target: string }[] = [];
  for (const slot of RELATION_SLOTS) {
    const v = d[slot];
    if (v === undefined) continue;
    for (const target of Array.isArray(v) ? v : [v]) {
      if (typeof target === 'string') out.push({ slot, target: resolveRef(target) });
    }
  }
  for (const rel of (d.relations as { predicate?: string; target?: string }[] | undefined) ?? []) {
    if (rel?.predicate && rel?.target) out.push({ slot: rel.predicate, target: resolveRef(rel.target) });
  }
  return out;
}

/** Minimal schema.org projection for a concept page's JSON-LD. */
const SCHEMA_TYPE: Record<string, string> = {
  Person: 'Person', Organization: 'Organization', Role: 'OrganizationRole',
  Dataset: 'Dataset', Service: 'WebAPI', GlossaryTerm: 'DefinedTerm',
  Playbook: 'HowTo',
};

export function conceptJsonLd(e: Concept) {
  const d = e.data as Record<string, unknown>;
  const node: Record<string, unknown> = {
    '@context': 'https://schema.org',
    '@type': SCHEMA_TYPE[e.data.type] ?? 'CreativeWork',
    '@id': iriOf(e),
    name: titleOf(e),
  };
  if (d.description) node.description = d.description;
  if (d.resource) node.url = d.resource;
  if (Array.isArray(d.sameAs) && d.sameAs.length) node.sameAs = d.sameAs;
  return node;
}
