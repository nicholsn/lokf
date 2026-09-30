"""Adapt a published LinkML vocabulary so a LOKF domain schema can import it.

A domain schema imports ``lokf.yaml`` and a vocabulary side by side (SPEC
§6.2). LinkML merges the two into one namespace, so the vocabulary's copy must
share no element name with ``lokf.yaml``, and its concepts must descend from
``Concept`` to join the bundle's concept union. :func:`adapt` makes that copy
from the vocabulary as published, in six mechanical moves:

1. fold the vocabulary's own imports into one file, so the copy stands alone;
2. drop the two slots that cannot coexist with LOKF's, an identifier (LOKF's
   ``id`` is the subject) and an ``rdf:type`` slot (LOKF's ``type`` designates
   the class), and point what referenced them at LOKF's;
3. detach any slot that inherited from a dropped one, and demote every other
   type designator to an ordinary slot;
4. rename every other shared name and pin its IRI, so biolink's ``name``
   becomes ``biolink_name`` and still projects as ``rdfs:label``;
5. re-root the vocabulary's top classes on ``Concept``;
6. give classes CamelCase names and slots underscored ones: the forms ``type``,
   frontmatter keys and the JSON-LD context use.

Everything works on the plain YAML dict. SchemaView, from the runtime the
core install already has, verifies the result beside ``lokf.yaml``.
"""
from __future__ import annotations

import pathlib
import tempfile
from dataclasses import dataclass, field

import yaml
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
# What a slot_usage may still say about a slot LOKF now serves (id, type).
_USAGE_KEEP = (
    "required", "recommended", "description", "comments", "notes", "examples",
    "values_from", "see_also", "in_subset", "aliases",
)


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
    roots: list[str] = field(default_factory=list)
    tree_roots: list[str] = field(default_factory=list)
    canonical: dict[str, str] = field(default_factory=dict)
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
            f"re-rooted on Concept:    {', '.join(self.roots) or 'none (pass --root)'}",
            f"tree_root removed:       {', '.join(self.tree_roots) or 'none'}",
            f"canonical names:         {len(self.canonical)}",
        ]
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


# --- 2..6. the moves ----------------------------------------------------------

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
    # What referenced the vocabulary's slot now references LOKF's, which the
    # copy gets through its `lokf` import. A slot_usage on it keeps what
    # documents, not what would reshape LOKF's slot.
    for cls in (schema.get("classes") or {}).values():
        for name, usage in list((cls.get("slot_usage") or {}).items()):
            if name in dropped and isinstance(usage, dict):
                cls["slot_usage"][name] = {k: v for k, v in usage.items() if k in _USAGE_KEEP}
    rewrite_refs(schema, Renames(slots=dict(dropped)))
    for cls in (schema.get("classes") or {}).values():
        for key in _SLOT_REFS_ON_CLASS:
            if isinstance(cls.get(key), list):
                cls[key] = list(dict.fromkeys(cls[key]))
    return dropped, detached


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


def canonical_names(schema: dict) -> dict[str, str]:
    """Class names in CamelCase and slot names underscored: LinkML's canonical
    forms, which OKF's ``type``, frontmatter keys and the JSON-LD context use.
    Derived IRIs do not change (``in taxon`` was ``vocab:in_taxon`` already).
    Two names with one canonical form (``sample record`` and ``SampleRecord``)
    raise before anything is renamed: the rewrite would keep one definition."""
    for section, form in (("classes", camelcase), ("slots", underscore)):
        seen: dict[str, str] = {}
        for n in schema.get(section) or {}:
            other = seen.setdefault(form(n), n)
            if other != n:
                raise ValueError(
                    f"{section[:-1]} names {other!r} and {n!r} are both {form(n)!r} in canonical form"
                )
    r = Renames(
        elements={n: camelcase(n) for n in (schema.get("classes") or {}) if camelcase(n) != n},
        slots={n: underscore(n) for n in (schema.get("slots") or {}) if underscore(n) != n},
    )
    rewrite_refs(schema, r)
    return {**r.elements, **r.slots}


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
) -> tuple[dict, Report]:
    """The copy of *vocab* a domain schema imports beside ``lokf.yaml``, and a
    report of the moves. *roots* names classes to re-root on ``Concept``, in
    the vocabulary's own spelling or CamelCase, instead of the detected ones.
    *name* is the copy's schema name (default ``<stem>_lokf``)."""
    vocab = pathlib.Path(vocab)
    lokf_dict = load_schema(schema_path(lokf))
    schema, folded = fold_imports(vocab)
    version = schema.get("version")
    report = Report(
        source=f"{vocab.name} ({schema.get('name', vocab.stem)}{f' {version}' if version else ''})",
        folded=folded,
    )

    report.dropped, report.detached = drop_twins(schema)
    report.demoted = demote_designators(schema)
    shared = shared_names(schema, lokf_dict)
    try:
        report.renamed = rename_shared(schema, shared, prefix or schema.get("default_prefix") or vocab.stem)
    except ValueError as exc:
        report.problems.append(str(exc))
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
    report.tree_roots = [camelcase(n) for n in reroot(schema, chosen)]
    try:
        report.canonical = canonical_names(schema)
    except ValueError as exc:
        report.problems.append(str(exc))
    report.roots = [camelcase(n) for n in chosen]

    schema["name"] = name or f"{vocab.stem}_lokf"
    if "id" in schema:
        schema["id"] = f"{str(schema['id']).rstrip('/#')}-lokf"
    moves = "; ".join(
        f"{k}: {v}" for k, v in (
            ("re-rooted on lokf:Concept", ", ".join(report.roots)),
            ("dropped for LOKF's", ", ".join(report.dropped)),
            ("renamed, IRIs unchanged", ", ".join(f"{a} -> {b}" for a, b in report.renamed.items())),
            ("designators demoted", ", ".join(report.demoted)),
        ) if v
    )
    schema["notes"] = list(schema.get("notes") or []) + [f"Adapted for LOKF by `lokf adapt`. {moves}."]
    return schema, report
