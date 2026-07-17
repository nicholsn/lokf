---
name: lokf-librarian
description: 'Scrape the host repository this skill sits inside and build/maintain the `lokf/` knowledge bundle as a sidecar, compliant with the Linked Open Knowledge Format (LOKF) schema (a semantic profile of OKF). Use when: creating or updating concept files under lokf/knowledge/; adding typed relationships (isPartOf/dependsOn/derivedFrom/about/references/...); choosing a LOKF class (Service/Metric/Dataset/Table/Policy/Playbook/GlossaryTerm/...); setting base_iri/context/id so frontmatter expands to JSON-LD/RDF; validating the bundle with JSON Schema and SHACL via the lokf toolkit; converting/serving the bundle as a graph; auditing lokf/ for correctness, gaps, or bugs; preparing a LOKF change for human maintainer review; or running the scheduled LLM-librarian task that keeps lokf/ accurate (Karpathy rule).'
---

# LOKF Librarian

Maintain `lokf/` - the host repository's knowledge captured as a [**Linked Open Knowledge Format (LOKF)**](https://lokf.nolan-nichols.com/specification/) bundle. LOKF is a **semantic profile of OKF**: the same directory of Markdown + YAML frontmatter, but every field, type, and relationship is bound to a public vocabulary (schema.org / DCAT / PROV-O), so the bundle expands losslessly to JSON/JSON-LD and RDF and is queryable with SPARQL. This skill covers the full lifecycle: **scrape -> build/maintain -> audit -> hand off for review -> keep fresh on a schedule.**

> Scope: this skill owns **only** `lokf/`. A plain, tooling-free sibling `okf/`
> would be owned by the separate **okf-librarian** skill. Every LOKF bundle is also a
> valid OKF bundle - keep the two consistent, but edit each through its own skill.
> If `lokf/` doesn't exist yet, bootstrap its directory and tooling with the
> **lokf-scaffolding** skill first; this skill assumes both are already in place.

## Layout

```
lokf/
|-- knowledge/            # the bundle - one Markdown file per concept
|   |-- index.md          # bundle metadata (base_iri, context, versions) + TOC
|   |-- log.md            # change history (reserved name)
|   |-- services/  datasets/  references/
|   |-- playbooks/  glossary/  org/
|-- pyproject.toml        # declares the `lokf` toolkit dependency
|-- justfile              # lokf-install / lokf-validate / lokf-convert / lokf-serve
|-- scripts/              # (optional) knowledge-librarian.sh, the scheduled-agent wrapper (step 4)
```

The LOKF **format** is defined once in LinkML (`lokf.yaml`); the JSON Schema, JSON-LD context, SHACL shapes, and OWL ontology are **generated** from it and MUST NOT be hand-edited. This repo's `lokf/` is a *consumer* of that published schema - you author concepts, the toolkit validates and projects them.

> **Bootstrap:** if the layout above is missing or incomplete, run the
> **lokf-scaffolding** skill first - it creates `knowledge/index.md` with the
> semantic header (Rule 2), `knowledge/log.md`, the domain directories, plus
> `pyproject.toml` and the `justfile` that `just lokf-validate` needs.

## Golden Rules (LOKF v0.1)

1. **It's [OKF first](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).** One concept per file, path = concept ID, `type` is the only strictly required field, permissive consumption. Everything plain OKF requires (enforced by the okf-librarian skill, where the repo maintains an `okf/` sibling) still holds here.
2. **The bundle-root `index.md` carries the semantic header.** It declares the keys that lift the whole bundle into RDF (values shown are illustrative - the real ones are minted at scaffolding time):
   ```yaml
   lokf_version: "0.1"
   okf_version: "0.1"
   base_iri: https://acme.example/knowledge/
   context: https://w3id.org/lokf/context.jsonld
   title: Acme Platform Knowledge Bundle
   description: ...
   license: https://creativecommons.org/licenses/by/4.0/
   publisher: { type: Organization, id: https://acme.example/knowledge/org/platform-team, name: Acme Platform Team }
   ```
   `base_iri` + concept ID mints each concept's IRI (`@id`); `context` maps frontmatter keys to IRIs. Do not remove these or the bundle degrades to plain OKF.
3. **Use a class from the LOKF type vocabulary** (consumers tolerate unknowns as `lokf:Concept`): `Dataset`, `Table`, `Metric`, `Service`, `Playbook`, `Policy`, `GlossaryTerm`, `Reference`, `Document`, `Person`, `Organization`. Type-specific fields: `Table/Dataset` -> `fields`, `distribution`; `Metric` -> `unit`,`formula`, `measures`; `Service` -> `endpoint`, `http_method`, `documentation`; `GlossaryTerm` -> `definition`, `abbreviation`.
4. **Prefer typed relationships over bare links** - this is LOKF's core upgrade. Each maps to a fixed RDF predicate; values are Concept IRIs (or IDs resolved against `base_iri`), all optional and multivalued:

   | field | predicate | meaning |
   |-------|-----------|---------|
   | `isPartOf` | `dcterms:isPartOf` | this is part of the target |
   | `hasPart` | `schema:hasPart` | the target is part of this |
   | `references` | `dcterms:references` | this refers to the target |
   | `dependsOn` | `dcterms:requires` | this depends on the target |
   | `derivedFrom` | `prov:wasDerivedFrom` | provenance |
   | `about` | `schema:about` | subject matter |
   | `sameAs` | `schema:sameAs` | same entity |
   | `relatedTo` | `dcterms:relation` | generic association |
   | `definedBy` | `rdfs:isDefinedBy` | formally defined by |
   | `source` | `dcterms:source` | sourced from the target |

   For predicates outside this set, use the generic `relations` list of reified objects (`predicate` from the `RelationType` vocab, e.g. `joinsWith`, plus `target`). Human-facing Markdown links in the body remain valid and encouraged alongside the typed fields.
5. **Core fields map to ontology terms:** `title`->`schema:name`, `description`->`schema:description`, `resource`->`schema:url`,`tags`->`schema:keywords`, `timestamp`->`schema:dateModified`, plus optional `id`, `created`, `version`, `license`, `author`, `citations`. Two JSON-LD aliases let plain OKF frontmatter behave as Linked Data: `type` -> `@type` (rdf:type, the concept's class) and `id` -> `@id` (the subject IRI).
6. **Stay permissive.** Missing optional fields, unknown `type`, unknown keys, and broken cross-links MUST NOT cause rejection.

## 1. Scrape & build

Derive concepts from the host repository (or, as an edge case, any directory tree) - never invent facts. **The bundle itself is the scrape map**: every concept records where it came from (`resource`, `derivedFrom`, `source`), and the map of knowledge sources is itself a reviewed concept. Steady-state runs are deterministic re-verification against that recorded provenance, not fresh discovery.

### Bootstrap discovery - first run, or whenever the bundle has no real concepts

Sweep the repository with generic heuristics and map what you find to LOKF classes:

| Look at | Typical finds | Class |
|---------|---------------|-------|
| manifests (`package.json`, `pyproject.toml`, `go.mod`, ...), entry points, `Dockerfile`/compose files, CI config | APIs, CLIs, UIs, workers, databases | `Service` |
| data and schema files (CSV/YAML/JSON/SQL), fixtures, migrations | datasets, tables | `Dataset` / `Table` (use `fields`, `distribution`) |
| external standards, specs, and ontologies the code or data encodes | upstream authorities | `Reference` (wire `derivedFrom` from the encoding `Dataset`) |
| README and docs install/run/operate guides | how-tos | `Playbook` |
| domain terms recurring across code, data, and docs | vocabulary | `GlossaryTerm` |
| ownership files (`CODEOWNERS`, manifest authors), publishers named inside data files | owners, publishers | `Organization` / `Person` - add only when another concept links to them (e.g. `Reference` -> `Organization` via `source`) |

Record the resulting map as a concept: **`playbooks/knowledge-sources.md`** (`type: Playbook`), listing each knowledge source (repo path or external URL), the class(es) it yields, and how to re-check it. Discovery output thereby lives in the bundle, versioned and human-reviewed like every other concept - not in this skill.

### Steady-state refresh - every later run

1. **Re-verify provenance.** For each existing concept, follow its `resource`/`derivedFrom`/`source` back to the origin: does it still exist, are the facts still true, do relations still point the right way? Fix drift.
2. **Re-walk `playbooks/knowledge-sources.md`.** Sources listed there may have grown new assets since the last run.
3. **Sweep for orphans.** Repository files or directories that no concept and no source-map entry accounts for are gap candidates: add a concept, extend the source map, or consciously leave them out.
4. **Update the source map** whenever the repository's knowledge geography changes - it must stay as accurate as the concepts it feeds.

Then add the semantic layer: pick the right class, set `id`, and wire typed relationships instead of guessing. Give every concept derived from the repository a `resource` (and `derivedFrom`/`source` where provenance is external) so the next refresh can re-verify it. The example below is **fictional** - an imaginary "Acme Platform" repo, not a concept of any real project; never copy its values, mint IRIs from the bundle's real `base_iri`:

```markdown
---
type: Service
id: https://acme.example/knowledge/services/orders-api
title: Orders API
description: REST API serving order data to the CLI and web UI.
endpoint: https://api.acme.example/orders
resource: https://github.com/acme/platform/tree/main/services/orders
dependsOn:
  - https://acme.example/knowledge/datasets/orders-db
---

# Overview

The **Orders API** generates its endpoints from `services/orders/openapi.yaml` and serves the order data consumed by the CLI and web UI...
```

Update the nearest `index.md` (bullet + `description`) and prepend a dated entry to `log.md` (newest first, ISO `YYYY-MM-DD`).

## 2. Audit (correctness, gaps, bugs)

Use the toolkit - it gives you two independent, generated validators. From
`lokf/`:

```bash
just lokf-install          # uv sync  (first time)
just lokf-validate         # JSON Schema on frontmatter + assembled bundle
just lokf-convert          # project to Turtle/RDF; eyeball the triples
just lokf-serve            # SPARQL endpoint + live graph explorer (optional)
```

`lokf validate` catches frontmatter/bundle-shape errors; the generated SHACL shapes catch cardinality/datatype/range violations on the projected graph. Beyond mechanical validity, audit for:

- **Correctness** - class matches the asset; typed relations point the right way (`isPartOf` vs `hasPart`, `dependsOn` vs `derivedFrom`); `id`/`base_iri` mint the expected IRIs; `endpoint`/`resource` still resolve.
- **Gaps** - new code/data files with no concept; untyped body links that should be typed relations; missing `id` on concepts other bundles link to; classes left as generic `lokf:Concept` that have a proper vocabulary type.
- **Bugs** - malformed YAML, invalid enum/datatype (fails JSON Schema or SHACL), relation targets that resolve to nothing *intended*, missing `base_iri`/`context` in the root `index.md`, drift from the corresponding `okf/` concept (when the repo maintains a plain `okf/` sibling).

Report findings as a checklist; fix mechanical issues directly and re-run `just lokf-validate`.

## 3. Hand off for human maintainer review

Open a PR scoped to `lokf/` with a summary, the `lokf validate` (and, when relevant, SHACL/convert) output, and citations for every claim whose authority lives outside the repository - the standards, ontologies, and upstream systems the bundle's `Reference` concepts point at. A human maintainer verifies against the canonical source and approves before merge. Once `.github/workflows/knowledge-validate.yaml` exists (see section 4), it runs `uv run lokf validate knowledge` on every `lokf/**` PR as the automated gate; until then, paste the local `just lokf-validate` output into the PR.

## 4. Scheduled librarian task (Karpathy rule)

Keep the graph continuously accurate rather than rewriting it in bursts. Three
pieces automate this rebuild loop - the **lokf-scaffolding** skill's Step 5
scaffolds them; this section is their operating manual:

**`.github/workflows/knowledge-librarian.yaml`** - the rebuild workflow. Runs weekly (Mondays 05:00 UTC) and on demand (`workflow_dispatch`). Each run: checks out full history -> sets up `uv` -> installs the `lokf` sidecar -> runs the agent -> validates -> diffs `lokf/knowledge/` (only the bundle, so tool artifacts never trigger a PR) -> if anything changed, commits to a fresh `knowledge-librarian/<date>-<run_id>` branch and opens a review PR via `github-script`. Guardrails: it holds only `contents: write` + `pull-requests: write`, never pushes to the default branch, never auto-merges, and opens no PR when nothing changed.

**`lokf/scripts/knowledge-librarian.sh`** - the agent wrapper the workflow invokes. Point the `KNOWLEDGE_LIBRARIAN_CMD` repository variable at `bash lokf/scripts/knowledge-librarian.sh` and set `AGENT_CLI` to your non-interactive agent command. The script selects the lokf-librarian skill, builds a prompt telling the agent to follow it and re-scrape the repo, then calls `AGENT_CLI`. Its contract: it edits **only** files under `lokf/knowledge/` and performs no git/PR operations - the workflow owns branch/commit/PR. If `KNOWLEDGE_LIBRARIAN_CMD` is unset, the workflow's agent step is a safe no-op, so the workflow is harmless until you wire the agent up.

**`.github/workflows/knowledge-validate.yaml`** - the gate. Its `validate` job runs `uv run lokf validate knowledge` on the librarian PR (and on every `lokf/**` PR and its own weekly schedule); keep it green. The bar: the projected RDF graph should always describe the repository as it is *today*.
