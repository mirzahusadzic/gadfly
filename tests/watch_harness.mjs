// The watch view (docs/public/javascripts/watch.js) mounted without a
// browser: tests/test_docs.py runs it and reads what it prints. One view's
// first frame never arrives, and each control is pressed before there is a
// frame to play; another, the doll stage's, plays its kept frames, is paused,
// picked and played the way a reader would, and then plays its sequence on
// a stand-in stage; one view's frames arrive out of the order they were
// picked; one doll view's stage data is missing; and one is opened with a run
// the address cannot name.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const kept = (stem) => JSON.parse(readFileSync(resolve(ROOT, `docs/public/assets/watch/${stem}.json`), 'utf8'));

class Node {
  constructor(tag = 'div') {
    this.tagName = tag;
    this.children = [];
    this.dataset = {};
    this.listeners = {};
    this.attributes = {};
    this.style = { setProperty() {} };
    this.classes = new Set();
    this.textContent = '';
    this.hidden = false;
    this.options = [];
    this.classList = {
      add: (...names) => names.forEach((n) => this.classes.add(n)),
      remove: (...names) => names.forEach((n) => this.classes.delete(n)),
      toggle: (name, on) => ((on ?? !this.classes.has(name)) ? this.classes.add(name) : this.classes.delete(name)),
      contains: (name) => this.classes.has(name),
    };
  }
  set className(names) {
    this.classes = new Set(names.split(' ').filter(Boolean));
  }
  get className() {
    return [...this.classes].join(' ');
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
  setAttribute(key, value) {
    this.attributes[key] = String(value);
  }
  getAttribute(key) {
    return this.attributes[key] ?? null;
  }
  // the selectors the view asks for: one class, or one attribute's value
  querySelector(selector) {
    const [, cls] = selector.match(/^\.([\w-]+)$/) ?? [];
    const [, key, value] = selector.match(/^\[([\w-]+)="([^"]*)"\]$/) ?? [];
    for (const child of this.children) {
      if (!(child instanceof Node)) continue;
      if (cls ? child.classes.has(cls) : child.attributes[key] === value) return child;
      const found = child.querySelector(selector);
      if (found) return found;
    }
    return null;
  }
  getBoundingClientRect() {
    return { top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0 };
  }
  get scrollHeight() {
    return 0; // nothing overflows, so no panel scrolls
  }
  get clientHeight() {
    return 0;
  }
  remove() {}
}

// the view's text, as a reader reads it: a line break as a newline
const text = (node) =>
  typeof node === 'string' ? node : node.tagName === 'br' ? '\n' : node.textContent + node.children.map(text).join('');
const find = (node, cls) => (node.classes?.has(cls) ? node : node.children?.map((c) => find(c, cls)).find(Boolean));

const view = (frames, names, dolls) => {
  const root = new Node();
  Object.assign(root.dataset, { frames, names }, dolls ? { dolls } : {});
  return root;
};
const waiting = view('upgrade', 'upgrade'); // its first frame never arrives
const dolls = view('22c-mirza-not-mine,22-kiran-paper', 'Mirza,Kiran', 'dolls');
const race = view('20-incident-cause,20b-incident-status', 'Cause,Status'); // frames arrive when told
const nodata = view('22c-mirza-not-mine,22-kiran-paper', 'Mirza,Kiran', 'nodata'); // no stage data
const badRun = view('18-notify-chain', 'Chain'); // opened with ?run=abc
const sight = [];
const held = new Map(); // a frame of the race view, and how to let it arrive
globalThis.Node = Node;
globalThis.Option = class {
  constructor(text, value) {
    Object.assign(this, { text, value });
  }
};
globalThis.document = {
  currentScript: { src: 'https://example.test/javascripts/watch.js?v=1' },
  head: new Node('head'),
  body: new Node('body'),
  createElement: (tag) => new Node(tag),
  createDocumentFragment: () => new Node('#fragment'),
  querySelector: () => null,
  querySelectorAll: (selector) => (selector === '.gadfly-watch' ? [waiting, dolls, race, nodata, badRun] : []),
};
globalThis.window = { matchMedia: () => ({ matches: false }), innerHeight: 800 };
globalThis.location = { search: '?example=18-notify-chain&run=abc', href: 'https://example.test/watch' };
globalThis.history = { state: {}, replaceState() {} };
globalThis.fetch = (url) => {
  const stem = new URL(url).pathname.split('/').pop().replace(/\.json$/, '');
  if (stem === 'upgrade') return new Promise(() => {});
  if (stem === 'nodata') return Promise.resolve({ ok: false, status: 404 });
  const answer = { ok: true, json: async () => kept(stem) };
  if (race.dataset.frames.split(',').includes(stem)) return new Promise((done) => held.set(stem, () => done(answer)));
  return Promise.resolve(answer);
};
globalThis.IntersectionObserver = class {
  constructor(call) {
    sight.push(call);
  }
  observe() {}
  disconnect() {}
};
globalThis.ResizeObserver = class {
  observe() {}
};
// a step's timer runs only when the harness says: what matters is whether
// the view is playing, and what a whole frame played to its end does next
const timers = new Map();
let timed = 0;
globalThis.setTimeout = (call) => {
  timers.set(++timed, call);
  return timed;
};
globalThis.clearTimeout = (id) => timers.delete(id);
const runTimers = () => {
  const due = [...timers.values()];
  timers.clear();
  for (const call of due) call();
};
(0, eval)(readFileSync(resolve(ROOT, 'docs/public/javascripts/watch.js'), 'utf8'));

const settle = () => new Promise((done) => setImmediate(done));
const part = (root, cls) => find(root, cls);
const out = { thrown: [] };
// what the view throws where no one catches it, said rather than ending the run
process.on('unhandledRejection', (error) => out.thrown.push(`${error.name}: ${error.message}`));

// pressed while the first frame still loads, each control does nothing
const player = part(waiting, 'w-player');
out.waiting = {};
for (const button of player.children) {
  try {
    button.click();
    out.waiting[button.textContent] = 'nothing';
  } catch (error) {
    out.waiting[button.textContent] = `${error.name}`;
  }
}

// the doll stage's view: its first frame plays once the view is in sight;
// after that, only Play starts it
await settle();
const play = part(dolls, 'w-play');
const examples = part(dolls, 'w-runs').children;
const playing = () => play.textContent === 'Pause';
const seen = { beforeSight: playing() };
sight[1]([{ isIntersecting: true }]);
seen.inSight = playing();
play.click();
seen.paused = playing();
examples[1].click();
await settle();
seen.pickedWhilePaused = playing();
play.click();
examples[0].click();
await settle();
seen.pickedWhilePlaying = playing();
out.dolls = seen;

// the question's card: the question's text, then the dolls beside it; who
// read it, each "through" on a line of its own
const ask = part(dolls, 'w-ask');
out.card = ask.children.map((c) => c.className);
out.by = text(part(ask, 'w-by'));

// the stage stands, a stand-in that says what the view asks of it: a
// reader's own step ends the sequence and stops a climb or gate under way;
// Play stops one under way and plays the frame again
const asked = [];
globalThis.window.gadflyDolls = {
  stage: () => ({
    frame() {},
    trial() {},
    climb: async () => asked.push('climb'),
    gate: async () => asked.push('gate'),
    cancel: () => asked.push('cancel'),
  }),
};
document.head.children.find((tag) => tag.src.includes('dolls.js')).onload();
await settle();
const strip = part(dolls, 'w-strip');
const story = {};
const playToTheEnd = async () => {
  for (let step = 0; step < 20 && timers.size; step++) runTimers();
  await settle();
};
asked.length = 0;
strip.children.at(-1).click(); // the verdict, while the sequence is on
story.verdict = asked.splice(0);
play.click(); // played again, from the first trial
story.replay = asked.splice(0);
await playToTheEnd();
story.afterVerdictPlayed = asked.splice(0); // the sequence it ended goes no further
part(dolls, 'w-player').children[0].click(); // Back
story.back = asked.splice(0);
out.story = story;

// two quick picks whose frames arrive in the other order: the later pick wins
await settle();
const [cause, status] = part(race, 'w-runs').children;
status.click();
held.get('20b-incident-status')();
await settle();
held.get('20-incident-cause')();
await settle();
const told = text(part(race, 'w-ask'));
out.race = {
  pressed: [cause, status].map((b) => b.getAttribute('aria-pressed')),
  // the two frames ask one question; what each maker is told to write differs
  shows: ['20-incident-cause', '20b-incident-status'].filter((stem) => told.includes(kept(stem).makerInstruction)),
};

// a doll view whose stage data is missing plays on without it, its example
// picker back in sight
out.unstaged = {
  picker: !part(nodata, 'w-bar').children[0].hidden,
  card: part(nodata, 'w-ask').children.map((c) => c.className),
};

// ?run=abc names no run: the view opens on the first
out.badRun = part(badRun, 'w-runs').children.map((b) => b.getAttribute('aria-pressed'));
console.log(JSON.stringify(out));
