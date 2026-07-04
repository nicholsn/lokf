import path from 'node:path';

/**
 * Concept bodies link to peers with markdown `.md` paths — relative
 * (`../glossary/active-user.md`) or bundle-root-absolute
 * (`/tables/user-events.md`, the form the author-concept skill teaches).
 * Rewrite them to the concept's site route, prefixed with the site's base so
 * they work on a GitHub *project* page under `/<repo>/`. External, mailto, and
 * anchor links are left alone; links outside `knowledge/` are left alone.
 *
 * `base` is the Astro `base` (e.g. `/my-kb` or `/`), injected from the config.
 */
const KNOWLEDGE_ROOT = path.join(process.cwd(), 'knowledge');

function walk(node, fn) {
  if (!node || typeof node !== 'object') return;
  if (node.type === 'link') fn(node);
  if (Array.isArray(node.children)) for (const c of node.children) walk(c, fn);
}

export default function remarkLokfLinks({ base = '/' } = {}) {
  const prefix = base === '/' ? '' : base.replace(/\/$/, '');
  return (tree, file) => {
    const filePath = file.path || (file.history && file.history[0]);
    const dir = filePath ? path.dirname(filePath) : KNOWLEDGE_ROOT;
    walk(tree, (node) => {
      const url = node.url || '';
      if (!url.endsWith('.md') || /^(https?:|mailto:|#)/.test(url)) return;
      const abs = url.startsWith('/')
        ? path.join(KNOWLEDGE_ROOT, url.replace(/^\//, ''))
        : path.resolve(dir, url);
      const rel = path.relative(KNOWLEDGE_ROOT, abs).replace(/\.md$/, '');
      if (rel.startsWith('..')) return;
      node.url = prefix + '/' + rel.split(path.sep).join('/');
    });
  };
}
