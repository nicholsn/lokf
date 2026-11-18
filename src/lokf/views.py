"""Compile a site's optional navigation manifest over the toolkit's local graph edges."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from difflib import get_close_matches
from functools import cache
from graphlib import CycleError, TopologicalSorter
from heapq import heapify, heappop, heappush
from importlib.resources import files
import json
from math import isfinite
from pathlib import Path
import re

from jsonschema.validators import validator_for
from ruamel.yaml import YAML, YAMLError

from lokf.model import Bundle
from lokf.schema import Vocabulary


@cache
def _validator():
    resource = files("lokf").joinpath("data", "lokf-views-v1.schema.json")
    schema = json.loads(resource.read_text(encoding="utf-8"))
    return validator_for(schema)(schema)


def _location(parts) -> str:
    return "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts).lstrip(".")


def _manifest(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as stream:
            manifest = YAML(typ="safe").load(stream)
    except YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc
    error = next(_validator().iter_errors(manifest), None)
    if error:
        message = error.message
        if error.validator == "oneOf":
            if error.schema.get("title") == "Column":
                message = "a column needs exactly one of 'field' or 'relation'"
            elif error.schema.get("title") == "Step":
                message = "a step needs exactly one direction, 'in' or 'out'"
        raise ValueError(f"{path}: {_location(error.absolute_path) or 'manifest'}: {message}")
    return manifest


def _unique(values, location: str) -> None:
    seen = set()
    for value in values:
        if value in seen:
            raise ValueError(f"{location}: duplicate {value!r}")
        seen.add(value)


# Match the written calendar day, even if normalizing the offset to UTC would
# cross midnight. Quoted and YAML-native dates have already passed through isoify.
_CALENDAR_DATE = re.compile(
    r"([0-9]{4}-[0-9]{2}-[0-9]{2})"
    r"(?:[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:(?:[0-5][0-9]|60)"
    r"(?:\.[0-9]+)?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9]))?"
)


def _day(value) -> str | None:
    match = _CALENDAR_DATE.fullmatch(value) if isinstance(value, str) else None
    if match:
        try:
            return date.fromisoformat(match[1]).isoformat()
        except ValueError:
            pass
    return None


class _Compiler:
    def __init__(self, bundle: Bundle, vocab: Vocabulary, graph: dict):
        self.vocab = vocab
        self.concepts = bundle.by_iri()
        self.ids = {c.concept_id: iri for iri, c in self.concepts.items()}
        self.types = vocab.subclasses_of("Concept")
        self.slots = {}
        self.relations = defaultdict(set)
        self.diagnostics = []
        self.records = {}
        self.adjacent = defaultdict(list)
        for rel in (*vocab.relation_slots.values(), *vocab.relation_types.values()):
            self.relations[rel.name].add(rel.uri)
            self.relations[rel.uri].add(rel.uri)
        for element in graph["edges"]:
            edge = element["data"]
            source, target = edge["source"], edge["target"]
            predicate = vocab.expand(edge["predicate"])
            reified = edge["reified"]
            self.adjacent["out", source, predicate].append((target, reified))
            self.adjacent["in", target, predicate].append((source, reified))

    def record(self, iri: str) -> dict:
        concept = self.concepts[iri]
        if concept.concept_id not in self.records:
            self.records[concept.concept_id] = {
                "title": str(concept.title or concept.concept_id), "fields": {}, "dates": {},
            }
        return self.records[concept.concept_id]

    def check_type(self, name: str, location: str) -> None:
        if name not in self.types:
            raise ValueError(f"{location}: unknown concept class {name!r} in this vocabulary")

    def resolve_step(self, step: dict, location: str) -> tuple:
        direction = "in" if "in" in step else "out"
        name = step[direction]
        iris = self.relations.get(self.vocab.expand(name), set())
        if not iris:
            hint = get_close_matches(name, self.relations.keys(), n=1)
            detail = f" Did you mean {hint[0]!r}?" if hint else ""
            raise ValueError(f"{location}.{direction}: unknown projected relation {name!r}.{detail}")
        if len(iris) != 1:
            raise ValueError(f"{location}.{direction}: ambiguous relation {name!r}. Use its predicate IRI.")
        if "type" in step:
            self.check_type(step["type"], f"{location}.type")
        return direction, next(iter(iris)), step.get("type")

    def allowed_field(self, cls: str, field: str, timeline: bool) -> bool:
        if cls not in self.slots:
            self.slots[cls] = self.vocab.induced_slots(cls)
        slot = self.slots[cls].get(field)
        if not slot:
            return False
        ranges = slot["any_of"] or [slot["range"]]
        if timeline:
            return not slot["multivalued"] and all(r in {"date", "datetime"} for r in ranges)
        return any(r not in self.vocab.classes for r in ranges)

    def validate_display(
        self, display: dict, cls: str | None, location: str, root_cls: str | None = None,
    ) -> dict[str, tuple]:
        """Check the declaration and resolve its relation columns before reading any rows."""
        layout = display["layout"]
        allowed = {"layout"}
        if root_cls is None and layout == "list":
            allowed.add("family_by")
        if root_cls is not None and layout in {"list", "table"}:
            allowed.add("order_by")
        if layout == "table":
            allowed.add("columns")
            columns = display.get("columns") or []
            if not columns or columns[0].get("field") != "title":
                raise ValueError(f"{location}.columns: a table must start with a title column")
        else:
            allowed.add("embed")  # structurally permitted on indexes only
        if layout == "timeline":
            allowed.update(("date", "date_label", "direction"))
            if root_cls and "date_from" in display:
                allowed.add("date_from")
                cls = root_cls
            if not display.get("date") or not display.get("date_label", "").strip():
                raise ValueError(f"{location}: a timeline needs a date field and a visible date_label")
        unexpected = display.keys() - allowed
        if unexpected:
            raise ValueError(f"{location}: {layout} layout does not support {', '.join(sorted(unexpected))}")
        relations = {}
        fields = []
        for i, column in enumerate(display.get("columns", ())):
            column_location = f"{location}.columns[{i}]"
            if "relation" in column:
                relations[str(i)] = self.resolve_step(column["relation"], f"{column_location}.relation")
            else:
                fields.append((column["field"], f"{column_location}.field"))
        if layout == "timeline":
            fields.append((display["date"], f"{location}.date"))
        for field, field_location in fields:
            if layout == "table" and field == "title":
                continue
            if not any(self.allowed_field(c, field, layout == "timeline") for c in ([cls] if cls else self.types)):
                required = "single-valued date or datetime" if layout == "timeline" else "scalar or scalar list"
                raise ValueError(f"{field_location}: {field!r} must be a {required} field of {cls or 'an endpoint class'}")
        return relations

    def day(self, iri: str, name: str) -> str | None:
        concept = self.concepts[iri]
        dates = self.record(iri)["dates"]
        if name not in dates:
            raw = concept.data.get(name) if self.allowed_field(concept.type, name, True) else None
            dates[name] = _day(raw)
            if raw is not None and dates[name] is None:
                self.diagnostics.append(f"{concept.concept_id}.{name}: malformed date {raw!r}")
        return dates[name]

    def title_key(self, iri: str) -> tuple[str, str]:
        return self.record(iri)["title"], iri

    def ordered(self, iris, display: dict) -> list[str]:
        # Apply the title/IRI order first; stable date sorting preserves both tie-breakers.
        ranked = sorted(iris, key=self.title_key)
        for iri in ranked:
            concept = self.concepts[iri]
            record = self.record(iri)
            for column in display.get("columns", ()):
                name = column.get("field")
                if name is None or name == "title" or name in record["fields"]:
                    continue
                value = concept.data.get(name)
                if not self.allowed_field(concept.type, name, False) or not _scalar_cell(value):
                    value = None
                record["fields"][name] = value
        if display["layout"] == "timeline" and "date_from" not in display:
            name = display["date"]
            dated, undated = [], []
            for iri in ranked:
                if self.day(iri, name):
                    dated.append(iri)
                else:
                    undated.append(iri)
            dated.sort(key=lambda iri: self.record(iri)["dates"][name], reverse=display.get("direction") != "asc")
            return dated + undated
        return ranked

    def row(self, iri: str, relation_columns: dict[str, tuple]) -> dict:
        row = {"id": self.concepts[iri].concept_id}
        if relation_columns:
            links = {}
            for position, (direction, predicate, cls) in relation_columns.items():
                targets = {target for target, _ in self.adjacent.get((direction, iri, predicate), ())
                           if cls is None or self.concepts[target].type == cls}
                links[position] = [self.concepts[target].concept_id for target in sorted(targets, key=self.title_key)]
            row["links"] = links
        return row

    def predecessors(self, ranked: list[str], step: tuple) -> dict[str, list[str]]:
        """Restrict the declared relation to this collection; merge duplicate graph edges."""
        direction, predicate, cls = step
        selected = set(ranked)
        return {iri: sorted({
            target for target, _ in self.adjacent.get((direction, iri, predicate), ())
            if target in selected and (cls is None or self.concepts[target].type == cls)
        }) for iri in ranked}

    def precedence_order(self, predecessors: dict[str, list[str]], location: str) -> tuple[list[str], bool]:
        # The input keys are already in title/IRI order. Choose the earliest
        # eligible node after *each* step, including nodes that just became ready.
        sorter = TopologicalSorter(predecessors)
        try:
            sorter.prepare()
        except CycleError as exc:
            cycle = " → ".join(self.concepts[iri].concept_id for iri in exc.args[1])
            raise ValueError(f"{location}: cycle among selected concepts: {cycle}") from exc
        priority = {iri: i for i, iri in enumerate(predecessors)}
        ready = [(priority[iri], iri) for iri in sorter.get_ready()]
        heapify(ready)
        ordered = []
        unique = True
        while ready:
            if len(ready) > 1:
                unique = False
            _, iri = heappop(ready)
            ordered.append(iri)
            sorter.done(iri)
            for released in sorter.get_ready():
                heappush(ready, (priority[released], released))
        return ordered, unique

    def families(self, ranked: list[str], step: tuple, location: str) -> list[dict]:
        parents = self.predecessors(ranked, step)
        family_members = {iri: [] for iri in ranked if not parents[iri]}
        # Propagate only top-level ancestors. A diamond or multiple parents
        # within the same family still produces one membership.
        ancestors = {}
        parent_first, _ = self.precedence_order(parents, location)
        for iri in parent_first:
            ancestors[iri] = ({iri} if not parents[iri] else
                              {family for parent in parents[iri] for family in ancestors[parent]})
        for iri in ranked:
            for family in ancestors[iri]:
                if family != iri:
                    family_members[family].append(self.concepts[iri].concept_id)
        return [{"id": self.concepts[family].concept_id, "members": members}
                for family, members in family_members.items()]

    def section_rows(
        self, root: str, steps: list, display: dict, empty: Counter,
        order_step: tuple | None, relation_columns: dict[str, tuple], location: str,
    ) -> tuple[list[dict], str | None]:
        # Each chain is a tuple of (IRI, reified). Visiting prefixes in lexical
        # order lets the first arrival retain the smallest complete witness.
        frontier = {root: ()}
        for number, (direction, predicate, cls) in enumerate(steps):
            reached = {}
            for source, chain in sorted(frontier.items(), key=lambda entry: entry[1]):
                for target, reified in self.adjacent.get((direction, source, predicate), ()):
                    if cls is None or self.concepts[target].type == cls:
                        reached.setdefault(target, (*chain, (target, reified)))
            if not reached:
                empty[number] += 1
                return [], None
            frontier = reached
        frontier.pop(root, None)
        rows = []
        ranked = self.ordered(frontier, display)
        ordering = None
        if order_step:
            predecessors = self.predecessors(ranked, order_step)
            context = f"{location}.order_by (root {self.concepts[root].concept_id})"
            ranked, unique = self.precedence_order(predecessors, context)
            if len(ranked) >= 2:
                ordering = "complete" if unique else "partial"
                if not any(predecessors.values()):
                    ordering = "unlinked"
        for iri in ranked:
            row = self.row(iri, relation_columns)
            if len(steps) > 1:
                witness = []
                for (target, reified), (direction, predicate, _) in zip(frontier[iri], steps):
                    self.record(target)
                    witness.append({
                        "id": self.concepts[target].concept_id, "predicate": self.vocab.compact(predicate),
                        "direction": direction, "reified": reified,
                    })
                row["witness"] = witness
            rows.append(row)
        return rows, ordering

    def view(self, view: dict, location: str) -> dict:
        selector = view["roots"]
        root_cls = selector["type"]
        self.check_type(root_cls, f"{location}.roots.type")
        relation_columns = self.validate_display(view["index"], root_cls, f"{location}.index")
        roots = [iri for iri, c in self.concepts.items() if c.type == root_cls]
        if "concept" in selector:
            iri = self.ids.get(selector["concept"])
            if iri not in roots:
                raise ValueError(f"{location}.roots.concept: {selector['concept']!r} does not select a {root_cls}")
            roots = [iri]
        ranked = self.ordered(roots, view["index"])
        root_rows = [{**self.row(iri, relation_columns), "sections": {}} for iri in ranked]
        self.diagnostics.append(f"{view['id']}: {len(roots)} roots")
        sections = view.get("sections", [])
        names = [item["id"] for item in sections]
        _unique(names, f"{location}.sections")
        embeds = view["index"].get("embed", [])
        _unique(embeds, f"{location}.index.embed")
        for name in embeds:
            if name not in names:
                raise ValueError(f"{location}.index.embed: unknown section {name!r}")
        for i, section in enumerate(sections):
            prefix = f"{location}.sections[{i}]"
            steps = [self.resolve_step(step, f"{prefix}.path[{j}]")
                     for j, step in enumerate(section["path"])]
            display = section["display"]
            relation_columns = self.validate_display(display, steps[-1][2], f"{prefix}.display", root_cls)
            order_step = (self.resolve_step(display["order_by"], f"{prefix}.display.order_by")
                          if "order_by" in display else None)
            empty = Counter()
            total = 0
            for row in root_rows:
                root = self.ids[row["id"]]
                if "date_from" in display:
                    self.day(root, display["date"])
                rows, ordering = self.section_rows(
                    root, steps, display, empty, order_step, relation_columns, f"{prefix}.display",
                )
                row["sections"][section["id"]] = rows
                if ordering:
                    row.setdefault("ordering", {})[section["id"]] = ordering
                total += len(rows)
            label = f"{view['id']}.{section['id']}"
            self.diagnostics.append(f"{label}: {total} section memberships across {len(roots)} roots")
            for number, count in sorted(empty.items()):
                direction, predicate, cls = steps[number]
                self.diagnostics.append(f"{label}: {count} roots first empty at path[{number}] "
                                        f"({direction} {self.vocab.compact(predicate)}, type {cls or 'any'})")
        result = {
            "id": view["id"], "title": view["title"], "description": view["description"],
            "placement": view.get("placement", "after_text"),
            "index": view["index"], "roots": root_rows,
            "sections": [{k: s[k] for k in ("id", "title", "display")} for s in sections],
        }
        if "family_by" in view["index"]:
            path = f"{location}.index.family_by"
            step = self.resolve_step(view["index"]["family_by"], path)
            result["families"] = self.families(ranked, step, path)
            self.diagnostics.append(f"{view['id']}: {len(result['families'])} top-level families")
        return result


def _scalar_cell(value) -> bool:
    values = value if isinstance(value, list) else [value]
    return all(isinstance(v, (str, bool, int, float)) and not (isinstance(v, float) and not isfinite(v))
               for v in values)


def compile_views(manifest_path: Path, bundle: Bundle, vocab: Vocabulary, graph: dict) -> dict:
    """Return a JSON-ready, deterministic plan for the static renderer, or raise ValueError."""
    manifest = _manifest(manifest_path)
    try:
        duplicates = bundle.duplicate_iris()
        if duplicates:
            iri, ids = duplicates[0]
            raise ValueError(f"duplicate concept IRI {iri!r} shared by {', '.join(ids)}")
        compiler = _Compiler(bundle, vocab, graph)
        _unique((view["id"] for view in manifest["views"]), "views")
        views = [compiler.view(view, f"views[{i}]") for i, view in enumerate(manifest["views"])]
        return {"views": views, "records": dict(sorted(compiler.records.items())), "diagnostics": compiler.diagnostics}
    except ValueError as exc:
        raise ValueError(f"{manifest_path}: {exc}") from exc
