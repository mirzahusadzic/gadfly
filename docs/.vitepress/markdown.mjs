/** Markdown rules that let the pages read on the site as they read on GitHub,
 * without changing them. */
import { readFileSync } from 'node:fs';
import { posix } from 'node:path';

/** A link to a frame's file, `../examples/upgrade.json#L16`, opens that file
 * on GitHub, with its lines numbered; on the site it opens the frame's source
 * page (docs/frames/), the same line marked. */
export function frameLinks(md) {
  const index = JSON.parse(readFileSync(new URL('frames.json', import.meta.url), 'utf8'));
  const pages = new Map(Object.entries(index).map(([stem, frame]) => [frame.path, stem]));
  md.core.ruler.push('frame-links', (state) => {
    const here = posix.dirname(posix.join('docs', state.env.relativePath ?? ''));
    for (const block of state.tokens) {
      for (const token of block.children ?? []) {
        if (token.type !== 'link_open') continue;
        const [path, line] = token.attrGet('href').split('#');
        if (/^[a-z]+:|^\//.test(path) || !path.endsWith('.json')) continue;
        const stem = pages.get(posix.normalize(posix.join(here, path)));
        if (stem) token.attrSet('href', `/frames/${stem}${line ? `#${line}` : ''}`);
      }
    }
  });
}

/** A page's own runs, played: `<!-- watch 07-sql-rule 08-clock-rule -->`
 * is a comment on GitHub, and on the site the watch view
 * (public/javascripts/watch.js) with those examples alone, each named as its
 * frame is; `<!-- watch group payments-demo -->` plays a group's questions,
 * picked from its index. */
export function watchMarkers(md) {
  const index = JSON.parse(readFileSync(new URL('frames.json', import.meta.url), 'utf8'));
  md.core.ruler.push('watch-markers', (state) => {
    for (const token of state.tokens) {
      if (token.type !== 'html_block') continue;
      const group = token.content.trim().match(/^<!-- watch group ([\w-]+) -->$/);
      if (group) {
        token.content = `<div class="gadfly-watch" data-group="${group[1]}"></div>\n`;
        continue;
      }
      const marker = token.content.trim().match(/^<!-- watch (dolls )?([\w -]+) -->$/);
      if (!marker) continue;
      const stems = marker[2].trim().split(/\s+/);
      const unknown = stems.filter((stem) => !index[stem]);
      if (unknown.length) throw new Error(`${state.env.relativePath} plays no frame named ${unknown.join(', ')}`);
      const names = stems.map((stem) => index[stem].name);
      // `watch dolls` stands the doll stage beside the question, and plays the frames in order
      const dolls = marker[1] ? ' data-dolls="dolls"' : '';
      token.content = `<div class="gadfly-watch"${dolls} data-frames="${stems.join(',')}" data-names="${names.join(',')}"></div>\n`;
    }
  });
}

/** GitHub's anchor for a heading: lower case, punctuation dropped, spaces as
 * hyphens, so a link to a heading works in both places. */
export const githubSlug = (heading) =>
  heading
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N} _-]/gu, '')
    .replaceAll(' ', '-');

/** GitHub's own math, $`…`$, which the essay uses so that it reads on GitHub.
 * The math rule takes the backticks into the formula, or the code rule takes
 * the formula as code between two dollars; either way it becomes math. */
export function githubMath(md) {
  md.core.ruler.push('github-math', (state) => {
    for (const block of state.tokens) {
      const tokens = block.children;
      if (!tokens) continue;
      for (let i = 0; i < tokens.length; i++) {
        const token = tokens[i];
        if (token.type === 'math_inline' && /^`[^`]+`$/u.test(token.content)) {
          token.content = token.content.slice(1, -1);
          continue;
        }
        const [before, after] = [tokens[i - 1], tokens[i + 1]];
        if (
          token.type === 'code_inline' &&
          before?.type === 'text' &&
          after?.type === 'text' &&
          before.content.endsWith('$') &&
          after.content.startsWith('$')
        ) {
          before.content = before.content.slice(0, -1);
          after.content = after.content.slice(1);
          const math = new state.Token('math_inline', 'math', 0);
          math.content = token.content;
          math.markup = '$';
          tokens[i] = math;
        }
      }
    }
  });
}

/** A `mermaid` fence becomes a chart drawn in the browser from the fence's own
 * text and configuration, in the page's light or dark. */
export function mermaidFences(md) {
  const fence = md.renderer.rules.fence;
  md.renderer.rules.fence = (tokens, index, options, env, self) =>
    tokens[index].info.trim() === 'mermaid'
      ? `<MermaidDiagram source="${encodeURIComponent(tokens[index].content)}" />\n`
      : fence(tokens, index, options, env, self);
}

const text = (node) =>
  node.type === 'text' ? node.value : (node.children ?? []).map(text).join('');

/** A long line of code wraps instead of scrolling, under its own text: a
 * transcript row under the start of its last column (after the last gap of
 * two or more spaces near the line's start), so a frame's evidence wraps
 * under the evidence; any other line two characters past its indent. The
 * page reads --hang, and --indent on a phone. */
export const hangingLines = () => ({
  name: 'gadfly:hanging-lines',
  line(node) {
    const line = text(node);
    const indent = line.length - line.trimStart().length + 2;
    let column = 0;
    for (const gap of line.matchAll(/ {2,}(?=\S)/gu)) {
      const at = gap.index + gap[0].length;
      if (gap.index > indent - 2 && at <= 40) column = at;
    }
    node.properties.style = `--indent:${indent};--hang:${column || indent}`;
  },
});

/** A code block that would hide HIDE lines or more past its first FOLD shows
 * those FOLD, and a button under them shows the rest (theme/fold.js). A
 * shorter one is shown whole, since its button would take the height the fold
 * saves; GitHub shows every block whole. */
export const FOLD = 12;
export const HIDE = 4;

/** The lines after the first FOLD, together with the line break before each,
 * in a span of their own, so that hiding it leaves no empty line. */
export const foldedLines = () => ({
  name: 'gadfly:folded-lines',
  code(node) {
    const lines = node.children.filter((child) => child.type === 'element');
    if (lines.length - FOLD < HIDE) return;
    const rest = node.children.splice(node.children.indexOf(lines[FOLD - 1]) + 1);
    node.children.push({ type: 'element', tagName: 'span', properties: { class: 'fold-rest' }, children: rest });
  },
});

/** The button that folds and unfolds a long block, last in its box, after the
 * copy button's code; its other label waits in data-other. */
export function foldedFences(md) {
  const fence = md.renderer.rules.fence;
  md.renderer.rules.fence = (tokens, index, options, env, self) => {
    const html = fence(tokens, index, options, env, self);
    if (!html.includes('<span class="fold-rest">')) return html;
    // the lines the highlighter drew, as the reader sees and copies them:
    // blank lines it drops at the end are not counted
    const lines = html.match(/<span class="line[" ]/g).length;
    const button =
      `<button type="button" class="fold" aria-expanded="false" data-other="Show the first ${FOLD} lines">` +
      `Show all ${lines} lines</button>`;
    return html.replace(/<\/div>$/, `${button}</div>`);
  };
}
