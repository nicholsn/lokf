// Keep the Astro docs DRY: derive shared content from the repo's canonical
// sources (README.md, SPEC.md, the example bundle) at build time, so nothing
// is authored twice. Run before `astro build`/`dev` (see package.json).
//
//   - README/SPEC `<!-- --8<-- [start:NAME] -->…[end:NAME]` sections become
//     importable partials under src/generated/.
//   - Two example files become fenced-code partials.
//   - SPEC.md becomes the Specification page (its H1 dropped; Starlight adds
//     the title).
//
// All outputs are generated (gitignored); edit the sources, not these.
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "..", "..");
const GEN = resolve(HERE, "..", "src", "generated");
const DOCS = resolve(HERE, "..", "src", "content", "docs");

const read = (rel) => readFileSync(resolve(REPO, rel), "utf8");

/** Extract every `[start:NAME]…[end:NAME]` marker section from a file. */
function sections(text) {
  const re =
    /<!-- --8<-- \[start:([a-z-]+)\] -->\n([\s\S]*?)\n<!-- --8<-- \[end:\1\] -->/g;
  const out = {};
  for (const m of text.matchAll(re)) out[m[1]] = m[2];
  return out;
}

function writePartial(name, body) {
  writeFileSync(resolve(GEN, `${name}.md`), body.trimEnd() + "\n");
}

function fenced(lang, body) {
  return "```" + lang + "\n" + body.replace(/\n+$/, "") + "\n```\n";
}

mkdirSync(GEN, { recursive: true });

// -- shared marker sections from README + SPEC -----------------------------
const readme = sections(read("README.md"));
const spec = sections(read("SPEC.md"));
for (const [name, body] of Object.entries({ ...readme, ...spec })) {
  writePartial(name, body);
}

// -- example-file embeds (shown as code blocks) ----------------------------
writePartial(
  "metric-source",
  fenced(
    'markdown title="metrics/weekly-active-users.md"',
    read("examples/acme-knowledge/metrics/weekly-active-users.md"),
  ),
);
writePartial(
  "metric-nt",
  // N-Triples is a subset of Turtle, so the `turtle` grammar highlights it.
  fenced(
    'turtle title="examples/weekly-active-users.nt"',
    read("examples/weekly-active-users.nt"),
  ),
);

// -- the Specification page, generated from SPEC.md ------------------------
const specBody = read("SPEC.md")
  .replace(/^#\s.*\n+/, "") // drop the leading H1 (Starlight adds the title)
  .replace(/<!-- --8<-- \[(?:start|end):[a-z-]+\] -->\n?/g, ""); // drop markers
writeFileSync(
  resolve(DOCS, "specification.md"),
  `---
title: Specification
description: The LOKF v0.1 specification — motivation, conformance, and the full field tables.
---

${specBody}`,
);

// -- Dataset JSON-LD for build-time <head> injection (SEO) -----------------
// `lokf export` (sync:data, run first) wrote datasets.jsonld to public/; make
// it importable so the Head component can embed it in the rendered HTML.
const datasets = resolve(HERE, "..", "public", "datasets.jsonld");
if (existsSync(datasets)) {
  copyFileSync(datasets, resolve(GEN, "datasets.json"));
}

const names = [
  ...Object.keys(readme),
  ...Object.keys(spec),
  "metric-source",
  "metric-nt",
];
console.log(`sync-content: ${names.length} partials + specification.md + datasets.json`);
