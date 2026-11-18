/** Colors for concept types in the graph explorer. */

/** The core LOKF types keep these colors from graph to graph. */
export const TYPE_COLORS = {
  Person: '#c96f3b', Organization: '#5b8def', Role: '#2ea77d',
  Document: '#9b6dd6', Reference: '#d2a53a', Dataset: '#4bacc6',
  Table: '#3f8f96', Metric: '#c1558b', Service: '#7f8c4f',
  GlossaryTerm: '#d2a53a', Playbook: '#d05b5b',
};

/** Colors for other types, such as a domain vocabulary's, in this order. */
export const PALETTE = [
  '#5b8def', '#2ea77d', '#c1558b', '#9b6dd6', '#d2a53a', '#4bacc6', '#d05b5b',
  '#c96f3b', '#7f8c4f', '#8a6fb0', '#3f8f96', '#b8862a',
];

/**
 * A distinct color for each of `types`, so no two types in one graph share
 * one: a core type keeps its own color, every other type takes the next
 * palette color not yet in use, and past the palette, hues spaced by the
 * golden angle.
 */
export function typeColors(types) {
  const colorOf = {};
  const used = new Set();
  for (const type of types) {
    const color = TYPE_COLORS[type];
    if (color && !used.has(color)) { colorOf[type] = color; used.add(color); }
  }
  const spare = PALETTE.filter((color) => !used.has(color));
  let extra = 0;
  for (const type of types) {
    if (colorOf[type]) continue;
    colorOf[type] = spare.shift() ?? `hsl(${Math.round((extra++ * 137.508) % 360)}, 55%, 52%)`;
  }
  return colorOf;
}
