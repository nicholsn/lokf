---
title: Contributing
description: How to contribute to LOKF — the build model, the single source of truth, and responsible AI use.
---

Contributions are welcome — a new concept type, a mapping fix, a documentation
improvement, or a bug report.

## The single source of truth

LOKF is defined **once** in
[`lokf.yaml`](https://github.com/nicholsn/lokf/blob/main/lokf.yaml), a
[LinkML](https://linkml.io) schema. The JSON-LD context, JSON Schema, SHACL
shapes, and OWL ontology are **generated** from it — never hand-edit them.

| File | Hand-edit? |
| ---- | :--------: |
| `lokf.yaml` | ✅ the schema |
| `SPEC.md`, `examples/…/*.md`, `web/…` | ✅ prose, examples, docs |
| `lokf.context.jsonld`, `lokf.schema.json`, `lokf.shacl.ttl`, `lokf.owl.ttl`, `examples/*.nt` | ⚙️ generated |

## Set up

```bash
git clone https://github.com/nicholsn/lokf
cd lokf
uv sync
```

## Make a change

1. Edit the source: `lokf.yaml` for the vocabulary, `src/lokf/` for the toolkit,
   `examples/` for the reference bundle, or `web/` for these docs.
2. When adding a **type** or **field**, map it to an established public ontology
   term (schema.org, DCAT, PROV-O, SKOS, W3C ORG, …) rather than minting a new
   term — reuse is the whole point of LOKF.
3. Regenerate and re-validate everything:

   ```bash
   just build     # regenerate artifacts + re-validate the reference bundle
   just test      # run the test suite
   ```

4. Commit the regenerated artifacts alongside your schema change, so the
   generated files never drift from `lokf.yaml`.

## Open a pull request

- `just build` and `just test` must pass.
- Regenerated artifacts are committed.
- Describe the change and the reasoning; if you touched the vocabulary, note
  which public terms you reused and why.

## Responsible AI use

LOKF is built openly with AI assistance, and we ask contributors to use these
tools responsibly. The essentials:

- **You own what you submit.** Regardless of what tools helped, you are the
  author — understand it, verify it, and be ready to defend it in review.
- **No AI co-authorship.** AI is never credited as a commit author or
  co-author; the human running the tool is solely responsible.
- **Disclose when it matters.** If you propose a change in code or schema you
  don't fully understand, say that AI suggested it so reviewers can weigh it
  appropriately.
- **Humans own discussion.** AI can help you draft, but must not autonomously
  post to issues or discussions.

The full policy is the
[AI Covenant](https://github.com/nicholsn/lokf/blob/main/AI_COVENANT.md),
adapted from the
[LinkML AI Covenant](https://github.com/linkml/linkml/blob/main/AI_COVENANT.md).
