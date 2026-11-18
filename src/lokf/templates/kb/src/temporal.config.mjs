/**
 * Optional temporal view. Keep only fields and relations that have the same
 * meaning in your bundle. The builder chooses the date/relation pair covering
 * the most linked concepts; it never mixes date meanings in one timeline.
 *
 * A date path may be a top-level frontmatter field or a dotted path such as
 * `generated.at`. A relation matches either a graph edge's slot or predicate.
 * `recordRole: 'source'` means the dated concept points to its group;
 * `recordRole: 'target'` means the group points to the dated concept.
 */
export const temporalConfig = {
  dateFields: [
    { path: 'created', label: 'Concept creation date' },
    { path: 'generated.at', label: 'Content generation date' },
    { path: 'timestamp', label: 'Last meaningful change date' },
  ],
  groupRelations: [
    { relation: 'about', recordRole: 'source', label: 'About' },
    { relation: 'isPartOf', recordRole: 'source', label: 'Part of' },
    { relation: 'hasPart', recordRole: 'target', label: 'Has part' },
  ],
  // Empty lists include every concept type. Specify types to narrow a domain.
  recordTypes: [],
  groupTypes: [],
  minimumRecords: 2,
};
