import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

// The toolkit is the authority for relation slots, CURIE expansion, domain
// vocabularies, and trust signals. Keep the site's graph and JSON-LD on that
// projection instead of maintaining a second parser in Astro.
const output = join(process.cwd(), 'src', 'generated');
mkdirSync(output, { recursive: true });
const toolkit = process.env.LOKF_TOOLKIT_SPEC || 'lokf==__LOKF_PACKAGE_VERSION__';
const local = process.env.LOKF_EXPORT_EXECUTABLE;
const command = local || 'uvx';
const args = local
  ? ['export', 'knowledge', '--out-dir', output]
  : ['--from', toolkit, 'lokf', 'export', 'knowledge', '--out-dir', output];
const result = spawnSync(command, args, { stdio: 'inherit' });
if (result.error) {
  console.error(`Could not run ${command}: ${result.error.message}. Install uv to build this site.`);
  process.exit(1);
}
if (result.status !== 0) process.exit(result.status || 1);
for (const name of ['graph.json', 'concepts.jsonld']) {
  if (!existsSync(join(output, name))) {
    console.error(`LOKF export did not produce ${name}`);
    process.exit(1);
  }
}
