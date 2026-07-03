---
title: Relation proposer
description: How lokf propose reads your prose links and suggests typed relations.
sidebar:
  order: 5
---

LOKF keeps [two layers in one file](/guide/relationships/): human-facing
markdown links in the body, and typed frontmatter fields that carry the
*kind* of link. In practice the prose layer always runs ahead — you write
`derived from [Orders](/datasets/orders.md)` long before you remember to add
a `derivedFrom:` field. `lokf propose` closes that gap: it reads the links
you already wrote and suggests the typed edges they imply.

```bash
uv run lokf propose mykb/                    # dry-run: table of proposals
uv run lokf propose mykb/ --json             # same list, machine-readable
uv run lokf propose mykb/ --min-confidence 0.5   # drop the weak ones
uv run lokf propose mykb/ --apply --min-confidence 0.5   # write frontmatter
uv run lokf propose mykb/ --json --apply     # apply + JSON report of what was written
```

Or from Python:

```python
import lokf
from lokf.propose import apply, propose

bundle = lokf.load_bundle("mykb")
proposals = propose(bundle)                  # optionally: vocab=..., concept=...
for p in proposals:
    print(p.source.concept_id, p.link.text, p.relation.curie,
          p.confidence, p.rationale)

applied = apply(proposals, min_confidence=0.5)   # round-trips the files
```

Each `Proposal` carries the **source** concept, the prose **link** (text,
target, and the sentence it sits in), the suggested **relation** (a
`Relation` from the [vocabulary](/reference/api/)), a **confidence**
score, and a **rationale** — the evidence, so you can judge the suggestion
without opening the file. See the proposer in action in the
[tutorial](/toolkit/tutorial/#4-propose-typed-relations).

## How the heuristics work

The proposer is deliberately simple, and every rule is inspectable — the
whole cue table is one importable tuple, `lokf.propose.CUE_TABLE`.

**Links first.** `extract_links()` collects the markdown links in a
concept's body — skipping images, fenced code blocks, and inline code — and
resolves each target against the bundle (root-relative like
`/datasets/orders.md`, file-relative, Concept ID, or full IRI all work).
Links that don't resolve to a concept *in the same bundle* produce no
proposal: the proposer only wires up your own graph.

**Cue phrases around the link.** For each link, the sentence around it is
matched against a priority-ordered table of cue patterns: wording like
*derived / computed / built from* points at `derivedFrom`
(`prov:wasDerivedFrom`), *depends / requires / needs* at `dependsOn`
(`dcterms:requires`), *measures / counts* at `measures`, *part of / within*
at `isPartOf`, *same as / alias* at `sameAs`, *attributed to / authored by*
at `wasAttributedTo`, *joins with / joined on* at `joinsWith`, and so on
across the [relation vocabulary](/guide/relationships/). The first row
that matches
(and whose relation the source's type may carry) wins. A link whose sentence
matches no cue at all falls back to a low-confidence `relatedTo` — the
weakest, most honest claim available.

**Type-aware domains.** A relation is only proposed where the schema says it
can live. Most relation slots are declared on `Concept` and apply to every
type, but `measures` is declared on `Metric` alone — so "measures" in a
Playbook's prose never yields a `measures` proposal. The domains come from
`lokf.vocabulary()` (`relation_slots["measures"].domains` →
`frozenset({'Metric'})`), not from a hardcoded list, so schema changes flow
through automatically.

**Skip what's already asserted.** An edge whose target IRI already appears
in the source's frontmatter — under a named relation field or a
`relations:` entry — is not proposed again. Re-running `lokf propose` on a
fully-typed bundle proposes nothing, which makes it safe to run repeatedly
as the prose evolves.

## Confidence

Confidence is a **heuristic score, not a probability**. Each cue carries a
base score reflecting how unambiguous its wording is (about 0.5 for vague
cues like *from*, up to 0.8 for *same as*); a cue sitting right next to the
link text earns an adjacency boost, and everything is capped at 0.95 —
nothing pattern-matched is ever certain. The no-cue `relatedTo` fallback
scores 0.25. The rationale states which case you're in:

```text
cue "derived" adjacent to link      # base + adjacency boost
cue "requires" in sentence          # base only
no cue phrase matched               # relatedTo fallback
```

`--min-confidence F` filters both the printed table and what `--apply`
writes; the Python `apply()` defaults to `0.0` (everything you pass it).
Pick a threshold by reading a dry run, not by treating the number as
calibrated — `0.5` keeps every cue-backed proposal and drops only the
`relatedTo` fallbacks.

## Dry-run, then apply

The default invocation **changes nothing** — it prints the proposal table
and exits. That's the intended workflow: read the rationale column, then
apply.

`--apply` (or `apply()` in Python, which returns the proposals it actually
wrote) writes accepted proposals into the concept files using a round-trip
YAML editor (ruamel), so comments, key order, and quoting in your
frontmatter survive the edit. Duplicates are never written, and the body is
untouched. Where a proposal lands depends on the relation:

- **Named slot** — relations with `is_slot=True` (`derivedFrom`,
  `dependsOn`, `measures`, …) become ordinary frontmatter fields, the
  target's IRI appended to the list.
- **Reified `relations:` entry** — predicates from the `RelationType`
  vocabulary that have no dedicated field (`joinsWith`, `wasAttributedTo`)
  are written as [reified relations](/guide/relationships/#custom-predicates-relations):

  ```yaml
  relations:
    - predicate: joinsWith
      target: https://acme.example/knowledge/tables/customers
  ```

The two forms do **not** project to identical RDF. A named slot becomes a
direct triple with its bound predicate
(`<metric> prov:wasDerivedFrom <dataset>`); a `relations:` entry projects as
a [reified statement](/guide/relationships/#custom-predicates-relations)
— an `rdf:Statement` node reached via `lokf:relations` that carries the
predicate and target — not a direct triple. The
[knowledge-graph page](/graph/) flattens reified entries back into
labeled edges for display, so both forms look the same in the picture, but
SPARQL over `bundle.graph()` sees the difference.

`--json` composes with `--apply`: the proposals are still written, and the
JSON output reports the outcome — every proposal that was written gains
`"applied": true`.

## Honest limits

:::caution[It's a heuristic, not an oracle]
The proposer does sentence-level pattern matching — no parser, no
embedding model, no LLM. That buys you speed, determinism, and offline
operation, and costs you nuance:

- **No grammar.** Negations and hedges ("is *not* derived from…") still
  trigger the cue, and the match doesn't know subject from object: in a
  dataset's page, "the WAU metric is computed from this dataset"
  proposes *dataset* `derivedFrom` *metric* — backwards.
- **One cue per sentence.** The highest-priority matching cue wins for
  *every* link in that sentence. "Derived from [Orders] and measures
  [conversion]" in a single sentence proposes `derivedFrom` for both
  links; split the sentence and each link gets its own cue.
- **Only what's linked.** Relationships stated without a markdown link,
  or linked to targets outside the bundle, are invisible to it.

Treat the output as a review queue, not a source of truth: dry-run
first, apply with a threshold, and read the `git diff` before you
commit. The typed frontmatter is a *claim about your domain* — the tool
drafts it; you assert it.
:::
