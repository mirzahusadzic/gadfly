/** Markdown rules that let the pages read on the site as they read on GitHub,
 * without changing them. */

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
