import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

/**
 * The `knowledge/` directory at the repo root IS the content: a LOKF bundle of
 * markdown concept files. OKF requires only `type`, and consumers must
 * tolerate unknown keys — so the schema validates the common fields and
 * passes everything else through. `index.md` and `log.md` are reserved bundle
 * files (OKF §3), not concepts.
 */
const knowledge = defineCollection({
  loader: glob({
    pattern: ['**/*.md', '!index.md', '!log.md'],
    base: './knowledge',
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
