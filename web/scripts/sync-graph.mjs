// Keep the Starlight graph demo on the exact explorer used by `lokf new`.
// Copy its component and dependency-free helpers into web/ before Astro runs:
// Vite then resolves Astro and Cytoscape from this site's node_modules.
// All outputs are gitignored under src/generated/.
import { copyFileSync, mkdirSync, readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(here, '../../src/lokf/templates/kb/src');
const target = resolve(here, '../src/generated/graph-explorer');
const files = [
  'components/GraphExplorer.astro',
  ...readdirSync(resolve(source, 'lib'))
    .filter((name) => /^graph-.*\.mjs$/.test(name))
    .sort()
    .map((name) => `lib/${name}`),
];

for (const file of files) {
  const destination = resolve(target, file);
  mkdirSync(dirname(destination), { recursive: true });
  copyFileSync(resolve(source, file), destination);
}

console.log(`sync-graph: ${files.length} shared explorer files`);
