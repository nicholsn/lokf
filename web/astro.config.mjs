// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

// The project site lives under /lokf on the custom domain.
export default defineConfig({
  site: "https://www.nolan-nichols.com",
  base: "/lokf",
  integrations: [
    starlight({
      title: "LOKF",
      description:
        "Linked Open Knowledge Format — write OKF markdown, get a queryable knowledge graph.",
      social: [
        { icon: "github", label: "GitHub", href: "https://github.com/nicholsn/lokf" },
      ],
      editLink: { baseUrl: "https://github.com/nicholsn/lokf/edit/main/web/" },
      customCss: ["./src/styles/theme.css"],
      sidebar: [
        { label: "Home", slug: "index" },
        {
          label: "Guide",
          items: [{ autogenerate: { directory: "guide" } }],
        },
        { label: "Knowledge graph", slug: "graph" },
      ],
    }),
  ],
});
