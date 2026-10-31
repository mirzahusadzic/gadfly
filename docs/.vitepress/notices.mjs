/** The licences of what the built site ships, written beside it: every
 * package its pages run (VitePress's client, Vue, its search, Mermaid with all
 * it bundles, ELK), each with the licence text it carries, the MathJax that
 * draws the essay's formulas into the pages, and the fonts' licences.
 * docs/notices.md names them and links here. The build fails when a shipped
 * package neither declares a licence nor carries one. */
import { copyFileSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = new URL('../../', import.meta.url);
// What the pages run, and what drew them; the leaves ship alone, not their
// own dependencies (VitePress's build tools, MathJax's), which stay at build.
const ROOTS = [
  'vue', 'minisearch', 'mark.js', 'focus-trap', '@vueuse/core', '@vueuse/integrations',
  'mermaid', '@mermaid-js/layout-elk',
];
const LEAVES = ['vitepress', 'mathjax-full'];
const LICENCE = /^(licen[cs]e|copying)(\.(md|txt|markdown))?$/i;
const FONTS = new URL('docs/.vitepress/theme/fonts/', root);

/** Each shipped package's place in node_modules, found as Node finds it. */
function shipped() {
  const lock = JSON.parse(readFileSync(new URL('package-lock.json', root), 'utf8')).packages;
  const place = (name, parent) => {
    for (let base = parent; ; base = base.includes('/node_modules/')
      ? base.slice(0, base.lastIndexOf('/node_modules/')) : '') {
      const key = `${base ? `${base}/` : ''}node_modules/${name}`;
      if (key in lock) return key;
      if (!base) return null;
    }
  };
  const seen = new Set();
  const todo = [...ROOTS, ...LEAVES].map((name) => [name, '']);
  while (todo.length) {
    const [name, parent] = todo.pop();
    const key = place(name, parent);
    if (!key || seen.has(key) || key.includes('node_modules/@types/')) continue;
    seen.add(key);
    if (LEAVES.includes(name)) continue;
    for (const dependency of Object.keys(lock[key].dependencies ?? {})) todo.push([dependency, key]);
  }
  return [...seen].sort();
}

function entry(key) {
  const dir = new URL(`${key}/`, root);
  const found = JSON.parse(readFileSync(new URL('package.json', dir), 'utf8'));
  const declared = typeof found.license === 'string' ? found.license : found.license?.type;
  const file = readdirSync(dir).find((name) => LICENCE.test(name));
  if (!declared && !file) throw new Error(`${key} ships with the site but carries no licence`);
  const licence = declared ?? 'licence not declared, its text below';
  const source = found.repository?.url ?? found.repository ?? found.homepage ?? '';
  const text = file
    ? readFileSync(new URL(file, dir), 'utf8').trim()
    : `This package carries no licence file; its package.json declares ${licence}.` +
      (source ? `\nIts source: ${source}` : '');
  return `${'-'.repeat(72)}\n${found.name} ${found.version}, ${licence}\n\n${text}\n`;
}

/** Writes notices/third-party.txt and the fonts' licences into the built site. */
export function writeNotices(outDir) {
  const folder = join(outDir, 'notices');
  mkdirSync(folder, { recursive: true });
  const packages = shipped();
  const header =
    'The Gadfly docs site ships the packages below. Each is listed with its\n' +
    'version, the licence it declares and the licence text it carries.\n' +
    `${packages.length} packages. The fonts' licences are beside this file.\n`;
  writeFileSync(join(folder, 'third-party.txt'), [header, ...packages.map(entry)].join('\n'));
  for (const font of readdirSync(FONTS).filter((name) => name.endsWith('-OFL.txt'))) {
    copyFileSync(new URL(font, FONTS), join(folder, font));
  }
}
