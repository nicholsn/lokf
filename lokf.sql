-- # Class: KnowledgeBundle Description: A self-contained, hierarchical collection of concept documents — the unit of distribution (a git repo, tarball, or subdirectory). Maps to a DCAT Catalog. When a whole bundle is serialized as a single JSON-LD document, this class is the tree root; individual concept files validate against Concept (or a subclass).
--     * Slot: id
--     * Slot: lokf_version Description: The LOKF version the bundle targets (e.g. "0.1").
--     * Slot: okf_version Description: The OKF version the bundle remains compatible with (e.g. "0.1").
--     * Slot: base_iri Description: The base IRI against which Concept IDs are resolved to produce each concept's stable `id`.
--     * Slot: context Description: The URL of the JSON-LD @context to attach to this bundle's concepts to interpret their frontmatter as Linked Data.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: publisher_id Description: The agent responsible for making the bundle available.
-- # Abstract Class: Concept Description: A single unit of knowledge within a bundle, represented as one markdown document. The abstract base of every LOKF type. Its own IRI (`id`) is the RDF subject; the markdown body and typed relations become triples about that subject.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
--     * Slot: KnowledgeBundle_id Description: Autocreated FK slot
-- # Class: Dataset Description: A collection of data, published or curated for access and reuse.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
-- # Class: Table Description: A structured, tabular dataset (e.g. a warehouse table or view) whose columns are described by Field objects under `fields`.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
-- # Class: Metric Description: A precisely defined, measurable quantity — the canonical definition of a business or operational metric.
--     * Slot: unit Description: The unit of measurement (e.g. USD, seconds, count).
--     * Slot: formula Description: The calculation or definition expression for a metric.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
-- # Class: Service Description: A callable service or API endpoint.
--     * Slot: endpoint Description: The base URL or invocation endpoint of a service.
--     * Slot: http_method Description: The HTTP method used to invoke the service, if applicable.
--     * Slot: documentation Description: A link to the service's documentation.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
-- # Class: Playbook Description: A procedure or runbook — an ordered set of steps to accomplish a task or respond to an event.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
-- # Class: Policy Description: A governance, compliance, or operational policy document.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
-- # Class: GlossaryTerm Description: A defined term in a controlled vocabulary or glossary. Maps to schema:DefinedTerm and skos:Concept.
--     * Slot: definition Description: The formal definition of a term.
--     * Slot: abbreviation Description: A short form or acronym for a term.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
-- # Class: Reference Description: A concept that mirrors an external source (a page, paper, or document) as a first-class citizen of the bundle so it can be cited and linked.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
-- # Class: Document Description: A general knowledge document that does not fit a more specific type.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
-- # Class: Role Description: A role an agent holds within an organization over a period of time — a job, appointment, or position. Reifies the agent–organization link so it can carry a title (roleName) and a start/end interval, following the schema.org Role and W3C ORG Membership patterns.
--     * Slot: roleName Description: The name/title of the role held (e.g. a job title).
--     * Slot: startDate Description: The date the role began (ISO 8601 date or year).
--     * Slot: endDate Description: The date the role ended; omit for a role still held.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
-- # Abstract Class: Agent Description: A person or organization responsible for a concept.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: name Description: A name.
--     * Slot: email Description: Contact email address.
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: Organization_id Description: Autocreated FK slot
-- # Class: Person Description: An individual person. Usable both as an inline Agent value (author, publisher) and as a standalone Concept document with a body and typed relations.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
--     * Slot: name Description: A name.
--     * Slot: email Description: Contact email address.
-- # Class: Organization Description: An organization, team, or group. Usable both as an inline Agent value (publisher) and as a standalone Concept document with a body and typed relations.
--     * Slot: id Description: The concept's stable IRI. By convention it is the bundle base IRI joined with the Concept ID (the file path within the bundle, minus the `.md` suffix). Becomes the JSON-LD @id / RDF subject.
--     * Slot: type Description: The concept's type. OKF's single required field. In LOKF the value SHOULD name a LOKF class (e.g. Metric, Dataset, Table, Playbook, GlossaryTerm); it designates the JSON-LD @type / rdf:type. Consumers MUST tolerate unknown values by treating the concept as a generic lokf:Concept.
--     * Slot: title Description: Human-readable display name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: resource Description: A URI that uniquely identifies the underlying real-world asset the concept describes (a table console URL, an API base URL, etc.). Absent for purely abstract concepts.
--     * Slot: timestamp Description: ISO 8601 datetime of the last meaningful change.
--     * Slot: created Description: ISO 8601 datetime the concept was created.
--     * Slot: version Description: A version string for the concept's content.
--     * Slot: license Description: The license under which the concept or bundle is offered.
--     * Slot: body Description: The markdown body of the concept document (everything after the frontmatter). Mapped to schema:text; carried as a field only in the JSON-LD / JSON serialization, not duplicated in the frontmatter.
--     * Slot: name Description: A name.
--     * Slot: email Description: Contact email address.
-- # Class: Field Description: A single column / property within a Table or Dataset schema. Maps to schema:PropertyValue.
--     * Slot: id
--     * Slot: name Description: A name.
--     * Slot: datatype Description: The data type of a field.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: unit Description: The unit of measurement (e.g. USD, seconds, count).
--     * Slot: is_key Description: Whether the field is (part of) the primary key.
--     * Slot: constraints Description: Free-text or expression describing constraints on a field.
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: Table_id Description: Autocreated FK slot
-- # Class: Distribution Description: A specific accessible form of a Dataset (a file, feed, or endpoint). Maps to dcat:Distribution.
--     * Slot: id
--     * Slot: name Description: A name.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: access_url Description: A URL that gives access to a distribution.
--     * Slot: media_type Description: The media (MIME) type of a distribution.
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: Table_id Description: Autocreated FK slot
-- # Class: Relation Description: A typed, reified relationship from the containing concept to a target, used when a predicate is not covered by one of the named relation slots. Modeled as an rdf:Statement (subject = the containing concept).
--     * Slot: id
--     * Slot: predicate Description: The relationship type. SHOULD be drawn from the RelationType vocabulary.
--     * Slot: target Description: The IRI (or Concept ID) of the relationship's object.
--     * Slot: relation_label Description: An optional human-readable label for the relationship.
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: Organization_id Description: Autocreated FK slot
-- # Class: Citation Description: A reference to an external source supporting a claim in a concept's body. Attached via the schema:citation predicate.
--     * Slot: id
--     * Slot: title Description: Human-readable display name.
--     * Slot: url Description: A URL.
--     * Slot: description Description: A single-sentence summary of the concept.
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: Organization_id Description: Autocreated FK slot
-- # Class: Concept_tags
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Concept_isPartOf
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Concept_hasPart
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Concept_references
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Concept_dependsOn
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Concept_derivedFrom
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Concept_about
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Concept_sameAs
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Concept_relatedTo
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Concept_definedBy
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Concept_source
--     * Slot: Concept_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Dataset_tags
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Dataset_isPartOf
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Dataset_hasPart
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Dataset_references
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Dataset_dependsOn
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Dataset_derivedFrom
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Dataset_about
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Dataset_sameAs
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Dataset_relatedTo
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Dataset_definedBy
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Dataset_source
--     * Slot: Dataset_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Table_tags
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Table_isPartOf
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Table_hasPart
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Table_references
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Table_dependsOn
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Table_derivedFrom
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Table_about
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Table_sameAs
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Table_relatedTo
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Table_definedBy
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Table_source
--     * Slot: Table_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Metric_measures
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: measures_id Description: What the metric measures (a concept IRI or description).
-- # Class: Metric_tags
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Metric_isPartOf
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Metric_hasPart
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Metric_references
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Metric_dependsOn
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Metric_derivedFrom
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Metric_about
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Metric_sameAs
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Metric_relatedTo
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Metric_definedBy
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Metric_source
--     * Slot: Metric_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Service_tags
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Service_isPartOf
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Service_hasPart
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Service_references
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Service_dependsOn
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Service_derivedFrom
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Service_about
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Service_sameAs
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Service_relatedTo
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Service_definedBy
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Service_source
--     * Slot: Service_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Playbook_tags
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Playbook_isPartOf
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Playbook_hasPart
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Playbook_references
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Playbook_dependsOn
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Playbook_derivedFrom
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Playbook_about
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Playbook_sameAs
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Playbook_relatedTo
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Playbook_definedBy
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Playbook_source
--     * Slot: Playbook_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Policy_tags
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Policy_isPartOf
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Policy_hasPart
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Policy_references
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Policy_dependsOn
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Policy_derivedFrom
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Policy_about
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Policy_sameAs
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Policy_relatedTo
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Policy_definedBy
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Policy_source
--     * Slot: Policy_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: GlossaryTerm_tags
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: GlossaryTerm_isPartOf
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: GlossaryTerm_hasPart
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: GlossaryTerm_references
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: GlossaryTerm_dependsOn
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: GlossaryTerm_derivedFrom
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: GlossaryTerm_about
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: GlossaryTerm_sameAs
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: GlossaryTerm_relatedTo
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: GlossaryTerm_definedBy
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: GlossaryTerm_source
--     * Slot: GlossaryTerm_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Reference_tags
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Reference_isPartOf
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Reference_hasPart
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Reference_references
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Reference_dependsOn
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Reference_derivedFrom
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Reference_about
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Reference_sameAs
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Reference_relatedTo
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Reference_definedBy
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Reference_source
--     * Slot: Reference_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Document_tags
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Document_isPartOf
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Document_hasPart
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Document_references
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Document_dependsOn
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Document_derivedFrom
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Document_about
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Document_sameAs
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Document_relatedTo
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Document_definedBy
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Document_source
--     * Slot: Document_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Role_memberOf
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: memberOf_id Description: The organization within which the role is held.
-- # Class: Role_holder
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: holder_id Description: The agent (typically a Person) who holds the role.
-- # Class: Role_tags
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Role_isPartOf
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Role_hasPart
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Role_references
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Role_dependsOn
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Role_derivedFrom
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Role_about
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Role_sameAs
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Role_relatedTo
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Role_definedBy
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Role_source
--     * Slot: Role_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Person_tags
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Person_isPartOf
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Person_hasPart
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Person_references
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Person_dependsOn
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Person_derivedFrom
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Person_about
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Person_sameAs
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Person_relatedTo
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Person_definedBy
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Person_source
--     * Slot: Person_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.
-- # Class: Organization_tags
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: tags Description: Short cross-cutting keywords for categorization.
-- # Class: Organization_isPartOf
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: isPartOf_id Description: The target concept that this concept is a part of.
-- # Class: Organization_hasPart
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: hasPart_id Description: A concept that is a part of this concept.
-- # Class: Organization_references
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: references_id Description: A concept or resource this concept refers to.
-- # Class: Organization_dependsOn
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: dependsOn_id Description: A concept this concept depends on.
-- # Class: Organization_derivedFrom
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: derivedFrom_id Description: An entity this concept was derived from (provenance).
-- # Class: Organization_about
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: about_id Description: The subject matter this concept is about.
-- # Class: Organization_sameAs
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: sameAs_id Description: An IRI asserting this concept is the same entity as another.
-- # Class: Organization_relatedTo
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: relatedTo_id Description: A generic association to another concept.
-- # Class: Organization_definedBy
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: definedBy_id Description: A resource that formally defines this concept.
-- # Class: Organization_source
--     * Slot: Organization_id Description: Autocreated FK slot
--     * Slot: source_id Description: A resource from which this concept is derived or sourced.

CREATE TABLE "KnowledgeBundle" (
	id INTEGER NOT NULL,
	lokf_version TEXT,
	okf_version TEXT,
	base_iri TEXT,
	context TEXT,
	title TEXT,
	description TEXT,
	license TEXT,
	publisher_id TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(publisher_id) REFERENCES "Agent" (id)
);
CREATE INDEX "ix_KnowledgeBundle_id" ON "KnowledgeBundle" (id);

CREATE TABLE "Concept" (
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	"KnowledgeBundle_id" INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY("KnowledgeBundle_id") REFERENCES "KnowledgeBundle" (id)
);
CREATE INDEX "ix_Concept_id" ON "Concept" (id);

CREATE TABLE "Dataset" (
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Dataset_id" ON "Dataset" (id);

CREATE TABLE "Table" (
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Table_id" ON "Table" (id);

CREATE TABLE "Metric" (
	unit TEXT,
	formula TEXT,
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Metric_id" ON "Metric" (id);

CREATE TABLE "Service" (
	endpoint TEXT,
	http_method TEXT,
	documentation TEXT,
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Service_id" ON "Service" (id);

CREATE TABLE "Playbook" (
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Playbook_id" ON "Playbook" (id);

CREATE TABLE "Policy" (
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Policy_id" ON "Policy" (id);

CREATE TABLE "GlossaryTerm" (
	definition TEXT,
	abbreviation TEXT,
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_GlossaryTerm_id" ON "GlossaryTerm" (id);

CREATE TABLE "Reference" (
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Reference_id" ON "Reference" (id);

CREATE TABLE "Document" (
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Document_id" ON "Document" (id);

CREATE TABLE "Role" (
	"roleName" TEXT,
	"startDate" TEXT,
	"endDate" TEXT,
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Role_id" ON "Role" (id);

CREATE TABLE "Agent" (
	type TEXT NOT NULL,
	id TEXT NOT NULL,
	name TEXT,
	email TEXT,
	"Concept_id" TEXT,
	"Dataset_id" TEXT,
	"Table_id" TEXT,
	"Metric_id" TEXT,
	"Service_id" TEXT,
	"Playbook_id" TEXT,
	"Policy_id" TEXT,
	"GlossaryTerm_id" TEXT,
	"Reference_id" TEXT,
	"Document_id" TEXT,
	"Role_id" TEXT,
	"Person_id" TEXT,
	"Organization_id" TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Agent_id" ON "Agent" (id);

CREATE TABLE "Person" (
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	name TEXT,
	email TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Person_id" ON "Person" (id);

CREATE TABLE "Organization" (
	id TEXT NOT NULL,
	type TEXT NOT NULL,
	title TEXT,
	description TEXT,
	resource TEXT,
	timestamp DATETIME,
	created DATETIME,
	version TEXT,
	license TEXT,
	body TEXT,
	name TEXT,
	email TEXT,
	PRIMARY KEY (id)
);
CREATE INDEX "ix_Organization_id" ON "Organization" (id);

CREATE TABLE "Field" (
	id INTEGER NOT NULL,
	name TEXT,
	datatype VARCHAR(8),
	description TEXT,
	unit TEXT,
	is_key BOOLEAN,
	constraints TEXT,
	"Dataset_id" TEXT,
	"Table_id" TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id)
);
CREATE INDEX "ix_Field_id" ON "Field" (id);

CREATE TABLE "Distribution" (
	id INTEGER NOT NULL,
	name TEXT,
	description TEXT,
	access_url TEXT,
	media_type TEXT,
	"Dataset_id" TEXT,
	"Table_id" TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id)
);
CREATE INDEX "ix_Distribution_id" ON "Distribution" (id);

CREATE TABLE "Relation" (
	id INTEGER NOT NULL,
	predicate VARCHAR(15) NOT NULL,
	target TEXT NOT NULL,
	relation_label TEXT,
	"Concept_id" TEXT,
	"Dataset_id" TEXT,
	"Table_id" TEXT,
	"Metric_id" TEXT,
	"Service_id" TEXT,
	"Playbook_id" TEXT,
	"Policy_id" TEXT,
	"GlossaryTerm_id" TEXT,
	"Reference_id" TEXT,
	"Document_id" TEXT,
	"Role_id" TEXT,
	"Person_id" TEXT,
	"Organization_id" TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(target) REFERENCES "Concept" (id),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Relation_id" ON "Relation" (id);

CREATE TABLE "Citation" (
	id INTEGER NOT NULL,
	title TEXT,
	url TEXT,
	description TEXT,
	"Concept_id" TEXT,
	"Dataset_id" TEXT,
	"Table_id" TEXT,
	"Metric_id" TEXT,
	"Service_id" TEXT,
	"Playbook_id" TEXT,
	"Policy_id" TEXT,
	"GlossaryTerm_id" TEXT,
	"Reference_id" TEXT,
	"Document_id" TEXT,
	"Role_id" TEXT,
	"Person_id" TEXT,
	"Organization_id" TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Citation_id" ON "Citation" (id);

CREATE TABLE "Concept_tags" (
	"Concept_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Concept_id", tags),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_tags_Concept_id" ON "Concept_tags" ("Concept_id");
CREATE INDEX "ix_Concept_tags_tags" ON "Concept_tags" (tags);

CREATE TABLE "Concept_isPartOf" (
	"Concept_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Concept_id", "isPartOf_id"),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_isPartOf_isPartOf_id" ON "Concept_isPartOf" ("isPartOf_id");
CREATE INDEX "ix_Concept_isPartOf_Concept_id" ON "Concept_isPartOf" ("Concept_id");

CREATE TABLE "Concept_hasPart" (
	"Concept_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Concept_id", "hasPart_id"),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_hasPart_Concept_id" ON "Concept_hasPart" ("Concept_id");
CREATE INDEX "ix_Concept_hasPart_hasPart_id" ON "Concept_hasPart" ("hasPart_id");

CREATE TABLE "Concept_references" (
	"Concept_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Concept_id", references_id),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_references_Concept_id" ON "Concept_references" ("Concept_id");
CREATE INDEX "ix_Concept_references_references_id" ON "Concept_references" (references_id);

CREATE TABLE "Concept_dependsOn" (
	"Concept_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Concept_id", "dependsOn_id"),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_dependsOn_dependsOn_id" ON "Concept_dependsOn" ("dependsOn_id");
CREATE INDEX "ix_Concept_dependsOn_Concept_id" ON "Concept_dependsOn" ("Concept_id");

CREATE TABLE "Concept_derivedFrom" (
	"Concept_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Concept_id", "derivedFrom_id"),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_derivedFrom_Concept_id" ON "Concept_derivedFrom" ("Concept_id");
CREATE INDEX "ix_Concept_derivedFrom_derivedFrom_id" ON "Concept_derivedFrom" ("derivedFrom_id");

CREATE TABLE "Concept_about" (
	"Concept_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Concept_id", about_id),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_about_about_id" ON "Concept_about" (about_id);
CREATE INDEX "ix_Concept_about_Concept_id" ON "Concept_about" ("Concept_id");

CREATE TABLE "Concept_sameAs" (
	"Concept_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Concept_id", "sameAs_id"),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_sameAs_Concept_id" ON "Concept_sameAs" ("Concept_id");
CREATE INDEX "ix_Concept_sameAs_sameAs_id" ON "Concept_sameAs" ("sameAs_id");

CREATE TABLE "Concept_relatedTo" (
	"Concept_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Concept_id", "relatedTo_id"),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_relatedTo_relatedTo_id" ON "Concept_relatedTo" ("relatedTo_id");
CREATE INDEX "ix_Concept_relatedTo_Concept_id" ON "Concept_relatedTo" ("Concept_id");

CREATE TABLE "Concept_definedBy" (
	"Concept_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Concept_id", "definedBy_id"),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_definedBy_definedBy_id" ON "Concept_definedBy" ("definedBy_id");
CREATE INDEX "ix_Concept_definedBy_Concept_id" ON "Concept_definedBy" ("Concept_id");

CREATE TABLE "Concept_source" (
	"Concept_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Concept_id", source_id),
	FOREIGN KEY("Concept_id") REFERENCES "Concept" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Concept_source_Concept_id" ON "Concept_source" ("Concept_id");
CREATE INDEX "ix_Concept_source_source_id" ON "Concept_source" (source_id);

CREATE TABLE "Dataset_tags" (
	"Dataset_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Dataset_id", tags),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id)
);
CREATE INDEX "ix_Dataset_tags_tags" ON "Dataset_tags" (tags);
CREATE INDEX "ix_Dataset_tags_Dataset_id" ON "Dataset_tags" ("Dataset_id");

CREATE TABLE "Dataset_isPartOf" (
	"Dataset_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Dataset_id", "isPartOf_id"),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Dataset_isPartOf_isPartOf_id" ON "Dataset_isPartOf" ("isPartOf_id");
CREATE INDEX "ix_Dataset_isPartOf_Dataset_id" ON "Dataset_isPartOf" ("Dataset_id");

CREATE TABLE "Dataset_hasPart" (
	"Dataset_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Dataset_id", "hasPart_id"),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Dataset_hasPart_hasPart_id" ON "Dataset_hasPart" ("hasPart_id");
CREATE INDEX "ix_Dataset_hasPart_Dataset_id" ON "Dataset_hasPart" ("Dataset_id");

CREATE TABLE "Dataset_references" (
	"Dataset_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Dataset_id", references_id),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Dataset_references_references_id" ON "Dataset_references" (references_id);
CREATE INDEX "ix_Dataset_references_Dataset_id" ON "Dataset_references" ("Dataset_id");

CREATE TABLE "Dataset_dependsOn" (
	"Dataset_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Dataset_id", "dependsOn_id"),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Dataset_dependsOn_Dataset_id" ON "Dataset_dependsOn" ("Dataset_id");
CREATE INDEX "ix_Dataset_dependsOn_dependsOn_id" ON "Dataset_dependsOn" ("dependsOn_id");

CREATE TABLE "Dataset_derivedFrom" (
	"Dataset_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Dataset_id", "derivedFrom_id"),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Dataset_derivedFrom_Dataset_id" ON "Dataset_derivedFrom" ("Dataset_id");
CREATE INDEX "ix_Dataset_derivedFrom_derivedFrom_id" ON "Dataset_derivedFrom" ("derivedFrom_id");

CREATE TABLE "Dataset_about" (
	"Dataset_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Dataset_id", about_id),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Dataset_about_Dataset_id" ON "Dataset_about" ("Dataset_id");
CREATE INDEX "ix_Dataset_about_about_id" ON "Dataset_about" (about_id);

CREATE TABLE "Dataset_sameAs" (
	"Dataset_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Dataset_id", "sameAs_id"),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Dataset_sameAs_sameAs_id" ON "Dataset_sameAs" ("sameAs_id");
CREATE INDEX "ix_Dataset_sameAs_Dataset_id" ON "Dataset_sameAs" ("Dataset_id");

CREATE TABLE "Dataset_relatedTo" (
	"Dataset_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Dataset_id", "relatedTo_id"),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Dataset_relatedTo_Dataset_id" ON "Dataset_relatedTo" ("Dataset_id");
CREATE INDEX "ix_Dataset_relatedTo_relatedTo_id" ON "Dataset_relatedTo" ("relatedTo_id");

CREATE TABLE "Dataset_definedBy" (
	"Dataset_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Dataset_id", "definedBy_id"),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Dataset_definedBy_definedBy_id" ON "Dataset_definedBy" ("definedBy_id");
CREATE INDEX "ix_Dataset_definedBy_Dataset_id" ON "Dataset_definedBy" ("Dataset_id");

CREATE TABLE "Dataset_source" (
	"Dataset_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Dataset_id", source_id),
	FOREIGN KEY("Dataset_id") REFERENCES "Dataset" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Dataset_source_Dataset_id" ON "Dataset_source" ("Dataset_id");
CREATE INDEX "ix_Dataset_source_source_id" ON "Dataset_source" (source_id);

CREATE TABLE "Table_tags" (
	"Table_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Table_id", tags),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id)
);
CREATE INDEX "ix_Table_tags_Table_id" ON "Table_tags" ("Table_id");
CREATE INDEX "ix_Table_tags_tags" ON "Table_tags" (tags);

CREATE TABLE "Table_isPartOf" (
	"Table_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Table_id", "isPartOf_id"),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Table_isPartOf_Table_id" ON "Table_isPartOf" ("Table_id");
CREATE INDEX "ix_Table_isPartOf_isPartOf_id" ON "Table_isPartOf" ("isPartOf_id");

CREATE TABLE "Table_hasPart" (
	"Table_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Table_id", "hasPart_id"),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Table_hasPart_Table_id" ON "Table_hasPart" ("Table_id");
CREATE INDEX "ix_Table_hasPart_hasPart_id" ON "Table_hasPart" ("hasPart_id");

CREATE TABLE "Table_references" (
	"Table_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Table_id", references_id),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Table_references_references_id" ON "Table_references" (references_id);
CREATE INDEX "ix_Table_references_Table_id" ON "Table_references" ("Table_id");

CREATE TABLE "Table_dependsOn" (
	"Table_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Table_id", "dependsOn_id"),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Table_dependsOn_Table_id" ON "Table_dependsOn" ("Table_id");
CREATE INDEX "ix_Table_dependsOn_dependsOn_id" ON "Table_dependsOn" ("dependsOn_id");

CREATE TABLE "Table_derivedFrom" (
	"Table_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Table_id", "derivedFrom_id"),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Table_derivedFrom_Table_id" ON "Table_derivedFrom" ("Table_id");
CREATE INDEX "ix_Table_derivedFrom_derivedFrom_id" ON "Table_derivedFrom" ("derivedFrom_id");

CREATE TABLE "Table_about" (
	"Table_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Table_id", about_id),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Table_about_about_id" ON "Table_about" (about_id);
CREATE INDEX "ix_Table_about_Table_id" ON "Table_about" ("Table_id");

CREATE TABLE "Table_sameAs" (
	"Table_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Table_id", "sameAs_id"),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Table_sameAs_Table_id" ON "Table_sameAs" ("Table_id");
CREATE INDEX "ix_Table_sameAs_sameAs_id" ON "Table_sameAs" ("sameAs_id");

CREATE TABLE "Table_relatedTo" (
	"Table_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Table_id", "relatedTo_id"),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Table_relatedTo_relatedTo_id" ON "Table_relatedTo" ("relatedTo_id");
CREATE INDEX "ix_Table_relatedTo_Table_id" ON "Table_relatedTo" ("Table_id");

CREATE TABLE "Table_definedBy" (
	"Table_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Table_id", "definedBy_id"),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Table_definedBy_definedBy_id" ON "Table_definedBy" ("definedBy_id");
CREATE INDEX "ix_Table_definedBy_Table_id" ON "Table_definedBy" ("Table_id");

CREATE TABLE "Table_source" (
	"Table_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Table_id", source_id),
	FOREIGN KEY("Table_id") REFERENCES "Table" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Table_source_source_id" ON "Table_source" (source_id);
CREATE INDEX "ix_Table_source_Table_id" ON "Table_source" ("Table_id");

CREATE TABLE "Metric_measures" (
	"Metric_id" TEXT,
	measures_id TEXT,
	PRIMARY KEY ("Metric_id", measures_id),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY(measures_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_measures_measures_id" ON "Metric_measures" (measures_id);
CREATE INDEX "ix_Metric_measures_Metric_id" ON "Metric_measures" ("Metric_id");

CREATE TABLE "Metric_tags" (
	"Metric_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Metric_id", tags),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id)
);
CREATE INDEX "ix_Metric_tags_tags" ON "Metric_tags" (tags);
CREATE INDEX "ix_Metric_tags_Metric_id" ON "Metric_tags" ("Metric_id");

CREATE TABLE "Metric_isPartOf" (
	"Metric_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Metric_id", "isPartOf_id"),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_isPartOf_isPartOf_id" ON "Metric_isPartOf" ("isPartOf_id");
CREATE INDEX "ix_Metric_isPartOf_Metric_id" ON "Metric_isPartOf" ("Metric_id");

CREATE TABLE "Metric_hasPart" (
	"Metric_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Metric_id", "hasPart_id"),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_hasPart_Metric_id" ON "Metric_hasPart" ("Metric_id");
CREATE INDEX "ix_Metric_hasPart_hasPart_id" ON "Metric_hasPart" ("hasPart_id");

CREATE TABLE "Metric_references" (
	"Metric_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Metric_id", references_id),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_references_references_id" ON "Metric_references" (references_id);
CREATE INDEX "ix_Metric_references_Metric_id" ON "Metric_references" ("Metric_id");

CREATE TABLE "Metric_dependsOn" (
	"Metric_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Metric_id", "dependsOn_id"),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_dependsOn_dependsOn_id" ON "Metric_dependsOn" ("dependsOn_id");
CREATE INDEX "ix_Metric_dependsOn_Metric_id" ON "Metric_dependsOn" ("Metric_id");

CREATE TABLE "Metric_derivedFrom" (
	"Metric_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Metric_id", "derivedFrom_id"),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_derivedFrom_Metric_id" ON "Metric_derivedFrom" ("Metric_id");
CREATE INDEX "ix_Metric_derivedFrom_derivedFrom_id" ON "Metric_derivedFrom" ("derivedFrom_id");

CREATE TABLE "Metric_about" (
	"Metric_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Metric_id", about_id),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_about_Metric_id" ON "Metric_about" ("Metric_id");
CREATE INDEX "ix_Metric_about_about_id" ON "Metric_about" (about_id);

CREATE TABLE "Metric_sameAs" (
	"Metric_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Metric_id", "sameAs_id"),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_sameAs_sameAs_id" ON "Metric_sameAs" ("sameAs_id");
CREATE INDEX "ix_Metric_sameAs_Metric_id" ON "Metric_sameAs" ("Metric_id");

CREATE TABLE "Metric_relatedTo" (
	"Metric_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Metric_id", "relatedTo_id"),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_relatedTo_relatedTo_id" ON "Metric_relatedTo" ("relatedTo_id");
CREATE INDEX "ix_Metric_relatedTo_Metric_id" ON "Metric_relatedTo" ("Metric_id");

CREATE TABLE "Metric_definedBy" (
	"Metric_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Metric_id", "definedBy_id"),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_definedBy_definedBy_id" ON "Metric_definedBy" ("definedBy_id");
CREATE INDEX "ix_Metric_definedBy_Metric_id" ON "Metric_definedBy" ("Metric_id");

CREATE TABLE "Metric_source" (
	"Metric_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Metric_id", source_id),
	FOREIGN KEY("Metric_id") REFERENCES "Metric" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Metric_source_Metric_id" ON "Metric_source" ("Metric_id");
CREATE INDEX "ix_Metric_source_source_id" ON "Metric_source" (source_id);

CREATE TABLE "Service_tags" (
	"Service_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Service_id", tags),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id)
);
CREATE INDEX "ix_Service_tags_tags" ON "Service_tags" (tags);
CREATE INDEX "ix_Service_tags_Service_id" ON "Service_tags" ("Service_id");

CREATE TABLE "Service_isPartOf" (
	"Service_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Service_id", "isPartOf_id"),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Service_isPartOf_Service_id" ON "Service_isPartOf" ("Service_id");
CREATE INDEX "ix_Service_isPartOf_isPartOf_id" ON "Service_isPartOf" ("isPartOf_id");

CREATE TABLE "Service_hasPart" (
	"Service_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Service_id", "hasPart_id"),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Service_hasPart_hasPart_id" ON "Service_hasPart" ("hasPart_id");
CREATE INDEX "ix_Service_hasPart_Service_id" ON "Service_hasPart" ("Service_id");

CREATE TABLE "Service_references" (
	"Service_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Service_id", references_id),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Service_references_references_id" ON "Service_references" (references_id);
CREATE INDEX "ix_Service_references_Service_id" ON "Service_references" ("Service_id");

CREATE TABLE "Service_dependsOn" (
	"Service_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Service_id", "dependsOn_id"),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Service_dependsOn_Service_id" ON "Service_dependsOn" ("Service_id");
CREATE INDEX "ix_Service_dependsOn_dependsOn_id" ON "Service_dependsOn" ("dependsOn_id");

CREATE TABLE "Service_derivedFrom" (
	"Service_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Service_id", "derivedFrom_id"),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Service_derivedFrom_derivedFrom_id" ON "Service_derivedFrom" ("derivedFrom_id");
CREATE INDEX "ix_Service_derivedFrom_Service_id" ON "Service_derivedFrom" ("Service_id");

CREATE TABLE "Service_about" (
	"Service_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Service_id", about_id),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Service_about_Service_id" ON "Service_about" ("Service_id");
CREATE INDEX "ix_Service_about_about_id" ON "Service_about" (about_id);

CREATE TABLE "Service_sameAs" (
	"Service_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Service_id", "sameAs_id"),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Service_sameAs_Service_id" ON "Service_sameAs" ("Service_id");
CREATE INDEX "ix_Service_sameAs_sameAs_id" ON "Service_sameAs" ("sameAs_id");

CREATE TABLE "Service_relatedTo" (
	"Service_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Service_id", "relatedTo_id"),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Service_relatedTo_Service_id" ON "Service_relatedTo" ("Service_id");
CREATE INDEX "ix_Service_relatedTo_relatedTo_id" ON "Service_relatedTo" ("relatedTo_id");

CREATE TABLE "Service_definedBy" (
	"Service_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Service_id", "definedBy_id"),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Service_definedBy_definedBy_id" ON "Service_definedBy" ("definedBy_id");
CREATE INDEX "ix_Service_definedBy_Service_id" ON "Service_definedBy" ("Service_id");

CREATE TABLE "Service_source" (
	"Service_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Service_id", source_id),
	FOREIGN KEY("Service_id") REFERENCES "Service" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Service_source_Service_id" ON "Service_source" ("Service_id");
CREATE INDEX "ix_Service_source_source_id" ON "Service_source" (source_id);

CREATE TABLE "Playbook_tags" (
	"Playbook_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Playbook_id", tags),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id)
);
CREATE INDEX "ix_Playbook_tags_tags" ON "Playbook_tags" (tags);
CREATE INDEX "ix_Playbook_tags_Playbook_id" ON "Playbook_tags" ("Playbook_id");

CREATE TABLE "Playbook_isPartOf" (
	"Playbook_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Playbook_id", "isPartOf_id"),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Playbook_isPartOf_Playbook_id" ON "Playbook_isPartOf" ("Playbook_id");
CREATE INDEX "ix_Playbook_isPartOf_isPartOf_id" ON "Playbook_isPartOf" ("isPartOf_id");

CREATE TABLE "Playbook_hasPart" (
	"Playbook_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Playbook_id", "hasPart_id"),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Playbook_hasPart_hasPart_id" ON "Playbook_hasPart" ("hasPart_id");
CREATE INDEX "ix_Playbook_hasPart_Playbook_id" ON "Playbook_hasPart" ("Playbook_id");

CREATE TABLE "Playbook_references" (
	"Playbook_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Playbook_id", references_id),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Playbook_references_Playbook_id" ON "Playbook_references" ("Playbook_id");
CREATE INDEX "ix_Playbook_references_references_id" ON "Playbook_references" (references_id);

CREATE TABLE "Playbook_dependsOn" (
	"Playbook_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Playbook_id", "dependsOn_id"),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Playbook_dependsOn_Playbook_id" ON "Playbook_dependsOn" ("Playbook_id");
CREATE INDEX "ix_Playbook_dependsOn_dependsOn_id" ON "Playbook_dependsOn" ("dependsOn_id");

CREATE TABLE "Playbook_derivedFrom" (
	"Playbook_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Playbook_id", "derivedFrom_id"),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Playbook_derivedFrom_derivedFrom_id" ON "Playbook_derivedFrom" ("derivedFrom_id");
CREATE INDEX "ix_Playbook_derivedFrom_Playbook_id" ON "Playbook_derivedFrom" ("Playbook_id");

CREATE TABLE "Playbook_about" (
	"Playbook_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Playbook_id", about_id),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Playbook_about_Playbook_id" ON "Playbook_about" ("Playbook_id");
CREATE INDEX "ix_Playbook_about_about_id" ON "Playbook_about" (about_id);

CREATE TABLE "Playbook_sameAs" (
	"Playbook_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Playbook_id", "sameAs_id"),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Playbook_sameAs_sameAs_id" ON "Playbook_sameAs" ("sameAs_id");
CREATE INDEX "ix_Playbook_sameAs_Playbook_id" ON "Playbook_sameAs" ("Playbook_id");

CREATE TABLE "Playbook_relatedTo" (
	"Playbook_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Playbook_id", "relatedTo_id"),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Playbook_relatedTo_Playbook_id" ON "Playbook_relatedTo" ("Playbook_id");
CREATE INDEX "ix_Playbook_relatedTo_relatedTo_id" ON "Playbook_relatedTo" ("relatedTo_id");

CREATE TABLE "Playbook_definedBy" (
	"Playbook_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Playbook_id", "definedBy_id"),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Playbook_definedBy_Playbook_id" ON "Playbook_definedBy" ("Playbook_id");
CREATE INDEX "ix_Playbook_definedBy_definedBy_id" ON "Playbook_definedBy" ("definedBy_id");

CREATE TABLE "Playbook_source" (
	"Playbook_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Playbook_id", source_id),
	FOREIGN KEY("Playbook_id") REFERENCES "Playbook" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Playbook_source_Playbook_id" ON "Playbook_source" ("Playbook_id");
CREATE INDEX "ix_Playbook_source_source_id" ON "Playbook_source" (source_id);

CREATE TABLE "Policy_tags" (
	"Policy_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Policy_id", tags),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id)
);
CREATE INDEX "ix_Policy_tags_Policy_id" ON "Policy_tags" ("Policy_id");
CREATE INDEX "ix_Policy_tags_tags" ON "Policy_tags" (tags);

CREATE TABLE "Policy_isPartOf" (
	"Policy_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Policy_id", "isPartOf_id"),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Policy_isPartOf_Policy_id" ON "Policy_isPartOf" ("Policy_id");
CREATE INDEX "ix_Policy_isPartOf_isPartOf_id" ON "Policy_isPartOf" ("isPartOf_id");

CREATE TABLE "Policy_hasPart" (
	"Policy_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Policy_id", "hasPart_id"),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Policy_hasPart_hasPart_id" ON "Policy_hasPart" ("hasPart_id");
CREATE INDEX "ix_Policy_hasPart_Policy_id" ON "Policy_hasPart" ("Policy_id");

CREATE TABLE "Policy_references" (
	"Policy_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Policy_id", references_id),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Policy_references_references_id" ON "Policy_references" (references_id);
CREATE INDEX "ix_Policy_references_Policy_id" ON "Policy_references" ("Policy_id");

CREATE TABLE "Policy_dependsOn" (
	"Policy_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Policy_id", "dependsOn_id"),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Policy_dependsOn_Policy_id" ON "Policy_dependsOn" ("Policy_id");
CREATE INDEX "ix_Policy_dependsOn_dependsOn_id" ON "Policy_dependsOn" ("dependsOn_id");

CREATE TABLE "Policy_derivedFrom" (
	"Policy_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Policy_id", "derivedFrom_id"),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Policy_derivedFrom_derivedFrom_id" ON "Policy_derivedFrom" ("derivedFrom_id");
CREATE INDEX "ix_Policy_derivedFrom_Policy_id" ON "Policy_derivedFrom" ("Policy_id");

CREATE TABLE "Policy_about" (
	"Policy_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Policy_id", about_id),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Policy_about_Policy_id" ON "Policy_about" ("Policy_id");
CREATE INDEX "ix_Policy_about_about_id" ON "Policy_about" (about_id);

CREATE TABLE "Policy_sameAs" (
	"Policy_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Policy_id", "sameAs_id"),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Policy_sameAs_sameAs_id" ON "Policy_sameAs" ("sameAs_id");
CREATE INDEX "ix_Policy_sameAs_Policy_id" ON "Policy_sameAs" ("Policy_id");

CREATE TABLE "Policy_relatedTo" (
	"Policy_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Policy_id", "relatedTo_id"),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Policy_relatedTo_relatedTo_id" ON "Policy_relatedTo" ("relatedTo_id");
CREATE INDEX "ix_Policy_relatedTo_Policy_id" ON "Policy_relatedTo" ("Policy_id");

CREATE TABLE "Policy_definedBy" (
	"Policy_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Policy_id", "definedBy_id"),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Policy_definedBy_Policy_id" ON "Policy_definedBy" ("Policy_id");
CREATE INDEX "ix_Policy_definedBy_definedBy_id" ON "Policy_definedBy" ("definedBy_id");

CREATE TABLE "Policy_source" (
	"Policy_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Policy_id", source_id),
	FOREIGN KEY("Policy_id") REFERENCES "Policy" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Policy_source_source_id" ON "Policy_source" (source_id);
CREATE INDEX "ix_Policy_source_Policy_id" ON "Policy_source" ("Policy_id");

CREATE TABLE "GlossaryTerm_tags" (
	"GlossaryTerm_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("GlossaryTerm_id", tags),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id)
);
CREATE INDEX "ix_GlossaryTerm_tags_GlossaryTerm_id" ON "GlossaryTerm_tags" ("GlossaryTerm_id");
CREATE INDEX "ix_GlossaryTerm_tags_tags" ON "GlossaryTerm_tags" (tags);

CREATE TABLE "GlossaryTerm_isPartOf" (
	"GlossaryTerm_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("GlossaryTerm_id", "isPartOf_id"),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_GlossaryTerm_isPartOf_isPartOf_id" ON "GlossaryTerm_isPartOf" ("isPartOf_id");
CREATE INDEX "ix_GlossaryTerm_isPartOf_GlossaryTerm_id" ON "GlossaryTerm_isPartOf" ("GlossaryTerm_id");

CREATE TABLE "GlossaryTerm_hasPart" (
	"GlossaryTerm_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("GlossaryTerm_id", "hasPart_id"),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_GlossaryTerm_hasPart_hasPart_id" ON "GlossaryTerm_hasPart" ("hasPart_id");
CREATE INDEX "ix_GlossaryTerm_hasPart_GlossaryTerm_id" ON "GlossaryTerm_hasPart" ("GlossaryTerm_id");

CREATE TABLE "GlossaryTerm_references" (
	"GlossaryTerm_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("GlossaryTerm_id", references_id),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_GlossaryTerm_references_references_id" ON "GlossaryTerm_references" (references_id);
CREATE INDEX "ix_GlossaryTerm_references_GlossaryTerm_id" ON "GlossaryTerm_references" ("GlossaryTerm_id");

CREATE TABLE "GlossaryTerm_dependsOn" (
	"GlossaryTerm_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("GlossaryTerm_id", "dependsOn_id"),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_GlossaryTerm_dependsOn_GlossaryTerm_id" ON "GlossaryTerm_dependsOn" ("GlossaryTerm_id");
CREATE INDEX "ix_GlossaryTerm_dependsOn_dependsOn_id" ON "GlossaryTerm_dependsOn" ("dependsOn_id");

CREATE TABLE "GlossaryTerm_derivedFrom" (
	"GlossaryTerm_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("GlossaryTerm_id", "derivedFrom_id"),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_GlossaryTerm_derivedFrom_GlossaryTerm_id" ON "GlossaryTerm_derivedFrom" ("GlossaryTerm_id");
CREATE INDEX "ix_GlossaryTerm_derivedFrom_derivedFrom_id" ON "GlossaryTerm_derivedFrom" ("derivedFrom_id");

CREATE TABLE "GlossaryTerm_about" (
	"GlossaryTerm_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("GlossaryTerm_id", about_id),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_GlossaryTerm_about_about_id" ON "GlossaryTerm_about" (about_id);
CREATE INDEX "ix_GlossaryTerm_about_GlossaryTerm_id" ON "GlossaryTerm_about" ("GlossaryTerm_id");

CREATE TABLE "GlossaryTerm_sameAs" (
	"GlossaryTerm_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("GlossaryTerm_id", "sameAs_id"),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_GlossaryTerm_sameAs_GlossaryTerm_id" ON "GlossaryTerm_sameAs" ("GlossaryTerm_id");
CREATE INDEX "ix_GlossaryTerm_sameAs_sameAs_id" ON "GlossaryTerm_sameAs" ("sameAs_id");

CREATE TABLE "GlossaryTerm_relatedTo" (
	"GlossaryTerm_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("GlossaryTerm_id", "relatedTo_id"),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_GlossaryTerm_relatedTo_relatedTo_id" ON "GlossaryTerm_relatedTo" ("relatedTo_id");
CREATE INDEX "ix_GlossaryTerm_relatedTo_GlossaryTerm_id" ON "GlossaryTerm_relatedTo" ("GlossaryTerm_id");

CREATE TABLE "GlossaryTerm_definedBy" (
	"GlossaryTerm_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("GlossaryTerm_id", "definedBy_id"),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_GlossaryTerm_definedBy_definedBy_id" ON "GlossaryTerm_definedBy" ("definedBy_id");
CREATE INDEX "ix_GlossaryTerm_definedBy_GlossaryTerm_id" ON "GlossaryTerm_definedBy" ("GlossaryTerm_id");

CREATE TABLE "GlossaryTerm_source" (
	"GlossaryTerm_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("GlossaryTerm_id", source_id),
	FOREIGN KEY("GlossaryTerm_id") REFERENCES "GlossaryTerm" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_GlossaryTerm_source_GlossaryTerm_id" ON "GlossaryTerm_source" ("GlossaryTerm_id");
CREATE INDEX "ix_GlossaryTerm_source_source_id" ON "GlossaryTerm_source" (source_id);

CREATE TABLE "Reference_tags" (
	"Reference_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Reference_id", tags),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id)
);
CREATE INDEX "ix_Reference_tags_tags" ON "Reference_tags" (tags);
CREATE INDEX "ix_Reference_tags_Reference_id" ON "Reference_tags" ("Reference_id");

CREATE TABLE "Reference_isPartOf" (
	"Reference_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Reference_id", "isPartOf_id"),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Reference_isPartOf_isPartOf_id" ON "Reference_isPartOf" ("isPartOf_id");
CREATE INDEX "ix_Reference_isPartOf_Reference_id" ON "Reference_isPartOf" ("Reference_id");

CREATE TABLE "Reference_hasPart" (
	"Reference_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Reference_id", "hasPart_id"),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Reference_hasPart_hasPart_id" ON "Reference_hasPart" ("hasPart_id");
CREATE INDEX "ix_Reference_hasPart_Reference_id" ON "Reference_hasPart" ("Reference_id");

CREATE TABLE "Reference_references" (
	"Reference_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Reference_id", references_id),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Reference_references_references_id" ON "Reference_references" (references_id);
CREATE INDEX "ix_Reference_references_Reference_id" ON "Reference_references" ("Reference_id");

CREATE TABLE "Reference_dependsOn" (
	"Reference_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Reference_id", "dependsOn_id"),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Reference_dependsOn_dependsOn_id" ON "Reference_dependsOn" ("dependsOn_id");
CREATE INDEX "ix_Reference_dependsOn_Reference_id" ON "Reference_dependsOn" ("Reference_id");

CREATE TABLE "Reference_derivedFrom" (
	"Reference_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Reference_id", "derivedFrom_id"),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Reference_derivedFrom_Reference_id" ON "Reference_derivedFrom" ("Reference_id");
CREATE INDEX "ix_Reference_derivedFrom_derivedFrom_id" ON "Reference_derivedFrom" ("derivedFrom_id");

CREATE TABLE "Reference_about" (
	"Reference_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Reference_id", about_id),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Reference_about_about_id" ON "Reference_about" (about_id);
CREATE INDEX "ix_Reference_about_Reference_id" ON "Reference_about" ("Reference_id");

CREATE TABLE "Reference_sameAs" (
	"Reference_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Reference_id", "sameAs_id"),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Reference_sameAs_sameAs_id" ON "Reference_sameAs" ("sameAs_id");
CREATE INDEX "ix_Reference_sameAs_Reference_id" ON "Reference_sameAs" ("Reference_id");

CREATE TABLE "Reference_relatedTo" (
	"Reference_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Reference_id", "relatedTo_id"),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Reference_relatedTo_relatedTo_id" ON "Reference_relatedTo" ("relatedTo_id");
CREATE INDEX "ix_Reference_relatedTo_Reference_id" ON "Reference_relatedTo" ("Reference_id");

CREATE TABLE "Reference_definedBy" (
	"Reference_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Reference_id", "definedBy_id"),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Reference_definedBy_Reference_id" ON "Reference_definedBy" ("Reference_id");
CREATE INDEX "ix_Reference_definedBy_definedBy_id" ON "Reference_definedBy" ("definedBy_id");

CREATE TABLE "Reference_source" (
	"Reference_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Reference_id", source_id),
	FOREIGN KEY("Reference_id") REFERENCES "Reference" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Reference_source_source_id" ON "Reference_source" (source_id);
CREATE INDEX "ix_Reference_source_Reference_id" ON "Reference_source" ("Reference_id");

CREATE TABLE "Document_tags" (
	"Document_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Document_id", tags),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id)
);
CREATE INDEX "ix_Document_tags_tags" ON "Document_tags" (tags);
CREATE INDEX "ix_Document_tags_Document_id" ON "Document_tags" ("Document_id");

CREATE TABLE "Document_isPartOf" (
	"Document_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Document_id", "isPartOf_id"),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Document_isPartOf_Document_id" ON "Document_isPartOf" ("Document_id");
CREATE INDEX "ix_Document_isPartOf_isPartOf_id" ON "Document_isPartOf" ("isPartOf_id");

CREATE TABLE "Document_hasPart" (
	"Document_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Document_id", "hasPart_id"),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Document_hasPart_hasPart_id" ON "Document_hasPart" ("hasPart_id");
CREATE INDEX "ix_Document_hasPart_Document_id" ON "Document_hasPart" ("Document_id");

CREATE TABLE "Document_references" (
	"Document_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Document_id", references_id),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Document_references_Document_id" ON "Document_references" ("Document_id");
CREATE INDEX "ix_Document_references_references_id" ON "Document_references" (references_id);

CREATE TABLE "Document_dependsOn" (
	"Document_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Document_id", "dependsOn_id"),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Document_dependsOn_dependsOn_id" ON "Document_dependsOn" ("dependsOn_id");
CREATE INDEX "ix_Document_dependsOn_Document_id" ON "Document_dependsOn" ("Document_id");

CREATE TABLE "Document_derivedFrom" (
	"Document_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Document_id", "derivedFrom_id"),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Document_derivedFrom_Document_id" ON "Document_derivedFrom" ("Document_id");
CREATE INDEX "ix_Document_derivedFrom_derivedFrom_id" ON "Document_derivedFrom" ("derivedFrom_id");

CREATE TABLE "Document_about" (
	"Document_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Document_id", about_id),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Document_about_about_id" ON "Document_about" (about_id);
CREATE INDEX "ix_Document_about_Document_id" ON "Document_about" ("Document_id");

CREATE TABLE "Document_sameAs" (
	"Document_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Document_id", "sameAs_id"),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Document_sameAs_sameAs_id" ON "Document_sameAs" ("sameAs_id");
CREATE INDEX "ix_Document_sameAs_Document_id" ON "Document_sameAs" ("Document_id");

CREATE TABLE "Document_relatedTo" (
	"Document_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Document_id", "relatedTo_id"),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Document_relatedTo_Document_id" ON "Document_relatedTo" ("Document_id");
CREATE INDEX "ix_Document_relatedTo_relatedTo_id" ON "Document_relatedTo" ("relatedTo_id");

CREATE TABLE "Document_definedBy" (
	"Document_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Document_id", "definedBy_id"),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Document_definedBy_definedBy_id" ON "Document_definedBy" ("definedBy_id");
CREATE INDEX "ix_Document_definedBy_Document_id" ON "Document_definedBy" ("Document_id");

CREATE TABLE "Document_source" (
	"Document_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Document_id", source_id),
	FOREIGN KEY("Document_id") REFERENCES "Document" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Document_source_source_id" ON "Document_source" (source_id);
CREATE INDEX "ix_Document_source_Document_id" ON "Document_source" ("Document_id");

CREATE TABLE "Role_memberOf" (
	"Role_id" TEXT,
	"memberOf_id" TEXT,
	PRIMARY KEY ("Role_id", "memberOf_id"),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("memberOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_memberOf_memberOf_id" ON "Role_memberOf" ("memberOf_id");
CREATE INDEX "ix_Role_memberOf_Role_id" ON "Role_memberOf" ("Role_id");

CREATE TABLE "Role_holder" (
	"Role_id" TEXT,
	holder_id TEXT,
	PRIMARY KEY ("Role_id", holder_id),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY(holder_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_holder_Role_id" ON "Role_holder" ("Role_id");
CREATE INDEX "ix_Role_holder_holder_id" ON "Role_holder" (holder_id);

CREATE TABLE "Role_tags" (
	"Role_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Role_id", tags),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id)
);
CREATE INDEX "ix_Role_tags_Role_id" ON "Role_tags" ("Role_id");
CREATE INDEX "ix_Role_tags_tags" ON "Role_tags" (tags);

CREATE TABLE "Role_isPartOf" (
	"Role_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Role_id", "isPartOf_id"),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_isPartOf_Role_id" ON "Role_isPartOf" ("Role_id");
CREATE INDEX "ix_Role_isPartOf_isPartOf_id" ON "Role_isPartOf" ("isPartOf_id");

CREATE TABLE "Role_hasPart" (
	"Role_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Role_id", "hasPart_id"),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_hasPart_hasPart_id" ON "Role_hasPart" ("hasPart_id");
CREATE INDEX "ix_Role_hasPart_Role_id" ON "Role_hasPart" ("Role_id");

CREATE TABLE "Role_references" (
	"Role_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Role_id", references_id),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_references_references_id" ON "Role_references" (references_id);
CREATE INDEX "ix_Role_references_Role_id" ON "Role_references" ("Role_id");

CREATE TABLE "Role_dependsOn" (
	"Role_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Role_id", "dependsOn_id"),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_dependsOn_dependsOn_id" ON "Role_dependsOn" ("dependsOn_id");
CREATE INDEX "ix_Role_dependsOn_Role_id" ON "Role_dependsOn" ("Role_id");

CREATE TABLE "Role_derivedFrom" (
	"Role_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Role_id", "derivedFrom_id"),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_derivedFrom_Role_id" ON "Role_derivedFrom" ("Role_id");
CREATE INDEX "ix_Role_derivedFrom_derivedFrom_id" ON "Role_derivedFrom" ("derivedFrom_id");

CREATE TABLE "Role_about" (
	"Role_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Role_id", about_id),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_about_Role_id" ON "Role_about" ("Role_id");
CREATE INDEX "ix_Role_about_about_id" ON "Role_about" (about_id);

CREATE TABLE "Role_sameAs" (
	"Role_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Role_id", "sameAs_id"),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_sameAs_Role_id" ON "Role_sameAs" ("Role_id");
CREATE INDEX "ix_Role_sameAs_sameAs_id" ON "Role_sameAs" ("sameAs_id");

CREATE TABLE "Role_relatedTo" (
	"Role_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Role_id", "relatedTo_id"),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_relatedTo_relatedTo_id" ON "Role_relatedTo" ("relatedTo_id");
CREATE INDEX "ix_Role_relatedTo_Role_id" ON "Role_relatedTo" ("Role_id");

CREATE TABLE "Role_definedBy" (
	"Role_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Role_id", "definedBy_id"),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_definedBy_definedBy_id" ON "Role_definedBy" ("definedBy_id");
CREATE INDEX "ix_Role_definedBy_Role_id" ON "Role_definedBy" ("Role_id");

CREATE TABLE "Role_source" (
	"Role_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Role_id", source_id),
	FOREIGN KEY("Role_id") REFERENCES "Role" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Role_source_Role_id" ON "Role_source" ("Role_id");
CREATE INDEX "ix_Role_source_source_id" ON "Role_source" (source_id);

CREATE TABLE "Person_tags" (
	"Person_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Person_id", tags),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id)
);
CREATE INDEX "ix_Person_tags_tags" ON "Person_tags" (tags);
CREATE INDEX "ix_Person_tags_Person_id" ON "Person_tags" ("Person_id");

CREATE TABLE "Person_isPartOf" (
	"Person_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Person_id", "isPartOf_id"),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Person_isPartOf_isPartOf_id" ON "Person_isPartOf" ("isPartOf_id");
CREATE INDEX "ix_Person_isPartOf_Person_id" ON "Person_isPartOf" ("Person_id");

CREATE TABLE "Person_hasPart" (
	"Person_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Person_id", "hasPart_id"),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Person_hasPart_Person_id" ON "Person_hasPart" ("Person_id");
CREATE INDEX "ix_Person_hasPart_hasPart_id" ON "Person_hasPart" ("hasPart_id");

CREATE TABLE "Person_references" (
	"Person_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Person_id", references_id),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Person_references_Person_id" ON "Person_references" ("Person_id");
CREATE INDEX "ix_Person_references_references_id" ON "Person_references" (references_id);

CREATE TABLE "Person_dependsOn" (
	"Person_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Person_id", "dependsOn_id"),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Person_dependsOn_dependsOn_id" ON "Person_dependsOn" ("dependsOn_id");
CREATE INDEX "ix_Person_dependsOn_Person_id" ON "Person_dependsOn" ("Person_id");

CREATE TABLE "Person_derivedFrom" (
	"Person_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Person_id", "derivedFrom_id"),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Person_derivedFrom_derivedFrom_id" ON "Person_derivedFrom" ("derivedFrom_id");
CREATE INDEX "ix_Person_derivedFrom_Person_id" ON "Person_derivedFrom" ("Person_id");

CREATE TABLE "Person_about" (
	"Person_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Person_id", about_id),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Person_about_Person_id" ON "Person_about" ("Person_id");
CREATE INDEX "ix_Person_about_about_id" ON "Person_about" (about_id);

CREATE TABLE "Person_sameAs" (
	"Person_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Person_id", "sameAs_id"),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Person_sameAs_sameAs_id" ON "Person_sameAs" ("sameAs_id");
CREATE INDEX "ix_Person_sameAs_Person_id" ON "Person_sameAs" ("Person_id");

CREATE TABLE "Person_relatedTo" (
	"Person_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Person_id", "relatedTo_id"),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Person_relatedTo_relatedTo_id" ON "Person_relatedTo" ("relatedTo_id");
CREATE INDEX "ix_Person_relatedTo_Person_id" ON "Person_relatedTo" ("Person_id");

CREATE TABLE "Person_definedBy" (
	"Person_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Person_id", "definedBy_id"),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Person_definedBy_Person_id" ON "Person_definedBy" ("Person_id");
CREATE INDEX "ix_Person_definedBy_definedBy_id" ON "Person_definedBy" ("definedBy_id");

CREATE TABLE "Person_source" (
	"Person_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Person_id", source_id),
	FOREIGN KEY("Person_id") REFERENCES "Person" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Person_source_source_id" ON "Person_source" (source_id);
CREATE INDEX "ix_Person_source_Person_id" ON "Person_source" ("Person_id");

CREATE TABLE "Organization_tags" (
	"Organization_id" TEXT,
	tags TEXT,
	PRIMARY KEY ("Organization_id", tags),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id)
);
CREATE INDEX "ix_Organization_tags_tags" ON "Organization_tags" (tags);
CREATE INDEX "ix_Organization_tags_Organization_id" ON "Organization_tags" ("Organization_id");

CREATE TABLE "Organization_isPartOf" (
	"Organization_id" TEXT,
	"isPartOf_id" TEXT,
	PRIMARY KEY ("Organization_id", "isPartOf_id"),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY("isPartOf_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Organization_isPartOf_isPartOf_id" ON "Organization_isPartOf" ("isPartOf_id");
CREATE INDEX "ix_Organization_isPartOf_Organization_id" ON "Organization_isPartOf" ("Organization_id");

CREATE TABLE "Organization_hasPart" (
	"Organization_id" TEXT,
	"hasPart_id" TEXT,
	PRIMARY KEY ("Organization_id", "hasPart_id"),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY("hasPart_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Organization_hasPart_hasPart_id" ON "Organization_hasPart" ("hasPart_id");
CREATE INDEX "ix_Organization_hasPart_Organization_id" ON "Organization_hasPart" ("Organization_id");

CREATE TABLE "Organization_references" (
	"Organization_id" TEXT,
	references_id TEXT,
	PRIMARY KEY ("Organization_id", references_id),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY(references_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Organization_references_Organization_id" ON "Organization_references" ("Organization_id");
CREATE INDEX "ix_Organization_references_references_id" ON "Organization_references" (references_id);

CREATE TABLE "Organization_dependsOn" (
	"Organization_id" TEXT,
	"dependsOn_id" TEXT,
	PRIMARY KEY ("Organization_id", "dependsOn_id"),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY("dependsOn_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Organization_dependsOn_dependsOn_id" ON "Organization_dependsOn" ("dependsOn_id");
CREATE INDEX "ix_Organization_dependsOn_Organization_id" ON "Organization_dependsOn" ("Organization_id");

CREATE TABLE "Organization_derivedFrom" (
	"Organization_id" TEXT,
	"derivedFrom_id" TEXT,
	PRIMARY KEY ("Organization_id", "derivedFrom_id"),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY("derivedFrom_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Organization_derivedFrom_Organization_id" ON "Organization_derivedFrom" ("Organization_id");
CREATE INDEX "ix_Organization_derivedFrom_derivedFrom_id" ON "Organization_derivedFrom" ("derivedFrom_id");

CREATE TABLE "Organization_about" (
	"Organization_id" TEXT,
	about_id TEXT,
	PRIMARY KEY ("Organization_id", about_id),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY(about_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Organization_about_about_id" ON "Organization_about" (about_id);
CREATE INDEX "ix_Organization_about_Organization_id" ON "Organization_about" ("Organization_id");

CREATE TABLE "Organization_sameAs" (
	"Organization_id" TEXT,
	"sameAs_id" TEXT,
	PRIMARY KEY ("Organization_id", "sameAs_id"),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY("sameAs_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Organization_sameAs_sameAs_id" ON "Organization_sameAs" ("sameAs_id");
CREATE INDEX "ix_Organization_sameAs_Organization_id" ON "Organization_sameAs" ("Organization_id");

CREATE TABLE "Organization_relatedTo" (
	"Organization_id" TEXT,
	"relatedTo_id" TEXT,
	PRIMARY KEY ("Organization_id", "relatedTo_id"),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY("relatedTo_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Organization_relatedTo_Organization_id" ON "Organization_relatedTo" ("Organization_id");
CREATE INDEX "ix_Organization_relatedTo_relatedTo_id" ON "Organization_relatedTo" ("relatedTo_id");

CREATE TABLE "Organization_definedBy" (
	"Organization_id" TEXT,
	"definedBy_id" TEXT,
	PRIMARY KEY ("Organization_id", "definedBy_id"),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY("definedBy_id") REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Organization_definedBy_definedBy_id" ON "Organization_definedBy" ("definedBy_id");
CREATE INDEX "ix_Organization_definedBy_Organization_id" ON "Organization_definedBy" ("Organization_id");

CREATE TABLE "Organization_source" (
	"Organization_id" TEXT,
	source_id TEXT,
	PRIMARY KEY ("Organization_id", source_id),
	FOREIGN KEY("Organization_id") REFERENCES "Organization" (id),
	FOREIGN KEY(source_id) REFERENCES "Concept" (id)
);
CREATE INDEX "ix_Organization_source_Organization_id" ON "Organization_source" ("Organization_id");
CREATE INDEX "ix_Organization_source_source_id" ON "Organization_source" (source_id);

