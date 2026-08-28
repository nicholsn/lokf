---
name: author-concept
description: Scaffold a new LOKF concept markdown file with the right type, frontmatter, and body, then inspect its RDF. Use when adding a metric, dataset, table, glossary term, service, or playbook to a knowledge bundle.
---

# Author a LOKF concept

## Purpose

A LOKF bundle is a directory of markdown files. Each concept is one file with
YAML frontmatter (the structured facts) and a markdown body (the prose, with
links to other concepts). This skill scaffolds a well-formed concept file and
verifies it by rendering the RDF the toolkit will produce from it.

## When to use

- Adding a new metric, dataset, table, glossary term, service, playbook,
  policy, document, or reference to an existing bundle.
- Turning a loose note or spec into a canonical, agent-readable concept.

Do not use this to bulk-import — author one concept per file.

## The concept types

Pick the `type` that fits (from `lokf vocab` classes):

| type          | Use for                                             |
|---------------|-----------------------------------------------------|
| `Metric`      | A measured quantity with a formula/unit.            |
| `Dataset`     | A collection of data (DCAT dataset).                |
| `Table`       | One tabular resource, usually with `fields`.        |
| `GlossaryTerm`| A defined term of art.                              |
| `Service`     | An API or running service.                          |
| `Playbook`    | A runbook / procedure (Diátaxis how-to).            |
| `Tutorial`    | A learning-oriented lesson (Diátaxis tutorial).     |
| `Explanation` | A background / conceptual discussion (Diátaxis).    |
| `Policy`      | A rule or governance statement.                     |
| `Document`    | A prose document.                                   |
| `Reference`   | An external citation-like reference.                |
| `AttestedComputation` | A sanctioned, immutable computation recipe (a `prov:Plan`). |

Run `lokf vocab` first if you are unsure which relation slots a type supports.

## Steps

1. **Choose a home directory and slug.** Put the file where its type lives in
   the bundle, e.g. `metrics/<slug>.md`, `datasets/<slug>.md`,
   `tables/<slug>.md`, `glossary/<slug>.md`. Use a kebab-case slug.

2. **Write the frontmatter.** Always include `type`, `id`, `title`,
   `description`, and provenance via `generated` (OKF v0.2 - `{ by, at }`,
   which supersedes the v0.1 `timestamp`). The `id` is the bundle `base_iri`
   (from the bundle's `index.md`) plus the file's relative path without `.md`.
   Example for a metric:

   ```yaml
   ---
   type: Metric
   id: https://acme.example/knowledge/metrics/signup-rate
   title: Signup Rate
   description: Share of visitors who complete signup in the session.
   unit: percent
   formula: COUNT(DISTINCT signups) / COUNT(DISTINCT sessions)
   tags: [growth, funnel]
   generated:
     by: human:jsmith@acme
     at: 2026-07-03T00:00:00Z
   status: stable
   ---
   ```

   Add type-appropriate fields: `Metric` takes `unit`/`formula`/`version`;
   `Table` takes a `fields:` list (`name`, `datatype`, `description`,
   `is_key`); `Service` takes `endpoint`/`http_method`/`documentation`;
   `GlossaryTerm` takes `definition`/`abbreviation`;
   `AttestedComputation` takes `runtime` (REQUIRED), `parameters`
   (each `{ name, type, required }`), `computation`, `executor`, `attester`.
   Any type may add the
   optional `genre` facet to tag the Diátaxis mode of its body — orthogonal
   to `type`; keep one mode per concept. Pick the value with the Diátaxis
   compass — two questions about the reader the body serves:

   | the reader is…          | …doing (action)   | …thinking (cognition) |
   |-------------------------|-------------------|-----------------------|
   | studying (acquisition)  | `genre: tutorial` | `genre: explanation`  |
   | working (application)   | `genre: how-to`   | `genre: reference`    |

   This table is not hardcoded lore: every `DiataxisMode` value in the
   schema carries its quadrant as `diataxis_action_cognition` /
   `diataxis_acquisition_application` annotations, so you can derive or
   verify it from the installed schema:

   ```bash
   python3 -c "import yaml, importlib.resources as r; \
   pv = yaml.safe_load((r.files('lokf')/'data'/'lokf.yaml').read_text())['enums']['DiataxisMode']['permissible_values']; \
   [print(k.ljust(12), v['annotations']) for k, v in pv.items()]"
   ```

   **Optional OKF v0.2 trust, provenance & lifecycle families** — add only what
   the source actually attests (their absence is meaningful, never an error):

   - `sources:` — list of materials the concept is based on, each `resource`
     (REQUIRED) plus optional `id`, `title`, `author`, `usage_count`,
     `last_modified` (supersedes the v0.1 `citations`).
   - `verified:` — list of `{ by, at }` verification events. Trust tiers derive
     from the actors: none ⇒ unverified, only non-human actors ⇒
     machine-confirmed, any `human:<id>` ⇒ human-reviewed.
   - `status:` — `draft` | `stable` | `deprecated` (absent ⇒ stable);
     `stale_after:` — a `YYYY-MM-DD` date after which the concept is stale.

   Actors (`generated.by`, `verified[].by`, `sources[].author`) are plain OKF §7
   strings — `<producer>/<version>`, `human:<id>`, `process:<id>` — never IRIs.

3. **Add typed relations as frontmatter keys** where the link is precise. These
   are the `slot`-flagged rows from `lokf vocab`, each ranged on other
   concepts by IRI:

   ```yaml
   measures:
     - https://acme.example/knowledge/glossary/active-user
   derivedFrom:
     - https://acme.example/knowledge/tables/user-events
   dependsOn:
     - https://acme.example/knowledge/glossary/active-user
   ```

   Common slots: `about`, `hasPart`/`isPartOf`, `dependsOn`, `derivedFrom`,
   `references`, `source`, `measures` (Metric), `definedBy`, `relatedTo`.

4. **Write the body** with headings and links to other concepts. Prose links
   like `[User Events](/tables/user-events.md)` are later upgraded to typed
   relations by the `enrich-relations` skill, so link generously:

   ```markdown
   # Definition

   **Signup Rate** counts distinct completed [signups](/glossary/active-user.md)
   over distinct sessions, computed from [User Events](/tables/user-events.md).

   # Notes

   - Excludes internal test accounts.
   ```

5. **Register it in `index.md`** so it is part of the bundle: add a bullet
   under the right heading, e.g.
   `* [Signup Rate](metrics/signup-rate.md) - Session signup conversion.`

6. **Inspect the RDF** to confirm the frontmatter parsed and the relations
   bound to the right predicates:

   ```bash
   lokf convert metrics/signup-rate.md --format ttl
   ```

   A single file resolves its IRIs via the enclosing bundle. Check that each
   frontmatter relation appears as the expected predicate (e.g. `derivedFrom`
   → `prov:wasDerivedFrom`, `measures` → `lokf:measures`).

7. **Validate the whole bundle** renders cleanly:

   ```bash
   lokf convert . --format ttl | tail -5
   ```

## Done when

- `lokf convert <file>` emits the concept with its `type`, `title`, and every
  intended typed relation as the correct predicate.
- The concept is listed in `index.md` and the whole-bundle convert succeeds.
