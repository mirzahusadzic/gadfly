/** Gadfly's documentation site. The pages are docs/, written to read on
 * GitHub: this file gives each its place in the sidebar, and the Markdown
 * rules make them read on the site as they do there. */
import { createHash } from 'node:crypto';
import { copyFileSync, mkdirSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { createCssVariablesTheme } from 'shiki';
import { defineConfig } from 'vitepress';
import { frameLinks, githubMath, githubSlug, hangingLines, mermaidFences } from './markdown.mjs';
import { writeNotices } from './notices.mjs';
import { HEAD } from './theme/theme.js';

const github = 'https://github.com/mirzahusadzic/gadfly';
// The version the package declares, for the foot of every page.
const version = readFileSync(new URL('../../pyproject.toml', import.meta.url), 'utf8').match(
  /^version = "([^"]+)"/m,
)[1];
const description =
  'A fixed-rule, counterfactual test for premises that must survive a handoff.';

// The sidebar, sorted by who reads it: a first look, the examples (a ladder,
// each step building on the ones before it), guides for writing and reading
// frames, the reference, and the background. A page left out of it is a
// draft, and goes in srcExclude, which keeps it off the site and its search.
const guides = ['write-a-frame', 'interventions', 'reading-a-verdict', 'batteries'];
const reference = ['command-line', 'reference', 'glossary', 'troubleshooting', 'roadmap', 'breadth/'];
const sidebar = [
  { text: 'Home', link: '/' },
  {
    text: 'Start here',
    items: [
      { text: 'In plain words', link: '/in-plain-words' },
      { text: 'Your first frame', link: '/first-frame' },
      { text: 'Framework', link: '/framework' },
    ],
  },
  {
    text: 'Examples',
    items: [
      { text: 'The ladder', link: '/examples/' },
      { text: 'Watch a run', link: '/examples/watch' },
      { text: 'Cooled', link: '/examples/cooled' },
      { text: 'Quorum', link: '/examples/quorum' },
      { text: 'Misaligned', link: '/examples/misaligned' },
      { text: 'Cumulative', link: '/examples/cumulative' },
      { text: 'A frame built wrong', link: '/examples/built-wrong' },
      { text: 'Bypass', link: '/examples/bypass' },
      { text: 'Several inputs', link: '/examples/inputs' },
      { text: 'Grain', link: '/examples/grain' },
      { text: 'Paths', link: '/examples/paths' },
      { text: 'Inversion', link: '/examples/inversion' },
      { text: 'Asked', link: '/examples/asked' },
      { text: 'Each anchor alone', link: '/examples/each-anchor' },
      { text: 'Run your own', link: '/examples/your-own' },
    ],
  },
  {
    text: 'Guides',
    items: [
      { text: 'Write a frame', link: '/write-a-frame' },
      { text: 'Interventions', link: '/interventions' },
      { text: 'Reading a verdict', link: '/reading-a-verdict' },
      { text: 'Batteries', link: '/batteries' },
    ],
  },
  {
    text: 'Reference',
    items: [
      { text: 'Command line', link: '/command-line' },
      { text: 'Python API', link: '/reference' },
      { text: 'Glossary', link: '/glossary' },
      { text: 'Troubleshooting', link: '/troubleshooting' },
      {
        text: 'Extending Gadfly',
        collapsed: true,
        items: [
          { text: 'Overview', link: '/roadmap' },
          { text: 'Placement intervention', link: '/breadth/placement-intervention' },
          { text: 'Local JSON battery', link: '/breadth/local-json-battery' },
          { text: 'Example report', link: '/breadth/report-example' },
        ],
      },
    ],
  },
  {
    text: 'Background',
    items: [
      { text: 'Architecture and limits', link: '/architecture' },
      { text: 'When meaning is load-bearing', link: '/load-bearing' },
      { text: 'Fonts and libraries', link: '/notices' },
    ],
  },
];

// The watch view's script and data keep their names, and the host lets a
// browser keep them for ten minutes: a version from their content, in the
// address the page asks for, makes every change a new address.
const watchFiles = [
  'public/javascripts/watch.js',
  ...readdirSync(new URL('../public/assets/watch/', import.meta.url)).sort().map((f) => `public/assets/watch/${f}`),
];
const watchVersion = createHash('sha256')
  .update(watchFiles.map((f) => readFileSync(new URL(`../${f}`, import.meta.url))).join('\0'))
  .digest('hex')
  .slice(0, 12);

export default defineConfig({
  title: 'Gadfly',
  description,
  lang: 'en',
  base: '/gadfly/',
  cleanUrls: true,
  // The theme menu (theme/ThemeMenu.vue) applies the theme, from the page head
  // before the first paint; VitePress's own switch is off.
  appearance: false,
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/gadfly/favicon.svg' }],
    ['script', {}, HEAD],
  ],
  markdown: {
    math: true,
    // Code takes its colours from the page, so each colour study can set its
    // own (theme/custom.css, --shiki-*).
    theme: createCssVariablesTheme({ name: 'gadfly', variablePrefix: '--shiki-' }),
    // Each page's headings, which the rule below reads: a list of levels
    // here, where the outline's is a range.
    headers: { level: [2, 3, 4] },
    anchor: { slugify: githubSlug },
    codeTransformers: [hangingLines()],
    config(md) {
      md.use(githubMath);
      md.use(mermaidFences);
      md.use(frameLinks);
    },
  },
  // A page without headings (Watch a run) has no outline, so its column
  // takes the outline's room.
  // Each published frame's file, for its source page's download link, and
  // the licences of what the site ships (notices.mjs).
  buildEnd({ outDir }) {
    writeNotices(outDir);
    const index = JSON.parse(readFileSync(new URL('frames.json', import.meta.url), 'utf8'));
    mkdirSync(join(outDir, 'frames'), { recursive: true });
    for (const [stem, { path }] of Object.entries(index)) {
      copyFileSync(new URL(`../../${path}`, import.meta.url), join(outDir, 'frames', `${stem}.json`));
    }
  },
  transformPageData(pageData) {
    if (!pageData.headers?.length) pageData.frontmatter.aside ??= false;
  },
  themeConfig: {
    nav: [
      { text: 'Start here', link: '/in-plain-words', activeMatch: '^/(in-plain-words|first-frame|framework)' },
      { text: 'Examples', link: '/examples/', activeMatch: '^/examples/' },
      { text: 'Guides', link: '/write-a-frame', activeMatch: `^/(${guides.join('|')})` },
      { text: 'Reference', link: '/command-line', activeMatch: `^/(${reference.join('|')})` },
    ],
    sidebar,
    outline: { level: [2, 4], label: 'On this page' },
    search: { provider: 'local' },
    editLink: { pattern: `${github}/edit/main/docs/:path`, text: 'Edit this page on GitHub' },
    socialLinks: [{ icon: 'github', link: github }],
    gadfly: { version, github },
  },
  vite: {
    // Mermaid's ELK layout is one chunk of about 2 MB, loaded only by a page
    // with a chart.
    build: { chunkSizeWarningLimit: 2500 },
    define: { __WATCH_VERSION__: JSON.stringify(watchVersion) },
  },
});
