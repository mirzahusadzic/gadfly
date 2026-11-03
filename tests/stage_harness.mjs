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
  redraw: () => asked.push(['redraw']),
}, data);
const [row, caption, original, variants] = box.children;
const seen = {};

// each visit's picture: every doll named from another region of the pool,
// every line that names a doll or a colour told as the picture shows them;
// the box under the caption shows the set as it was read, word for word
const labels = row.children.map((fig) => fig.children[1].textContent);
const regionOf = Object.fromEntries(Object.entries(data.variation.names).flatMap(([region, names]) => names.map((n) => [n, region])));
const kiranLines = Object.fromEntries([...data.dolls[1].lines, ...data.dolls[1].extra].map((l) => [l.id, l.text]));
const scarf = hooks.text(kirans, 'scarf', kiranLines.scarf).match(/^My headscarf is (.+) and covers my head and shoulders\.$/);
const visit = {
  regions: new Set(labels.map((n) => regionOf[n])).size,
  pooled: labels.every((n) => n in regionOf),
  named: hooks.text(kirans, 'name', kiranLines.name) === `My name is ${labels[1]}.`,
  paper: hooks.text(kirans, 'paper', kiranLines.paper).includes(`My name is ${labels[1]}, and I am a boy.`),
  scarf: Boolean(scarf) && data.variation.colours.some((c) => c.scarf === scarf[1]),
  renamedFrom: hooks.text(kirans, 'inside', kiranLines.inside) === `${labels[1]} sits inside ${labels[0]}.`,
};
const box_ = original.children[1].children[0]; // the checkbox in its label
box_.checked = true;
box_.listeners.change[0]();
const namesAsRead = row.children.map((fig) => fig.children[1].textContent);
visit.asRead = {
  names: namesAsRead,
  lines: Object.entries(kiranLines).every(([id, text]) => hooks.text(kirans, id, text) === text),
  redrawn: asked.splice(0),
};
seen.visit = visit;
const doll = (name) => row.children.find((fig) => fig.children[1].textContent === name);
const regions = (fig) => {
  const all = [];
  const walk = (node) => (all.push(node), node.children.forEach(walk));
  walk(fig.children[0]);
  return all.filter((node) => node.dataset.part);
};
const isCut = (name, part) => regions(doll(name)).find((g) => g.dataset.part === part)?.classes.has('is-cut');
const marked = () => row.children.filter((fig) => fig.classes.has('is-reframed')).length;

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
const noteShown = !doll('Amani').children[2].hidden && doll('Amani').children[2].textContent;
const selectedAfterGate = row.children.filter((fig) => fig.getAttribute('aria-pressed') === 'true').length;
const travellingAfterGate = row.classes.has('is-travelling');
hooks.trial({ removed: [] }, frames[kirans]);
seen.gate = { afterGate, afterTrial: marked(), note: noteShown };
hooks.frame(mirzas, frames[mirzas]);
seen.gate.afterPick = marked();
const amaniNote = doll('Amani').children[2];
seen.gate.noteAfterPick = amaniNote.hidden;
seen.gate.selectionBack = selectedAfterGate === 1 && !travellingAfterGate;

// Kiran's two frames stay on the stage whichever doll plays, the one played
// pressed, so nothing comes and goes as the sequence moves on
const pressed = () => variants.children.map((b) => [b.textContent, b.getAttribute('aria-pressed')]);
seen.variants = { mirza: pressed() };
hooks.frame(kirans, frames[kirans]);
seen.variants.kiran = pressed();
doll('Amani').click();
seen.variants.amani = pressed();

// a reader's own step in the view, as Back, during a climb or a gate: it
// stops at its next step, and the stage shows the frame the view plays; a
// gate's mark already made stays (pass 12, W2)
hooks.frame(mirzas, frames[mirzas]);
const own = caption.textContent;
const climbingBack = hooks.climb();
hooks.cancel();
await climbingBack;
const cut = { caption: caption.textContent === own, passing: row.children.filter((fig) => fig.classes.has('is-passing')).length, travelling: row.classes.has('is-travelling') };
hooks.frame(kirans, frames[kirans]);
const gatingBack = hooks.gate();
hooks.cancel();
await gatingBack;
cut.gateMarked = marked();
await hooks.gate();
hooks.cancel();
cut.markKept = marked();
seen.cancel = cut;

// a line hovered shows in the caption only while the pointer is on it
// (pass 12, W5)
hooks.frame(kirans, frames[kirans]);
const narration = caption.textContent;
const region = regions(doll('Kiran')).find((g) => g.dataset.part === 'body');
const on = { target: { closest: (selector) => (selector === '.d-region' ? region : doll('Kiran')) } };
row.listeners.pointerover[0](on);
const hovered = caption.textContent;
row.listeners.pointerout[0](on);
seen.hover = { hovered: hovered.startsWith('Kiran says'), restored: caption.textContent === narration };

// the climb: the selection travels up with the paper's words, doll by doll,
// never jumping, and rests on Kiran until Kiran's frame is shown
hooks.frame(mirzas, frames[mirzas]);
const passing = () => row.children.filter((fig) => fig.classes.has('is-passing')).map((fig) => fig.children[1].textContent);
const steps = [];
let said = caption.textContent;
Object.defineProperty(caption, 'textContent', {
  get: () => said,
  set(value) {
    said = value;
    steps.push(passing());
  },
});
await hooks.climb();
const resting = { passing: passing(), travelling: row.classes.has('is-travelling') };
hooks.frame(kirans, frames[kirans]);
const pressedNow = row.children.filter((fig) => fig.getAttribute('aria-pressed') === 'true').map((fig) => fig.children[1].textContent);
seen.climb = { steps, resting, shown: { pressed: pressedNow, travelling: row.classes.has('is-travelling') } };

console.log(JSON.stringify(seen));
