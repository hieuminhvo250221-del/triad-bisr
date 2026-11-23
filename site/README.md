# TRIAD-BISR project site

Astro static site published to GitHub Pages at `https://hieuminhvo250221-del.github.io/triad-bisr/`.
English lives at `/`, Vietnamese at `/vi/`. All numbers on the page are generated from `../results/`
by `../tools/site_data.py` — nothing measured is typed into the markup.

## Commands (run from `site/`)

```
npm run data      # regenerate src/data/generated/*.json from ../results/
npm run dev       # local preview at http://localhost:4321/triad-bisr/
npm run build     # data + astro check + static build to dist/
npm run check     # astro check only
npm run screens   # Playwright screenshots into .screens/ (needs `npm run dev` or preview running)
python ../tools/site_data.py --check   # print the extracted try15 values for eyeballing
```

## Updating after a new OpenLane run

1. Export the run: `bash flow/openlane/export.sh <tag>` in WSL, then `bash tools/sync_results.sh`.
2. Edit `results/asic/CURRENT` to the new tag.
3. `npm run data && npm run build` — the page picks up every number automatically.

## Adding / editing a section

- English: `src/content/sections/en/NN-slug.mdx`; Vietnamese: `src/content/sections/vi/NN-slug.mdx`.
- Frontmatter: `title`, `kicker` (mono label), `order` (controls sort order; the displayed
  section number is the sorted position 01…N), `id` (anchor — must be identical in both
  languages; the build fails if one language lacks an id).
- The hero comes from `src/content/hero/{en,vi}.mdx` (frontmatter `title`, `tagline`,
  `heading`, `figureCaption`; the body is the lede). Hand-written bilingual tables and the
  command list live in `src/content/tables/static.yaml`.
- Components available in MDX (passed via the `components` prop — no imports needed):
  `<Num k="asic.<key>" digits={n} unit="…"/>` (locale-aware numbers), `<StatRow>`/`<Stat>`,
  `<Status level="ok|warn|pend"/>` (shown as pass/open/pending), `<Figure>`, `<Note>`,
  `<Chart id="repair-rate"/>`, `<DataTable id="…"/>` with ids `specs`, `prior-art`,
  `modules`, `theorems`, `gates`, `signoff`, `timing`, `n90`, `automb`, `fit`,
  `fit-constants`, `ppa-breakdown`, `ppa-sweep`, `physical`, `<ArchDiagram/>`,
  `<RepairStepper/>` (driven by `generated/traces.json` from `tools/site_traces.py`),
  `<Chip3D/>` (on-demand Three.js viewer; payloads in `public/chip3d/<tag>/` from
  `tools/site_chip3d.py` + `results/chip3d/<tag>/`), `<LargeMemory/>`,
  `<Commands/>` (renders `static.yaml: commands`).

## Adding a number

Put the source under `results/`, extend `tools/site_data.py` to emit it into a generated JSON key,
then reference it with `<Num k="file.key"/>` or in a component via `lib/data.ts:get()`. A missing key
fails the build — there is no silent blank.

## Deploy

`.github/workflows/pages.yml` builds and deploys on pushes to `main` that touch `site/**`,
`results/**`, or `tools/site_data.py`.
