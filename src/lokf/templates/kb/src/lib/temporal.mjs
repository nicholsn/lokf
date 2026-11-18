/** Build a timeline from dated concepts and one asserted grouping relation. */

function fieldAt(data, path) {
  return path.split('.').reduce((value, key) => value && typeof value === 'object' ? value[key] : undefined, data);
}

export function calendarDate(value) {
  if (value instanceof Date && !Number.isFinite(value.getTime())) return '';
  const text = value instanceof Date ? value.toISOString() : String(value ?? '');
  const match = /^(\d{4}-\d{2}-\d{2})(?:$|T)/.exec(text);
  if (!match || !Number.isFinite(Date.parse(text))) return '';
  const day = match[1];
  const parsedDay = new Date(`${day}T00:00:00Z`);
  return Number.isFinite(parsedDay.getTime()) && parsedDay.toISOString().slice(0, 10) === day ? day : '';
}

const byDate = (a, b) => b.date.localeCompare(a.date) || a.title.localeCompare(b.title) || a.id.localeCompare(b.id);

/**
 * `documents` hold {id, title, type, href, data}; `graph` is the canonical
 * toolkit export. Returns null unless a single date/relation pair has enough
 * linked, dated concepts to make a useful view.
 */
export function buildTemporalEvidence(documents, graph, config) {
  const docs = new Map(documents.map(doc => [doc.id, doc]));
  const nodeIds = new Map((graph.nodes ?? []).map(node => [String(node.data.id), String(node.data.concept_id)]));
  const permitted = (type, types) => !types?.length || types.includes(type);
  const minimum = Number.isInteger(config.minimumRecords) && config.minimumRecords > 0 ? config.minimumRecords : 2;
  let best = null;

  for (const dateField of config.dateFields ?? []) {
    if (!dateField.path || !dateField.label) continue;
    const dates = new Map(documents.filter(doc => permitted(doc.type, config.recordTypes))
      .map(doc => [doc.id, calendarDate(fieldAt(doc.data, dateField.path))])
      .filter(([, date]) => date));
    if (dates.size < minimum) continue;

    for (const grouping of config.groupRelations ?? []) {
      if (!grouping.relation || !grouping.label || !['source', 'target'].includes(grouping.recordRole)) continue;
      const recordGroups = new Map();
      for (const edge of graph.edges ?? []) {
        const data = edge.data ?? {};
        if (data.slot !== grouping.relation && data.predicate !== grouping.relation) continue;
        const source = nodeIds.get(String(data.source));
        const target = nodeIds.get(String(data.target));
        const recordId = grouping.recordRole === 'source' ? source : target;
        const groupId = grouping.recordRole === 'source' ? target : source;
        if (!recordId || !groupId || recordId === groupId || !dates.has(recordId)) continue;
        const group = docs.get(groupId);
        if (!group || !permitted(group.type, config.groupTypes)) continue;
        if (!recordGroups.has(recordId)) recordGroups.set(recordId, new Set());
        recordGroups.get(recordId).add(groupId);
      }
      if (recordGroups.size >= minimum && (!best || recordGroups.size > best.recordGroups.size)) {
        best = { dateField, grouping, recordGroups, dates };
      }
    }
  }
  if (!best) return null;

  const records = [...best.recordGroups].map(([id, groupIds]) => {
    const doc = docs.get(id);
    const groups = [...groupIds].map(groupId => {
      const group = docs.get(groupId);
      return { id: groupId, title: group.title, href: group.href, type: group.type };
    }).sort((a, b) => a.title.localeCompare(b.title) || a.id.localeCompare(b.id));
    return { id, title: doc.title, href: doc.href, type: doc.type, date: best.dates.get(id), groups };
  }).sort(byDate);

  const periodMap = new Map();
  const groupMap = new Map();
  for (const record of records) {
    const period = record.date.slice(0, 7);
    if (!periodMap.has(period)) periodMap.set(period, []);
    periodMap.get(period).push(record);
    for (const group of record.groups) {
      if (!groupMap.has(group.id)) groupMap.set(group.id, { ...group, records: [] });
      groupMap.get(group.id).records.push(record);
    }
  }
  const periods = [...periodMap].sort(([a], [b]) => b.localeCompare(a))
    .map(([key, items]) => ({
      key,
      label: new Intl.DateTimeFormat('en', { month: 'long', year: 'numeric', timeZone: 'UTC' })
        .format(new Date(`${key}-01T00:00:00Z`)),
      records: items,
    }));
  const groups = [...groupMap.values()].sort((a, b) =>
    b.records.length - a.records.length || a.title.localeCompare(b.title) || a.id.localeCompare(b.id));

  return {
    dateField: best.dateField,
    grouping: best.grouping,
    records,
    periods,
    groups,
  };
}
