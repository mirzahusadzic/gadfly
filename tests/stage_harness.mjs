// The doll stage (docs/public/javascripts/dolls.js) driven without a browser,
// on a page small enough for what the stage touches: tests/test_docs.py runs
// it and reads the JSON it prints, one entry for each thing a reader does.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read = (path) => JSON.parse(readFileSync(resolve(ROOT, path), 'utf8'));

class Node {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.listeners = {};
    this.style = { setProperty() {} };
    this.textContent = '';
    this.classes = new Set();
  }
  set innerHTML(text) {
    this.html = text; // shapes only; the stage never sets text this way
  }
  get childNodes() {
    return this.children;
  }
  setAttribute(key, value) {
    this.attributes[key] = String(value);
  }
  getAttribute(key) {
    return this.attributes[key] ?? null;
  }
  append(...nodes) {
    this.children.push(...nodes.filter((n) => n != null));
  }
  replaceChildren(...nodes) {
    this.children = nodes.filter((n) => n != null);
  }
  addEventListener(type, call) {
    (this.listeners[type] ??= []).push(call);
  }
  click() {
    for (const call of this.listeners.click ?? []) call({ target: this });
  }
  get classList() {
    const set = this.classes;
    return {
      add: (...names) => names.forEach((n) => set.add(n)),
      remove: (...names) => names.forEach((n) => set.delete(n)),
      toggle: (name, on) => ((on ?? !set.has(name)) ? set.add(name) : set.delete(name)),
      contains: (name) => set.has(name),
      replace: (from, to) => (set.delete(from), set.add(to)),
    };
  }
}

globalThis.window = { matchMedia: () => ({ matches: true }) }; // reduced motion: short waits
globalThis.document = { createElement: (t) => new Node(t), createElementNS: (_, t) => new Node(t) };
await import(resolve(ROOT, 'docs/public/javascripts/dolls.js'));

const data = read('docs/public/assets/watch/dolls.json');
const frames = Object.fromEntries(
  Object.keys(data.frames).map((stem) => [stem, read(`docs/public/assets/watch/${stem}.json`)]),
);
const [mirzas, kirans] = [data.order[0], data.order[2]];
const asked = [];
const box = new Node('div');
const hooks = window.gadflyDolls.stage(box, {
  select: (stem) => asked.push(['select', stem]),
  hold: () => asked.push(['hold']),
}, data);
const [row, caption] = box.children;
const doll = (name) => row.children.find((fig) => fig.children[1].textContent === name);
const regions = (fig) => {
  const all = [];
  const walk = (node) => (all.push(node), node.children.forEach(walk));
  walk(fig.children[0]);
  return all.filter((node) => node.dataset.part);
};
const isCut = (name, part) => regions(doll(name)).find((g) => g.dataset.part === part)?.classes.has('is-cut');
const marked = () => row.children.filter((fig) => fig.classes.has('is-reframed')).length;
const seen = {};

// what others say of a doll is drawn last, over its outline and ring
seen.decoyOnTop = doll('Kiran').children[0].children.at(-1).dataset.part === 'decoy';

// a walked doll picked while Kiran's frame plays: the view holds, and Kiran's
// trials no longer paint the stage
hooks.frame(kirans, frames[kirans]);
doll('Amani').click();
hooks.trial({ removed: ['trim'] }, frames[kirans]);
seen.walked = { asked: asked.splice(0), amaniTrimCut: isCut('Amani', 'trim'), caption: caption.textContent };

// a climb under way when a reader picks Kiran: the climb stops at its next step
hooks.frame(mirzas, frames[mirzas]);
const climbing = hooks.climb();
doll('Kiran').click();
hooks.frame(kirans, frames[kirans]);
const taken = caption.textContent;
await climbing;
seen.takeover = { asked: asked.splice(0), captionKept: caption.textContent === taken };

// the gate's mark stays through Back and Next, until a doll is picked
hooks.frame(kirans, frames[kirans]);
await hooks.gate();
const afterGate = marked();
hooks.trial({ removed: [] }, frames[kirans]);
seen.gate = { afterGate, afterTrial: marked() };
hooks.frame(mirzas, frames[mirzas]);
seen.gate.afterPick = marked();

console.log(JSON.stringify(seen));
