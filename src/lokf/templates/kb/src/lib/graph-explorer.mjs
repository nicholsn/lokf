import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
import { graphIndex, MAX_NODES, rankChoices } from './graph-scope.mjs';
import { typeColors } from './graph-colors.mjs';
import { LAYOUTS, readView, writeView, validLayout } from './graph-view.mjs';
import { prepareLayout } from './graph-layouts.mjs';
import { findPath } from './graph-path.mjs';

cytoscape.use(fcose);

const SHAPES = ['ellipse', 'round-rectangle', 'diamond', 'hexagon', 'triangle', 'star'];
const value = (item) => String(item ?? '');
const label = (data) => value(data.label || data.concept_id || data.id);
const typeTitle = (data) => value(data.type_title || data.type) || 'Concept';
const connections = (count) => `${count} connection${count === 1 ? '' : 's'}`;
const query = (root, selector) => root.querySelector(selector);
const all = (root, selector) => [...root.querySelectorAll(selector)];
const setText = (root, selector, text) => { query(root, selector).textContent = text; };
const colorVar = (root, name, fallback) => getComputedStyle(root).getPropertyValue(name).trim() || fallback;
const add = (parent, tag, text, className = '') => {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  parent.append(element);
  return element;
};

function pageHref(data, sourceBase) {
  const input = data.href || (sourceBase && data.concept_id ? `${sourceBase.replace(/\/$/, '')}/${data.concept_id}.md` : '');
  if (!input) return '';
  try {
    const url = new URL(input, location.href);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
  } catch { return ''; }
}

export function startGraphExplorer(root) {
  if (root.dataset.ready) return;
  root.dataset.ready = '1';
  const mount = query(root, '.lokf-graph__canvas');
  const chooser = query(root, '.lokf-graph__concept');
  const choices = query(root, '.lokf-graph__choices');
  const search = query(root, '.lokf-graph__search');
  const status = query(root, '.lokf-graph__status');
  const pagination = query(root, '.lokf-graph__pagination');
  const previous = query(root, '[data-action="previous"]');
  const next = query(root, '[data-action="next"]');
  const layoutSelect = query(root, '.lokf-graph__layout');
  const layoutButton = query(root, '[data-action="layouts"]');
  const layoutPanel = query(root, '.lokf-graph__layout-panel');
  const edgeLabels = query(root, '[data-action="edge-labels"]');
  const detail = query(root, '.lokf-graph__detail');
  const list = query(root, '.lokf-graph__list');
  const listItems = query(list, 'ul');
  const groupBrowser = query(root, '.lokf-graph__group-browser');
  const groupsEl = query(root, '.lokf-graph__groups');
  const pathFrom = query(root, '[data-path="from"]');
  const pathTo = query(root, '[data-path="to"]');
  const pathResult = query(root, '.lokf-graph__path-result');
  const communityExclude = new Set((root.dataset.communityExclude || '').split(',').filter(Boolean));
  let state = readView(new URLSearchParams(location.search));
  let index;
  let whole;
  let graph;
  let cy;
  let request;
  let layoutFrame = 0;
  let sourceBase = root.dataset.sourceBase || '';

  function syncUrl(push = false) {
    const url = writeView(new URL(location.href), state);
    if (url.href !== location.href) history[push ? 'pushState' : 'replaceState']({}, '', url);
    return url.href;
  }

  function setView(view, save = true) {
    state.view = view === 'list' ? 'list' : 'graph';
    root.dataset.view = state.view;
    list.hidden = state.view !== 'list';
    all(root, '[data-view]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.view === state.view)));
    if (state.view === 'graph' && cy) requestAnimationFrame(() => { cy.resize(); cy.fit(cy.nodes('.concept').not('.hidden'), 45); });
    if (save) syncUrl();
  }

  function showChoices() {
    choices.replaceChildren();
    const term = chooser.value.trim().toLowerCase();
    if (!term || !index) { choices.hidden = true; chooser.setAttribute('aria-expanded', 'false'); return; }
    const found = rankChoices(index.nodes, term);
    for (const node of found) {
      const option = add(choices, 'button', label(node));
      option.type = 'button';
      option.setAttribute('role', 'option');
      add(option, 'small', `${node.type_title || node.type || 'Concept'} · ${node.concept_id}`);
      option.addEventListener('click', () => chooseConcept(node.concept_id));
    }
    if (!found.length) add(choices, 'p', 'No matching concepts in this knowledge base.');
    choices.hidden = false;
    chooser.setAttribute('aria-expanded', 'true');
  }

  function chooseConcept(id) {
    chooser.value = index.nodes.find((node) => node.concept_id === id)?.label || id;
    choices.hidden = true;
    chooser.setAttribute('aria-expanded', 'false');
    state.focus = id;
    state.page = 1;
    state.selected = id;
    if (index.count > MAX_NODES && root.dataset.dataBase) loadGraph(true);
    else { selectNode(id, true); syncUrl(true); }
  }

  async function fetchJson(url, signal) {
    const response = await fetch(url, { signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async function loadGraph(push = false) {
    request?.abort();
    const controller = new AbortController();
    request = controller;
    root.dataset.state = 'loading';
    status.textContent = 'Loading graph…';
    previous.disabled = next.disabled = true;
    try {
      const scoped = index.count > MAX_NODES && root.dataset.dataBase;
      if (scoped) {
        const requested = index.nodes.some((node) => node.concept_id === state.focus) ? state.focus : index.default_focus;
        if (requested !== state.focus) { state.focus = requested; state.page = 1; }
        const path = requested.split('/').map(encodeURIComponent).join('/');
        try {
          graph = await fetchJson(`${root.dataset.dataBase}${path}/${state.page}.json`, controller.signal);
        } catch (error) {
          if (state.page === 1 || controller.signal.aborted) throw error;
          // A shared page link may outlive a changed neighborhood.
          state.page = 1;
          graph = await fetchJson(`${root.dataset.dataBase}${path}/1.json`, controller.signal);
        }
      } else {
        graph = whole || await fetchJson(root.dataset.graphSrc, controller.signal);
        whole = graph;
      }
      if (controller.signal.aborted) return;
      sourceBase ||= value(graph.meta?.source_base);
      render();
      root.dataset.state = 'ready';
      const scope = graph.scope;
      pagination.hidden = !scope;
      if (scope) {
        status.textContent = `${scope.title} · ${scope.start}–${scope.end} of ${scope.total} direct connections · ${graph.nodes.length} concepts${scope.pages > 1 ? ` · Page ${scope.page} of ${scope.pages}` : ''}${scope.context_omitted ? ` · ${scope.context_omitted} context concepts omitted` : ''}`;
        previous.disabled = scope.page <= 1;
        next.disabled = scope.page >= scope.pages;
      } else status.textContent = `${graph.nodes.length} concepts and ${graph.edges.length} relations`;
      syncUrl(push);
    } catch (error) {
      if (controller.signal.aborted) return;
      root.dataset.state = 'error';
      mount.textContent = `Could not load graph: ${error instanceof Error ? error.message : error}`;
      status.textContent = 'Could not load graph. Choose another concept or reload the page.';
      pagination.hidden = false;
    }
  }

  function filterOptions() {
    const types = [...new Set(graph.nodes.map((node) => value(node.data.type)))].sort();
    const predicates = [...new Set(graph.edges.map((edge) => value(edge.data.predicate)))].sort();
    const colorOf = typeColors(types);
    const titles = new Map([
      ...graph.nodes.map((node) => [value(node.data.type), typeTitle(node.data)]),
      ...graph.edges.map((edge) => [value(edge.data.predicate), value(edge.data.title) || value(edge.data.predicate)]),
    ]);
    const shapeOf = Object.fromEntries(types.map((type, i) => [type, SHAPES[i % SHAPES.length]]));
    const create = (selector, values, hidden) => {
      const container = query(root, `${selector} .lokf-graph__filter-items`);
      container.replaceChildren();
      for (const item of values) {
        const line = add(container, 'label', '');
        const input = document.createElement('input');
        input.type = 'checkbox'; input.value = item; input.checked = !hidden.includes(item);
        line.append(input);
        if (selector.includes('type')) {
          const swatch = add(line, 'span', '', 'lokf-graph__swatch');
          swatch.style.background = colorOf[item];
        }
        line.append(document.createTextNode(titles.get(item) || item || '(unspecified)'));
        if (titles.get(item) && titles.get(item) !== item) line.title = item;
        input.addEventListener('change', () => applyFilters());
      }
    };
    create('[data-filter="type"]', types, state.hiddenTypes);
    create('[data-filter="predicate"]', predicates, state.hiddenRelations);
    return { colorOf, shapeOf };
  }

  function checked(selector) {
    return new Set(all(root, `${selector} input:checked`).map((input) => input.value));
  }

  function applyFilters(save = true) {
    if (!cy) return;
    const types = checked('[data-filter="type"]');
    const relations = checked('[data-filter="predicate"]');
    state.hiddenTypes = all(root, '[data-filter="type"] input:not(:checked)').map((input) => input.value);
    state.hiddenRelations = all(root, '[data-filter="predicate"] input:not(:checked)').map((input) => input.value);
    cy.batch(() => {
      cy.nodes('.concept').forEach((node) => node.toggleClass('hidden', !types.has(value(node.data('type')))));
      cy.edges().forEach((edge) => edge.toggleClass('hidden', !relations.has(value(edge.data('predicate'))) || edge.source().hasClass('hidden') || edge.target().hasClass('hidden')));
    });
    if (state.selected && !cy.nodes('.concept').not('.hidden').filter((node) => node.data('concept_id') === state.selected).length) {
      state.selected = '';
      detail.hidden = true;
      cy.nodes('.concept').unselect();
    }
    updateSearch();
    updatePathOptions();
    pathResult.replaceChildren();
    runLayout();
    if (save) syncUrl();
  }

  function updateSearch() {
    if (!cy) return;
    state.query = search.value;
    const term = search.value.trim().toLowerCase();
    const visible = cy.nodes('.concept').not('.hidden');
    const matches = visible.filter((node) => `${label(node.data())} ${value(node.data('concept_id'))}`.toLowerCase().includes(term));
    visible.forEach((node) => node.toggleClass('dim', !!term && !matches.contains(node)));
    setText(root, '.lokf-graph__matches', term ? `${matches.length} matching concepts in this view` : `${visible.length} visible concepts in this view`);
    renderList();
  }

  function renderList() {
    if (!cy) return;
    listItems.replaceChildren();
    const term = search.value.trim().toLowerCase();
    const nodes = cy.nodes('.concept').not('.hidden').filter((node) => !term || `${label(node.data())} ${value(node.data('concept_id'))}`.toLowerCase().includes(term))
      .sort((a, b) => label(a.data()).localeCompare(label(b.data())));
    for (const node of nodes) {
      const item = add(listItems, 'li', '');
      const button = add(item, 'button', label(node.data()));
      button.type = 'button';
      add(button, 'small', `${typeTitle(node.data())} · ${connections(node.connectedEdges().not('.hidden').length)}`);
      button.addEventListener('click', () => selectNode(node.data('concept_id'), true));
    }
    if (!nodes.length) add(listItems, 'li', 'No concepts match the current filters.');
  }

  function updatePathOptions() {
    if (!cy) return;
    const visible = cy.nodes('.concept').not('.hidden').sort((a, b) => label(a.data()).localeCompare(label(b.data())));
    for (const select of [pathFrom, pathTo]) {
      const old = select.value;
      select.replaceChildren();
      for (const node of visible) {
        const option = add(select, 'option', `${label(node.data())} · ${typeTitle(node.data())}`);
        option.value = node.id();
      }
      if (visible.some((node) => node.id() === old)) select.value = old;
      else if (select === pathTo && visible.length > 1) select.value = visible[1].id();
    }
    if (!pathFrom.value && visible.length) pathFrom.value = visible[0].id();
    if (!pathTo.value && visible.length > 1) pathTo.value = visible[1].id();
  }

  function detailField(list, name, content) {
    if (content === undefined || content === null || content === '') return;
    add(list, 'dt', name);
    add(list, 'dd', value(content));
  }

  function selectNode(id, push = false) {
    if (!cy || !id) return;
    const node = cy.nodes('.concept').filter((item) => item.data('concept_id') === id || item.id() === id).first();
    if (!node.length || node.hasClass('hidden')) return;
    state.selected = value(node.data('concept_id'));
    if (pathFrom.options.length) pathFrom.value = node.id();
    cy.nodes('.concept').unselect();
    node.select();
    const data = node.data();
    setText(root, '.lokf-graph__detail-title', label(data));
    setText(root, '.lokf-graph__detail-description', value(data.description));
    const metadata = query(root, '.lokf-graph__detail-meta');
    metadata.replaceChildren();
    detailField(metadata, 'Type', typeTitle(data));
    detailField(metadata, 'Status', data.status);
    detailField(metadata, 'Trust tier', data.trust_tier);
    if (data.stale === true) detailField(metadata, 'Freshness', 'Marked stale');
    detailField(metadata, 'IRI', data.id);
    const relations = query(root, '.lokf-graph__detail-relations');
    relations.replaceChildren();
    const edges = node.connectedEdges().not('.hidden').sort((a, b) => value(a.data('predicate')).localeCompare(value(b.data('predicate'))));
    for (const edge of edges) {
      const outgoing = edge.source().id() === node.id();
      const neighbor = outgoing ? edge.target() : edge.source();
      const rel = outgoing
        ? `→ ${value(edge.data('title')) || value(edge.data('predicate')) || 'related to'}`
        : value(edge.data('incoming_title')) || `← ${value(edge.data('predicate')) || 'related to'}`;
      const reified = edge.data('reified') ? ' · reified' : '';
      const text = `${rel}${reified} · ${label(neighbor.data())}`;
      const item = add(relations, 'li', '');
      const button = add(item, 'button', text);
      button.type = 'button';
      button.addEventListener('click', () => selectNode(neighbor.data('concept_id'), true));
    }
    if (!edges.length) add(relations, 'li', 'No visible connections in this view.');
    const page = query(root, '.lokf-graph__detail-page');
    const href = pageHref(data, sourceBase);
    page.hidden = !href;
    if (href) page.href = href;
    query(root, '[data-action="explore"]').hidden = !root.dataset.dataBase || index.count <= MAX_NODES;
    detail.hidden = false;
    if (state.view === 'graph') cy.animate({ center: { eles: node }, zoom: Math.max(1, Math.min(cy.zoom(), 1.5)), duration: 250 });
    if (push) syncUrl(true);
  }

  function renderGroups() {
    const grouped = ['communities', 'types'].includes(state.layout);
    groupBrowser.hidden = !grouped;
    groupsEl.replaceChildren();
    if (!grouped || !cy) return;
    const groups = cy.nodes('.layout-group');
    for (const parent of groups) {
      const section = add(groupsEl, 'section', '');
      add(section, 'h4', `${parent.data('label')} (${parent.children().length})`);
      const items = add(section, 'ul', '');
      for (const node of parent.children().sort((a, b) => label(a.data()).localeCompare(label(b.data())))) {
        const item = add(items, 'li', '');
        const button = add(item, 'button', label(node.data()));
        button.type = 'button';
        button.addEventListener('click', () => selectNode(node.data('concept_id'), true));
      }
    }
    if (!groups.length) add(groupsEl, 'p', 'No groups in this filtered view.');
  }

  function runLayout() {
    if (!cy) return;
    cancelAnimationFrame(layoutFrame);
    const status = query(root, '.lokf-graph__layout-status');
    status.textContent = 'Arranging visible concepts…';
    layoutFrame = requestAnimationFrame(() => {
      try {
        const prepared = prepareLayout(cy, state.layout, communityExclude);
        prepared.elements.layout(prepared.options).run();
        setText(root, '.lokf-graph__layout-help', prepared.description);
        status.textContent = `${prepared.nodes} concepts arranged${prepared.groups ? ` in ${prepared.groups} groups` : ''}.`;
        renderGroups();
        if (state.selected) selectNode(state.selected);
      } catch (error) {
        status.textContent = `Could not arrange this view: ${error instanceof Error ? error.message : error}`;
      }
    });
  }

  function render() {
    cancelAnimationFrame(layoutFrame);
    cy?.destroy();
    mount.replaceChildren();
    detail.hidden = true;
    const { colorOf, shapeOf } = filterOptions();
    const fg = colorVar(root, '--graph-text', '#253246');
    const line = colorVar(root, '--graph-muted', '#657387');
    const nodes = graph.nodes.map((node) => ({ data: {
      ...node.data, label: label(node.data), color: colorOf[value(node.data.type)], shape: shapeOf[value(node.data.type)],
    }, classes: 'concept' }));
    const edges = graph.edges.map((edge) => ({ data: { ...edge.data } }));
    cy = cytoscape({
      container: mount, elements: { nodes, edges }, minZoom: .2, maxZoom: 3,
      wheelSensitivity: .3, layout: { name: 'preset' },
      style: [
        { selector: 'node.concept', style: { 'background-color': 'data(color)', shape: 'data(shape)', label: 'data(label)', color: fg, 'font-size': 11, 'text-wrap': 'wrap', 'text-max-width': '115px', 'text-valign': 'bottom', 'text-margin-y': 4, width: 27, height: 27 } },
        { selector: 'node.layout-group', style: { 'background-color': line, 'background-opacity': .05, 'border-color': line, 'border-opacity': .32, 'border-width': 1, shape: 'round-rectangle', label: 'data(label)', 'font-size': 13, 'font-weight': 'bold', color: line, 'text-valign': 'top', 'text-margin-y': -12, padding: 30 } },
        { selector: 'edge', style: { 'line-color': line, 'line-opacity': .55, 'target-arrow-color': line, 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', width: 1.5, label: '', 'font-size': 9, color: line, 'text-rotation': 'autorotate' } },
        { selector: 'edge.labels-on', style: { label: (edge) => value(edge.data('title') || edge.data('predicate')) } },
        { selector: 'node:selected', style: { 'border-width': 4, 'border-color': fg } },
        { selector: '.dim', style: { opacity: .15 } },
        { selector: '.hidden', style: { display: 'none' } },
      ],
    });
    cy.on('tap', 'node.concept', (event) => selectNode(event.target.data('concept_id'), true));
    cy.edges().toggleClass('labels-on', state.labels);
    edgeLabels.checked = state.labels;
    search.value = state.query;
    layoutSelect.value = validLayout(state.layout);
    setView(state.view, false);
    applyFilters(false);
    if (state.selected || (state.focus && index.count <= MAX_NODES)) {
      requestAnimationFrame(() => selectNode(state.selected || state.focus));
    }
  }

  chooser.addEventListener('input', showChoices);
  chooser.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') { choices.hidden = true; chooser.setAttribute('aria-expanded', 'false'); }
    if (event.key === 'Enter') { event.preventDefault(); query(choices, 'button')?.click(); }
  });
  document.addEventListener('click', (event) => {
    if (!query(root, '.lokf-graph__chooser').contains(event.target)) { choices.hidden = true; chooser.setAttribute('aria-expanded', 'false'); }
  });
  query(root, '[data-action="show-default"]').addEventListener('click', () => {
    state.focus = index.count > MAX_NODES ? index.default_focus : '';
    state.page = 1; state.selected = '';
    chooser.value = ''; choices.hidden = true;
    if (index.count > MAX_NODES && root.dataset.dataBase) loadGraph(true);
    else { detail.hidden = true; cy?.nodes('.concept').unselect(); cy?.fit(cy.nodes('.concept').not('.hidden'), 45); syncUrl(true); }
  });
  previous.addEventListener('click', () => { state.page = Math.max(1, state.page - 1); state.selected = ''; loadGraph(true); });
  next.addEventListener('click', () => { state.page += 1; state.selected = ''; loadGraph(true); });
  search.addEventListener('input', () => { updateSearch(); syncUrl(); });
  all(root, '[data-view]').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
  query(root, '[data-action="reset-filters"]').addEventListener('click', () => {
    all(root, '.lokf-graph__filter-items input').forEach((input) => { input.checked = true; });
    search.value = ''; applyFilters();
  });
  query(root, '[data-action="find-path"]').addEventListener('click', () => {
    pathResult.replaceChildren();
    if (!graph || !pathFrom.value || !pathTo.value) {
      pathResult.textContent = 'Choose two visible concepts.';
      return;
    }
    const directed = query(root, '[data-path="directed"]').checked;
    const path = findPath(graph, pathFrom.value, pathTo.value, { ...state, directed });
    if (!path) {
      pathResult.textContent = 'No path found with the current scope and filters. Try a different concept or show more relation types.';
      return;
    }
    if (!path.steps.length) { pathResult.textContent = 'These are the same concept.'; return; }
    add(pathResult, 'p', `${path.steps.length} relation${path.steps.length === 1 ? '' : 's'} in the shortest path through this view:`);
    const steps = add(pathResult, 'ol', '');
    for (const step of path.steps) {
      const relation = value(step.edge.data.title) || value(step.edge.data.predicate) || 'related to';
      const text = `${label(step.from.data)} ${step.forward ? '→' : '←'} ${relation}${step.edge.data.reified ? ' [reified]' : ''} ${step.forward ? '→' : '←'} ${label(step.to.data)}`;
      add(steps, 'li', text);
    }
  });
  query(root, '[data-action="share"]').addEventListener('click', async () => {
    const url = syncUrl();
    const status = query(root, '.lokf-graph__share-status');
    try { await navigator.clipboard.writeText(url); status.textContent = 'Link copied.'; }
    catch { status.textContent = 'Copy unavailable; use the address bar URL.'; }
  });
  layoutButton.addEventListener('click', () => {
    layoutPanel.hidden = !layoutPanel.hidden;
    layoutButton.setAttribute('aria-expanded', String(!layoutPanel.hidden));
    if (!layoutPanel.hidden) layoutSelect.focus();
  });
  layoutPanel.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') { layoutPanel.hidden = true; layoutButton.setAttribute('aria-expanded', 'false'); layoutButton.focus(); }
  });
  layoutSelect.addEventListener('change', () => { state.layout = validLayout(layoutSelect.value); runLayout(); syncUrl(); });
  edgeLabels.addEventListener('change', () => { state.labels = edgeLabels.checked; cy?.edges().toggleClass('labels-on', state.labels); syncUrl(); });
  query(root, '[data-action="rearrange"]').addEventListener('click', runLayout);
  query(root, '[data-action="fit"]').addEventListener('click', () => cy?.fit(cy.nodes('.concept').not('.hidden'), 45));
  const stage = query(root, '.lokf-graph__stage');
  const fullButton = query(root, '[data-action="fullscreen"]');
  fullButton.addEventListener('click', () => document.fullscreenElement ? document.exitFullscreen() : stage.requestFullscreen?.());
  document.addEventListener('fullscreenchange', () => { fullButton.textContent = document.fullscreenElement === stage ? '⛶ Exit full screen' : '⛶ Full screen'; requestAnimationFrame(() => { cy?.resize(); cy?.fit(cy.nodes('.concept').not('.hidden'), 45); }); });
  query(root, '.lokf-graph__close').addEventListener('click', () => { detail.hidden = true; state.selected = ''; cy?.nodes('.concept').unselect(); syncUrl(); });
  query(root, '[data-action="explore"]').addEventListener('click', () => { if (state.selected) chooseConcept(state.selected); });
  window.addEventListener('popstate', () => {
    state = readView(new URLSearchParams(location.search));
    loadGraph();
  });

  (async () => {
    try {
      if (root.dataset.indexSrc) index = await fetchJson(root.dataset.indexSrc);
      else { whole = await fetchJson(root.dataset.graphSrc); index = graphIndex(whole); }
      if (!index.nodes.length) { mount.textContent = 'This knowledge base has no concepts yet.'; status.textContent = 'No concepts'; return; }
      if (state.focus) chooser.value = index.nodes.find((node) => node.concept_id === state.focus)?.label || state.focus;
      loadGraph();
    } catch (error) {
      mount.textContent = `Could not load graph: ${error instanceof Error ? error.message : error}`;
      status.textContent = 'Could not load graph.';
    }
  })();
}
