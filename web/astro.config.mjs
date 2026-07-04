// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import mermaid from "astro-mermaid";

// Served at its own subdomain (no base path).
export default defineConfig({
  site: "https://lokf.nolan-nichols.com",
  integrations: [
    // Renders ```mermaid fences client-side, synced to the Starlight theme.
    // Must precede starlight() so it can hook Expressive Code.
    mermaid({ theme: "neutral", autoTheme: true }),
    starlight({
      title: "LOKF",
      description:
        "Linked Open Knowledge Format — write OKF markdown, get a queryable knowledge graph.",
      social: [
        { icon: "github", label: "GitHub", href: "https://github.com/nicholsn/lokf" },
      ],
      editLink: { baseUrl: "https://github.com/nicholsn/lokf/edit/main/web/" },
      customCss: ["./src/styles/theme.css"],
      components: { Head: "./src/components/Head.astro" },
      sidebar: [
        { label: "Home", slug: "index" },
        { label: "Getting started", slug: "getting-started" },
        {
          label: "Guide",
          items: [{ autogenerate: { directory: "guide" } }],
        },
        { label: "Knowledge graph", slug: "graph" },
        { label: "Example bundle", slug: "examples" },
        { label: "Specification", slug: "specification" },
        {
          label: "Toolkit",
          items: [{ autogenerate: { directory: "toolkit" } }],
        },
        {
          label: "Reference",
          items: [{ autogenerate: { directory: "reference" } }],
        },
        { label: "Contributing", slug: "contributing" },
      ],
    }),
  ],
});
