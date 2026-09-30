---
title: Adapt a vocabulary
description: lokf adapt turns a published LinkML vocabulary into a file a domain schema imports beside lokf.yaml.
sidebar:
  order: 9
---

`lokf adapt` writes the copy of a published LinkML vocabulary that a
[domain schema](/guide/domain-schemas/) imports beside `lokf.yaml`. LinkML
merges imports into one namespace, so the copy may share no element name
with `lokf.yaml`, and its concepts must descend from `Concept` to join the
bundle's concept union. The command makes both true mechanically and
verifies the result.

```bash
lokf adapt biolink_model.yaml                       # -> biolink_model_lokf.yaml beside it
lokf adapt biolink_model.yaml -o schema/biolink_lokf.yaml --lokf schema/lokf.yaml
```

It needs only the core install. Validating or projecting a bundle *under*
the result needs `lokf[build]`, as `--schema` always does.

## What it changes

| Move | What | Why |
|---|---|---|
| fold imports | The vocabulary's own imports are merged into the one file; the copy imports `linkml:types` and `lokf`. | Imports resolve beside the file that names them; the copy must stand alone. |
| drop for LOKF's | The vocabulary's identifier slot and its `rdf:type` slot are deleted; what listed them now lists LOKF's `id` and `type`. | A class carries one identifier and one type designator, and LOKF's are those. |
| detach, demote | A slot that inherited from a dropped one loses its `is_a`; every other `designates_type` is stripped. | Biolink's `category: is_a: type` would otherwise inherit LOKF's designator; `type` is the one. |
| rename, IRIs kept | Every name `lokf.yaml` also defines, in any section, is renamed (`name` → `biolink_name`, `agent` → `BiolinkAgent`) with its `slot_uri`/`class_uri` pinned and the old name in `aliases`. | The name is local to the schema; the IRI carries the meaning. A type and a slot called `unit` is an overlap LinkML warns about. |
| re-root | Every rootless, non-mixin class that carries the identifier gets `is_a: Concept`; `tree_root` comes off. | One line puts the whole vocabulary in the concept union; `KnowledgeBundle` is the document root. |
| canonical names | Class names CamelCased, slot names underscored. | `type`, frontmatter keys and the JSON-LD context all use these forms; derived IRIs do not change. |
| verify | The copy is loaded beside `lokf.yaml` with SchemaView: every reference resolves, no name is shared, every re-rooted class reaches `Concept`. | Fails loudly rather than leaving a copy that validates nothing. |

The report names each move's targets, and the copy's schema-level `notes`
record them for anyone who opens the file.

## Options

| Option | Meaning |
|---|---|
| `-o, --output PATH` | Where to write the copy (default `<stem>_lokf.yaml` beside the input). |
| `--root CLASS` | A class to re-root on `Concept`, as the vocabulary names it; repeatable, replaces detection. A vocabulary with no identifier slot (gist's shape) detects no root; name one, or bridge its classes as the guide shows. |
| `--lokf PATH` | The `lokf.yaml` to share no name with (default: a local checkout, else the copy packaged with lokf). |
| `--prefix P` | Prefix for renamed elements (default: the vocabulary's `default_prefix`). |
| `--dry-run` | Print the report and verify the copy; write nothing. |
| `--check` | Write nothing; exit 1 unless `--output` already holds exactly this copy and it verifies. |

## In CI

The copy depends on two moving inputs, the vocabulary's release and
`lokf.yaml`. Keep it fresh with one step:

```bash
lokf adapt upstream/biolink_model.yaml -o schema/biolink_lokf.yaml --lokf schema/lokf.yaml --check
```

The lokf repository's `just biolink` is the worked case: it fetches
biolink-model at a pinned tag, checks its sha256, adapts it, and validates
and projects `examples/biolink/`.

## Limits

- A slot ranged over `uriorcurie` projects as an `xsd:anyURI` literal, a
  class-ranged one as an IRI; that is the vocabulary's choice, kept.
- An unranged slot takes the vocabulary's `default_range`, usually `string`,
  so an object property the vocabulary left unranged projects as a literal.
- Comments in the source YAML are not carried over; the copy is generated,
  not edited.
