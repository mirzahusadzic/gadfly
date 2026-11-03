// A long code block's fold (docs/.vitepress/markdown.mjs, theme/fold.js),
// rendered by the site's own Markdown settings without a browser:
// tests/test_docs.py runs it and reads the JSON it prints.
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createMarkdownRenderer } from 'vitepress';
import config from '../docs/.vitepress/config.mjs';
import { toggle } from '../docs/.vitepress/theme/fold.js';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const md = await createMarkdownRenderer(resolve(ROOT, 'docs'), config.markdown, config.base, {
  warn() {},
  info() {},
  error: console.error,
});

const block = (n) => ['```text', ...Array.from({ length: n }, (_, i) => `line ${i + 1} <of> "${n}"`), '```'].join('\n');
const render = (source) => md.render(source, { relativePath: 'examples/dolls.md' });
// a block as a reader's copy takes it: every line, tags gone, in order
const copied = (html) =>
  html
    .match(/<pre[^>]*>([\s\S]*)<\/pre>/)[1]
    .replace(/<[^>]+>/g, '')
    .replace(/&#x([\da-f]+);/gi, (_, hex) => String.fromCodePoint(Number.parseInt(hex, 16)))
    .replaceAll('&lt;', '<')
    .replaceAll('&gt;', '>')
    .replaceAll('&quot;', '"')
    .replaceAll('&amp;', '&');
const folded = (n) => {
  const html = render(block(n));
  const rest = html.match(/<span class="fold-rest">([\s\S]*?)<\/span><\/code>/);
  const button = html.match(/<button type="button" class="fold"([^>]*)>([^<]*)<\/button><\/div>$/);
  return {
    shown: (html.split('<span class="fold-rest">')[0].match(/class="line"/g) ?? []).length,
    hidden: rest ? (rest[1].match(/class="line"/g) ?? []).length : 0,
    restOpensOnBreak: rest ? rest[1].startsWith('\n') : null,
    button: button ? { label: button[2], other: button[1].match(/data-other="([^"]*)"/)[1] } : null,
    whole: copied(html) === block(n).split('\n').slice(1, -1).join('\n'),
  };
};

const out = {
  ...Object.fromEntries([12, 13, 15, 16, 45].map((n) => [n, folded(n)])),
  mermaid: render(['```mermaid', ...Array.from({ length: 14 }, () => 'a --> b'), '```'].join('\n')).includes('fold'),
};

// the button: pressed, the rest shows and its label offers the first twelve;
// pressed again, the rest folds, and a block folded from below keeps its
// button in sight
const button = {
  attributes: { 'aria-expanded': 'false' },
  dataset: { other: 'Show the first 12 lines' },
  textContent: 'Show all 45 lines',
  scrolled: false,
  top: 100,
  getAttribute(key) {
    return this.attributes[key];
  },
  setAttribute(key, value) {
    this.attributes[key] = value;
  },
  getBoundingClientRect() {
    return { top: this.top };
  },
  scrollIntoView() {
    this.scrolled = true;
  },
};
toggle(button);
out.opened = [button.attributes['aria-expanded'], button.textContent, button.scrolled];
button.top = -400; // the reader has read on below the block
toggle(button);
out.closed = [button.attributes['aria-expanded'], button.textContent, button.scrolled];
console.log(JSON.stringify(out));
