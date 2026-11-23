import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const sections = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/sections" }),
  schema: z.object({
    title: z.string(),
    kicker: z.string(),
    order: z.number(),
    id: z.string(),
  }),
});

const hero = defineCollection({
  loader: glob({ pattern: "*.mdx", base: "./src/content/hero" }),
  schema: z.object({
    title: z.string(),
    tagline: z.string(),
    heading: z.string(),
    figureCaption: z.string(),
  }),
});

export const collections = { sections, hero };
