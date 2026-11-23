import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

export default defineConfig({
  site: "https://hieuminhvo250221-del.github.io",
  base: "/triad-bisr",
  output: "static",
  integrations: [mdx()],
});
