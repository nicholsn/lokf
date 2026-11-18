/** Portable, static full-text search over the generated site's concepts. */

export function terms(value) {
  return String(value ?? '')
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .match(/[\p{L}\p{N}]+/gu) ?? [];
}

export function searchableText(markdown) {
  return String(markdown ?? '')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/<[^>]*>/g, ' ')
    .replace(/[`*_>#|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function buildIndex(documents) {
  const postings = Object.create(null);
  documents.forEach((doc, id) => {
    const fields = [
      [doc.title, 8],
      [doc.tags.join(' '), 5],
      [doc.description, 3],
      [doc.text, 1],
    ];
    for (const [value, weight] of fields) {
      for (const word of new Set(terms(value))) {
        const matches = postings[word] ||= Object.create(null);
        matches[id] = (matches[id] || 0) + weight;
      }
    }
  });
  return { documents, postings };
}

const sortedWords = new WeakMap();
function prefixWords(postings, prefix) {
  let words = sortedWords.get(postings);
  if (!words) {
    words = Object.keys(postings).sort();
    sortedWords.set(postings, words);
  }
  let lo = 0, hi = words.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (words[mid] < prefix) lo = mid + 1;
    else hi = mid;
  }
  const found = [];
  for (let i = lo; i < words.length && words[i].startsWith(prefix); i++) {
    if (words[i] !== prefix) found.push(words[i]);
  }
  return found;
}

/** All query words must match; the final word also matches word prefixes. */
export function searchIndex(index, query, filters = {}) {
  const queryTerms = [...new Set(terms(query))].slice(0, 12);
  let scores;
  queryTerms.forEach((word, position) => {
    const matches = new Map();
    const add = (posting, multiplier) => {
      for (const [id, score] of Object.entries(posting ?? {})) {
        const number = Number(id);
        matches.set(number, Math.max(matches.get(number) ?? 0, Number(score) * multiplier));
      }
    };
    add(index.postings[word], 2);
    if (position === queryTerms.length - 1 && word.length >= 2) {
      for (const longer of prefixWords(index.postings, word)) add(index.postings[longer], 1);
    }
    scores = scores === undefined
      ? matches
      : new Map([...scores].filter(([id]) => matches.has(id))
          .map(([id, score]) => [id, score + matches.get(id)]));
  });
  const ids = scores ? [...scores.keys()] : index.documents.map((_, id) => id);
  return ids.filter(id => {
    const doc = index.documents[id];
    return (!filters.type || doc.type === filters.type)
      && (!filters.tag || doc.tags.includes(filters.tag))
      && (!filters.status || doc.status === filters.status)
      && (!filters.genre || doc.genre === filters.genre)
      && (!filters.trust || doc.trust_tier === filters.trust)
      && (!filters.freshness || (filters.freshness === 'stale' ? doc.stale : !doc.stale))
      && (!filters.from || doc.date && doc.date >= filters.from)
      && (!filters.to || doc.date && doc.date <= filters.to);
  }).sort((a, b) => {
    const x = index.documents[a], y = index.documents[b];
    const relevance = filters.sort === 'newest' ? 0 : (scores?.get(b) ?? 0) - (scores?.get(a) ?? 0);
    return relevance || y.date.localeCompare(x.date) || x.title.localeCompare(y.title) || x.href.localeCompare(y.href);
  });
}

/** A plain-text excerpt centered on the first visible query hit. */
export function snippetFor(doc, query, length = 250) {
  const value = [doc.description, doc.text].filter(Boolean).join(' ').trim();
  if (!value) return '';
  const queryTerms = [...new Set(terms(query))];
  const last = queryTerms.at(-1);
  let hit = 0;
  if (queryTerms.length) {
    for (const match of value.matchAll(/[\p{L}\p{N}]+/gu)) {
      const word = terms(match[0])[0];
      if (queryTerms.includes(word) || (last?.length >= 2 && word.startsWith(last))) {
        hit = match.index ?? 0;
        break;
      }
    }
  }
  const start = Math.max(0, hit - 70);
  const end = Math.min(value.length, start + length);
  return `${start ? '…' : ''}${value.slice(start, end)}${end < value.length ? '…' : ''}`;
}
