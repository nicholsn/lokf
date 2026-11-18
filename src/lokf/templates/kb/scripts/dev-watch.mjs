import { existsSync, readFileSync } from 'node:fs';
import { dirname, extname, join, resolve } from 'node:path';

function declaredSchema(projectFile) {
  if (!existsSync(projectFile)) return '';
  let inLokf = false;
  for (const line of readFileSync(projectFile, 'utf8').split(/\r?\n/)) {
    const section = line.match(/^\s*\[([^\]]+)\]\s*(?:#.*)?$/);
    if (section) { inLokf = section[1] === 'tool.lokf'; continue; }
    if (!inLokf) continue;
    const entry = line.match(/^\s*schema\s*=\s*("(?:\\.|[^"])*"|'[^']*')/);
    if (entry) {
      try { return entry[1].startsWith('"') ? JSON.parse(entry[1]) : entry[1].slice(1, -1); }
      catch { return ''; }
    }
  }
  return '';
}

function localImports(schemaFile) {
  if (!existsSync(schemaFile)) return [];
  const lines = readFileSync(schemaFile, 'utf8').split(/\r?\n/);
  const imports = [];
  let inImports = false;
  for (const line of lines) {
    const start = line.match(/^imports:\s*(.*)$/);
    if (start) {
      inImports = true;
      const inline = start[1].split('#')[0].trim();
      if (inline.startsWith('[') && inline.endsWith(']')) imports.push(...inline.slice(1, -1).split(','));
      else if (inline) imports.push(inline);
      continue;
    }
    if (!inImports) continue;
    const item = line.match(/^\s+-\s+(.+)$/);
    if (item) { imports.push(item[1]); continue; }
    if (line.trim() && !line.trim().startsWith('#')) break;
  }
  return imports.map((item) => item.trim().replace(/^['"]|['"]$/g, '').split(/\s+#/)[0])
    .filter((item) => item && !item.includes(':'))
    .map((item) => resolve(dirname(schemaFile), extname(item) ? item : `${item}.yaml`));
}

/** Schema and local LinkML imports declared by this site's pyproject.toml. */
export function configuredSchemaFiles(root) {
  const name = declaredSchema(join(root, 'pyproject.toml'));
  if (!name) return [];
  const files = new Set();
  const pending = [resolve(root, name)];
  while (pending.length) {
    const file = pending.pop();
    if (files.has(file)) continue;
    files.add(file);
    pending.push(...localImports(file));
  }
  return [...files];
}

/** Coalesce save bursts; if a save arrives during a run, process it afterward. */
export function createDebouncedTask(run, onSuccess, delay = 250) {
  let timer;
  let pending = false;
  let running = false;
  let closed = false;
  async function drain() {
    if (running || closed || !pending) return;
    running = true;
    let latestSucceeded = false;
    try {
      while (pending && !closed) {
        pending = false;
        latestSucceeded = await run();
      }
      if (latestSucceeded && !closed) onSuccess();
    } finally {
      running = false;
    }
  }
  return {
    schedule() {
      if (closed) return;
      pending = true;
      clearTimeout(timer);
      timer = setTimeout(drain, delay);
    },
    close() { closed = true; clearTimeout(timer); },
  };
}
