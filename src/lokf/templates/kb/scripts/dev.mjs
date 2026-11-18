import { spawn } from 'node:child_process';
import { watch } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { configuredSchemaFiles, createDebouncedTask } from './dev-watch.mjs';

const root = process.cwd();
const astroBin = join(root, 'node_modules', 'astro', 'bin', 'astro.mjs');
const exportScript = join(root, 'scripts', 'export-graph.mjs');
const schemaWatchers = new Map();
const otherWatchers = [];
let schemaTargets = new Set();
let astro;
let exporting;
let restartTimeout;
let restartQueued = false;
let stopping = false;

function closeWatchers() {
  for (const watcher of otherWatchers) watcher.close();
  for (const watcher of schemaWatchers.values()) watcher.close();
  schemaWatchers.clear();
  task.close();
  clearTimeout(restartTimeout);
}

function shutdown(signal = 'SIGTERM') {
  if (stopping) return;
  stopping = true;
  closeWatchers();
  exporting?.kill(signal);
  if (astro && astro.exitCode === null) astro.kill(signal);
  process.exitCode = signal === 'SIGINT' ? 130 : 143;
}

function startAstro() {
  if (stopping) return;
  astro = spawn(process.execPath, [astroBin, 'dev', ...process.argv.slice(2)], { cwd: root, stdio: 'inherit' });
  astro.on('error', (error) => console.error(`[lokf dev] Astro could not start: ${error.message}`));
  astro.on('close', (code, signal) => {
    clearTimeout(restartTimeout);
    astro = undefined;
    if (stopping) return;
    if (restartQueued) {
      restartQueued = false;
      startAstro();
      return;
    }
    stopping = true;
    closeWatchers();
    exporting?.kill('SIGTERM');
    process.exitCode = code === 0 ? 0 : (code ?? 1);
  });
}

function restartAstro() {
  if (stopping) return;
  if (!astro) { startAstro(); return; }
  if (restartQueued) return;
  restartQueued = true;
  astro.kill('SIGTERM');
  restartTimeout = setTimeout(() => {
    if (restartQueued && astro?.exitCode === null) astro.kill('SIGKILL');
  }, 5000);
  restartTimeout.unref();
}

function runExport() {
  return new Promise((resolve) => {
    console.log('[lokf dev] Knowledge changed; updating graph and search data…');
    exporting = spawn(process.execPath, [exportScript], { cwd: root, stdio: 'inherit' });
    exporting.on('error', (error) => console.error(`[lokf dev] Export could not start: ${error.message}`));
    exporting.on('close', (code) => {
      exporting = undefined;
      if (code !== 0) console.error('[lokf dev] Export failed; the dev server is still running. Fix the bundle and save again.');
      resolve(code === 0);
    });
  });
}

const task = createDebouncedTask(runExport, () => {
  if (!stopping) {
    console.log('[lokf dev] Projections updated; refreshing Astro routes…');
    restartAstro();
  }
});

function scheduleExport() {
  if (stopping) return;
  task.schedule();
}

function watchDirectory(directory, options, onChange) {
  try {
    const watcher = watch(directory, options, onChange);
    watcher.on('error', (error) => {
      console.error(`[lokf dev] Cannot watch ${directory}: ${error.message}`);
      console.error('[lokf dev] File watching is unavailable; stopping so generated data cannot silently become stale.');
      shutdown('SIGTERM');
      process.exitCode = 1;
    });
    return watcher;
  } catch (error) {
    console.error(`[lokf dev] Cannot watch ${directory}: ${error.message}`);
    return undefined;
  }
}

function refreshSchemaWatchers() {
  let files;
  try { files = configuredSchemaFiles(root); }
  catch (error) { console.error(`[lokf dev] Cannot read schema configuration: ${error.message}`); return; }
  schemaTargets = new Set(files.map((file) => resolve(file)));
  const directories = new Set(files.map(dirname));
  for (const [directory, watcher] of schemaWatchers) {
    if (!directories.has(directory)) { watcher.close(); schemaWatchers.delete(directory); }
  }
  for (const directory of directories) {
    if (schemaWatchers.has(directory)) continue;
    const watcher = watchDirectory(directory, {}, (_event, filename) => {
      if (filename && !schemaTargets.has(resolve(directory, String(filename)))) return;
      refreshSchemaWatchers();
      scheduleExport();
    });
    if (watcher) schemaWatchers.set(directory, watcher);
    else {
      console.error('[lokf dev] File watching is unavailable; stopping so generated data cannot silently become stale.');
      shutdown('SIGTERM');
      process.exitCode = 1;
      return;
    }
  }
}

process.once('SIGINT', () => shutdown('SIGINT'));
process.once('SIGTERM', () => shutdown('SIGTERM'));
const knowledgeWatcher = watchDirectory(join(root, 'knowledge'), { recursive: true }, scheduleExport);
if (knowledgeWatcher) otherWatchers.push(knowledgeWatcher);
const configWatcher = watchDirectory(root, {}, (_event, filename) => {
  if (String(filename) === 'lokf.views.yaml') {
    scheduleExport();
    return;
  }
  if (filename && String(filename) !== 'pyproject.toml') return;
  refreshSchemaWatchers();
  scheduleExport();
});
if (configWatcher) otherWatchers.push(configWatcher);
if (!knowledgeWatcher || !configWatcher) {
  console.error('[lokf dev] File watching is unavailable; stopping so generated data cannot silently become stale.');
  closeWatchers();
  process.exitCode = 1;
} else {
  refreshSchemaWatchers();
  startAstro();
}
