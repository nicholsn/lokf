import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { href } from './lokf';
import { incomingTitle, relationTitle, typeTitle } from './labels.mjs';

export type GraphElement = { data: Record<string, any> };
export type GraphData = {
  nodes: GraphElement[];
  edges: GraphElement[];
  external_edges?: GraphElement[];
  meta?: Record<string, unknown>;
};

const generated = (name: string) => join(process.cwd(), 'src', 'generated', name);

async function readGenerated(name: string): Promise<any> {
  try {
    return JSON.parse(await readFile(generated(name), 'utf8'));
  } catch (error) {
    throw new Error(`Cannot read ${name}; run npm run build or npm run dev to generate LOKF data.`, { cause: error });
  }
}

let graphPromise: Promise<GraphData> | undefined;
let conceptsPromise: Promise<any> | undefined;

/**
 * The same schema-aware graph emitted by `lokf export`, with site URLs added
 * and every type and relation titled as the schema names it (`type_title` on
 * nodes; `title` and, read from the target, `incoming_title` on edges).
 */
export function loadGraphData(): Promise<GraphData> {
  const read = () => Promise.all([readGenerated('graph.json'), loadConceptsJsonLd()])
    .then(([graph, concepts]) => {
      const byIri = new Map<string, Record<string, any>>(
        (concepts['@graph'] ?? []).map((doc: Record<string, any>) => [String(doc.id), doc]),
      );
      const vocabulary = graph.meta?.vocabulary;
      const titled = (edge: GraphElement) => ({
        data: {
          ...edge.data,
          title: relationTitle(vocabulary, edge.data.slot || edge.data.predicate),
          incoming_title: incomingTitle(vocabulary, edge.data.slot || edge.data.predicate),
        },
      });
      return {
        ...graph,
        nodes: graph.nodes.map((node: GraphElement) => {
          const doc = byIri.get(String(node.data.id));
          return {
            data: {
              ...node.data,
              href: href('/' + node.data.concept_id),
              type_title: typeTitle(vocabulary, node.data.type),
              ...(doc?.description ? { description: doc.description } : {}),
              ...(Array.isArray(doc?.tags) ? { tags: doc.tags } : {}),
            },
          };
        }),
        edges: graph.edges.map(titled),
        external_edges: (graph.external_edges ?? []).map(titled),
      };
    });
  if (import.meta.env.DEV) return read();
  return graphPromise ||= read();
}

/** The schema's titles for the types, relations and fields the graph uses. */
export async function loadVocabulary(): Promise<Record<string, any>> {
  return ((await loadGraphData()).meta?.vocabulary ?? {}) as Record<string, any>;
}

export function loadConceptsJsonLd() {
  if (import.meta.env.DEV) return readGenerated('concepts.jsonld');
  return conceptsPromise ||= readGenerated('concepts.jsonld');
}

type ProjectionIndex = {
  nodes: Map<string, Record<string, any>>;
  documents: Map<string, Record<string, any>>;
  outgoing: Map<string, GraphElement[]>;
  incoming: Map<string, GraphElement[]>;
  context: unknown;
};
let projectionPromise: Promise<ProjectionIndex> | undefined;

/** Reuse corpus-wide lookup maps while rendering every static concept page. */
export function loadProjectionIndex(): Promise<ProjectionIndex> {
  const read = () => Promise.all([loadGraphData(), loadConceptsJsonLd()]).then(([graph, jsonld]) => {
    const nodes = new Map(graph.nodes.map(node => [String(node.data.id), node.data]));
    const documents = new Map<string, Record<string, any>>(
      (jsonld['@graph'] ?? []).map((doc: Record<string, any>) => [String(doc.id), doc]),
    );
    const outgoing = new Map<string, GraphElement[]>();
    const incoming = new Map<string, GraphElement[]>();
    for (const edge of [...graph.edges, ...(graph.external_edges ?? [])]) {
      const source = String(edge.data.source);
      const target = String(edge.data.target);
      if (!outgoing.has(source)) outgoing.set(source, []);
      outgoing.get(source)!.push(edge);
      if (!incoming.has(target)) incoming.set(target, []);
      incoming.get(target)!.push(edge);
    }
    return { nodes, documents, outgoing, incoming, context: jsonld['@context'] };
  });
  if (import.meta.env.DEV) return read();
  return projectionPromise ||= read();
}
