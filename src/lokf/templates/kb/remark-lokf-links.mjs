import path from 'node:path';

/**
 * Concept bodies link to peers with markdown `.md` paths — relative
 * (`../glossary/active-user.md`) or bundle-root-absolute
 * (`/tables/user-events.md`, the form the author-concept skill teaches).
 * Rewrite them to the concept's site route, prefixed with the site's base so
 * they work on a GitHub *project* page under `/<repo>/`. External, mailto, and
 * anchor links are left alone; links outside `knowledge/` are left alone.
 *
 * Raw HTML and active URL schemes are escaped so imported knowledge cannot
 * insert browser scripts. `base` is Astro's base, injected from the config.
 */
const KNOWLEDGE_ROOT = path.join(process.cwd(), 'knowledge');

function walk(node, fn) {
  if (!node || typeof node !== 'object') return;
  if (node.type === 'link' || node.type === 'image' || node.type === 'html') fn(node);
  if (Array.isArray(node.children)) for (const c of node.children) walk(c, fn);
}

const textOf = (node) => node.value ?? node.alt ??
  (node.children ?? []).map(textOf).join('');

export default function remarkLokfLinks({ base = '/' } = {}) {
  const prefix = base === '/' ? '' : base.replace(/\/$/, '');
  return (tree, file) => {
    const filePath = file.path || (file.history && file.history[0]);
    const dir = filePath ? path.dirname(filePath) : KNOWLEDGE_ROOT;
    walk(tree, (node) => {
      if (node.type === 'html') {
        node.type = 'text';
        return;
      }
      const rawUrl = String(node.url || '');
      if (/[\x00-\x1f\x7f]/.test(rawUrl)) {
        node.value = textOf(node);
        node.type = 'text';
        delete node.url;
        delete node.children;
        return;
      }
      const url = rawUrl.trim();
      node.url = url;
      // Do not publish active schemes from a bundle's Markdown as browser
      // links. The content may have been imported from an external source.
      if (/^[a-z][a-z0-9+.-]*:/i.test(url) && !/^(https?:|mailto:)/i.test(url)) {
        node.value = textOf(node);
        node.type = 'text';
        delete node.url;
        delete node.children;
        return;
      }
      if (/^(https?:|mailto:|#)/i.test(url) || url.startsWith('//')) return;
      const match = /^([^?#]+\.md)([?#].*)?$/.exec(url);
      if (!match) return;
      const [, markdownPath, suffix = ''] = match;
      const abs = markdownPath.startsWith('/')
        ? path.join(KNOWLEDGE_ROOT, markdownPath.replace(/^\//, ''))
        : path.resolve(dir, markdownPath);
      const rel = path.relative(KNOWLEDGE_ROOT, abs).replace(/\.md$/, '');
      if (rel.startsWith('..')) return;
      // A directory's index.md is its section page; the root's is the home page.
      const route = rel === 'index' ? ''
        : rel.endsWith(path.sep + 'index') ? rel.slice(0, -'index'.length)
        : rel;
      node.url = prefix + '/' + route.split(path.sep).join('/') + suffix;
    });
  };
}
