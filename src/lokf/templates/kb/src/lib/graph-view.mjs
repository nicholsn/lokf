export const LAYOUTS = {
  fcose: { label: 'Connected neighborhoods', description: 'Force placement that keeps connected concepts near one another.' },
  communities: { label: 'Community clusters', description: 'Groups densely connected concepts in this view. These are inferred groups, not established categories.' },
  types: { label: 'Group by concept type', description: 'Groups concepts by their stored types.' },
  cose: { label: 'Spread connections', description: 'Spreads visible concepts using a classic force layout.' },
  radial: { label: 'Connection hubs', description: 'Places concepts with more visible connections nearer the center. Counts describe this view, not global importance.' },
};
export const validLayout = (value) => Object.hasOwn(LAYOUTS, value) ? value : 'fcose';

export function readView(params) {
  const page = Number(params.get('page') || 1);
  return {
    focus: params.get('focus') || '',
    page: Number.isSafeInteger(page) && page > 0 ? page : 1,
    layout: validLayout(params.get('layout')),
    view: params.get('view') === 'list' ? 'list' : 'graph',
    query: params.get('q') || '',
    selected: params.get('node') || '',
    hiddenTypes: (params.get('hideTypes') || '').split(',').filter(Boolean),
    hiddenRelations: (params.get('hideRelations') || '').split(',').filter(Boolean),
    labels: params.get('labels') === '1',
  };
}

export function writeView(url, state) {
  const values = {
    focus: state.focus || '', page: state.page > 1 ? String(state.page) : '',
    layout: state.layout !== 'fcose' ? validLayout(state.layout) : '',
    view: state.view === 'list' ? 'list' : '', q: state.query || '',
    node: state.selected || '',
    hideTypes: [...(state.hiddenTypes || [])].sort().join(','),
    hideRelations: [...(state.hiddenRelations || [])].sort().join(','),
    labels: state.labels ? '1' : '',
  };
  for (const [key, value] of Object.entries(values)) {
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  }
  return url;
}
