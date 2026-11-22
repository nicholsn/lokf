"""A static TBox reference, resolved by LinkML rather than inferred from instances."""
from __future__ import annotations

from linkml_runtime.utils.schemaview import SchemaView
from lokf.schema import schema_path

FORMAT = "lokf-schema-docs-v1"


def schema_documentation(path=None):
    """Include imported/abstract classes and effective, class-specific slot constraints."""
    view = SchemaView(str(schema_path(path)))
    classes = view.all_classes()
    slots = view.all_slots(attributes=False)
    enums = view.all_enums()
    types = view.all_types()

    def basic(element):
        return {"name": str(element.name), "title": str(element.title or element.name),
                "description": str(element.description or ""),
                "origin": str(element.from_schema or ""),
                "local": str(element.from_schema) == str(view.schema.id)}

    def slot_row(slot):
        row = basic(slot)
        for key in ("range", "required", "recommended", "multivalued", "pattern",
                    "minimum_value", "maximum_value", "minimum_cardinality",
                    "maximum_cardinality", "exact_cardinality", "inlined", "inlined_as_list", "identifier",
                    "key", "readonly", "is_a"):
            value = getattr(slot, key, None)
            if value is not None:
                row[key] = value if isinstance(value, (str, bool, int, float)) else str(value)
        row["uri"] = str(view.get_uri(slot, expand=True))
        row["any_of"] = [str(x.range) for x in slot.any_of if x.range]
        return row

    class_rows = []
    for name, cls in sorted(classes.items()):
        row = basic(cls)
        row.update(uri=str(view.get_uri(cls, expand=True)), abstract=bool(cls.abstract),
                   mixin=bool(cls.mixin), is_a=str(cls.is_a) if cls.is_a else None,
                   mixins=[str(x) for x in cls.mixins], slots=[])
        direct = set(cls.slots) | set(cls.attributes)
        attributes = {attr for ancestor in view.class_ancestors(name) for attr in classes[ancestor].attributes}
        for slot in view.class_induced_slots(name):
            field = slot_row(slot)
            if slot.name in attributes:
                field["class_attribute"] = True
            field["declared_here"] = slot.name in direct
            field["overridden_here"] = slot.name in cls.slot_usage
            row["slots"].append(field)
        row["slots"].sort(key=lambda x: x["name"])
        class_rows.append(row)
    return {"format": FORMAT, "name": str(view.schema.name), "id": str(view.schema.id),
            "title": str(view.schema.title or view.schema.name),
            "description": str(view.schema.description or ""),
            "classes": class_rows,
            "slots": [slot_row(s) for _, s in sorted(slots.items())],
            "enums": [{**basic(e), "values": [
                {"name": str(n), "description": str(v.description or ""),
                 "meaning": str(v.meaning or "")} for n, v in e.permissible_values.items()
            ]} for _, e in sorted(enums.items())],
            "types": [{**basic(t), "uri": str(t.uri or ""),
                       "base": str(t.base or t.typeof or "")} for _, t in sorted(types.items())]}
