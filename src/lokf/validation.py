"""Read-only validation of a local Markdown bundle for CLI and MCP callers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property, lru_cache, partial
import json
import os
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from typing_extensions import TypedDict

import yaml
from linkml_runtime.utils.formatutils import underscore

from lokf.events import event_diagnostics
from lokf.excerpts import excerpt_conflict_findings, excerpt_findings
from lokf.logs import _check_log_files
from lokf.model import Bundle, _load_bundle_files
from lokf.parse import DocumentError
from lokf.resources import exclusion_findings, resource_findings, resource_root
from lokf.schema import domain_schema, projection_schema, schema_context, schema_path
from lokf.schema_sources import SchemaInputs, cache_per_root, local_view_caches, parsed

MAX_DIAGNOSTICS = 100
MAX_TEXT = 512


class Diagnostic(TypedDict):
    check: str
    code: str
    severity: str
    message: str
    document: str | None
    field: str | None
    line: int | None


class ValidationResult(TypedDict):
    """Structured result advertised by the bundle MCP server."""
    outcome: Literal["valid", "invalid", "incomplete"]
    checks: dict[str, Literal["disabled", "skipped", "passed", "failed", "unavailable"]]
    concept_count: int | None
    diagnostics: list[Diagnostic]
    diagnostic_count: int
    omitted: int
    resources: dict[str, int]
    excerpts: dict[str, int]
    schema: dict[str, str | None]
    source: dict[str, str | None]


def _bounded(text: str) -> str:
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT - 1] + "…"


@dataclass
class ValidationReport:
    """The verdict covers every finding, including diagnostics omitted from the response."""
    checks: dict[str, str]
    limit: int
    outcome: str = "valid"
    exit_code: int = 0
    diagnostics: list[Diagnostic] = field(default_factory=list)
    total: int = 0
    concept_count: int | None = None
    excerpts: dict = field(default_factory=dict)
    resources: dict = field(default_factory=dict)
    selected_schema: Path | None = None
    schema_revision: str | None = None
    schema_reason: str | None = "schema unavailable"

    def _record(self, check, code, severity, message, document=None, field=None, line=None):
        self.total += 1
        if len(self.diagnostics) < self.limit:
            self.diagnostics.append({
                "check": check, "code": code, "severity": severity,
                "message": _bounded(message), "document": _bounded(document) if document else None,
                "field": _bounded(field) if field else None, "line": line,
            })
        if severity == "error":
            if self.checks[check] != "unavailable":
                self.checks[check] = "failed"
            self.outcome = "invalid"
            self.exit_code = 1

    def _unavailable(self, check, code, message, exit_code=1, document=None, field=None):
        previous = self.outcome
        self._record(check, code, "error", message, document, field)
        self.checks[check] = "unavailable"
        self.outcome = "invalid" if previous == "invalid" else "incomplete"
        self.exit_code = exit_code

    def as_dict(self) -> ValidationResult:
        """Bounded, JSON-serializable result for a live bundle."""
        return {
            "outcome": self.outcome, "checks": self.checks, "concept_count": self.concept_count,
            "diagnostics": self.diagnostics, "diagnostic_count": self.total,
            "omitted": self.total - len(self.diagnostics), "excerpts": self.excerpts, "resources": self.resources,
            "schema": {"revision": self.schema_revision, "reason": self.schema_reason},
            "source": {"kind": "live_bundle", "revision": None, "reason": "live files read during validation"},
        }


@lru_cache(maxsize=1)
def _packaged_shapes(turtle: bytes):
    from rdflib import Graph
    # validate_graph copies these shapes before applying per-bundle constraints.
    return Graph().parse(data=turtle, format="turtle")


def _compile_validator(path, target_class, *, closed, include_range_class_descendants, path_override):
    import jsonschema
    from linkml.generators.jsonschemagen import JsonSchemaGenerator

    if path_override is None:
        from linkml.utils.helpers import get_range_associated_slots

        generator = JsonSchemaGenerator(str(path), mergeimports=True, not_closed=not closed,
                                        include_range_class_descendants=include_range_class_descendants)
        # Set the target after localizing the view. Passing top_class to the constructor
        # would look it up while LinkML's process-wide memoizers are still attached.
        local_view_caches(generator.schemaview)
        generator.top_class = target_class
        if generator.schemaview.get_class(target_class) is None:
            raise ValueError(f"Schema does not declare {target_class}")
        try:
            schema = generator.generate()
        finally:
            # LinkML also memoizes (view, range) in a module-level helper. Its
            # public cache API only supports clearing all entries. Clear it once
            # per generation, including failures, so it cannot pin expired views.
            clear = getattr(get_range_associated_slots, "cache_clear", None)
            if clear is not None:
                clear()
    else:
        schema = json.loads(Path(path_override).read_bytes())
    cls = jsonschema.validators.validator_for(schema, default=jsonschema.Draft7Validator)
    return cls(schema, format_checker=cls.FORMAT_CHECKER)


class _ValidationSchema:
    """Revision-owned context for LinkML's JSON Schema validation plugin."""

    target_class = "KnowledgeBundle"

    def __init__(self, path: Path, inputs: SchemaInputs | None = None, directory: TemporaryDirectory | None = None):
        self.path = path
        self.inputs = inputs
        self.directory = directory  # Own the private files for this revision's lifetime.
        self.json_schema_validator = lru_cache(maxsize=1)(partial(_compile_validator, path, self.target_class))

    @cached_property
    def definitions(self):
        return self.json_schema_validator(closed=True, include_range_class_descendants=True,
                                          path_override=None).schema["$defs"]

    @cached_property
    def shapes(self):
        from lokf.shacl import build_shapes
        return build_shapes(self.path, inputs=self.inputs)

    @cached_property
    def default_shapes(self):
        from importlib.resources import files

        packaged = files("lokf") / "data"
        # The captured root retains the original bytes before its imports were rewritten.
        if self.inputs and self.inputs.sources[0].data == (packaged / "lokf.yaml").read_bytes():
            return _packaged_shapes((packaged / "lokf.shacl.ttl").read_bytes())
        return self.shapes


@cache_per_root
def _local_schema(inputs: SchemaInputs) -> _ValidationSchema:
    """Path-based LinkML generators reopen imports. Give them only captured inputs."""
    directory = TemporaryDirectory(prefix="lokf-validation-")
    try:
        for i, source in enumerate(inputs.sources):
            dest = Path(directory.name) / f"{i}.yaml"
            if inputs.edges[i]:
                spec = dict(parsed(source.data), imports=[str(j) for j in inputs.edges[i]])
                dest.write_text(yaml.dump(spec, Dumper=getattr(yaml, "CSafeDumper", yaml.SafeDumper),
                                          sort_keys=False), encoding="utf-8")
            else:
                dest.write_bytes(source.data)
        return _ValidationSchema(Path(directory.name) / "0.yaml", inputs, directory)
    except BaseException:
        directory.cleanup()
        raise


def _pointer(path):
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in path)


def _authored_path(path, mappings):
    if len(path) >= 2 and path[0] in mappings and path[1] == 0:
        return [path[0], *path[2:]]
    return path


def _nested_errors(error):
    """Descend union failures, omitting branches incompatible with the value type."""
    if not error.context:
        yield error
        return
    branches = {}
    for child in error.context:
        branch = next(iter(child.schema_path), None)
        branches.setdefault(branch, []).append(child)
    compatible = [group for group in branches.values() if not any(
        child.validator == "type" and list(child.absolute_path) == list(error.absolute_path)
        for child in group
    )]
    for group in compatible or branches.values():
        for child in group:
            yield from _nested_errors(child)


def _field_errors(error, path):
    """Extract the offending key without sending the instance or document body."""
    if error.validator == "additionalProperties":
        allowed = error.schema.get("properties", {})
        patterns = error.schema.get("patternProperties", {})
        for key in sorted(error.instance, key=str):
            if key in allowed or any(re.search(pattern, str(key)) for pattern in patterns):
                continue
            yield "schema.unknown_field", path + [key], f"Undeclared field: {key}"
    elif error.validator == "required":
        for key in error.validator_value:
            if key not in error.instance:
                yield "schema.required", path + [key], f"Missing required field: {key}"
    elif error.validator == "anyOf" and isinstance(error.instance, dict) and "type" not in error.instance:
        # Check the actual alternatives so a domain union can allow an untyped value.
        requiring_type = {e.schema_path[0] for e in error.context if not e.path and e.schema_path
                          and e.validator == "required" and "type" in e.validator_value}
        if requiring_type == set(range(len(error.validator_value))):
            yield "schema.required", path + ["type"], "Missing required field: type"
        else:
            yield "schema.anyOf", path, "Value violates the anyOf constraint."
    else:
        rule = str(error.validator)
        reason = f"Expected type {error.validator_value}." if rule == "type" else f"Value violates the {rule} constraint."
        yield "schema." + rule, path, reason


def _class_errors(error, name, schema):
    """Return the declared class's errors with paths relative to the concept."""
    reference = {"$ref": f"#/$defs/{name}"}
    for index, alternative in enumerate(error.validator_value):
        if alternative == reference:
            depth = len(error.absolute_path)
            children = (e for e in error.context if next(iter(e.schema_path), None) == index)
            return [(d, list(d.absolute_path)[depth:]) for child in children for d in _nested_errors(child)]
    # A class can be declared without being a direct alternative of this union.
    import jsonschema

    defs = schema.definitions
    if name not in defs:
        return None
    sub = {"$defs": defs, **defs[name]}
    cls = jsonschema.validators.validator_for(sub)
    validator = cls(sub, format_checker=cls.FORMAT_CHECKER)
    return [(d, list(d.absolute_path)) for e in validator.iter_errors(error.instance) for d in _nested_errors(e)]


def _schema_findings(report, bundle, schema, emit):
    from linkml.validator.plugins import JsonschemaValidationPlugin

    results = JsonschemaValidationPlugin(closed=True).process(dict(bundle.meta, concepts=bundle.docs()), schema)
    missing_fields = set()
    for row in results:
        error = row.source
        severity = row.severity.name
        level = {"WARN": "warning", "WARNING": "warning", "FATAL": "error"}.get(severity, severity.lower())
        path = list(error.absolute_path) if error is not None else []
        doc = "index.md"
        local = path
        mappings = ()
        if len(path) >= 2 and path[0] == "concepts" and isinstance(path[1], int):
            concept = bundle.concepts[path[1]]
            doc = concept.path.relative_to(bundle.root).as_posix()
            mappings = concept.authored_mappings
            local = path[2:]
        if error is None:
            report._record("schema", "schema.validation", level, row.message, doc)
            if emit:
                emit(f"[{severity}] {row.message}")
            continue
        message = row.message
        errors = [(error, local)]
        if error.validator == "anyOf" and isinstance(error.instance, dict) and "type" in error.instance:
            name = error.instance["type"]
            details = _class_errors(error, name, schema) if isinstance(name, str) else None
            if details:
                errors = [(d, local + relative) for d, relative in details]
                if emit:
                    prefix = path[:len(path) - len(local)]
                    specifics = dict.fromkeys(f"{_pointer(prefix + _authored_path(local + rel, mappings))}: {d.message}"
                                              for d, rel in details)
                    message += f"\n  on {name}: " + "; ".join(specifics)
            elif not isinstance(name, str):
                report._record("schema", "schema.type", level, "Expected type string.", doc, _pointer([*local, "type"]))
                errors = []
            elif details is None:
                reason = (f"`type: {name!r}` isn't a class this schema declares. A project-specific type "
                          "needs a domain vocabulary that `imports: [lokf]` and adds it - see `lokf validate --schema`.")
                report._record("schema", "schema.unknown_type", level, reason, doc, _pointer([*local, "type"]))
                message += "\n  hint: " + reason
                errors = []
        for detail, detail_path in errors:
            for code, field_path, reason in _field_errors(detail, detail_path):
                pointer = _pointer(_authored_path(field_path, mappings))
                if code == "schema.required":
                    if (doc, pointer) in missing_fields:
                        continue
                    missing_fields.add((doc, pointer))
                report._record("schema", code, level, reason, doc, pointer)
        if emit:
            emit(f"[{severity}] {message}")


def _shacl_findings(report, bundle, selected, schema, emit):
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import RDF, SH
    from lokf.shacl import validate_graph

    inputs = schema.inputs
    shapes = schema.default_shapes if selected is None else schema.shapes
    # Core bundles use the published authoring context. Type lookup still uses
    # the captured schema, including for a core checkout edited during this call.
    context = schema_context(None) if selected is None else None
    graph = bundle.graph(context=context, schema=inputs or selected)
    by_iri = bundle.by_iri()
    conforms, results, text = validate_graph(graph, shapes, bundle.base_iri, by_iri)
    if conforms:
        return
    if not isinstance(results, Graph):
        raise ValueError("SHACL engine could not produce a validation report")
    if emit:
        emit(text)
    duplicates = dict(bundle.duplicate_iris()) if len(by_iri) < len(bundle.concepts) else {}
    concepts = {c.concept_id: c for c in bundle.concepts} if duplicates else {}

    @lru_cache(maxsize=32)
    def assertion_sources(subject):
        # RDF merges duplicate subjects. Project their already-loaded documents
        # separately only when the failing assertion needs attribution.
        sources = {}
        for concept_id in duplicates[str(subject)]:
            candidate = concepts[concept_id]
            single = Bundle(bundle.root, bundle.meta, [candidate])
            projection = single.graph(context=context, schema=inputs or selected)
            for pair in projection.predicate_objects(subject):
                sources[pair] = None if pair in sources else candidate
        return sources

    findings = []
    for node in results.subjects(RDF.type, SH.ValidationResult):
        component = results.value(node, SH.sourceConstraintComponent)
        name = str(component).removeprefix(str(SH)).removesuffix("ConstraintComponent")
        focus = results.value(node, SH.focusNode)
        path = results.value(node, SH.resultPath)
        value = results.value(node, SH.value)
        concept = by_iri.get(str(focus)) if isinstance(focus, URIRef) else None
        if str(focus) in duplicates:
            concept = None
            if isinstance(path, URIRef) and isinstance(value, (URIRef, Literal)):
                concept = assertion_sources(focus).get((path, value))
        prop = str(path) if isinstance(path, URIRef) else ""
        document = concept.path.relative_to(bundle.root).as_posix() if concept else ""
        reason = f"RDF value violates the SHACL {name} constraint."
        if component == SH.ClassConstraintComponent:
            shape = results.value(node, SH.sourceShape)
            expected = shapes.value(shape, SH["class"]) if shape is not None else None
            if isinstance(expected, URIRef):
                target = f"Target {value}" if isinstance(value, URIRef) else "Referenced value"
                reason = f"{target} must have class {expected}."
        findings.append((document, prop, name, reason))
    for doc, prop, name, reason in sorted(findings):
        report._record("shacl", "shacl." + name, "error", reason, doc, prop)
    if not findings:
        report._record("shacl", "shacl.violation", "error", "RDF does not conform to the shapes.")


def _markdown_files(root):
    """Enumerate the validation input once. A failed scan must reach the caller."""
    files = []
    pending = [root]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                path = Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                if path.match("*.md"):
                    files.append(path)
    return sorted(files)


def validate_bundle(bundle: str | Path, *, schema: str | Path | None = None,
                    check_ids: bool = False, check_refs: bool = False, check_resources: bool = False,
                    check_excerpts: bool = False, shacl: bool = False, root: str | Path | None = None,
                    max_diagnostics: int = 50, emit: Callable[[str], None] | None = None) -> ValidationReport:
    """Validate a local bundle. An optional sink receives full CLI diagnostics in check order."""
    directory = Path(bundle)
    selected = {"input": True, "schema": True, "logs": True, "exclusions": True,
                "excerpt_conflicts": True, "events": True, "ids": check_ids, "refs": check_refs,
                "resources": check_resources, "excerpts": check_excerpts, "shacl": shacl}
    if type(max_diagnostics) is not int or not 1 <= max_diagnostics <= MAX_DIAGNOSTICS:
        raise ValueError(f"max_diagnostics must be between 1 and {MAX_DIAGNOSTICS}")
    report = ValidationReport({k: "skipped" if enabled else "disabled" for k, enabled in selected.items()},
                              max_diagnostics)
    current = "input"

    def unavailable(code, message, exit_code=1, *, cli_message=None):
        report._unavailable(current, code, message, exit_code)
        if emit:
            emit(cli_message or message)
        return report

    try:
        if not directory.is_dir():
            return unavailable("input.bundle", "Bundle must be an existing directory.", 2)
        if root is not None and not (check_resources or check_excerpts):
            return unavailable("input.root", "--root requires --check-resources or --check-excerpts", 2)
        if root is not None and not Path(root).is_dir():
            return unavailable("input.root", "Resource root must be an existing directory.", 2)
        if schema is not None and not Path(schema).is_file():
            return unavailable("input.schema", "Explicit schema must be an existing file.", 2)
        if shacl:
            try:
                import pyshacl  # noqa: F401
            except ModuleNotFoundError:
                current = "shacl"
                return unavailable("dependency.shacl", "SHACL validation needs the optional extra: pip install 'lokf[shacl]'")
        try:
            from linkml.validator.plugins import JsonschemaValidationPlugin  # noqa: F401
        except ModuleNotFoundError:
            current = "schema"
            return unavailable("dependency.linkml", "validation needs LinkML, which the core install leaves out.\n"
                               "  install:  uv pip install 'lokf[build]'\n"
                               "  one-off:  uvx --from 'lokf[build]' lokf validate <bundle>")
        current = "schema"
        report.selected_schema = domain_schema(schema, directory)
        path = schema_path(report.selected_schema)
        current = "input"
        markdown_files = _markdown_files(directory)
        kb = _load_bundle_files(directory, markdown_files, (directory / "index.md") in markdown_files)
        report.concept_count = len(kb.concepts)
        report.checks[current] = "passed"
        current = "schema"
        captured = projection_schema(path)
        prepared = _local_schema(captured) if isinstance(captured, SchemaInputs) else _ValidationSchema(path)
        inputs = prepared.inputs
        report.schema_revision = inputs.metadata()["revision"] if inputs else None
        report.schema_reason = None if inputs else "schema has live imports"
        report.checks[current] = "passed"
        _schema_findings(report, kb, prepared, emit)
        current = "logs"
        report.checks[current] = "passed"
        for severity, logfile, line, message in _check_log_files(p for p in markdown_files if p.match("log.md")):
            report._record(current, "log.heading", severity.lower(), message,
                          logfile.relative_to(directory).as_posix(), line=line)
            if emit:
                emit(f"[{severity}] {logfile}:{line}: {message}")

        def record_located(check, findings):
            report.checks[check] = "passed"
            for code, doc, field, severity, msg in findings:
                if code in ("excerpt.unavailable", "resource.unavailable"):
                    report._unavailable(check, code, msg, document=doc, field=field)
                else:
                    report._record(check, code, severity.lower(), msg, doc, field)
                if emit:
                    emit(f"[{severity}] {msg}")

        # Source ids expand under the projection's context; a schema with live
        # imports falls back to the published one rather than fetching here.
        if report.selected_schema is None or inputs is None:
            source_context = schema_context(None)
        else:
            source_context = schema_context(inputs)
        for current, findings in (
            ("exclusions", exclusion_findings(kb)),
            ("excerpt_conflicts", excerpt_conflict_findings(kb, source_context)),
            ("events", event_diagnostics(kb)),
        ):
            record_located(current, findings)
        if check_ids:
            current = "ids"
            report.checks[current] = "passed"
            for iri, ids in kb.duplicate_iris():
                msg = f"id declared by more than one file: {iri} ({', '.join(ids)})"
                report._record(current, "id.duplicate", "error", msg, ids[0] + ".md", "/id")
                if emit:
                    emit(f"[ERROR] {msg}")
        if check_refs:
            current = "refs"
            report.checks[current] = "passed"
            concepts = {c.concept_id: c for c in kb.concepts}
            for concept_id, slot, target in kb.dangling_refs(schema_path=inputs or path):
                key = slot if slot in concepts[concept_id].data else underscore(slot)
                msg = f"{concept_id}: `{slot}` target does not resolve to a concept in the bundle: {target}"
                report._record(current, "reference.missing", "error", msg, concept_id + ".md", _pointer([key]))
                if emit:
                    emit(f"[ERROR] {msg}")
        if check_resources or check_excerpts:
            current = "resources" if check_resources else "excerpts"
            resource_dir = Path(root) if root is not None else resource_root(directory)
            if check_resources:
                record_located(current, resource_findings(kb, resource_dir, report.resources))
            if check_excerpts:
                current = "excerpts"
                record_located(current, excerpt_findings(kb, resource_dir, report.excerpts))
        if shacl and report.outcome == "valid":
            current = "shacl"
            report.checks[current] = "passed"
            _shacl_findings(report, kb, report.selected_schema, prepared, emit)
    except DocumentError as exc:
        report._record(current, exc.code, "error", exc.reason.splitlines()[0],
                      Path(exc.where).relative_to(directory).as_posix(), line=exc.line)
        if emit:
            emit(str(exc))
    except Exception as exc:
        # Third-party schema generators and validators have different exception types.
        # An engine or filesystem failure cannot certify or reject the content.
        reason = f"Could not complete the {current} check ({type(exc).__name__})."
        if current == "input" and isinstance(exc, OSError) and exc.filename:
            location = Path(exc.filename)
            if location.is_relative_to(directory):
                reason = f"Could not inspect {location.relative_to(directory).as_posix()!r} ({type(exc).__name__})."
        if current == "schema" and report.selected_schema is None and isinstance(exc, (FileNotFoundError, ValueError)):
            reason = str(exc).partition("\n")[0] or reason
        return unavailable(current + ".unavailable", reason, cli_message=str(exc))
    return report
