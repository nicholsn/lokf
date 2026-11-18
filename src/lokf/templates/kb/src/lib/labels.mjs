/**
 * How the site names a schema's terms. `lokf export` writes the schema's
 * titles into graph.json as `meta.vocabulary` (each type, each relation read
 * from either end, each type's own fields); these helpers read it, and fall
 * back to the raw name made readable for a graph exported without it.
 */

/** A schema name as words: `DataStage` → "Data stage", `isPartOf` → "Is part of". */
export function readable(name) {
  const words = String(name ?? '')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((word) => (word.length > 1 && word === word.toUpperCase() ? word : word.toLowerCase()));
  const text = words.join(' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** The title of concept type `type`. */
export function typeTitle(vocabulary, type) {
  return vocabulary?.types?.[type]?.title || readable(type) || 'Concept';
}

/** Relation `slot` as its subject reads it: "Derived from". */
export function relationTitle(vocabulary, slot) {
  return vocabulary?.relations?.[slot]?.title || readable(slot);
}

/**
 * Relation `slot` as its object reads it, on the target's page: the schema's
 * `inverse_title` ("Has derivative"), or, where it gives none, the forward
 * title behind an arrow that points at this concept.
 */
export function incomingTitle(vocabulary, slot) {
  return vocabulary?.relations?.[slot]?.inverse_title || `← ${relationTitle(vocabulary, slot)}`;
}

/** The value fields the schema declares for concept type `type`, in order. */
export function fieldsOf(vocabulary, type) {
  const fields = vocabulary?.fields?.[type];
  return Array.isArray(fields) ? fields : [];
}

/** A field's frontmatter value as display strings; nested objects are skipped. */
export function fieldValues(value) {
  return (Array.isArray(value) ? value : [value])
    .filter((item) => item instanceof Date || (item !== null && item !== undefined && item !== '' && typeof item !== 'object'))
    .map((item) => item instanceof Date ? item.toISOString().replace(/T00:00:00\.000Z$/, '') : String(item));
}
