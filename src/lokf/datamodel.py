# Auto generated from lokf.yaml by pythongen.py version: 0.0.1
# Generation date: 2026-07-04T07:42:18
# Schema: lokf
#
# id: https://w3id.org/lokf/schema
# description: LOKF is a semantic, ontology-grounded profile of the Google Open Knowledge Format (OKF v0.1). It preserves OKF's authoring model — a directory of markdown files, each with a small YAML frontmatter block describing one concept — but binds every concept, field, and relationship to established web vocabularies (schema.org, W3C DCAT, and W3C PROV-O). Because the frontmatter keys are LinkML slots mapped to IRIs, a LOKF concept file, once a LinkML-generated JSON-LD @context is attached, is simultaneously human-readable markdown AND valid JSON-LD that expands losslessly to RDF triples. The entire format is defined in this single LinkML schema, from which the JSON-LD context, JSON Schema, SHACL shapes, and an OWL ontology are generated.
# license: https://creativecommons.org/licenses/by/4.0/

import dataclasses
import re
from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    time
)
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Union
)

from jsonasobj2 import (
    JsonObj,
    as_dict
)
from linkml_runtime.linkml_model.meta import (
    EnumDefinition,
    PermissibleValue,
    PvFormulaOptions
)
from linkml_runtime.utils.curienamespace import CurieNamespace
from linkml_runtime.utils.enumerations import EnumDefinitionImpl
from linkml_runtime.utils.formatutils import (
    camelcase,
    sfx,
    underscore
)
from linkml_runtime.utils.metamodelcore import (
    bnode,
    empty_dict,
    empty_list
)
from linkml_runtime.utils.slot import Slot
from linkml_runtime.utils.yamlutils import (
    YAMLRoot,
    extended_float,
    extended_int,
    extended_str
)
from rdflib import (
    Namespace,
    URIRef
)

from linkml_runtime.linkml_model.types import Boolean, Datetime, String, Uri, Uriorcurie
from linkml_runtime.utils.metamodelcore import Bool, URI, URIorCURIE, XSDDateTime

metamodel_version = "1.11.0"
version = "0.1.0"

# Namespaces
DCAT = CurieNamespace('dcat', 'http://www.w3.org/ns/dcat#')
DCTERMS = CurieNamespace('dcterms', 'http://purl.org/dc/terms/')
FOAF = CurieNamespace('foaf', 'http://xmlns.com/foaf/0.1/')
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
LOKF = CurieNamespace('lokf', 'https://w3id.org/lokf/')
ORG = CurieNamespace('org', 'http://www.w3.org/ns/org#')
OWL = CurieNamespace('owl', 'http://www.w3.org/2002/07/owl#')
PAV = CurieNamespace('pav', 'http://purl.org/pav/')
PROV = CurieNamespace('prov', 'http://www.w3.org/ns/prov#')
RDF = CurieNamespace('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
RDFS = CurieNamespace('rdfs', 'http://www.w3.org/2000/01/rdf-schema#')
SCHEMA = CurieNamespace('schema', 'http://schema.org/')
SKOS = CurieNamespace('skos', 'http://www.w3.org/2004/02/skos/core#')
VIVO = CurieNamespace('vivo', 'http://vivoweb.org/ontology/core#')
XSD = CurieNamespace('xsd', 'http://www.w3.org/2001/XMLSchema#')
DEFAULT_ = LOKF


# Types

# Class references
class ConceptId(URIorCURIE):
    pass


class DatasetId(ConceptId):
    pass


class TableId(DatasetId):
    pass


class MetricId(ConceptId):
    pass


class ServiceId(ConceptId):
    pass


class PlaybookId(ConceptId):
    pass


class PolicyId(ConceptId):
    pass


class GlossaryTermId(ConceptId):
    pass


class ReferenceId(ConceptId):
    pass


class DocumentId(ConceptId):
    pass


class RoleId(ConceptId):
    pass


class AgentId(URIorCURIE):
    pass


class PersonId(AgentId):
    pass


class OrganizationId(AgentId):
    pass


@dataclass(repr=False)
class KnowledgeBundle(YAMLRoot):
    """
    A self-contained, hierarchical collection of concept documents — the unit of distribution (a git repo, tarball, or
    subdirectory). Maps to a DCAT Catalog. When a whole bundle is serialized as a single JSON-LD document, this class
    is the tree root; individual concept files validate against Concept (or a subclass).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = LOKF["KnowledgeBundle"]
    class_class_curie: ClassVar[str] = "lokf:KnowledgeBundle"
    class_name: ClassVar[str] = "KnowledgeBundle"
    class_model_uri: ClassVar[URIRef] = LOKF.KnowledgeBundle

    lokf_version: Optional[str] = None
    okf_version: Optional[str] = None
    base_iri: Optional[Union[str, URI]] = None
    context: Optional[Union[str, URI]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    license: Optional[Union[str, URIorCURIE]] = None
    publisher: Optional[Union[dict, "Agent"]] = None
    concepts: Optional[Union[dict[Union[str, ConceptId], Union[dict, "Concept"]], list[Union[dict, "Concept"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.lokf_version is not None and not isinstance(self.lokf_version, str):
            self.lokf_version = str(self.lokf_version)

        if self.okf_version is not None and not isinstance(self.okf_version, str):
            self.okf_version = str(self.okf_version)

        if self.base_iri is not None and not isinstance(self.base_iri, URI):
            self.base_iri = URI(self.base_iri)

        if self.context is not None and not isinstance(self.context, URI):
            self.context = URI(self.context)

        if self.title is not None and not isinstance(self.title, str):
            self.title = str(self.title)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.license is not None and not isinstance(self.license, URIorCURIE):
            self.license = URIorCURIE(self.license)

        if self.publisher is not None and not isinstance(self.publisher, Agent):
            self.publisher = Agent(**as_dict(self.publisher))

        self._normalize_inlined_as_list(slot_name="concepts", slot_type=Concept, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Concept(YAMLRoot):
    """
    A single unit of knowledge within a bundle, represented as one markdown document. The abstract base of every LOKF
    type. Its own IRI (`id`) is the RDF subject; the markdown body and typed relations become triples about that
    subject.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = LOKF["Concept"]
    class_class_curie: ClassVar[str] = "lokf:Concept"
    class_name: ClassVar[str] = "Concept"
    class_model_uri: ClassVar[URIRef] = LOKF.Concept

    id: Union[str, ConceptId] = None
    type: str = None
    title: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[Union[str, URIorCURIE]] = None
    tags: Optional[Union[str, list[str]]] = empty_list()
    timestamp: Optional[Union[str, XSDDateTime]] = None
    created: Optional[Union[str, XSDDateTime]] = None
    version: Optional[str] = None
    license: Optional[Union[str, URIorCURIE]] = None
    author: Optional[Union[dict[Union[str, AgentId], Union[dict, "Agent"]], list[Union[dict, "Agent"]]]] = empty_dict()
    body: Optional[str] = None
    citations: Optional[Union[Union[dict, "Citation"], list[Union[dict, "Citation"]]]] = empty_list()
    relations: Optional[Union[Union[dict, "Relation"], list[Union[dict, "Relation"]]]] = empty_list()
    isPartOf: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    hasPart: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    references: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    dependsOn: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    derivedFrom: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    about: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    sameAs: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    relatedTo: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    definedBy: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    source: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ConceptId):
            self.id = ConceptId(self.id)

        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)

        if self.title is not None and not isinstance(self.title, str):
            self.title = str(self.title)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.resource is not None and not isinstance(self.resource, URIorCURIE):
            self.resource = URIorCURIE(self.resource)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        if self.timestamp is not None and not isinstance(self.timestamp, XSDDateTime):
            self.timestamp = XSDDateTime(self.timestamp)

        if self.created is not None and not isinstance(self.created, XSDDateTime):
            self.created = XSDDateTime(self.created)

        if self.version is not None and not isinstance(self.version, str):
            self.version = str(self.version)

        if self.license is not None and not isinstance(self.license, URIorCURIE):
            self.license = URIorCURIE(self.license)

        self._normalize_inlined_as_list(slot_name="author", slot_type=Agent, key_name="id", keyed=True)

        if self.body is not None and not isinstance(self.body, str):
            self.body = str(self.body)

        if not isinstance(self.citations, list):
            self.citations = [self.citations] if self.citations is not None else []
        self.citations = [v if isinstance(v, Citation) else Citation(**as_dict(v)) for v in self.citations]

        self._normalize_inlined_as_list(slot_name="relations", slot_type=Relation, key_name="predicate", keyed=False)

        if not isinstance(self.isPartOf, list):
            self.isPartOf = [self.isPartOf] if self.isPartOf is not None else []
        self.isPartOf = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.isPartOf]

        if not isinstance(self.hasPart, list):
            self.hasPart = [self.hasPart] if self.hasPart is not None else []
        self.hasPart = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.hasPart]

        if not isinstance(self.references, list):
            self.references = [self.references] if self.references is not None else []
        self.references = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.references]

        if not isinstance(self.dependsOn, list):
            self.dependsOn = [self.dependsOn] if self.dependsOn is not None else []
        self.dependsOn = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.dependsOn]

        if not isinstance(self.derivedFrom, list):
            self.derivedFrom = [self.derivedFrom] if self.derivedFrom is not None else []
        self.derivedFrom = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.derivedFrom]

        if not isinstance(self.about, list):
            self.about = [self.about] if self.about is not None else []
        self.about = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.about]

        if not isinstance(self.sameAs, list):
            self.sameAs = [self.sameAs] if self.sameAs is not None else []
        self.sameAs = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.sameAs]

        if not isinstance(self.relatedTo, list):
            self.relatedTo = [self.relatedTo] if self.relatedTo is not None else []
        self.relatedTo = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.relatedTo]

        if not isinstance(self.definedBy, list):
            self.definedBy = [self.definedBy] if self.definedBy is not None else []
        self.definedBy = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.definedBy]

        if not isinstance(self.source, list):
            self.source = [self.source] if self.source is not None else []
        self.source = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.source]

        super().__post_init__(**kwargs)


    def __new__(cls, *args, **kwargs):

        type_designator = "type"
        if not type_designator in kwargs:
            return super().__new__(cls,*args,**kwargs)
        else:
            type_designator_value = kwargs[type_designator]
            target_cls = cls._class_for("class_name", type_designator_value)


            if target_cls is None:
                raise ValueError(f"Wrong type designator value: class {cls.__name__} "
                                 f"has no subclass with ['class_name']='{kwargs[type_designator]}'")
            return super().__new__(target_cls,*args,**kwargs)



@dataclass(repr=False)
class Dataset(Concept):
    """
    A collection of data, published or curated for access and reuse.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["Dataset"]
    class_class_curie: ClassVar[str] = "schema:Dataset"
    class_name: ClassVar[str] = "Dataset"
    class_model_uri: ClassVar[URIRef] = LOKF.Dataset

    id: Union[str, DatasetId] = None
    type: str = None
    distribution: Optional[Union[Union[dict, "Distribution"], list[Union[dict, "Distribution"]]]] = empty_list()
    fields: Optional[Union[Union[dict, "Field"], list[Union[dict, "Field"]]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DatasetId):
            self.id = DatasetId(self.id)

        if not isinstance(self.distribution, list):
            self.distribution = [self.distribution] if self.distribution is not None else []
        self.distribution = [v if isinstance(v, Distribution) else Distribution(**as_dict(v)) for v in self.distribution]

        if not isinstance(self.fields, list):
            self.fields = [self.fields] if self.fields is not None else []
        self.fields = [v if isinstance(v, Field) else Field(**as_dict(v)) for v in self.fields]

        super().__post_init__(**kwargs)
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)


@dataclass(repr=False)
class Table(Dataset):
    """
    A structured, tabular dataset (e.g. a warehouse table or view) whose columns are described by Field objects under
    `fields`.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = LOKF["Table"]
    class_class_curie: ClassVar[str] = "lokf:Table"
    class_name: ClassVar[str] = "Table"
    class_model_uri: ClassVar[URIRef] = LOKF.Table

    id: Union[str, TableId] = None
    type: str = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, TableId):
            self.id = TableId(self.id)

        super().__post_init__(**kwargs)
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)


@dataclass(repr=False)
class Metric(Concept):
    """
    A precisely defined, measurable quantity — the canonical definition of a business or operational metric.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = LOKF["Metric"]
    class_class_curie: ClassVar[str] = "lokf:Metric"
    class_name: ClassVar[str] = "Metric"
    class_model_uri: ClassVar[URIRef] = LOKF.Metric

    id: Union[str, MetricId] = None
    type: str = None
    unit: Optional[str] = None
    formula: Optional[str] = None
    measures: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, MetricId):
            self.id = MetricId(self.id)

        if self.unit is not None and not isinstance(self.unit, str):
            self.unit = str(self.unit)

        if self.formula is not None and not isinstance(self.formula, str):
            self.formula = str(self.formula)

        if not isinstance(self.measures, list):
            self.measures = [self.measures] if self.measures is not None else []
        self.measures = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.measures]

        super().__post_init__(**kwargs)
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)


@dataclass(repr=False)
class Service(Concept):
    """
    A callable service or API endpoint.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["WebAPI"]
    class_class_curie: ClassVar[str] = "schema:WebAPI"
    class_name: ClassVar[str] = "Service"
    class_model_uri: ClassVar[URIRef] = LOKF.Service

    id: Union[str, ServiceId] = None
    type: str = None
    endpoint: Optional[Union[str, URIorCURIE]] = None
    http_method: Optional[str] = None
    documentation: Optional[Union[str, URIorCURIE]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ServiceId):
            self.id = ServiceId(self.id)

        if self.endpoint is not None and not isinstance(self.endpoint, URIorCURIE):
            self.endpoint = URIorCURIE(self.endpoint)

        if self.http_method is not None and not isinstance(self.http_method, str):
            self.http_method = str(self.http_method)

        if self.documentation is not None and not isinstance(self.documentation, URIorCURIE):
            self.documentation = URIorCURIE(self.documentation)

        super().__post_init__(**kwargs)
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)


@dataclass(repr=False)
class Playbook(Concept):
    """
    A procedure or runbook — an ordered set of steps to accomplish a task or respond to an event.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = LOKF["Playbook"]
    class_class_curie: ClassVar[str] = "lokf:Playbook"
    class_name: ClassVar[str] = "Playbook"
    class_model_uri: ClassVar[URIRef] = LOKF.Playbook

    id: Union[str, PlaybookId] = None
    type: str = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, PlaybookId):
            self.id = PlaybookId(self.id)

        super().__post_init__(**kwargs)
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)


@dataclass(repr=False)
class Policy(Concept):
    """
    A governance, compliance, or operational policy document.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = LOKF["Policy"]
    class_class_curie: ClassVar[str] = "lokf:Policy"
    class_name: ClassVar[str] = "Policy"
    class_model_uri: ClassVar[URIRef] = LOKF.Policy

    id: Union[str, PolicyId] = None
    type: str = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, PolicyId):
            self.id = PolicyId(self.id)

        super().__post_init__(**kwargs)
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)


@dataclass(repr=False)
class GlossaryTerm(Concept):
    """
    A defined term in a controlled vocabulary or glossary. Maps to schema:DefinedTerm and skos:Concept.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["DefinedTerm"]
    class_class_curie: ClassVar[str] = "schema:DefinedTerm"
    class_name: ClassVar[str] = "GlossaryTerm"
    class_model_uri: ClassVar[URIRef] = LOKF.GlossaryTerm

    id: Union[str, GlossaryTermId] = None
    type: str = None
    definition: Optional[str] = None
    abbreviation: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, GlossaryTermId):
            self.id = GlossaryTermId(self.id)

        if self.definition is not None and not isinstance(self.definition, str):
            self.definition = str(self.definition)

        if self.abbreviation is not None and not isinstance(self.abbreviation, str):
            self.abbreviation = str(self.abbreviation)

        super().__post_init__(**kwargs)
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)


@dataclass(repr=False)
class Reference(Concept):
    """
    A concept that mirrors an external source (a page, paper, or document) as a first-class citizen of the bundle so
    it can be cited and linked.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = LOKF["Reference"]
    class_class_curie: ClassVar[str] = "lokf:Reference"
    class_name: ClassVar[str] = "Reference"
    class_model_uri: ClassVar[URIRef] = LOKF.Reference

    id: Union[str, ReferenceId] = None
    type: str = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, ReferenceId):
            self.id = ReferenceId(self.id)

        super().__post_init__(**kwargs)
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)


@dataclass(repr=False)
class Document(Concept):
    """
    A general knowledge document that does not fit a more specific type.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = LOKF["Document"]
    class_class_curie: ClassVar[str] = "lokf:Document"
    class_name: ClassVar[str] = "Document"
    class_model_uri: ClassVar[URIRef] = LOKF.Document

    id: Union[str, DocumentId] = None
    type: str = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DocumentId):
            self.id = DocumentId(self.id)

        super().__post_init__(**kwargs)
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)


@dataclass(repr=False)
class Role(Concept):
    """
    A role an agent holds within an organization over a period of time — a job, appointment, or position. Reifies the
    agent–organization link so it can carry a title (roleName) and a start/end interval, following the schema.org Role
    and W3C ORG Membership patterns.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["OrganizationRole"]
    class_class_curie: ClassVar[str] = "schema:OrganizationRole"
    class_name: ClassVar[str] = "Role"
    class_model_uri: ClassVar[URIRef] = LOKF.Role

    id: Union[str, RoleId] = None
    type: str = None
    roleName: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    memberOf: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    holder: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, RoleId):
            self.id = RoleId(self.id)

        if self.roleName is not None and not isinstance(self.roleName, str):
            self.roleName = str(self.roleName)

        if self.startDate is not None and not isinstance(self.startDate, str):
            self.startDate = str(self.startDate)

        if self.endDate is not None and not isinstance(self.endDate, str):
            self.endDate = str(self.endDate)

        if not isinstance(self.memberOf, list):
            self.memberOf = [self.memberOf] if self.memberOf is not None else []
        self.memberOf = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.memberOf]

        if not isinstance(self.holder, list):
            self.holder = [self.holder] if self.holder is not None else []
        self.holder = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.holder]

        super().__post_init__(**kwargs)
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)


@dataclass(repr=False)
class Agent(YAMLRoot):
    """
    A person or organization responsible for a concept.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = PROV["Agent"]
    class_class_curie: ClassVar[str] = "prov:Agent"
    class_name: ClassVar[str] = "Agent"
    class_model_uri: ClassVar[URIRef] = LOKF.Agent

    id: Union[str, AgentId] = None
    type: str = None
    name: Optional[str] = None
    email: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)

        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, AgentId):
            self.id = AgentId(self.id)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.email is not None and not isinstance(self.email, str):
            self.email = str(self.email)

        super().__post_init__(**kwargs)


    def __new__(cls, *args, **kwargs):

        type_designator = "type"
        if not type_designator in kwargs:
            return super().__new__(cls,*args,**kwargs)
        else:
            type_designator_value = kwargs[type_designator]
            target_cls = cls._class_for("class_name", type_designator_value)


            if target_cls is None:
                raise ValueError(f"Wrong type designator value: class {cls.__name__} "
                                 f"has no subclass with ['class_name']='{kwargs[type_designator]}'")
            return super().__new__(target_cls,*args,**kwargs)



@dataclass(repr=False)
class Person(Agent):
    """
    An individual person. Usable both as an inline Agent value (author, publisher) and as a standalone Concept
    document with a body and typed relations.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["Person"]
    class_class_curie: ClassVar[str] = "schema:Person"
    class_name: ClassVar[str] = "Person"
    class_model_uri: ClassVar[URIRef] = LOKF.Person

    id: Union[str, PersonId] = None
    type: str = None
    title: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[Union[str, URIorCURIE]] = None
    tags: Optional[Union[str, list[str]]] = empty_list()
    timestamp: Optional[Union[str, XSDDateTime]] = None
    created: Optional[Union[str, XSDDateTime]] = None
    version: Optional[str] = None
    license: Optional[Union[str, URIorCURIE]] = None
    author: Optional[Union[dict[Union[str, AgentId], Union[dict, Agent]], list[Union[dict, Agent]]]] = empty_dict()
    body: Optional[str] = None
    citations: Optional[Union[Union[dict, "Citation"], list[Union[dict, "Citation"]]]] = empty_list()
    relations: Optional[Union[Union[dict, "Relation"], list[Union[dict, "Relation"]]]] = empty_list()
    isPartOf: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    hasPart: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    references: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    dependsOn: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    derivedFrom: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    about: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    sameAs: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    relatedTo: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    definedBy: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    source: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, PersonId):
            self.id = PersonId(self.id)

        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)

        if self.title is not None and not isinstance(self.title, str):
            self.title = str(self.title)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.resource is not None and not isinstance(self.resource, URIorCURIE):
            self.resource = URIorCURIE(self.resource)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        if self.timestamp is not None and not isinstance(self.timestamp, XSDDateTime):
            self.timestamp = XSDDateTime(self.timestamp)

        if self.created is not None and not isinstance(self.created, XSDDateTime):
            self.created = XSDDateTime(self.created)

        if self.version is not None and not isinstance(self.version, str):
            self.version = str(self.version)

        if self.license is not None and not isinstance(self.license, URIorCURIE):
            self.license = URIorCURIE(self.license)

        self._normalize_inlined_as_list(slot_name="author", slot_type=Agent, key_name="id", keyed=True)

        if self.body is not None and not isinstance(self.body, str):
            self.body = str(self.body)

        if not isinstance(self.citations, list):
            self.citations = [self.citations] if self.citations is not None else []
        self.citations = [v if isinstance(v, Citation) else Citation(**as_dict(v)) for v in self.citations]

        self._normalize_inlined_as_list(slot_name="relations", slot_type=Relation, key_name="predicate", keyed=False)

        if not isinstance(self.isPartOf, list):
            self.isPartOf = [self.isPartOf] if self.isPartOf is not None else []
        self.isPartOf = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.isPartOf]

        if not isinstance(self.hasPart, list):
            self.hasPart = [self.hasPart] if self.hasPart is not None else []
        self.hasPart = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.hasPart]

        if not isinstance(self.references, list):
            self.references = [self.references] if self.references is not None else []
        self.references = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.references]

        if not isinstance(self.dependsOn, list):
            self.dependsOn = [self.dependsOn] if self.dependsOn is not None else []
        self.dependsOn = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.dependsOn]

        if not isinstance(self.derivedFrom, list):
            self.derivedFrom = [self.derivedFrom] if self.derivedFrom is not None else []
        self.derivedFrom = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.derivedFrom]

        if not isinstance(self.about, list):
            self.about = [self.about] if self.about is not None else []
        self.about = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.about]

        if not isinstance(self.sameAs, list):
            self.sameAs = [self.sameAs] if self.sameAs is not None else []
        self.sameAs = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.sameAs]

        if not isinstance(self.relatedTo, list):
            self.relatedTo = [self.relatedTo] if self.relatedTo is not None else []
        self.relatedTo = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.relatedTo]

        if not isinstance(self.definedBy, list):
            self.definedBy = [self.definedBy] if self.definedBy is not None else []
        self.definedBy = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.definedBy]

        if not isinstance(self.source, list):
            self.source = [self.source] if self.source is not None else []
        self.source = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.source]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Organization(Agent):
    """
    An organization, team, or group. Usable both as an inline Agent value (publisher) and as a standalone Concept
    document with a body and typed relations.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["Organization"]
    class_class_curie: ClassVar[str] = "schema:Organization"
    class_name: ClassVar[str] = "Organization"
    class_model_uri: ClassVar[URIRef] = LOKF.Organization

    id: Union[str, OrganizationId] = None
    type: str = None
    title: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[Union[str, URIorCURIE]] = None
    tags: Optional[Union[str, list[str]]] = empty_list()
    timestamp: Optional[Union[str, XSDDateTime]] = None
    created: Optional[Union[str, XSDDateTime]] = None
    version: Optional[str] = None
    license: Optional[Union[str, URIorCURIE]] = None
    author: Optional[Union[dict[Union[str, AgentId], Union[dict, Agent]], list[Union[dict, Agent]]]] = empty_dict()
    body: Optional[str] = None
    citations: Optional[Union[Union[dict, "Citation"], list[Union[dict, "Citation"]]]] = empty_list()
    relations: Optional[Union[Union[dict, "Relation"], list[Union[dict, "Relation"]]]] = empty_list()
    isPartOf: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    hasPart: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    references: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    dependsOn: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    derivedFrom: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    about: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    sameAs: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    relatedTo: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    definedBy: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()
    source: Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, OrganizationId):
            self.id = OrganizationId(self.id)

        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        self.type = str(self.class_name)

        if self.title is not None and not isinstance(self.title, str):
            self.title = str(self.title)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.resource is not None and not isinstance(self.resource, URIorCURIE):
            self.resource = URIorCURIE(self.resource)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        if self.timestamp is not None and not isinstance(self.timestamp, XSDDateTime):
            self.timestamp = XSDDateTime(self.timestamp)

        if self.created is not None and not isinstance(self.created, XSDDateTime):
            self.created = XSDDateTime(self.created)

        if self.version is not None and not isinstance(self.version, str):
            self.version = str(self.version)

        if self.license is not None and not isinstance(self.license, URIorCURIE):
            self.license = URIorCURIE(self.license)

        self._normalize_inlined_as_list(slot_name="author", slot_type=Agent, key_name="id", keyed=True)

        if self.body is not None and not isinstance(self.body, str):
            self.body = str(self.body)

        if not isinstance(self.citations, list):
            self.citations = [self.citations] if self.citations is not None else []
        self.citations = [v if isinstance(v, Citation) else Citation(**as_dict(v)) for v in self.citations]

        self._normalize_inlined_as_list(slot_name="relations", slot_type=Relation, key_name="predicate", keyed=False)

        if not isinstance(self.isPartOf, list):
            self.isPartOf = [self.isPartOf] if self.isPartOf is not None else []
        self.isPartOf = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.isPartOf]

        if not isinstance(self.hasPart, list):
            self.hasPart = [self.hasPart] if self.hasPart is not None else []
        self.hasPart = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.hasPart]

        if not isinstance(self.references, list):
            self.references = [self.references] if self.references is not None else []
        self.references = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.references]

        if not isinstance(self.dependsOn, list):
            self.dependsOn = [self.dependsOn] if self.dependsOn is not None else []
        self.dependsOn = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.dependsOn]

        if not isinstance(self.derivedFrom, list):
            self.derivedFrom = [self.derivedFrom] if self.derivedFrom is not None else []
        self.derivedFrom = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.derivedFrom]

        if not isinstance(self.about, list):
            self.about = [self.about] if self.about is not None else []
        self.about = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.about]

        if not isinstance(self.sameAs, list):
            self.sameAs = [self.sameAs] if self.sameAs is not None else []
        self.sameAs = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.sameAs]

        if not isinstance(self.relatedTo, list):
            self.relatedTo = [self.relatedTo] if self.relatedTo is not None else []
        self.relatedTo = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.relatedTo]

        if not isinstance(self.definedBy, list):
            self.definedBy = [self.definedBy] if self.definedBy is not None else []
        self.definedBy = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.definedBy]

        if not isinstance(self.source, list):
            self.source = [self.source] if self.source is not None else []
        self.source = [v if isinstance(v, ConceptId) else ConceptId(v) for v in self.source]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Field(YAMLRoot):
    """
    A single column / property within a Table or Dataset schema. Maps to schema:PropertyValue.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["PropertyValue"]
    class_class_curie: ClassVar[str] = "schema:PropertyValue"
    class_name: ClassVar[str] = "Field"
    class_model_uri: ClassVar[URIRef] = LOKF.Field

    name: Optional[str] = None
    datatype: Optional[Union[str, "FieldType"]] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    is_key: Optional[Union[bool, Bool]] = None
    constraints: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.datatype is not None and not isinstance(self.datatype, FieldType):
            self.datatype = FieldType(self.datatype)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.unit is not None and not isinstance(self.unit, str):
            self.unit = str(self.unit)

        if self.is_key is not None and not isinstance(self.is_key, Bool):
            self.is_key = Bool(self.is_key)

        if self.constraints is not None and not isinstance(self.constraints, str):
            self.constraints = str(self.constraints)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Distribution(YAMLRoot):
    """
    A specific accessible form of a Dataset (a file, feed, or endpoint). Maps to dcat:Distribution.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = DCAT["Distribution"]
    class_class_curie: ClassVar[str] = "dcat:Distribution"
    class_name: ClassVar[str] = "Distribution"
    class_model_uri: ClassVar[URIRef] = LOKF.Distribution

    name: Optional[str] = None
    description: Optional[str] = None
    access_url: Optional[Union[str, URIorCURIE]] = None
    media_type: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.access_url is not None and not isinstance(self.access_url, URIorCURIE):
            self.access_url = URIorCURIE(self.access_url)

        if self.media_type is not None and not isinstance(self.media_type, str):
            self.media_type = str(self.media_type)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Relation(YAMLRoot):
    """
    A typed, reified relationship from the containing concept to a target, used when a predicate is not covered by one
    of the named relation slots. Modeled as an rdf:Statement (subject = the containing concept).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = RDF["Statement"]
    class_class_curie: ClassVar[str] = "rdf:Statement"
    class_name: ClassVar[str] = "Relation"
    class_model_uri: ClassVar[URIRef] = LOKF.Relation

    predicate: Union[str, "RelationType"] = None
    target: Union[str, ConceptId] = None
    relation_label: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.predicate):
            self.MissingRequiredField("predicate")
        if not isinstance(self.predicate, RelationType):
            self.predicate = RelationType(self.predicate)

        if self._is_empty(self.target):
            self.MissingRequiredField("target")
        if not isinstance(self.target, ConceptId):
            self.target = ConceptId(self.target)

        if self.relation_label is not None and not isinstance(self.relation_label, str):
            self.relation_label = str(self.relation_label)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Citation(YAMLRoot):
    """
    A reference to an external source supporting a claim in a concept's body. Attached via the schema:citation
    predicate.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = SCHEMA["CreativeWork"]
    class_class_curie: ClassVar[str] = "schema:CreativeWork"
    class_name: ClassVar[str] = "Citation"
    class_model_uri: ClassVar[URIRef] = LOKF.Citation

    title: Optional[str] = None
    url: Optional[Union[str, URIorCURIE]] = None
    description: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.title is not None and not isinstance(self.title, str):
            self.title = str(self.title)

        if self.url is not None and not isinstance(self.url, URIorCURIE):
            self.url = URIorCURIE(self.url)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        super().__post_init__(**kwargs)


# Enumerations
class RelationType(EnumDefinitionImpl):
    """
    The recommended controlled vocabulary of relationship predicates for reified Relations. Each value carries a
    `meaning` mapping to its RDF predicate in schema.org, Dublin Core Terms, PROV-O, RDFS, or OWL.
    """
    isPartOf = PermissibleValue(
        text="isPartOf",
        description="The concept is a part of the target.",
        meaning=DCTERMS["isPartOf"])
    hasPart = PermissibleValue(
        text="hasPart",
        description="The target is a part of the concept.",
        meaning=SCHEMA["hasPart"])
    references = PermissibleValue(
        text="references",
        description="The concept refers to the target.",
        meaning=DCTERMS["references"])
    dependsOn = PermissibleValue(
        text="dependsOn",
        description="The concept depends on the target.",
        meaning=DCTERMS["requires"])
    derivedFrom = PermissibleValue(
        text="derivedFrom",
        description="The concept was derived from the target.",
        meaning=PROV["wasDerivedFrom"])
    about = PermissibleValue(
        text="about",
        description="The concept is about the target.",
        meaning=SCHEMA["about"])
    sameAs = PermissibleValue(
        text="sameAs",
        description="The concept is the same entity as the target.",
        meaning=OWL["sameAs"])
    relatedTo = PermissibleValue(
        text="relatedTo",
        description="The concept is generically related to the target.",
        meaning=DCTERMS["relation"])
    wasAttributedTo = PermissibleValue(
        text="wasAttributedTo",
        description="The concept was attributed to the target agent.",
        meaning=PROV["wasAttributedTo"])
    definedBy = PermissibleValue(
        text="definedBy",
        description="The concept is formally defined by the target.",
        meaning=RDFS["isDefinedBy"])
    measures = PermissibleValue(
        text="measures",
        description="The concept (a metric) measures the target.",
        meaning=LOKF["measures"])
    joinsWith = PermissibleValue(
        text="joinsWith",
        description="The concept (a table) is joined with the target.",
        meaning=LOKF["joinsWith"])
    source = PermissibleValue(
        text="source",
        description="The concept is sourced from the target.",
        meaning=DCTERMS["source"])
    memberOf = PermissibleValue(
        text="memberOf",
        description="The concept (a role) is held within the target organization.",
        meaning=SCHEMA["memberOf"])
    holder = PermissibleValue(
        text="holder",
        description="The target agent holds this concept (a role).",
        meaning=ORG["member"])

    _defn = EnumDefinition(
        name="RelationType",
        description="""The recommended controlled vocabulary of relationship predicates for reified Relations. Each value carries a `meaning` mapping to its RDF predicate in schema.org, Dublin Core Terms, PROV-O, RDFS, or OWL.""",
    )

class FieldType(EnumDefinitionImpl):
    """
    Datatypes for dataset/table fields, each mapped to its XSD (or RDF) type.
    """
    string = PermissibleValue(
        text="string",
        meaning=XSD["string"])
    integer = PermissibleValue(
        text="integer",
        meaning=XSD["integer"])
    number = PermissibleValue(
        text="number",
        meaning=XSD["decimal"])
    boolean = PermissibleValue(
        text="boolean",
        meaning=XSD["boolean"])
    date = PermissibleValue(
        text="date",
        meaning=XSD["date"])
    datetime = PermissibleValue(
        text="datetime",
        meaning=XSD["dateTime"])
    time = PermissibleValue(
        text="time",
        meaning=XSD["time"])
    uri = PermissibleValue(
        text="uri",
        meaning=XSD["anyURI"])
    json = PermissibleValue(
        text="json",
        meaning=RDF["JSON"])

    _defn = EnumDefinition(
        name="FieldType",
        description="Datatypes for dataset/table fields, each mapped to its XSD (or RDF) type.",
    )

# Slots
class slots:
    pass

slots.id = Slot(uri=SCHEMA.identifier, name="id", curie=SCHEMA.curie('identifier'),
                   model_uri=LOKF.id, domain=None, range=URIRef)

slots.type = Slot(uri=LOKF.type, name="type", curie=LOKF.curie('type'),
                   model_uri=LOKF.type, domain=None, range=str)

slots.title = Slot(uri=SCHEMA.name, name="title", curie=SCHEMA.curie('name'),
                   model_uri=LOKF.title, domain=None, range=Optional[str])

slots.description = Slot(uri=SCHEMA.description, name="description", curie=SCHEMA.curie('description'),
                   model_uri=LOKF.description, domain=None, range=Optional[str])

slots.resource = Slot(uri=SCHEMA.url, name="resource", curie=SCHEMA.curie('url'),
                   model_uri=LOKF.resource, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.tags = Slot(uri=SCHEMA.keywords, name="tags", curie=SCHEMA.curie('keywords'),
                   model_uri=LOKF.tags, domain=None, range=Optional[Union[str, list[str]]])

slots.timestamp = Slot(uri=SCHEMA.dateModified, name="timestamp", curie=SCHEMA.curie('dateModified'),
                   model_uri=LOKF.timestamp, domain=None, range=Optional[Union[str, XSDDateTime]])

slots.created = Slot(uri=SCHEMA.dateCreated, name="created", curie=SCHEMA.curie('dateCreated'),
                   model_uri=LOKF.created, domain=None, range=Optional[Union[str, XSDDateTime]])

slots.version = Slot(uri=SCHEMA.version, name="version", curie=SCHEMA.curie('version'),
                   model_uri=LOKF.version, domain=None, range=Optional[str])

slots.license = Slot(uri=SCHEMA.license, name="license", curie=SCHEMA.curie('license'),
                   model_uri=LOKF.license, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.author = Slot(uri=SCHEMA.author, name="author", curie=SCHEMA.curie('author'),
                   model_uri=LOKF.author, domain=None, range=Optional[Union[dict[Union[str, AgentId], Union[dict, Agent]], list[Union[dict, Agent]]]])

slots.publisher = Slot(uri=SCHEMA.publisher, name="publisher", curie=SCHEMA.curie('publisher'),
                   model_uri=LOKF.publisher, domain=None, range=Optional[Union[dict, Agent]])

slots.body = Slot(uri=SCHEMA.text, name="body", curie=SCHEMA.curie('text'),
                   model_uri=LOKF.body, domain=None, range=Optional[str])

slots.citations = Slot(uri=SCHEMA.citation, name="citations", curie=SCHEMA.curie('citation'),
                   model_uri=LOKF.citations, domain=None, range=Optional[Union[Union[dict, Citation], list[Union[dict, Citation]]]])

slots.concepts = Slot(uri=DCAT.dataset, name="concepts", curie=DCAT.curie('dataset'),
                   model_uri=LOKF.concepts, domain=None, range=Optional[Union[dict[Union[str, ConceptId], Union[dict, Concept]], list[Union[dict, Concept]]]])

slots.relations = Slot(uri=LOKF.relations, name="relations", curie=LOKF.curie('relations'),
                   model_uri=LOKF.relations, domain=None, range=Optional[Union[Union[dict, Relation], list[Union[dict, Relation]]]])

slots.isPartOf = Slot(uri=DCTERMS.isPartOf, name="isPartOf", curie=DCTERMS.curie('isPartOf'),
                   model_uri=LOKF.isPartOf, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.hasPart = Slot(uri=SCHEMA.hasPart, name="hasPart", curie=SCHEMA.curie('hasPart'),
                   model_uri=LOKF.hasPart, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.references = Slot(uri=DCTERMS.references, name="references", curie=DCTERMS.curie('references'),
                   model_uri=LOKF.references, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.dependsOn = Slot(uri=DCTERMS.requires, name="dependsOn", curie=DCTERMS.curie('requires'),
                   model_uri=LOKF.dependsOn, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.derivedFrom = Slot(uri=PROV.wasDerivedFrom, name="derivedFrom", curie=PROV.curie('wasDerivedFrom'),
                   model_uri=LOKF.derivedFrom, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.about = Slot(uri=SCHEMA.about, name="about", curie=SCHEMA.curie('about'),
                   model_uri=LOKF.about, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.sameAs = Slot(uri=SCHEMA.sameAs, name="sameAs", curie=SCHEMA.curie('sameAs'),
                   model_uri=LOKF.sameAs, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.relatedTo = Slot(uri=DCTERMS.relation, name="relatedTo", curie=DCTERMS.curie('relation'),
                   model_uri=LOKF.relatedTo, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.definedBy = Slot(uri=RDFS.isDefinedBy, name="definedBy", curie=RDFS.curie('isDefinedBy'),
                   model_uri=LOKF.definedBy, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.source = Slot(uri=DCTERMS.source, name="source", curie=DCTERMS.curie('source'),
                   model_uri=LOKF.source, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.predicate = Slot(uri=RDF.predicate, name="predicate", curie=RDF.curie('predicate'),
                   model_uri=LOKF.predicate, domain=None, range=Union[str, "RelationType"])

slots.target = Slot(uri=RDF.object, name="target", curie=RDF.curie('object'),
                   model_uri=LOKF.target, domain=None, range=Union[str, ConceptId])

slots.relation_label = Slot(uri=RDFS.label, name="relation_label", curie=RDFS.curie('label'),
                   model_uri=LOKF.relation_label, domain=None, range=Optional[str])

slots.distribution = Slot(uri=DCAT.distribution, name="distribution", curie=DCAT.curie('distribution'),
                   model_uri=LOKF.distribution, domain=None, range=Optional[Union[Union[dict, Distribution], list[Union[dict, Distribution]]]])

slots.fields = Slot(uri=LOKF.field, name="fields", curie=LOKF.curie('field'),
                   model_uri=LOKF.fields, domain=None, range=Optional[Union[Union[dict, Field], list[Union[dict, Field]]]])

slots.name = Slot(uri=SCHEMA.name, name="name", curie=SCHEMA.curie('name'),
                   model_uri=LOKF.name, domain=None, range=Optional[str])

slots.email = Slot(uri=SCHEMA.email, name="email", curie=SCHEMA.curie('email'),
                   model_uri=LOKF.email, domain=None, range=Optional[str])

slots.datatype = Slot(uri=LOKF.datatype, name="datatype", curie=LOKF.curie('datatype'),
                   model_uri=LOKF.datatype, domain=None, range=Optional[Union[str, "FieldType"]])

slots.unit = Slot(uri=SCHEMA.unitText, name="unit", curie=SCHEMA.curie('unitText'),
                   model_uri=LOKF.unit, domain=None, range=Optional[str])

slots.is_key = Slot(uri=LOKF.isKey, name="is_key", curie=LOKF.curie('isKey'),
                   model_uri=LOKF.is_key, domain=None, range=Optional[Union[bool, Bool]])

slots.constraints = Slot(uri=LOKF.constraints, name="constraints", curie=LOKF.curie('constraints'),
                   model_uri=LOKF.constraints, domain=None, range=Optional[str])

slots.access_url = Slot(uri=DCAT.accessURL, name="access_url", curie=DCAT.curie('accessURL'),
                   model_uri=LOKF.access_url, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.media_type = Slot(uri=DCAT.mediaType, name="media_type", curie=DCAT.curie('mediaType'),
                   model_uri=LOKF.media_type, domain=None, range=Optional[str])

slots.formula = Slot(uri=LOKF.formula, name="formula", curie=LOKF.curie('formula'),
                   model_uri=LOKF.formula, domain=None, range=Optional[str])

slots.measures = Slot(uri=LOKF.measures, name="measures", curie=LOKF.curie('measures'),
                   model_uri=LOKF.measures, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.endpoint = Slot(uri=SCHEMA.url, name="endpoint", curie=SCHEMA.curie('url'),
                   model_uri=LOKF.endpoint, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.http_method = Slot(uri=SCHEMA.httpMethod, name="http_method", curie=SCHEMA.curie('httpMethod'),
                   model_uri=LOKF.http_method, domain=None, range=Optional[str])

slots.documentation = Slot(uri=SCHEMA.documentation, name="documentation", curie=SCHEMA.curie('documentation'),
                   model_uri=LOKF.documentation, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.definition = Slot(uri=SKOS.definition, name="definition", curie=SKOS.curie('definition'),
                   model_uri=LOKF.definition, domain=None, range=Optional[str])

slots.abbreviation = Slot(uri=SCHEMA.alternateName, name="abbreviation", curie=SCHEMA.curie('alternateName'),
                   model_uri=LOKF.abbreviation, domain=None, range=Optional[str])

slots.roleName = Slot(uri=SCHEMA.roleName, name="roleName", curie=SCHEMA.curie('roleName'),
                   model_uri=LOKF.roleName, domain=None, range=Optional[str])

slots.startDate = Slot(uri=SCHEMA.startDate, name="startDate", curie=SCHEMA.curie('startDate'),
                   model_uri=LOKF.startDate, domain=None, range=Optional[str])

slots.endDate = Slot(uri=SCHEMA.endDate, name="endDate", curie=SCHEMA.curie('endDate'),
                   model_uri=LOKF.endDate, domain=None, range=Optional[str])

slots.memberOf = Slot(uri=SCHEMA.memberOf, name="memberOf", curie=SCHEMA.curie('memberOf'),
                   model_uri=LOKF.memberOf, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.holder = Slot(uri=ORG.member, name="holder", curie=ORG.curie('member'),
                   model_uri=LOKF.holder, domain=None, range=Optional[Union[Union[str, ConceptId], list[Union[str, ConceptId]]]])

slots.url = Slot(uri=SCHEMA.url, name="url", curie=SCHEMA.curie('url'),
                   model_uri=LOKF.url, domain=None, range=Optional[Union[str, URIorCURIE]])

slots.lokf_version = Slot(uri=LOKF.lokfVersion, name="lokf_version", curie=LOKF.curie('lokfVersion'),
                   model_uri=LOKF.lokf_version, domain=None, range=Optional[str])

slots.okf_version = Slot(uri=LOKF.okfVersion, name="okf_version", curie=LOKF.curie('okfVersion'),
                   model_uri=LOKF.okf_version, domain=None, range=Optional[str])

slots.base_iri = Slot(uri=LOKF.baseIri, name="base_iri", curie=LOKF.curie('baseIri'),
                   model_uri=LOKF.base_iri, domain=None, range=Optional[Union[str, URI]])

slots.context = Slot(uri=LOKF.context, name="context", curie=LOKF.curie('context'),
                   model_uri=LOKF.context, domain=None, range=Optional[Union[str, URI]])

