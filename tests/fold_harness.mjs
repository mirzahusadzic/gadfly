// A long code block's fold (docs/.vitepress/markdown.mjs, theme/fold.js), run
// with Node alone on a block as Shiki hands it to the site's transformer and
// as VitePress wraps it: tests/test_docs.py runs it and reads the JSON it
// prints. The site's own build, in CI's docs job, folds every page the same.
import { foldedFences, foldedLines } from '../docs/.vitepress/markdown.mjs';
import { toggle } from '../docs/.vitepress/theme/fold.js';

const block = (n) => Array.from({ length: n }, (_, i) => `line ${i + 1} <of> "${n}"`);

// Shiki's code element: one span a line, each holding the line's tokens, with
// a line break between two lines
const text = (value) => ({ type: 'text', value });
const span = (cls, children) => ({ type: 'element', tagName: 'span', properties: cls ? { class: cls } : {}, children });
const code = (lines) => ({
  type: 'element',
  tagName: 'code',
  properties: {},
  children: lines.flatMap((line, i) => [...(i ? [text('\n')] : []), span('line', [span(null, [text(line)])])]),
});
const escape = (value) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const html = (node) =>
  node.type === 'text'
    ? escape(node.value)
    : `<${node.tagName}${node.properties.class ? ` class="${node.properties.class}"` : ''}>${node.children.map(html).join('')}</${node.tagName}>`;

// the fence as VitePress renders it, the site's fold rule over it
function render(lines, rendered) {
  const md = { renderer: { rules: { fence: () => rendered } } };
  foldedFences(md);
  return md.renderer.rules.fence([{ content: `${lines.join('\n')}\n`, info: 'text' }], 0, {}, {}, null);
}
function fenced(lines) {
  const node = code(lines);
  foldedLines().code(node);
  const shown = '<button title="Copy Code" class="copy"></button><span class="lang">text</span>';
  return render(lines, `<div class="language-text">${shown}<pre class="shiki">${html(node)}</pre>\n</div>`);
}

// a block as a reader's copy takes it: every line, tags gone, in order
const copied = (page) =>
  page
    .match(/<pre[^>]*>([\s\S]*)<\/pre>/)[1]
    .replace(/<[^>]+>/g, '')
    .replaceAll('&lt;', '<')
    .replaceAll('&gt;', '>')
    .replaceAll('&amp;', '&');
const folded = (n) => {
  const page = fenced(block(n));
  const rest = page.match(/<span class="fold-rest">([\s\S]*?)<\/span><\/code>/);
  const button = page.match(/<button type="button" class="fold"([^>]*)>([^<]*)<\/button><\/div>$/);
  return {
    shown: (page.split('<span class="fold-rest">')[0].match(/class="line"/g) ?? []).length,
    hidden: rest ? (rest[1].match(/class="line"/g) ?? []).length : 0,
    restOpensOnBreak: rest ? rest[1].startsWith('\n') : null,
    button: button ? { label: button[2], other: button[1].match(/data-other="([^"]*)"/)[1] } : null,
    whole: copied(page) === block(n).join('\n'),
  };
};

const out = {
  ...Object.fromEntries([12, 13, 15, 16, 45].map((n) => [n, folded(n)])),
  // a chart is drawn, never folded, however long its text
  mermaid: render(block(45), '<MermaidDiagram source="a" />\n').includes('fold'),
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
