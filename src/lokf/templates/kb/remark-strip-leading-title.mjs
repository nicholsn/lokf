/**
 * Concept bodies often open with a `# Title` (and sometimes an `*italic
 * subtitle*`) that duplicates the page heading the layout already renders from
 * frontmatter. Strip that leading title — and a following emphasis-only
 * paragraph — so the body is just prose.
 */
export default function remarkStripLeadingTitle() {
  return (tree) => {
    const c = tree.children;
    if (c.length && c[0].type === 'heading' && c[0].depth === 1) {
      c.shift();
      if (
        c.length &&
        c[0].type === 'paragraph' &&
        c[0].children.length === 1 &&
        c[0].children[0].type === 'emphasis'
      ) {
        c.shift();
      }
    }
  };
}
