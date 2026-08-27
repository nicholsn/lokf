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
- **Python support tracks the LinkML ecosystem.** `requires-python` is `>=3.10`
  to match the linkml baseline (linkml-project-copier scaffolds `>=3.10`), so
  `lokf` installs into a hybrid linkml/lokf repo without forcing its floor up.
  Don't raise it without a reason the code actually needs; CI tests every
  version in the classifiers.
- **Reuse public vocabulary.** New types and fields should map to established
  ontology terms (schema.org, DCAT, PROV-O, SKOS, W3C ORG, …) rather than mint
  new ones — reuse is the whole point of LOKF.
- **Licensing (inbound = outbound).** Contributions to the toolkit (`src/`,
  `tests/`, the build tooling) are accepted under the Apache License 2.0;
  contributions to the specification and vocabulary (`SPEC.md`, `lokf.yaml`)
  under CC-BY-4.0. See the [License section of the README](README.md#license).
- **Responsible AI use.** LOKF is built with AI assistance. Please review the
  [AI Covenant](AI_COVENANT.md): you own everything you submit, and AI is never
  credited as a commit co-author.
