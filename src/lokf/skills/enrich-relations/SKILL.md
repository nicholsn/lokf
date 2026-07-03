---
name: enrich-relations
description: Turn plain markdown links in concept bodies into typed RDF relations using 'lokf propose', review the suggestions, then apply the good ones. Use to raise a bundle's link graph from prose to typed edges.
---

# Enrich relations from body links

## Purpose

Concept bodies contain markdown links between concepts (`[X](/path/x.md)`).
On their own those are just prose. `lokf propose` reads each link, infers the
best typed relation for it (from the schema vocabulary), and — with `--apply` —
writes it back into the source concept's frontmatter as a real predicate. This
turns an informal document into a typed knowledge graph.

## When to use

- After authoring or importing concepts whose bodies link to each other but
  whose frontmatter has few or no typed relations.
- To audit which body links are still untyped.

## How proposal works

For each markdown link in a concept body, `propose` resolves the target to a
concept IRI and picks a relation from the vocabulary, scoring a `confidence`
and recording a `rationale`. It only proposes relations valid for the source
concept's type (a `measures` proposal only on a `Metric`, etc.). It never
overwrites an existing frontmatter relation.

## Steps

1. **Dry-run first (no writes).** Review every proposal as a table:

   ```bash
   lokf propose examples/acme-knowledge
   ```

   Columns: `SOURCE`, `LINK`, `PREDICATE` (the CURIE it would write), `CONF`,
   `RATIONALE`. Read each row and sanity-check the predicate against the link's
   intent.

2. **Get machine-readable detail** when you need the target IRI or exact
   confidence to decide a threshold:

   ```bash
   lokf propose examples/acme-knowledge --json
   ```

3. **Set a confidence floor** to drop weak guesses. Inspect the distribution,
   then filter:

   ```bash
   lokf propose examples/acme-knowledge --min-confidence 0.6
   ```

4. **Apply the accepted proposals.** `--apply` writes each surviving proposal
   into the source concept's frontmatter. Combine with `--min-confidence` so
   only trusted edges land:

   ```bash
   lokf propose examples/acme-knowledge --min-confidence 0.6 --apply
   ```

   The command reports `wrote <relation> -> <target> in <file>` per edge and a
   final `applied N of M` line. `--json --apply` marks each row with
   `"applied": true|false`.

5. **Review the diff.** `--apply` edits frontmatter in place. Inspect what
   changed (e.g. `git diff`) before keeping it — confirm each new key is the
   relation you wanted and points at the right IRI.

6. **Verify the graph grew.** Re-render the RDF and confirm the new typed edges
   are present:

   ```bash
   lokf convert examples/acme-knowledge --format ttl | grep -E "prov:|dcterms:|schema:"
   ```

   Re-running `lokf propose` (dry) should now show fewer proposals, since
   applied links are no longer untyped.

## Cautions

- `--apply` mutates files. Always dry-run and pick a `--min-confidence` floor
  first; do not apply blind.
- Low-confidence proposals often default to a generic `relatedTo`/`references`.
  Prefer authoring a precise relation by hand (see the `author-concept` skill)
  over accepting a vague one.

## Done when

- The high-confidence proposals are applied and appear in the target files'
  frontmatter as the correct predicates.
- The remaining `lokf propose` output is only links you deliberately left
  untyped.
