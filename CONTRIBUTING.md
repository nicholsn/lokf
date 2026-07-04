# Contributing to LOKF

Thanks for your interest in the Linked Open Knowledge Format! The full guide
lives in the documentation: <https://lokf.nolan-nichols.com/contributing/>.

A few essentials:

- **One source of truth.** LOKF is defined in `lokf.yaml`. The JSON-LD context,
  JSON Schema, SHACL shapes, and OWL ontology are all generated from it. Edit
  `lokf.yaml` (or the toolkit in `src/`, the docs in `web/`, or the tests), then
  run `just build` to regenerate every artifact and re-validate the reference
  bundle — never hand-edit a generated file.
- **Verify before you push.** `just build` and `just test` must pass, and any
  regenerated artifacts must be committed alongside the schema change.
- **Reuse public vocabulary.** New types and fields should map to established
  ontology terms (schema.org, DCAT, PROV-O, SKOS, W3C ORG, …) rather than mint
  new ones — reuse is the whole point of LOKF.
- **Responsible AI use.** LOKF is built with AI assistance. Please review the
  [AI Covenant](AI_COVENANT.md): you own everything you submit, and AI is never
  credited as a commit co-author.
