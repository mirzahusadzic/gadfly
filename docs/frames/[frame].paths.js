/** A page for each frame the site publishes (docs/.vitepress/frames.json,
 * which tools/doc_outputs.py writes): the file exactly as written, each line
 * numbered and linkable, the hash its records name, and a way back to the page
 * that shows it in words. A reader meets the words first; this is the source
 * one link away. */
import { readFileSync } from 'node:fs';

const root = new URL('../../', import.meta.url);
const index = JSON.parse(readFileSync(new URL('docs/.vitepress/frames.json', root), 'utf8'));
const github = 'https://github.com/mirzahusadzic/gadfly';
const escape = (text) =>
  text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

function page(stem, { path, name, hash, shown }) {
  const lines = readFileSync(new URL(path, root), 'utf8').replace(/\n$/, '').split('\n');
  const numbered = lines
    .map((line, i) => `<span class="line" id="L${i + 1}"><a href="#L${i + 1}">${i + 1}</a>${escape(line)}</span>`)
    .join('');
  const elsewhere = `[the file on GitHub](${github}/blob/main/${path}) or [download it](/frames/${stem}.json)`;
  const ways = shown
    ? `[Read it in words](/${shown}), or see ${elsewhere}.`
    : `See ${elsewhere}.`;
  return [
    `# ${path}`,
    '',
    `The frame \`${name}\` as written. Every record made under it names its hash,`,
    `\`${hash}\`, and a changed file is a different frame.`,
    '',
    ways,
    '',
    `<pre class="gf-source" v-pre>${numbered}</pre>`,
    '',
  ].join('\n');
}

export default {
  watch: ['../.vitepress/frames.json'],
  paths: () =>
    Object.entries(index).map(([stem, frame]) => ({
      params: { frame: stem, title: frame.path },
      content: page(stem, frame),
    })),
};
