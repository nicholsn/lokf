/** Routes and return links for the toolkit's ordered, compiled view plan. */
export const INDEX_SIZE = 20;
export const SECTION_SIZE = 25;
export const PREVIEW_SIZE = 3;

type Scalar = string | number | boolean;
type RelationStep = ({ in: string } | { out: string }) & { type?: string };
export interface ViewRecord {
  title: string;
  fields: Record<string, Scalar | Scalar[] | null>;
  dates: Record<string, string | null>;
}
export interface Display {
  layout: 'list' | 'table' | 'timeline';
  date?: string;
  date_label?: string;
  date_from?: 'root';
  order_by?: RelationStep;
  columns?: ({ field: string; label: string } | { relation: RelationStep; label: string })[];
}
export interface Section { id: string; title: string; display: Display }
export interface Row {
  id: string;
  links?: Record<string, string[]>; // Related concept IDs by zero-based table column.
  witness?: { id: string; predicate: string; direction: 'in' | 'out'; reified: boolean }[];
}
export type OrderStatus = 'complete' | 'partial' | 'unlinked';
export interface Root extends Row { sections: Record<string, Row[]>; ordering?: Record<string, OrderStatus> }
export interface View {
  id: string;
  title: string;
  description: string;
  index: Display & { embed?: string[]; family_by?: RelationStep };
  sections: Section[];
  roots: Root[];
  families?: { id: string; members: string[] }[];
}
export interface Plan { views: View[]; records: Record<string, ViewRecord> }
export interface IndexFamily {
  root: Root;
  members: Root[];
  repeated: string[];
}
export interface ViewPage { view: View; page: number; families?: IndexFamily[]; detail?: { root: Root; section: Section } }

export function encodedPath(path: string) {
  return path.split('/').map(encodeURIComponent).join('/');
}
export function sectionId(view: View, section: Section) {
  return `view.${view.id}.${section.id}`;
}
export function rowId(scope: string, id: string) {
  // One fragment token even for concept IDs containing whitespace, slashes, or Unicode.
  return `${scope}:${Buffer.from(id, 'utf8').toString('base64url')}`;
}
export function indexPath(view: View, page = 1) {
  return page === 1 ? `views/${view.id}` : `views/${view.id}/page/${page}`;
}
function sectionRoute(view: View, section: Section, root: Root, page: number) {
  return `views/${view.id}/sections/${section.id}/${root.id}/page/${page}`;
}
/** Site-relative encoded link; give it to href() to apply Astro's project base. */
export function sectionLink(view: View, section: Section, root: Root, page = 1, member?: string) {
  const fragment = sectionId(view, section);
  const route = page === 1 ? root.id : sectionRoute(view, section, root, page);
  return `${encodedPath(route)}/#${member ? rowId(fragment, member) : fragment}`;
}
export function rootScope(view: View) { return `index.${view.id}`; }

export function pageSlice<T>(items: T[], page: number, size: number) {
  return items.slice((page - 1) * size, page * size);
}

export function buildNavigation(plan: Plan) {
  const pages = new Map<string, ViewPage>();
  const roots = new Map<string, {view: View; root: Root; link: string}[]>();
  const memberships = new Map<string, {title: string; section: string; link: string}[]>();
  const addPage = (path: string, info: ViewPage) => {
    if (pages.has(path)) throw new Error(`Declarative view route collision at /${path}/`);
    pages.set(path, info);
  };

  for (const view of plan.views) {
    const indexPages = Math.max(1, Math.ceil((view.families ?? view.roots).length / INDEX_SIZE));
    const indexLinks = new Map<string, string>();
    const byId = new Map(view.roots.map(root => [root.id, root]));
    for (let page = 1; page <= indexPages; page++) {
      const path = indexPath(view, page);
      const anchor = (id: string) => `${path}/#${rowId(rootScope(view), id)}`;
      const info: ViewPage = { view, page };
      if (view.families) {
        info.families = pageSlice(view.families, page, INDEX_SIZE).map(({ id, members }) => {
          indexLinks.set(id, anchor(id));
          // A shared descendant links back to its first family in the index.
          const repeated = members.filter(member => indexLinks.has(member));
          for (const member of members) {
            if (!indexLinks.has(member)) indexLinks.set(member, anchor(member));
          }
          return { root: byId.get(id)!, members: members.map(member => byId.get(member)!), repeated };
        });
      } else {
        for (const root of pageSlice(view.roots, page, INDEX_SIZE)) indexLinks.set(root.id, anchor(root.id));
      }
      addPage(path, info);
    }

    for (const root of view.roots) {
      const link = indexLinks.get(root.id)!;
      if (!roots.has(root.id)) roots.set(root.id, []);
      roots.get(root.id)!.push({ view, root, link });

      for (const section of view.sections) {
        const rows = root.sections[section.id];
        for (let page = 2; page <= Math.ceil(rows.length / SECTION_SIZE); page++) {
          addPage(sectionRoute(view, section, root, page), { view, page, detail: { root, section } });
        }
        rows.forEach((row, i) => {
          if (!memberships.has(row.id)) memberships.set(row.id, []);
          memberships.get(row.id)!.push({
            title: plan.records[root.id].title,
            section: section.title,
            link: sectionLink(view, section, root, 1 + Math.floor(i / SECTION_SIZE), row.id),
          });
        });
      }
    }
  }
  return { ...plan, pages, roots, memberships };
}

export type Navigation = ReturnType<typeof buildNavigation>;

/** Vite renders a concept's Markdown headings on the same page as these fragments. */
export function checkConceptFragments(navigation: Navigation, id: string, headings: { slug: string }[]) {
  const occupied = new Set(headings.map(h => h.slug));
  for (const { view, root } of navigation.roots.get(id) ?? []) {
    for (const section of view.sections) {
      const scope = sectionId(view, section);
      const anchors = [scope, ...pageSlice(root.sections[section.id], 1, SECTION_SIZE).map(r => rowId(scope, r.id))];
      for (const anchor of anchors) {
        if (occupied.has(anchor)) throw new Error(`View fragment collision on ${id}: #${anchor}`);
        occupied.add(anchor);
      }
    }
  }
}
