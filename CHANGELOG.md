# Changelog

Notable changes to the `lokf` package and the LinkML schema it ships.

The **format version** (`lokf_version` in a bundle's `index.md`) and the
**package version** are separate tracks — see [SPEC §12](./SPEC.md#12-versioning).
This file tracks the package. Releases before 0.8.0 are described on the
[GitHub releases page](https://github.com/nicholsn/lokf/releases).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the 0.x caveat that a minor release may tighten validation.

## [Unreleased]

Format version is unchanged: **LOKF v0.2**. The schema now accepts what
OKF v0.2 writes.

### Changed

- **`supporting_text` is renamed `excerpt`** on `Source`, the name proposed
  for OKF in [knowledge-catalog#438]; its predicate is `lokf:excerpt`. A
  bundle written against 0.8.0 must rename the key.
- **`stale_after`, `usage_window.from`/`to` and `sources[].last_modified` are
  `datetime`**, as OKF defines every timestamp, so OKF's own
  `stale_after: 2026-09-23T00:00:00Z` now validates. A bare `YYYY-MM-DD` is
  read as that day at midnight UTC, so existing bundles need no change.

### Added

- `lokf vocab --all --json` and MCP `get_vocabulary(all=True)` report each
  slot's `pattern` and `required`, and each class's `slot_usage` including
  its `recommended` fields. Follow-up to [#61].
- `additionalType` (`schema:additionalType`) on `Concept`: the producer's
  `type` when it names no LOKF class.
- `revision` on `generated` and `verified[]` events (`lokf:revision`): the
  commit id, ETag or content digest of the resource the event checked,
  proposed for OKF in [knowledge-catalog#437]. Absent means unrecorded.

### Fixed

- The RDF projection dropped an unknown `type` (`BigQuery Table` left the
  node untyped; `Skill` minted an undeclared class). Both are now
  `lokf:Concept`, with the original string kept as `additionalType`, as
  SPEC §8 states. A class declared only in a domain schema (`--schema`)
  projects the same way, where it minted `lokf:<Class>` before.
- SPEC §8 names `lokf validate` as the strict producer-side check and
  `convert`/`query`/`serve` as the permissive OKF consumers; §9.1 states
  that the 0.8.0 patterns narrow nothing OKF defines.

## [0.8.0] — 2026-09-16

Format version is unchanged: **LOKF v0.2**, realized by schema 0.8.0.

### Changed — validation is stricter

The schema now carries `pattern` constraints, which the generated
`lokf.schema.json` enforces. **A bundle that validated under 0.7.0 can fail
under 0.8.0** ([#69]):

| Field | Constraint |
|---|---|
| `base_iri` | absolute `http(s)`, ending in `/` or `#` |
| `generated.by`, `verified[].by` | `human:<id>`, `process:<id>`, or `<producer>/<version>` |
| `sources[].author` | any `<prefix>:<id>` or `<producer>/<version>` (looser than `by`) |
| `email` | an address shape |

`http_method` is now the closed `HttpMethod` enum — `GET`, `POST`, `PUT`,
`PATCH`, `DELETE`, `HEAD`, `OPTIONS`, uppercase. A lowercase or non-listed
verb no longer validates.

These are documented in [SPEC §9.1](./SPEC.md#91-field-constraints). If a
bundle trips one, the fix is normally in the bundle; a project that needs
different rules can validate against its own schema that `imports: [lokf]`
via `lokf validate --schema`.

### Added

- `lokf validate --check-refs` — referential integrity for typed relations. A
  relation target naming the bundle's own namespace must resolve to a concept
  in it, so a stale or invented IRI is caught instead of passing as a valid
  string. Scoped to the bundle's namespace, so external resources in
  `definedBy`/`source` are not errors. Opt-in. ([#79], closes [#64])
- `lokf vocab --all` and MCP `get_vocabulary(all=True)` — the full schema
  reference (classes, slots, value enums with descriptions), not just the
  typed-relation table. ([#74])
- `supporting_text` on `Source` (`linkml:excerpt`) — the exact quoted passage
  from a source, so a claim stays re-verifiable. ([#67])
- `recommended:` on `Metric` (`unit`, `formula`, `measures`), `GlossaryTerm`
  (`definition`) and `Service` (`endpoint`, `documentation`). Advisory schema
  metadata; no generator emits it yet. ([#69])

### Fixed

- The MCP server reported an empty `serverInfo.version`, so clients could not
  tell which `lokf` they were talking to. ([#80])
- `lokf validate` reported a bare "is not valid under any of the given
  schemas" for an undeclared frontmatter key. It now names the offending key
  and class, and an unrecognized `type:` points at `--schema` and the
  `imports: [lokf]` extension path. ([#77], closes [#73])
- `lokf new` appended a second terminator to a `#`-terminated `base_iri`,
  minting ids like `…#/thing`. ([#69])

### Internal

- `lokf-build` is byte-reproducible. Re-running the generators over an
  unmodified `lokf.yaml` used to rewrite ~2,575 lines; it now produces none.
  Wall-clock stamps dropped, the `CREATE INDEX` block sorted, set-valued
  `rdf:List`s sorted and blank nodes relabelled by content hash. A
  `generated-fresh` CI job now fails if the committed artifacts do not match
  a fresh build. ([#78])
- Slot descriptions capped at 400 characters, with rationale moved into
  `comments:`. ([#75])
- `base_iri` documented as an identifier namespace rather than a hyperlink —
  it need not resolve. ([#76])
- Docs guarded against drift: the package version quoted in prose, the
  existence of every documented `lokf` command, and root-doc links are now
  asserted by tests. ([#80])
- Dependency updates. ([#62], [#63], [#70], [#71], [#72])

[knowledge-catalog#437]: https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/437
[knowledge-catalog#438]: https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/438
[#61]: https://github.com/nicholsn/lokf/issues/61
[#62]: https://github.com/nicholsn/lokf/pull/62
[#63]: https://github.com/nicholsn/lokf/pull/63
[#64]: https://github.com/nicholsn/lokf/issues/64
[#67]: https://github.com/nicholsn/lokf/pull/67
[#69]: https://github.com/nicholsn/lokf/pull/69
[#70]: https://github.com/nicholsn/lokf/pull/70
[#71]: https://github.com/nicholsn/lokf/pull/71
[#72]: https://github.com/nicholsn/lokf/pull/72
[#73]: https://github.com/nicholsn/lokf/issues/73
[#74]: https://github.com/nicholsn/lokf/pull/74
[#75]: https://github.com/nicholsn/lokf/pull/75
[#76]: https://github.com/nicholsn/lokf/pull/76
[#77]: https://github.com/nicholsn/lokf/pull/77
[#78]: https://github.com/nicholsn/lokf/pull/78
[#79]: https://github.com/nicholsn/lokf/pull/79
[#80]: https://github.com/nicholsn/lokf/pull/80
[0.8.0]: https://github.com/nicholsn/lokf/compare/v0.7.0...v0.8.0
