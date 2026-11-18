import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, renameSync, rmSync } from 'node:fs';
import { join } from 'node:path';

// The toolkit is the authority for relation slots, CURIE expansion, domain
// vocabularies, and trust signals. Keep the site's graph and JSON-LD on that
// projection instead of maintaining a second parser in Astro.
const output = join(process.cwd(), 'src', 'generated');
mkdirSync(output, { recursive: true });
// The `build` extra brings LinkML, which reads a domain vocabulary declared in
// pyproject.toml (`[tool.lokf] schema`); the core install leaves it out.
const toolkit = process.env.LOKF_TOOLKIT_SPEC || 'lokf[build]==__LOKF_PACKAGE_VERSION__';
const local = process.env.LOKF_EXPORT_EXECUTABLE;
const command = local || 'uvx';
const manifest = 'lokf.views.yaml';
const hasViews = existsSync(manifest);
const stage = mkdtempSync(join(output, '.export-'));
try {
  const args = ['export', 'knowledge', '--out-dir', stage];
  if (hasViews) args.push('--views', manifest);
  if (!local) args.unshift('--from', toolkit, 'lokf');
  const result = spawnSync(command, args, { stdio: 'inherit' });
  if (result.error) throw new Error(`Could not run ${command}: ${result.error.message}`);
  if (result.status !== 0) {
    process.exitCode = result.status || 1;
  } else {
    const files = ['graph.json', 'concepts.jsonld', 'graph.nt', 'datasets.jsonld'];
    if (hasViews) files.push('views.json');
    for (const name of files) {
      if (!existsSync(join(stage, name))) throw new Error(`LOKF export did not produce ${name}`);
    }
    for (const name of files) renameSync(join(stage, name), join(output, name));
    if (!hasViews) rmSync(join(output, 'views.json'), { force: true });
  }
} finally {
  rmSync(stage, { recursive: true, force: true });
}
