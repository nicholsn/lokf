import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

/**
 * The `knowledge/` directory at the repo root IS the content: a LOKF bundle of
 * markdown concept files. OKF requires only `type`, and consumers must
 * tolerate unknown keys — so the schema validates the common fields and
 * passes everything else through.
 */
const knowledge = defineCollection({
  loader: glob({
    // `index.md` and `log.md` are reserved bundle files (OKF §3) at ANY depth —
    // the toolkit ignores them everywhere, so exclude them everywhere (`**`
    // matches zero segments too, keeping the root files excluded).
    pattern: ['**/*.md', '!**/index.md', '!**/log.md'],
    base: './knowledge',
    // Preserve the literal relative path as the entry id (Astro's default
    // slugifies it), so a concept's IRI (base_iri + id) matches the toolkit's
    // concept_id exactly — no case/underscore drift between site and graph.
    generateId: ({ entry }) => entry.replace(/\.md$/, ''),
  }),
  schema: z
    .object({
      type: z.string(),
      title: z.string().optional(),
      description: z.string().optional(),
      resource: z.string().optional(),
      tags: z.array(z.string()).optional(),
    })
    .passthrough(),
});

export const collections = { knowledge };
