# Typed relationships

Where OKF has one untyped markdown link, LOKF provides a set of **named
relation fields**, each pinned to an RDF predicate. This is LOKF's core
upgrade: a link no longer just asserts *that* concept A relates to concept B —
it says *how*.

Values are Concept IRIs (or Concept IDs resolved against the bundle's
`base_iri`). All relation fields are optional and multivalued.

| Field         | RDF predicate (`slot_uri`)   | Meaning                                   |
|---------------|------------------------------|-------------------------------------------|
| `isPartOf`    | `dcterms:isPartOf`           | This concept is part of the target.       |
| `hasPart`     | `schema:hasPart`             | The target is part of this concept.       |
| `references`  | `dcterms:references`         | This concept refers to the target.        |
| `dependsOn`   | `dcterms:requires`           | This concept depends on the target.       |
| `derivedFrom` | `prov:wasDerivedFrom`        | Provenance: derived from the target.      |
| `about`       | `schema:about`               | Subject matter of this concept.           |
| `sameAs`      | `schema:sameAs`              | Same entity as the target (close `owl:sameAs`). |
| `relatedTo`   | `dcterms:relation`           | Generic association.                      |
| `definedBy`   | `rdfs:isDefinedBy`           | A resource that formally defines this.    |
| `source`      | `dcterms:source`             | Sourced/derived from the target.          |

## Custom predicates: `relations`

For predicates outside this set, use the generic **`relations`** field — a
list of reified `Relation` objects, each a `predicate` (drawn from the
`RelationType` vocabulary, e.g. `joinsWith`, `wasAttributedTo`) plus a
`target`:

```yaml
relations:
  - predicate: joinsWith
    target: https://acme.example/knowledge/tables/customers
    relation_label: "join on customer_id"
```

## Body links still work

!!! note "Two layers, one file"

    Human-facing markdown links in the body (OKF §5) remain valid and
    encouraged; the typed frontmatter fields are the machine-readable layer
    that carries the *kind* of link.

For example, the reference bundle's WAU metric links to its glossary term in
prose *and* declares the machine edge:

```yaml
dependsOn:
  - https://acme.example/knowledge/glossary/active-user   # dcterms:requires
```
