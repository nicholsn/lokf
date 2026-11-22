import { join } from 'node:path';
import { readFile } from 'node:fs/promises';
import config from '../../site.config.mjs';
import { href } from './lokf';
import { schemaPath, type SchemaKind } from './schema-browser';

export const schemaHref = (model: any, kind: SchemaKind, name: string) => href(schemaPath(model, kind, name));
let cached: Promise<any> | undefined;
export function loadSchema() {
  if (config.schemaBrowser !== true) return Promise.resolve(null);
  const read = async () => {
    const model = JSON.parse(await readFile(join(process.cwd(), 'src', 'generated', 'schema.json'), 'utf8'));
    if (model.format !== 'lokf-schema-docs-v1') throw new Error('Unsupported schema documentation format. Re-run lokf export --schema-docs.');
    return model;
  };
  return import.meta.env.DEV ? read() : cached ||= read();
}
export function rangeHref(model: any, name: string) {
  for (const kind of ['classes', 'enums', 'types'] as const) {
    if (model[kind].some((item: any) => item.name === name)) return schemaHref(model, kind, name);
  }
}
