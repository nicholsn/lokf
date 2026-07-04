// @ts-check
import { defineConfig } from 'astro/config';
import remarkLokfLinks from './remark-lokf-links.mjs';
import remarkStripLeadingTitle from './remark-strip-leading-title.mjs';

// `site` + `base` are derived from the bundle's base_iri, so the site works
// both on a custom domain (base "/") and as a GitHub *project* page
// (base "/<repo>"). Internal links use the href() helper in src/lib/lokf.ts,
// which prefixes import.meta.env.BASE_URL. The remark plugins rewrite concept
// `.md` cross-links to base-aware routes and drop a body's redundant leading
// `# Title` (the layout renders it from frontmatter).
export default defineConfig({
  site: '__KB_SITE__',
  base: '__KB_BASE__',
  markdown: {
    remarkPlugins: [
      [remarkLokfLinks, { base: '__KB_BASE__' }],
      remarkStripLeadingTitle,
    ],
  },
});
