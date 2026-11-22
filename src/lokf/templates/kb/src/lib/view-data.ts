import { readFile } from 'node:fs/promises';
import { existsSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { buildNavigation, type Navigation, type Plan } from './view-navigation.ts';

async function readViews() {
  let plan: Plan;
  try {
    const source = await readFile(join(process.cwd(), 'src', 'generated', 'views.json'), 'utf8');
    plan = JSON.parse(source);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
    plan = { views: [], records: {} };
  }
  return buildNavigation(plan);
}

let navigation: Promise<Navigation> | undefined;
export function loadViews() {
  if (import.meta.env.DEV) return readViews();
  return navigation ||= readViews();
}

export function checkPublicRoute(path: string, kind: string, publicDir: string) {
  let asset = publicDir;
  for (const part of [...path.split('/'), 'index.html']) {
    asset = join(asset, part);
    if (!existsSync(asset)) break;
    if (!statSync(asset).isDirectory() || part === 'index.html') {
      throw new Error(`${kind} route /${path}/ collides with ${asset}`);
    }
  }
}

/** Generated URLs share Astro's catch-all with concept pages and its output with public/. */
export function checkViewRoutes(navigation: Navigation, concepts: { id: string }[], publicDir = join(process.cwd(), 'public')) {
  if (!navigation.pages.size) return;
  const ids = new Set(concepts.map(c => c.id));
  for (const path of navigation.pages.keys()) {
    if (ids.has(path)) throw new Error(`View route /${path}/ collides with knowledge/${path}.md`);
    checkPublicRoute(path, 'View', publicDir);
  }
  for (const id of Object.keys(navigation.records)) {
    if (!ids.has(id)) {
      throw new Error(`View record "${id}" has no Astro concept page. Check the content loader output for knowledge/${id}.md`);
    }
  }
}
