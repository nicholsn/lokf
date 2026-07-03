# Typed relationships

Where OKF has one untyped markdown link, LOKF provides a set of **named
relation fields**, each pinned to an RDF predicate. This is LOKF's core
upgrade: a link no longer just asserts *that* concept A relates to concept B —
it says *how*.

Values are Concept IRIs (or Concept IDs resolved against the bundle's
`base_iri`). All relation fields are optional and multivalued.

--8<-- "SPEC.md:rel-table"

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
