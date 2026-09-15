import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";
import starlightThemeVintage from "starlight-theme-vintage";

export default defineConfig({
  site: "https://robertagterhuis.github.io",
  base: "/speckit-azure-interview",
  srcDir: "./site-docs",
  integrations: [
    starlight({
        disable404Route: true,
      title: "Spec Kit Azure Interview",
      description:
        "Guided Azure architecture discovery, intended-design review, and verification.",
      plugins: [starlightThemeVintage()],

      social: [
        {
          icon: "github",
          label: "GitHub",
          href:
            "https://github.com/RobertAgterhuis/" +
            "speckit-azure-interview",
        },
      ],
      editLink: {
        baseUrl:
          "https://github.com/RobertAgterhuis/" +
          "speckit-azure-interview/edit/main/site-docs/content/docs/",
      },
      sidebar: [
        {
          label: "Start Here",
          items: [
            {
              label: "Overview",
              slug: "index",
            },
            {
              label: "Getting Started",
              slug: "getting-started",
            },
            {
              label: "Complete Workflow",
              slug: "workflow",
            },
          ],
        },
        {
          label: "Commands",
          items: [
            {
              autogenerate: {
                directory: "commands",
              },
            },
          ],
        },
        {
          label: "Artifacts",
          items: [
            {
              autogenerate: {
                directory: "artifacts",
              },
            },
          ],
        },
        {
          label: "Integrations",
          items: [
            {
              autogenerate: {
                directory: "integrations",
              },
            },
          ],
        },
        {
          label: "Development",
          items: [
            {
              autogenerate: {
                directory: "development",
              },
            },
          ],
        },
      ],
    }),
  ],
});