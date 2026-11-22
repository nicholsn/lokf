import { join } from 'node:path';
import { checkPublicRoute } from './view-data.ts';

export const schemaKinds = ['classes', 'slots', 'enums', 'types'] as const;
export type SchemaKind = typeof schemaKinds[number];
type Schema = Record<SchemaKind, { name: string }[]>;

export function schemaPath(model: Schema, kind: SchemaKind, name: string) {
  // A case-insensitive build filesystem must give Gene and gene distinct pages.
  const caseCollision = model[kind].some(term =>
    term.name !== name && term.name.toLowerCase() === name.toLowerCase());
  const segment = /^[A-Za-z0-9_-]+$/.test(name) && !caseCollision
    ? name : '~' + Buffer.from(name).toString('hex');
  return `schema/${kind}/${segment}`;
}

const schemaRoute = /^schema(?:\/|$)/i;

export function checkSectionRoutes(sections: string[], viewPaths: Iterable<string>, schemaBrowser: boolean) {
  const views = new Set(Array.from(viewPaths, path => path.toLowerCase()));
  for (const section of sections) {
    const source = `knowledge/${section}/index.md`;
    if (schemaBrowser && schemaRoute.test(section)) {
      throw new Error(`Schema browser route collision at /${section}/ with ${source}. Rename the section or disable schemaBrowser.`);
    }
    if (views.has(section.toLowerCase())) {
      throw new Error(`View route /${section}/ collides with ${source}. Rename the section or change the view ID.`);
    }
  }
}

export function checkSchemaRoutes(model: Schema, concepts: {id: string}[], viewPaths: Iterable<string>,
                                  publicDir = join(process.cwd(), 'public')) {
  for (const path of [...concepts.map(entry => entry.id), ...viewPaths]) {
    if (schemaRoute.test(path)) {
      throw new Error(`Schema browser route collision at /${path}/. Rename the record or view, or disable schemaBrowser.`);
    }
  }
  checkPublicRoute('schema', 'Schema browser', publicDir);
  for (const kind of schemaKinds) {
    for (const term of model[kind]) checkPublicRoute(schemaPath(model, kind, term.name), 'Schema browser', publicDir);
  }
}

interface Bounds {
  required?: boolean;
  multivalued?: boolean;
  minimum_cardinality?: number;
  maximum_cardinality?: number;
  exact_cardinality?: number;
}

export function slotCardinality(slot: Bounds) {
  const min = slot.exact_cardinality ?? Math.max(slot.minimum_cardinality ?? 0, slot.required ? 1 : 0);
  const declaredMax = slot.exact_cardinality ?? slot.maximum_cardinality;
  const max = slot.multivalued ? declaredMax ?? '*' : Math.min(declaredMax ?? 1, 1);
  return `${min}..${max}`;
}
