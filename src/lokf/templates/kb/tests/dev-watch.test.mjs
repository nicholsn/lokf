import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { copyFileSync, mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { configuredSchemaFiles, createDebouncedTask } from '../scripts/dev-watch.mjs';

async function until(condition, message) {
  const deadline = Date.now() + 3000;
  while (!condition()) {
    if (Date.now() > deadline) throw new Error(message);
    await new Promise((resolve) => setTimeout(resolve, 5));
  }
}

test('watches the configured LinkML schema and its local imports', () => {
  const root = mkdtempSync(join(tmpdir(), 'lokf-dev-watch-'));
  try {
    mkdirSync(join(root, 'vocab'));
    writeFileSync(join(root, 'pyproject.toml'), '[tool.other]\nschema = "ignore.yaml"\n[tool.lokf]\nschema = "vocab/domain.yaml"\n');
    writeFileSync(join(root, 'vocab/domain.yaml'), 'imports:\n  - local\n  - linkml:types\n  - lokf\n');
    writeFileSync(join(root, 'vocab/local.yaml'), 'imports: [domain]\n');
    assert.deepEqual(new Set(configuredSchemaFiles(root)), new Set([
      join(root, 'vocab/domain.yaml'), join(root, 'vocab/local.yaml'), join(root, 'vocab/lokf.yaml'),
    ]));
    writeFileSync(join(root, 'pyproject.toml'), '[tool.lokf]\nschema = "vocab/replacement.yaml"\n');
    assert.deepEqual(configuredSchemaFiles(root), [join(root, 'vocab/replacement.yaml')]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('debounces save bursts and runs one follow-up export for edits during export', async () => {
  let runs = 0;
  let refreshes = 0;
  let releaseFirst;
  const task = createDebouncedTask(async () => {
    runs++;
    if (runs === 1) await new Promise((resolve) => { releaseFirst = resolve; });
    return true;
  }, () => { refreshes++; }, 10);
  task.schedule(); task.schedule(); task.schedule();
  await until(() => runs === 1, 'first export did not start');
  task.schedule(); task.schedule();
  releaseFirst();
  await until(() => refreshes === 1, 'refresh did not follow exports');
  assert.equal(runs, 2);
  task.close();
  task.schedule();
  await new Promise((resolve) => setTimeout(resolve, 30));
  assert.equal(runs, 2);
});

test('dev watcher debounces exports, refreshes Astro, and shuts down', async (t) => {
  const root = mkdtempSync(join(tmpdir(), 'lokf-dev-process-'));
  let child;
  try {
    mkdirSync(join(root, 'scripts'));
    mkdirSync(join(root, 'knowledge'));
    mkdirSync(join(root, 'node_modules/astro/bin'), { recursive: true });
    for (const name of ['dev.mjs', 'dev-watch.mjs']) {
      copyFileSync(new URL(`../scripts/${name}`, import.meta.url), join(root, 'scripts', name));
    }
    writeFileSync(join(root, 'scripts/export-graph.mjs'), "console.log('export-run');\n");
    writeFileSync(join(root, 'node_modules/astro/bin/astro.mjs'), "console.log('astro-start'); process.on('SIGTERM', () => process.exit(0)); setInterval(() => {}, 1000);\n");
    child = spawn(process.execPath, [join(root, 'scripts/dev.mjs')], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    child.stdout.on('data', (chunk) => { output += chunk; });
    child.stderr.on('data', (chunk) => { output += chunk; });
    const waitFor = async (phrase, count) => {
      const deadline = Date.now() + 8000;
      while (output.split(phrase).length - 1 < count) {
        if (Date.now() > deadline) throw new Error(`Timed out waiting for ${phrase} × ${count}: ${output}`);
        await new Promise((resolve) => setTimeout(resolve, 25));
      }
    };
    const deadline = Date.now() + 8000;
    while (!output.includes('astro-start') && !output.includes('File watching is unavailable')) {
      if (Date.now() > deadline) throw new Error(`Timed out starting dev watcher: ${output}`);
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
    if (output.includes('File watching is unavailable')) {
      const code = child.exitCode ?? await new Promise((resolve) => child.once('close', resolve));
      assert.equal(code, 1);
      t.skip('OS file watchers are unavailable in this environment');
      return;
    }
    writeFileSync(join(root, 'knowledge/concept.md'), 'first');
    writeFileSync(join(root, 'knowledge/concept.md'), 'second');
    await waitFor('export-run', 1);
    await waitFor('astro-start', 2);
    writeFileSync(join(root, 'domain.yaml'), 'name: first\n');
    writeFileSync(join(root, 'pyproject.toml'), '[tool.lokf]\nschema = "domain.yaml"\n');
    await waitFor('export-run', 2);
    await waitFor('astro-start', 3);
    writeFileSync(join(root, 'domain.yaml'), 'name: second\n');
    await waitFor('export-run', 3);
    await waitFor('astro-start', 4);
    child.kill('SIGTERM');
    const code = child.exitCode ?? await new Promise((resolve) => child.once('close', resolve));
    assert.equal(code, 143);
    assert.equal(output.split('export-run').length - 1, 3);
  } finally {
    child?.kill('SIGKILL');
    rmSync(root, { recursive: true, force: true });
  }
});
