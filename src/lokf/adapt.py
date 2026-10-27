"""Adapt a published LinkML vocabulary so a LOKF domain schema can import it.

A domain schema imports ``lokf.yaml`` and a vocabulary side by side (SPEC
§6.2). LinkML merges the two into one namespace, so the vocabulary's copy must
share no element name with ``lokf.yaml``. Its concepts must also descend from
``Concept`` to join the bundle's concept union. :func:`adapt` makes that copy
from the vocabulary as published, in seven mechanical moves:

1. fold the vocabulary's own imports into one file, so the copy stands alone;
2. drop the two slots that cannot coexist with LOKF's, an identifier (LOKF's
   ``id`` is the subject) and an ``rdf:type`` slot (LOKF's ``type`` designates
   the class), and point what referenced them at LOKF's;
3. detach any slot that inherited from a dropped one, and demote every other
   type designator to an ordinary slot;
4. rename every other shared name and pin its IRI, so biolink's ``name``
   becomes ``biolink_name`` and still projects as ``rdfs:label``;
5. fold a slot or class attribute into LOKF's when it means what one of
   LOKF's slots means: its IRI matches, or ``--fold`` names it. Unless
   ``--keep`` holds it back, drop it as step 2 does. Copy its constraints,
   such as ``required`` or ``pattern``, into a ``slot_usage`` on every class
   that used it, so those classes still enforce them;
6. re-root the vocabulary's top classes on ``Concept``, and warn of an
   attribute on one of them that shadows a slot ``Concept`` lists;
7. give classes CamelCase names and slots underscored ones: the forms ``type``,
   frontmatter keys and the JSON-LD context use.

Everything works on the plain YAML dict. SchemaView, from the runtime the
core install already has, verifies the result beside ``lokf.yaml``.
"""
from __future__ import annotations

import pathlib
from copy import deepcopy
import tempfile
from dataclasses import dataclass, field

import yaml
from curies import Converter, Record
from linkml_runtime.utils.formatutils import camelcase, underscore

from lokf.schema import load_schema, schema_path

_SECTIONS = ("classes", "slots", "enums", "types", "subsets")
_RDF_TYPE = {"rdf:type", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"}

# Which metamodel fields name a class, a slot or another element. Enumerated
# from linkml_runtime.linkml_model.meta (ClassDefinition / SlotDefinition
# field types), so a rename follows every reference LinkML itself reads.
_CLASS_REFS_ON_CLASS = ("is_a", "mixins", "apply_to", "union_of", "disjoint_with")
_SLOT_REFS_ON_CLASS = ("slots", "defining_slots")
_SLOT_MAPS_ON_CLASS = ("slot_usage", "attributes", "slot_conditions")
_ELEMENT_REFS_ON_SLOT = ("range", "domain", "domain_of")
_SLOT_REFS_ON_SLOT = (
    "is_a", "mixins", "apply_to", "subproperty_of", "inverse", "transitive_form_of",
    "reflexive_transitive_form_of", "slot_group", "disjoint_with", "union_of",
)
_EXPRESSIONS = ("any_of", "all_of", "exactly_one_of", "none_of")
_CONDITIONS = ("preconditions", "postconditions", "elseconditions")
# What a slot_usage may still say about a slot LOKF now serves (id, type, a fold).
_USAGE_KEEP = (
    "required", "recommended", "description", "comments", "notes", "examples",
    "values_from", "see_also", "in_subset", "aliases",
)
# What a fold copies from the folded slot into a slot_usage on every class
# that used it: the constraints the vocabulary enforced, which now narrow
# LOKF's slot on that class alone. A slot_usage the class already had
# keeps these too and wins over the definition's, as it did in the vocabulary.
# `multivalued` is not carried: it is a shape, not a refinement, and
# find_folds refuses a fold whose shape differs from the target's.
_USAGE_CARRY = (
    "required", "pattern", "range", "minimum_value", "maximum_value", "values_from",
    "range_expression", "enum_range", "bindings", "value_presence", "equals_string",
    "equals_string_in", "equals_number", "equals_expression", "exact_cardinality",
    "minimum_cardinality", "maximum_cardinality", "has_member", "all_members",
    "none_of", "exactly_one_of", "any_of", "all_of", "array", "unit",
    "id_prefixes", "id_prefixes_are_closed", "list_elements_unique", "list_elements_ordered",
)
# LinkML's built-in types whose values are strings (`repr: str` in
# linkml:types), each a narrower lexical form of `string`.
_STRING_TYPES = frozenset({
    "string", "uriorcurie", "uri", "curie", "ncname", "date", "datetime", "time",
    "date_or_datetime", "objectidentifier", "nodeidentifier", "jsonpointer", "jsonpath", "sparqlpath",
})
# The built-in types a carried range may narrow a target of that type to:
# those whose values are a subset of the target's. A number or a boolean is
# not a string, so neither folds into `title`.
_NARROWER = {
    "string": _STRING_TYPES,
    "uriorcurie": frozenset({"uri", "curie"}),
    "date_or_datetime": frozenset({"date", "datetime"}),
}
# IRI prefixes whose owner publishes them in two forms. schema.org serves its
# terms at http://schema.org/ and at https://schema.org/ and states that both
# name the same terms, so a vocabulary bound to the https form (Bioregistry's)
# folds as one bound to the http form does. Every other IRI is compared as
# written: RFC 3986 does not equate the schemes, and a vocabulary may mean
# the difference.
_IRI_SYNONYMS = (("http://schema.org/", "https://schema.org/"),)


@dataclass
class Renames:
    """Old name -> new name, per kind. ``elements`` covers classes, enums and
    types, which share the ``range`` position."""

    elements: dict[str, str] = field(default_factory=dict)
    slots: dict[str, str] = field(default_factory=dict)
    subsets: dict[str, str] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.elements or self.slots or self.subsets)


@dataclass
class Report:
    """What :func:`adapt` did, in the order it did it."""

    source: str = ""
    folded: list[str] = field(default_factory=list)
    dropped: dict[str, str] = field(default_factory=dict)
    detached: list[str] = field(default_factory=list)
    demoted: list[str] = field(default_factory=list)
    renamed: dict[str, str] = field(default_factory=dict)
    folded_into: dict[str, str] = field(default_factory=dict)
    kept: list[str] = field(default_factory=list)
    roots: list[str] = field(default_factory=list)
    tree_roots: list[str] = field(default_factory=list)
    collided: dict[str, str] = field(default_factory=dict)
    canonical: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        def pairs(m: dict[str, str]) -> str:
            return ", ".join(a if a == b else f"{a} -> {b}" for a, b in m.items()) or "none"

        out = [
            f"folded imports:          {', '.join(self.folded) or 'none'}",
            f"dropped for LOKF's:      {pairs(self.dropped)}",
            f"detached from a dropped: {', '.join(self.detached) or 'none'}",
            f"demoted designators:     {', '.join(self.demoted) or 'none'}",
            f"renamed, IRIs kept:      {pairs(self.renamed)}",
            f"folded into LOKF's:      {pairs(self.folded_into)}",
            f"kept from folding:       {', '.join(self.kept) or 'none'}",
            f"re-rooted on Concept:    {', '.join(self.roots) or 'none (pass --root)'}",
            f"tree_root removed:       {', '.join(self.tree_roots) or 'none'}",
            f"one canonical form:      {pairs(self.collided)}",
            f"canonical names:         {len(self.canonical)}",
        ]
        out.extend(f"warning: {w}" for w in self.warnings)
        out.extend(f"problem: {p}" for p in self.problems)
        return out


# --- 1. fold imports ---------------------------------------------------------

def _follows(name: str) -> bool:
    return not name.startswith("linkml:")


def fold_imports(vocab: pathlib.Path) -> tuple[dict, list[str]]:
    """The vocabulary with every schema it imports (transitively, except
    ``linkml:`` ones) merged into it. The importing schema's definitions win
    on a shared name, as they do for LinkML. Returns the dict and the imports
    folded. An import is a sibling ``<name>.yaml``, as LinkML resolves it."""
    root = yaml.safe_load(vocab.read_text(encoding="utf-8"))
    if not isinstance(root, dict):
        raise ValueError(f"{vocab.name} is not a LinkML schema (a YAML mapping)")
    folded: list[str] = []
    seen = {vocab.resolve()}
    root_prefix = root.get("default_prefix")

    def pin_iris(schema: dict) -> None:
        # An element's IRI derives from the default_prefix of the file that
        # defines it; folded into a file with another, it must say so itself.
        theirs = schema.get("default_prefix")
        if not theirs or theirs == root_prefix:
            return
        for section, key, form in (
            ("classes", "class_uri", camelcase), ("slots", "slot_uri", underscore), ("enums", "enum_uri", camelcase),
        ):
            for name, elem in (schema.get(section) or {}).items():
                if isinstance(elem, dict):
                    elem.setdefault(key, f"{theirs}:{form(name)}")

    def folded_view(schema: dict, here: pathlib.Path) -> dict:
        """*schema* over everything it imports: a schema's own definitions win
        over its imports', and a later import over an earlier one, as LinkML
        resolves them."""
        acc: dict = {}
        for name in schema.get("imports") or []:
            if not _follows(name):
                continue
            path = (here / name).with_suffix(".yaml") if not name.endswith(".yaml") else here / name
            path = path.resolve()
            if not path.exists():
                raise FileNotFoundError(f"{vocab.name} imports {name!r}, but {path} does not exist")
            if path in seen:
                continue
            seen.add(path)
            part = yaml.safe_load(path.read_text(encoding="utf-8"))
            for section, defs in folded_view(part, path.parent).items():
                acc[section] = {**(acc.get(section) or {}), **defs}
            folded.append(name)
        pin_iris(schema)
        for section in (*_SECTIONS, "prefixes"):
            if schema.get(section):
                acc[section] = {**(acc.get(section) or {}), **schema[section]}
        return acc

    for section, defs in folded_view(root, vocab.parent).items():
        root[section] = defs
    root["imports"] = [i for i in root.get("imports") or [] if not _follows(i)]
    if "linkml:types" not in root["imports"]:
        root["imports"].insert(0, "linkml:types")
    root["imports"].append("lokf")
    return root, folded


# --- 2..7. the moves ----------------------------------------------------------

def _norm(section: str, name: str) -> str:
    if section == "classes":
        return camelcase(name)
    if section == "slots":
        return underscore(name)
    return name


def shared_names(schema: dict, lokf: dict) -> dict[str, list[str]]:
    """Per section, the vocabulary's names ``lokf.yaml`` defines anywhere.
    LinkML keeps classes, slots, enums, types and subsets in one namespace (a
    type and a slot called ``unit`` is an overlap it warns about), and
    compares names as it normalises them (``named thing`` is ``NamedThing``)."""
    raw = {n for section in _SECTIONS for n in (lokf.get(section) or {})}
    out: dict[str, list[str]] = {}
    for section in _SECTIONS:
        # Across sections LinkML compares names as written (LOKF's own `Source`
        # class and `source` slot coexist); within one, as it derives them.
        same = {_norm(section, n) for n in (lokf.get(section) or {})}
        hits = [n for n in (schema.get(section) or {}) if n in raw or _norm(section, n) in same]
        if hits:
            out[section] = hits
    return out


def _map(value, mapping: dict[str, str]):
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        return [mapping.get(v, v) if isinstance(v, str) else v for v in value]
    return value


def _rewrite_slot_expr(expr: dict, r: Renames) -> None:
    for key in _ELEMENT_REFS_ON_SLOT:
        if key in expr:
            expr[key] = _map(expr[key], r.elements)
    for key in _SLOT_REFS_ON_SLOT:
        if key in expr:
            expr[key] = _map(expr[key], r.slots)
    if "in_subset" in expr:
        expr["in_subset"] = _map(expr["in_subset"], r.subsets)
    for key in _EXPRESSIONS:
        for sub in expr.get(key) or []:
            if isinstance(sub, dict):
                _rewrite_slot_expr(sub, r)


def _rewrite_class_expr(cls: dict, r: Renames) -> None:
    for key in _CLASS_REFS_ON_CLASS:
        if key in cls:
            cls[key] = _map(cls[key], r.elements)
    for key in _SLOT_REFS_ON_CLASS:
        if key in cls:
            cls[key] = _map(cls[key], r.slots)
    if "in_subset" in cls:
        cls["in_subset"] = _map(cls["in_subset"], r.subsets)
    for key in _SLOT_MAPS_ON_CLASS:
        if isinstance(cls.get(key), dict):
            cls[key] = {r.slots.get(n, n): v for n, v in cls[key].items()}
            for v in cls[key].values():
                if isinstance(v, dict):
                    _rewrite_slot_expr(v, r)
    for key in _EXPRESSIONS:
        for sub in cls.get(key) or []:
            if isinstance(sub, dict):
                _rewrite_class_expr(sub, r)
    for rule in cls.get("rules") or []:
        for part in _CONDITIONS:
            if isinstance(rule.get(part), dict):
                _rewrite_class_expr(rule[part], r)
    for rule in cls.get("classification_rules") or []:
        if isinstance(rule, dict):
            _rewrite_class_expr(rule, r)
    for uk in (cls.get("unique_keys") or {}).values():
        if isinstance(uk, dict) and "unique_key_slots" in uk:
            uk["unique_key_slots"] = _map(uk["unique_key_slots"], r.slots)


def rewrite_refs(schema: dict, r: Renames) -> None:
    """Follow *r* through every reference in *schema*, definitions included:
    the keys of each section are renamed too."""
    if not r:
        return
    for section, mapping in (
        ("classes", r.elements), ("enums", r.elements), ("types", r.elements),
        ("slots", r.slots), ("subsets", r.subsets),
    ):
        if isinstance(schema.get(section), dict):
            schema[section] = {mapping.get(n, n): v for n, v in schema[section].items()}
    for cls in (schema.get("classes") or {}).values():
        if isinstance(cls, dict):
            _rewrite_class_expr(cls, r)
    for slot in (schema.get("slots") or {}).values():
        if isinstance(slot, dict):
            _rewrite_slot_expr(slot, r)
    for typ in (schema.get("types") or {}).values():
        if isinstance(typ, dict) and "typeof" in typ:
            typ["typeof"] = _map(typ["typeof"], r.elements)
    if "default_range" in schema:
        schema["default_range"] = _map(schema["default_range"], r.elements)


def drop_twins(schema: dict) -> tuple[dict[str, str], list[str]]:
    """Delete the vocabulary's identifier and ``rdf:type`` slots. A class can
    carry one of each, and LOKF's ``id`` and ``type`` are those, so what
    listed the vocabulary's now lists LOKF's. A slot that inherited from one
    is detached instead, or it would inherit LOKF's designator (biolink's
    ``category: is_a: type``). Returns (dropped -> LOKF's name, detached)."""
    slots = schema.get("slots") or {}
    dropped = {}
    for name, slot in slots.items():
        if not isinstance(slot, dict):
            continue
        if slot.get("identifier"):
            dropped[name] = "id"
        elif slot.get("slot_uri") in _RDF_TYPE or (
            slot.get("designates_type") and underscore(name) == "type"
        ):
            dropped[name] = "type"
    detached = []
    for name, slot in slots.items():
        if name in dropped or not isinstance(slot, dict):
            continue
        if slot.get("is_a") in dropped:
            del slot["is_a"]
            detached.append(name)
        if any(m in dropped for m in slot.get("mixins") or []):
            slot["mixins"] = [m for m in slot["mixins"] if m not in dropped]
            if not slot["mixins"]:
                del slot["mixins"]
            if name not in detached:
                detached.append(name)
    for name in dropped:
        del slots[name]
    # An identifier declared as a class attribute is the same twin: the class
    # lists LOKF's `id` instead.
    for cls in (schema.get("classes") or {}).values():
        for name, attr in list((cls.get("attributes") or {}).items()):
            if isinstance(attr, dict) and attr.get("identifier"):
                del cls["attributes"][name]
                cls["slots"] = list(cls.get("slots") or []) + ["id"]
                dropped[name] = "id"
    _point_at_lokf(schema, dropped)
    return dropped, detached


def _conjoin(left: dict, right: dict) -> dict:
    """Keep both restrictions when distinct source fields become one slot."""
    if not left:
        return deepcopy(right)
    if not right or left == right:
        return deepcopy(left)
    conflicts = {k for k in left.keys() & right.keys() if left[k] != right[k]}
    if not conflicts:
        return {**deepcopy(left), **deepcopy(right)}
    metadata = {k: deepcopy(v) for k, v in {**left, **right}.items() if k not in _USAGE_CARRY}
    constraints = [{k: deepcopy(v) for k, v in side.items() if k in _USAGE_CARRY}
                   for side in (left, right)]
    return {**metadata, "all_of": [c for c in constraints if c]}


def _point_at_lokf(schema: dict, served: dict[str, str], keep: tuple[str, ...] = _USAGE_KEEP) -> None:
    """What referenced a vocabulary slot in *served* now references LOKF's,
    which the copy gets through its `lokf` import. A slot_usage on it keeps
    only the keys in *keep*, never one that would reshape LOKF's slot."""
    for cls in (schema.get("classes") or {}).values():
        for name, usage in list((cls.get("slot_usage") or {}).items()):
            if name in served and isinstance(usage, dict):
                cls["slot_usage"][name] = {k: v for k, v in usage.items() if k in keep}
    combined = []
    for cls in (schema.get("classes") or {}).values():
        grouped = {}
        for name, usage in (cls.get("slot_usage") or {}).items():
            target = served.get(name, name)
            grouped[target] = _conjoin(grouped.get(target, {}), usage or {})
        combined.append((cls, grouped))
    rewrite_refs(schema, Renames(slots=dict(served)))
    for cls, grouped in combined:
        if grouped:
            for usage in grouped.values():
                _rewrite_slot_expr(usage, Renames(slots=dict(served)))
            cls["slot_usage"] = grouped
    for cls in (schema.get("classes") or {}).values():
        for key in _SLOT_REFS_ON_CLASS:
            if isinstance(cls.get(key), list):
                cls[key] = list(dict.fromkeys(cls[key]))


def demote_designators(schema: dict) -> list[str]:
    """Strip ``designates_type`` (and ``is_class_field``) from every remaining
    slot: LOKF's ``type`` is the one designator a concept has."""
    demoted = []
    for name, slot in (schema.get("slots") or {}).items():
        if isinstance(slot, dict) and slot.get("designates_type"):
            slot.pop("designates_type", None)
            slot.pop("is_class_field", None)
            demoted.append(name)
    for cls in (schema.get("classes") or {}).values():
        for key in ("slot_usage", "attributes"):
            for name, usage in (cls.get(key) or {}).items():
                if isinstance(usage, dict) and usage.get("designates_type"):
                    usage.pop("designates_type", None)
                    usage.pop("is_class_field", None)
                    if name not in demoted:
                        demoted.append(name)
    return demoted


def _default_curie_base(schema: dict) -> str:
    """What LinkML puts before an element's name to derive its IRI: the
    default prefix as a CURIE prefix, the default prefix itself when it is an
    IRI, else the schema id."""
    prefix = schema.get("default_prefix")
    if prefix and prefix in (schema.get("prefixes") or {}):
        return f"{prefix}:"
    if prefix and "://" in prefix:
        return prefix if prefix.endswith(("/", "#")) else prefix + "/"
    return str(schema.get("id", "")).rstrip("/#") + "/"


def rename_shared(schema: dict, shared: dict[str, list[str]], prefix: str) -> dict[str, str]:
    """Give every shared element another LinkML name and pin the IRI it had,
    explicitly where the vocabulary left it to its default prefix. The old
    name goes to ``aliases``. Slots, types and subsets become
    ``<prefix>_<name>``, classes and enums ``<Prefix><Name>``."""
    base = _default_curie_base(schema)
    r = Renames()
    for section, names in shared.items():
        for old in names:
            elem = schema[section][old]
            if not isinstance(elem, dict):
                elem = schema[section][old] = {}
            if section == "slots":
                new = f"{underscore(prefix)}_{underscore(old)}"
                elem.setdefault("slot_uri", f"{base}{underscore(old)}")
                r.slots[old] = new
            elif section == "subsets":
                new = f"{underscore(prefix)}_{underscore(old)}"
                r.subsets[old] = new
            elif section == "types":
                # A type's `uri` is its datatype, which `typeof` supplies; nothing to pin.
                new = f"{underscore(prefix)}_{underscore(old)}"
                r.elements[old] = new
            else:
                new = f"{camelcase(prefix)}{camelcase(old)}"
                uri_key = {"classes": "class_uri", "enums": "enum_uri"}[section]
                elem.setdefault(uri_key, f"{base}{camelcase(old)}")
                r.elements[old] = new
            if new in schema[section]:
                raise ValueError(f"cannot rename {section[:-1]} {old!r} to {new!r}: the vocabulary has one")
            aliases = list(elem.get("aliases") or [])
            if old not in aliases:
                elem["aliases"] = aliases + [old]
    rewrite_refs(schema, r)
    return {**r.elements, **r.slots, **r.subsets}


def _expand(curie: str, prefixes: dict) -> str:
    """*curie* as a full IRI where *prefixes* binds its prefix, else as written."""
    if "://" in curie or ":" not in curie:
        return curie
    pfx, local = curie.split(":", 1)
    base = prefixes.get(pfx)
    if isinstance(base, dict):
        base = base.get("prefix_reference")
    return f"{base}{local}" if base else curie


def _converter(prefixes: dict) -> Converter:
    """A ``curies`` converter over *prefixes* that reads each tuple in
    :data:`_IRI_SYNONYMS` as one IRI prefix. Two CURIE prefixes bound to one
    IRI prefix (biolink's ``dct`` beside LOKF's ``dcterms``) share a record,
    as curies requires."""
    first = {form: forms[0] for forms in _IRI_SYNONYMS for form in forms}
    names: dict[str, list[str]] = {}
    for pfx, ref in prefixes.items():
        if isinstance(ref, dict):
            ref = ref.get("prefix_reference")
        if isinstance(ref, str) and ref:
            names.setdefault(first.get(ref, ref), []).append(pfx)
    return Converter([
        Record(
            prefix=pfxs[0], prefix_synonyms=pfxs[1:], uri_prefix=base,
            uri_prefix_synonyms=[f for forms in _IRI_SYNONYMS if base in forms for f in forms if f != base],
        )
        for base, pfxs in names.items()
    ])


def _refines(v: str, t: str, schema: dict, lokf: dict) -> bool:
    """Whether a range *v* narrows LOKF's range *t*: *v* is *t*; a type whose
    ``typeof`` chain reaches *t* or a built-in :data:`_NARROWER` admits for
    it; or, for a class *t*, a class under it in ``lokf.yaml``. A class or an
    enum of the vocabulary's own never does: LOKF does not read it, and it
    would make a concept's value something LOKF's slot does not take."""
    if v == t:
        return True
    if v in (schema.get("classes") or {}) or v in (schema.get("enums") or {}):
        return False
    lokf_classes = lokf.get("classes") or {}
    if t in lokf_classes:
        seen: set[str] = set()
        while v in lokf_classes and v not in seen:
            if v == t:
                return True
            seen.add(v)
            v = (lokf_classes[v] or {}).get("is_a")
        return False
    if t in (lokf.get("enums") or {}):
        return False
    admitted = {t, *_NARROWER.get(t, ())}
    types = {**(lokf.get("types") or {}), **(schema.get("types") or {})}
    seen = set()
    while v and v not in seen:
        if v in admitted:
            return True
        seen.add(v)
        v = (types.get(v) or {}).get("typeof")
    return False


def _fold_view(schema: dict):
    """Build one isolated view per folding pass."""
    from linkml_runtime.linkml_model import SchemaDefinition
    from linkml_runtime.utils.schemaview import SchemaView

    data = deepcopy(schema)
    data.setdefault("id", "urn:lokf:adapt:probe")
    data.setdefault("name", "adapt_probe")
    data["imports"] = ["linkml:types"]
    return SchemaView(SchemaDefinition(**data))


def _effective_slot(schema: dict, name: str, cname: str | None = None, view=None) -> dict:
    """Materialize inheritance with LinkML's own rules, retaining authored fields."""
    from linkml_runtime.dumpers import yaml_dumper
    view = view or _fold_view(schema)
    fields = set()
    if name in (schema.get("slots") or {}):
        for parent in view.slot_ancestors(name):
            fields.update((schema.get("slots") or {}).get(parent) or {})
    if cname:
        for parent in view.class_ancestors(cname):
            cls = (schema.get("classes") or {}).get(parent) or {}
            fields.update((cls.get("attributes") or {}).get(name) or {})
            fields.update((cls.get("slot_usage") or {}).get(name) or {})
    if schema.get("default_range"):
        fields.add("range")
    if "structured_pattern" in fields:
        fields.add("pattern")
    induced = yaml.safe_load(yaml_dumper.dumps(view.induced_slot(name, cname)))
    return {k: v for k, v in induced.items() if k in fields}


def _shape_conflict(elem: dict, usages: list[tuple[str, dict]], target: str, schema: dict, lokf: dict) -> str | None:
    """Why *elem* cannot fold into LOKF's *target*, or ``None``: the first
    way its shape differs from the target's, on the definition or on a
    class's ``slot_usage`` of it (*usages*), whose values win on that class
    as they do in LinkML. A shape is ``multivalued`` and ``range``. A range
    that refines the target's (:func:`_refines`) is no conflict: it is
    copied."""
    lokf_slot = (lokf.get("slots") or {}).get(target) or {}
    t_multi = bool(lokf_slot.get("multivalued"))
    t_range = lokf_slot.get("range") or lokf.get("default_range") or "string"
    kinds = ("classes", "a class"), ("enums", "an enum")
    for where, shape in (("", elem), *((f" on class {c}", {**elem, **u}) for c, u in usages)):
        if bool(shape.get("multivalued")) != t_multi:
            theirs, ours = ("not multivalued", "is") if t_multi else ("multivalued", "is not")
            return f"is {theirs}{where} and LOKF's {target} {ours}"
        v = shape.get("range")
        if isinstance(v, str) and not _refines(v, t_range, schema, lokf):
            kind = next((f" ({k})" for s, k in kinds if v in (schema.get(s) or {}) or v in (lokf.get(s) or {})), "")
            return f"has range {v}{kind}{where} where LOKF's {target} takes {t_range}"
    return None


def find_folds(
    schema: dict,
    lokf: dict,
    asked: dict[str, str] | None = None,
    keep: list[str] | tuple[str, ...] = (),
    dropped: dict[str, str] | None = None,
    lokf_name: str = "lokf.yaml",
) -> tuple[dict[str, str], list[str], list[str]]:
    """Which vocabulary slots and class attributes fold into which of LOKF's,
    the names ``--keep`` holds back, and the problems that refuse a fold. An
    attribute is keyed ``Class.attr`` throughout.

    *asked* comes from ``--fold``: a slot or ``Class.attr``, in its own
    spelling or the canonical one, mapped to the LOKF slot it means. A name
    missing on either side is refused, and so is a slot :func:`drop_twins`
    already dropped (*dropped* names the LOKF slot it was dropped for).
    *keep* comes from ``--keep``: names left out of the IRI route, which
    must exist and not be in *asked*.

    Every other slot and attribute folds by IRI, when its ``slot_uri`` or an
    ``exact_mappings`` entry is the ``slot_uri`` of a slot ``Concept`` lists,
    other than ``id``, ``type`` or a deprecated slot. Only Concept's slots
    count, because a fold becomes what a concept writes. LOKF's ``name`` and
    ``relation_label`` describe other nodes, so ``schema:name`` folds into
    ``title``. Two of Concept's slots sharing an IRI refuse the fold until
    ``--fold`` chooses one. CURIEs expand with LOKF's prefixes under the
    vocabulary's own, and the forms in :data:`_IRI_SYNONYMS` compare equal.

    A shape that differs from the target's is refused however the fold was
    found (:func:`_shape_conflict`); ``--fold`` does not override it.
    *lokf_name* is the file named in a refusal."""
    slots = schema.get("slots") or {}
    classes = schema.get("classes") or {}
    lokf_slots = lokf.get("slots") or {}
    folds: dict[str, str] = {}
    problems: list[str] = []
    by_form = {underscore(n): n for n in slots}
    view = _fold_view(schema)

    def resolve(want: str) -> tuple[str | None, str | None]:
        """The vocabulary's own spelling of *want*, or why there is none."""
        if "." in want:
            cname, aname = want.split(".", 1)
            cls = next((n for n in classes if n == cname or camelcase(n) == camelcase(cname)), None)
            if cls is None:
                return None, f"the vocabulary has no class {cname}"
            attrs = (classes[cls] or {}).get("attributes") or {}
            attr = next((n for n in attrs if n == aname or underscore(n) == underscore(aname)), None)
            if attr is None:
                return None, f"class {cls} has no attribute {aname}"
            return f"{cls}.{attr}", None
        have = want if want in slots else by_form.get(underscore(want))
        if have is not None:
            return have, None
        gone = next((n for n in dropped or {} if n == want or underscore(n) == underscore(want)), None)
        if gone is not None:
            return None, f"the vocabulary's {gone} was dropped as LOKF's {dropped[gone]}"
        return None, f"the vocabulary has no slot {want}"

    def definition(key: str) -> tuple[dict, list[tuple[str, dict]]]:
        """The slot or attribute *key* names, and the slot_usages on a slot."""
        if "." in key:
            cname, aname = key.split(".", 1)
            return _effective_slot(schema, aname, cname, view), []
        usages = [
            (c, _effective_slot(schema, key, c, view)) for c, cls in classes.items()
            if isinstance(cls, dict) and isinstance((cls.get("slot_usage") or {}).get(key), dict)
        ]
        return _effective_slot(schema, key, view=view), usages

    wanted: dict[str, str] = {}
    for want, target in (asked or {}).items():
        have, why = resolve(want)
        if why:
            problems.append(f"--fold {want}={target}: {why}")
        if target not in lokf_slots:
            problems.append(f"--fold {want}={target}: {lokf_name} has no slot {target}")
        if have is None or target not in lokf_slots:
            continue
        wanted[have] = target
        conflict = _shape_conflict(*definition(have), target, schema, lokf)
        if conflict:
            problems.append(f"--fold {want}={target}: {have} {conflict}")
        else:
            folds[have] = target
    kept: list[str] = []
    for want in keep:
        have, why = resolve(want)
        if why:
            problems.append(f"--keep {want}: {why}")
        elif have in wanted:
            problems.append(f"--keep {want}: --fold names {have} too")
        elif have not in kept:
            kept.append(have)

    lokf_prefixes = lokf.get("prefixes") or {}
    prefixes = {**lokf_prefixes, **(schema.get("prefixes") or {})}
    same = _converter(prefixes)
    targets: dict[str, list[str]] = {}
    for n in ((lokf.get("classes") or {}).get("Concept") or {}).get("slots") or []:
        slot = lokf_slots.get(n) or {}
        if n in ("id", "type") or slot.get("deprecated") or not slot.get("slot_uri"):
            continue
        iri = same.standardize_uri(_expand(slot["slot_uri"], lokf_prefixes), passthrough=True)
        targets.setdefault(iri, []).append(n)

    def by_iri(key: str, what: str) -> None:
        elem, usages = definition(key)
        iris = [i for i in (elem.get("slot_uri"), *(elem.get("exact_mappings") or [])) if isinstance(i, str)]
        hits = sorted({
            t for i in iris for t in targets.get(same.standardize_uri(_expand(i, prefixes), passthrough=True), [])
        })
        if not hits:
            return
        if len(hits) > 1:
            problems.append(f"{what} has the IRI of LOKF's {' and '.join(hits)}; pass --fold {key}=<one of them>")
            return
        conflict = _shape_conflict(elem, usages, hits[0], schema, lokf)
        if conflict:
            problems.append(f"{what} has the IRI of LOKF's {hits[0]} but {conflict}; --keep {key} leaves it")
        else:
            folds[key] = hits[0]

    for name, slot in slots.items():
        if name not in wanted and name not in kept and isinstance(slot, dict):
            by_iri(name, f"slot {name}")
    for cname, cls in classes.items():
        for aname, attr in ((cls or {}).get("attributes") or {}).items():
            key = f"{cname}.{aname}"
            if key not in wanted and key not in kept and isinstance(attr, dict):
                by_iri(key, f"attribute {key}")
    return folds, kept, problems


def _carried(elem: dict) -> dict:
    return {k: elem[k] for k in _USAGE_CARRY if k in elem}


def fold_twins(schema: dict, folds: dict[str, str], renamed: dict[str, str] | None = None) -> dict[str, str]:
    """Delete each slot and ``Class.attr`` attribute in *folds*, and list
    LOKF's slot in its place, as :func:`drop_twins` does for an identifier.
    The slot's constraints (:data:`_USAGE_CARRY`) are copied into a
    ``slot_usage`` on every class that used it. Where that class already had
    a ``slot_usage`` for the slot, the class's own values win. A slot that
    inherited from a folded one now inherits from LOKF's. Runs after
    :func:`rename_shared`, which skips folded slots, so a vocabulary slot
    named like the target (its own ``title``) is renamed first. *renamed*
    maps each class and attribute to its name since then. Returns *folds* in
    the vocabulary's order, slots first."""
    renamed = renamed or {}
    slots = schema.get("slots") or {}
    classes = schema.get("classes") or {}
    done = {n: folds[n] for n in slots if n in folds}
    view = _fold_view(schema)
    effective = {name: _effective_slot(schema, name, view=view) for name in done}
    for name in done:
        carried = _carried(effective[name])
        for cls in classes.values():
            if not isinstance(cls, dict):
                continue
            usage = cls.get("slot_usage") or {}
            if name in (cls.get("slots") or []) or name in usage:
                merged = {**carried, **(usage.get(name) or {})}
                if merged:
                    cls.setdefault("slot_usage", {})[name] = merged
        del slots[name]
    _point_at_lokf(schema, done, keep=_USAGE_KEEP + _USAGE_CARRY)
    # An attribute by its name since the rename, in the class's own order.
    located = {}
    for key, target in folds.items():
        if "." in key:
            cname, aname = key.split(".", 1)
            located[renamed.get(cname, cname), renamed.get(aname, aname)] = (key, target)
    for cname, cls in classes.items():
        attrs = cls.get("attributes") or {}
        for aname in list(attrs):
            if (cname, aname) not in located:
                continue
            key, target = located[cname, aname]
            attr = attrs.pop(aname) or {}
            if not attrs:
                del cls["attributes"]
            cls["slots"] = list(dict.fromkeys([*(cls.get("slots") or []), target]))
            merged = _conjoin(_carried(attr), (cls.get("slot_usage") or {}).get(target) or {})
            if merged:
                cls.setdefault("slot_usage", {})[target] = merged
            done[key] = target
    return done


def find_roots(schema: dict) -> list[str]:
    """Rootless, non-mixin classes that list LOKF's ``id`` (the vocabulary's
    identifier, after :func:`drop_twins`): the classes whose instances are
    concepts. Biolink has exactly one, ``entity``."""
    classes = schema.get("classes") or {}

    def listed(cls: dict) -> set[str]:
        own = set(cls.get("slots") or []) | set((cls.get("attributes") or {}).keys())
        for mixin in cls.get("mixins") or []:  # a root may take its identifier from a mixin
            if isinstance(classes.get(mixin), dict):
                own |= listed(classes[mixin])
        return own

    roots = []
    for name, cls in classes.items():
        if not isinstance(cls, dict) or cls.get("is_a") or cls.get("mixin"):
            continue
        if "id" in listed(cls):
            roots.append(name)
    return roots


def reroot(schema: dict, roots: list[str]) -> list[str]:
    """Make *roots* subclasses of ``Concept``. ``tree_root`` comes off every
    class as well: LOKF's document root is ``KnowledgeBundle``, and LinkML
    warns about a second one. Returns the classes that carried it."""
    for name in roots:
        schema["classes"][name]["is_a"] = "Concept"
    had_tree_root = []
    for name, cls in (schema.get("classes") or {}).items():
        if isinstance(cls, dict) and cls.pop("tree_root", None):
            had_tree_root.append(name)
    return had_tree_root


def find_shadows(schema: dict, lokf: dict, roots: list[str]) -> list[str]:
    """Warnings for an attribute on a class in *roots*, or under one, that
    has the name of a slot ``Concept`` lists but not its IRI (a fold took
    those). SchemaView keeps the imported slot, so the attribute overrides
    nothing; it shadows LOKF's slot on its class alone, and a record of that
    class writes the attribute. Its name is the key such a record writes, so
    nothing is renamed, only reported."""
    classes = schema.get("classes") or {}
    concept = set(((lokf.get("classes") or {}).get("Concept") or {}).get("slots") or [])
    under = set(roots)
    grew = True
    while grew:
        grew = False
        for name, cls in classes.items():
            if name not in under and isinstance(cls, dict) and cls.get("is_a") in under:
                under.add(name)
                grew = True
    out = []
    for name, cls in classes.items():
        if name not in under:
            continue
        for attr in (cls.get("attributes") or {}):
            hit = next((s for s in (attr, underscore(attr)) if s in concept), None)
            if hit:
                out.append(
                    f"attribute {name}.{attr} has the name of LOKF's {hit} but not its IRI, and shadows it "
                    f"on {name}; --fold {name}.{attr}={hit} folds it"
                )
    return out


def canonical_names(schema: dict, prefix: str) -> tuple[dict[str, str], dict[str, str]]:
    """Class names in CamelCase and slot names underscored: LinkML's canonical
    forms, which OKF's ``type``, frontmatter keys and the JSON-LD context use.
    Derived IRIs do not change (``in taxon`` was ``vocab:in_taxon`` already).
    Two names with one canonical form (biolink's ``KnowledgeGraph`` and
    ``knowledge graph``) would leave one definition after the rewrite, so
    first every such name but one is renamed as a shared name is, with its IRI
    pinned: the one already canonical keeps its name, else the first. Returns
    the collision renames and the canonical ones."""
    collided: dict[str, list[str]] = {}
    for section, form in (("classes", camelcase), ("slots", underscore)):
        by_form: dict[str, list[str]] = {}
        for n in schema.get(section) or {}:
            by_form.setdefault(form(n), []).append(n)
        for canon, names in by_form.items():
            if len(names) > 1:
                keep = canon if canon in names else names[0]
                collided.setdefault(section, []).extend(n for n in names if n != keep)
    renamed = rename_shared(schema, collided, prefix) if collided else {}
    r = Renames(
        elements={n: camelcase(n) for n in (schema.get("classes") or {}) if camelcase(n) != n},
        slots={n: underscore(n) for n in (schema.get("slots") or {}) if underscore(n) != n},
    )
    rewrite_refs(schema, r)
    return renamed, {**r.elements, **r.slots}


# --- verify -------------------------------------------------------------------

def verify(adapted: pathlib.Path, lokf: pathlib.Path) -> list[str]:
    """Load the copy beside *lokf* with SchemaView and report what does not
    hold: a reference no schema defines, a name still shared, a class that
    lists LOKF's ``id`` but does not descend from ``Concept``."""
    from linkml_runtime.utils.schemaview import SchemaView

    schema = yaml.safe_load(adapted.read_text(encoding="utf-8"))
    problems = []
    for section, names in shared_names(schema, load_schema(lokf)).items():
        problems.append(f"{section} still shared with {lokf.name}: {', '.join(names)}")
    # Point the `lokf` import at the file we were given, wherever the copy sits.
    schema["imports"] = [
        str(lokf.resolve().with_suffix("")) if i == "lokf" else i for i in schema.get("imports") or []
    ]
    with tempfile.TemporaryDirectory() as tmp:
        probe = pathlib.Path(tmp) / adapted.name
        probe.write_text(yaml.safe_dump(schema, sort_keys=False, allow_unicode=True), encoding="utf-8")
        try:
            view = SchemaView(str(probe))
            classes, slots = view.all_classes(), view.all_slots()
        except Exception as exc:  # SchemaView raises many kinds; the copy is unusable either way
            return problems + [f"SchemaView cannot load the copy beside {lokf.name}: {exc}"]

        def ranges_of(expr) -> list[str]:
            return [r for r in (expr.range, *(a.range for a in expr.any_of or [])) if r]

        for cname in sorted(schema.get("classes") or {}):
            cls = classes.get(cname)
            if cls is None:
                problems.append(f"class {cname} did not load")
                continue
            for parent in (cls.is_a, *(cls.mixins or [])):
                if parent and parent not in classes:
                    problems.append(f"class {cname}: {parent} is not a class")
            for sname in (*(cls.slots or []), *(cls.slot_usage or {})):
                if sname not in slots:
                    problems.append(f"class {cname}: {sname} is not a slot")
            for sname, usage in (*(cls.slot_usage or {}).items(), *(cls.attributes or {}).items()):
                for ref in ranges_of(usage):
                    if view.get_element(ref) is None:
                        problems.append(f"class {cname}, slot {sname}: range {ref} is not defined")
            # A mixin is never a concept itself; the class that mixes it in is.
            if (
                "id" in (cls.slots or [])
                and not cls.mixin
                and "Concept" not in view.class_ancestors(cname)
            ):
                problems.append(f"class {cname} lists id but does not descend from Concept")
        for sname in sorted(schema.get("slots") or {}):
            slot = slots.get(sname)
            if slot is None:
                problems.append(f"slot {sname} did not load")
                continue
            for ref in (*ranges_of(slot), slot.domain, slot.is_a):
                if ref and view.get_element(ref) is None:
                    problems.append(f"slot {sname}: {ref} is not defined")
    return problems


# --- the whole thing -----------------------------------------------------------

def header(report: Report) -> str:
    return (
        f"# Generated by `lokf adapt` from {report.source}; do not edit.\n"
        "# Imports lokf: a domain schema lists this file beside it (SPEC 6.2).\n"
    )


class _Dumper(yaml.SafeDumper):
    """Multi-line strings as `|` blocks, so descriptions stay readable."""


def _str(dumper: yaml.SafeDumper, value: str):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _str)


def dump(schema: dict, head: str = "") -> str:
    return head + yaml.dump(schema, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=100)


def adapt(
    vocab: str | pathlib.Path,
    *,
    lokf: str | pathlib.Path | None = None,
    roots: list[str] | tuple[str, ...] = (),
    prefix: str | None = None,
    name: str | None = None,
    folds: dict[str, str] | None = None,
    keep: list[str] | tuple[str, ...] = (),
) -> tuple[dict, Report]:
    """The copy of *vocab* a domain schema imports beside ``lokf.yaml``, and a
    report of the moves. *roots* names classes to re-root on ``Concept``, in
    the vocabulary's own spelling or CamelCase, instead of the detected ones.
    *name* is the copy's schema name (default ``<stem>_lokf``). *folds* maps a
    vocabulary slot, or a ``Class.attr`` attribute, to the LOKF slot it
    means, beside those its IRI folds; *keep* names those its IRI must not."""
    vocab = pathlib.Path(vocab)
    lokf_path = schema_path(lokf)
    lokf_dict = load_schema(lokf_path)
    schema, folded = fold_imports(vocab)
    version = schema.get("version")
    report = Report(
        source=f"{vocab.name} ({schema.get('name', vocab.stem)}{f' {version}' if version else ''})",
        folded=folded,
    )

    prefix = prefix or schema.get("default_prefix") or vocab.stem
    report.dropped, report.detached = drop_twins(schema)
    fold, report.kept, problems = find_folds(schema, lokf_dict, folds, keep, report.dropped, lokf_path.name)
    report.problems.extend(problems)
    report.demoted = demote_designators(schema)
    # A folded slot is LOKF's from here on, so it is not renamed as shared.
    shared = {
        section: kept
        for section, names in shared_names(schema, lokf_dict).items()
        if (kept := [n for n in names if not (section == "slots" and n in fold)])
    }
    try:
        report.renamed = rename_shared(schema, shared, prefix)
    except ValueError as exc:
        report.problems.append(str(exc))
    report.folded_into = fold_twins(schema, fold, report.renamed)
    if roots:
        # A root may be named as the vocabulary spells it, before any rename.
        classes = schema.get("classes") or {}
        renamed = {camelcase(old): new for old, new in report.renamed.items() if new in classes}
        wanted = {camelcase(renamed.get(camelcase(r), r)) for r in roots}
        chosen = [n for n in schema.get("classes") or {} if camelcase(n) in wanted]
        missing = wanted - {camelcase(n) for n in chosen}
        if missing:
            report.problems.append(f"--root names no class: {', '.join(sorted(missing))}")
    else:
        chosen = find_roots(schema)
    had_tree_root = reroot(schema, chosen)
    try:
        report.collided, report.canonical = canonical_names(schema, prefix)
    except ValueError as exc:
        report.problems.append(str(exc))
    # Report roots by their final names: a collision rename happens after re-rooting.
    def final(n: str) -> str:
        return report.collided.get(n, camelcase(n))

    report.roots = [final(n) for n in chosen]
    report.tree_roots = [final(n) for n in had_tree_root]
    report.warnings = find_shadows(schema, lokf_dict, report.roots)

    schema["name"] = name or f"{vocab.stem}_lokf"
    if "id" in schema:
        schema["id"] = f"{str(schema['id']).rstrip('/#')}-lokf"
    moves = "; ".join(
        f"{k}: {v}" for k, v in (
            ("re-rooted on lokf:Concept", ", ".join(report.roots)),
            ("dropped for LOKF's", ", ".join(report.dropped)),
            ("renamed, IRIs unchanged", ", ".join(f"{a} -> {b}" for a, b in report.renamed.items())),
            ("folded into LOKF's", ", ".join(f"{a} -> {b}" for a, b in report.folded_into.items())),
            ("kept from folding", ", ".join(report.kept)),
            ("renamed for one canonical form", ", ".join(f"{a} -> {b}" for a, b in report.collided.items())),
            ("designators demoted", ", ".join(report.demoted)),
        ) if v
    )
    schema["notes"] = list(schema.get("notes") or []) + [f"Adapted for LOKF by `lokf adapt`. {moves}."]
    return schema, report
