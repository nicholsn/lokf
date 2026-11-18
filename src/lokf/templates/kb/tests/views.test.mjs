import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildNavigation, checkConceptFragments, filledSections, rowId } from '../src/lib/view-navigation.ts';
import { checkViewRoutes } from '../src/lib/view-data.ts';

function fixture() {
  const ids = Array.from({ length: 21 }, (_, i) => `issues/issue ${i}`);
  const children = Array.from({ length: 26 }, (_, i) => ({ id: `developments/${i}` }));
  const roots = ids.map((id, i) => ({ id, sections: { entries: i === 0 || i === 20 ? children : [] } }));
  return {
    views: [{
      id: 'editions', title: 'Editions', description: 'Browse editions', roots,
      index: { layout: 'list' },
      sections: [{ id: 'entries', title: 'Developments', display: { layout: 'list' } }],
    }],
    records: Object.fromEntries([...ids, ...children.map(c => c.id)].map(id => [id, { title: id, fields: {}, dates: {} }])),
  };
}

test('return links target the actual indexed root and section row across pagination boundaries', () => {
  const navigation = buildNavigation(fixture());
  const contexts = navigation.memberships.get('developments/25');
  assert.equal(contexts.length, 2);
  assert.equal(contexts[1].link,
    'views/editions/sections/entries/issues/issue%2020/page/2/#' + rowId('view.editions.entries', 'developments/25'));
  assert.equal(navigation.roots.get('issues/issue 20')[0].link,
    'views/editions/page/2/#' + rowId('index.editions', 'issues/issue 20'));
  assert.equal(navigation.memberships.get('developments/24')[1].link,
    'issues/issue%2020/#' + rowId('view.editions.entries', 'developments/24'));
  assert.equal(navigation.pages.size, 4);
  assert.ok(navigation.pages.has('views/editions/sections/entries/issues/issue 20/page/2'));
  assert.ok(navigation.pages.has('views/editions/page/2'));
});

test('only emitted view paths and page-one fragments are reserved', t => {
  const navigation = buildNavigation(fixture());
  const publicDir = mkdtempSync(join(tmpdir(), 'lokf-view-assets-'));
  t.after(() => rmSync(publicDir, { recursive: true }));
  const conceptPages = Object.keys(navigation.records).map(id => ({ id }));
  assert.doesNotThrow(() => checkViewRoutes(navigation, [...conceptPages, { id: 'views/spare' }], publicDir));
  assert.throws(() => checkViewRoutes(navigation, [], publicDir), /has no Astro concept page/);
  assert.throws(() => checkViewRoutes(navigation, [{ id: 'views/editions/page/2' }], publicDir), /collides with knowledge/);
  mkdirSync(join(publicDir, 'views/editions'), { recursive: true });
  writeFileSync(join(publicDir, 'views/editions/index.html'), 'owned by the site');
  assert.throws(() => checkViewRoutes(navigation, [], publicDir), /collides with/);
  assert.throws(() => checkConceptFragments(navigation, 'issues/issue 0', [{ slug: 'view.editions.entries' }]), /fragment collision/);
  assert.doesNotThrow(() => checkConceptFragments(navigation, 'issues/issue 0', [
    { slug: rowId('view.editions.entries', 'developments/25') },
  ]));
  assert.equal(buildNavigation({ views: [], records: {} }).pages.size, 0);
});

test('a root page leaves off sections with no rows and frees their fragments', () => {
  const navigation = buildNavigation(fixture());
  const shown = id => navigation.roots.get(id).flatMap(({ view, root }) => filledSections(view, root).map(s => s.id));
  assert.deepEqual(shown('issues/issue 0'), ['entries']);
  assert.deepEqual(shown('issues/issue 1'), []);
  assert.doesNotThrow(() => checkConceptFragments(navigation, 'issues/issue 1', [{ slug: 'view.editions.entries' }]));
});

test('empty collections still have a destination and generate no return links', () => {
  const plan = fixture();
  plan.views[0].roots = [];
  const navigation = buildNavigation(plan);
  assert.deepEqual([...navigation.pages.keys()], ['views/editions']);
  assert.equal(navigation.memberships.size, 0);
});

test('family pages keep descendants with each family and target their first appearance', () => {
  const ids = Array.from({ length: 21 }, (_, i) => `family/${i}`);
  const shared = 'assays/shared';
  const last = 'assays/last';
  const roots = [shared, last, ...ids].map(id => ({ id, sections: { stages: [] } }));
  roots[0].sections.stages = [{ id: 'stages/raw' }];
  const families = ids.map(id => ({ id, members: [] }));
  families[0].members = [shared];
  families[1].members = [shared];
  families[20].members = [last, shared];
  const view = {
    id: 'families', title: 'Data families', index: { layout: 'list', family_by: { out: 'isPartOf' } },
    roots, families, sections: [{ id: 'stages', title: 'Stages', display: { layout: 'list' } }],
  };
  const records = Object.fromEntries(roots.map(root => [root.id, { title: root.id }]));
  const nav = buildNavigation({ views: [view], records });
  const first = nav.pages.get('views/families').families;
  const second = nav.pages.get('views/families/page/2').families;
  assert.equal(nav.pages.size, 2);
  assert.equal(first.length, 20);
  assert.equal(second.length, 1);
  assert.equal(first[0].root.id, ids[0]);
  assert.deepEqual(first[0].members.map(member => member.id), [shared]);
  assert.deepEqual(first[0].repeated, []);
  assert.deepEqual(first[1].repeated, [shared]);
  assert.deepEqual(first[2].members, []);
  assert.deepEqual(second[0].members.map(member => member.id), [last, shared]);
  assert.deepEqual(second[0].repeated, [shared]);
  assert.equal(nav.roots.get(shared)[0].link, 'views/families/#' + rowId('index.families', shared));
  assert.equal(nav.roots.get(last)[0].link, 'views/families/page/2/#' + rowId('index.families', last));
  assert.equal(nav.roots.get(ids[20])[0].link, 'views/families/page/2/#' + rowId('index.families', ids[20]));
  assert.equal(nav.memberships.get('stages/raw')[0].link, shared + '/#' + rowId('view.families.stages', 'stages/raw'));
});
