# Type vocabulary

A concept's `type` SHOULD name one of the following classes. Each maps to a
public ontology term; consumers MUST tolerate unknown values by treating the
concept as a generic `lokf:Concept`.

--8<-- "SPEC.md:type-table"

## Type-specific fields

=== "Dataset / Table"

    - `fields` — a list of `Field` objects: `name`, `datatype`
      (`FieldType` → XSD), `description`, `unit`, `is_key`, `constraints`
    - `distribution` — `dcat:Distribution`

    ```yaml
    fields:
      - name: event_id
        datatype: string
        description: Globally unique event identifier.
        is_key: true
    ```

=== "Metric"

    - `unit` — `schema:unitText`
    - `formula` — `lokf:formula`
    - `measures` — `lokf:measures`, pointing at another Concept

    ```yaml
    unit: users
    formula: COUNT(DISTINCT user_id) over trailing 7 days
    measures:
      - https://acme.example/knowledge/glossary/active-user
    ```

=== "Service"

    - `endpoint` — `schema:url`
    - `http_method`
    - `documentation`

    ```yaml
    endpoint: https://api.acme.example/v2/analytics
    http_method: GET
    documentation: https://developers.acme.example/analytics
    ```

=== "GlossaryTerm"

    - `definition` — `skos:definition`
    - `abbreviation` — `schema:alternateName`

    ```yaml
    definition: A user who has performed at least one qualifying event.
    abbreviation: AU
    ```

!!! info "Authoritative definitions"

    The complete definitions — including the value objects `Field`,
    `Distribution`, `Relation`, `Citation`, and
    `Agent`/`Person`/`Organization` — live in
    [`lokf.yaml`](https://github.com/nicholsn/lokf/blob/main/lokf.yaml), the
    LinkML schema that is the single source of truth.
