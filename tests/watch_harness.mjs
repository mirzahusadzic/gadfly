// The watch view (docs/public/javascripts/watch.js) mounted without a
// browser: tests/test_docs.py runs it and reads what it prints. One view's
// first frame never arrives, and each control is pressed before there is a
// frame to play; another, the doll stage's, plays its kept frames, and is
// paused, picked and played the way a reader would.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');

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

const waiting = new Node(); // its first frame never arrives
waiting.dataset.frames = 'upgrade';
waiting.dataset.names = 'upgrade';
const dolls = new Node(); // the doll stage's view, its stage script never arrives
dolls.dataset.frames = '22c-mirza-not-mine,22-kiran-paper';
dolls.dataset.names = 'Mirza,Kiran';
dolls.dataset.dolls = 'dolls';
const sight = [];
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
  querySelectorAll: (selector) => (selector === '.gadfly-watch' ? [waiting, dolls] : []),
};
globalThis.window = { matchMedia: () => ({ matches: false }), innerHeight: 800 };
globalThis.location = { search: '', href: 'https://example.test/watch' };
globalThis.history = { state: {}, replaceState() {} };
globalThis.fetch = (url) => {
  const stem = new URL(url).pathname.split('/').pop().replace(/\.json$/, '');
  if (stem === 'upgrade' || stem === 'dolls') return new Promise(() => {});
  const data = JSON.parse(readFileSync(resolve(ROOT, `docs/public/assets/watch/${stem}.json`), 'utf8'));
  return Promise.resolve({ ok: true, json: async () => data });
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
// a step's timer is never run: what matters is whether the view is playing
globalThis.setTimeout = () => 1;
globalThis.clearTimeout = () => {};
(0, eval)(readFileSync(resolve(ROOT, 'docs/public/javascripts/watch.js'), 'utf8'));

const settle = () => new Promise((done) => setImmediate(done));
const part = (root, cls) => find(root, cls);
const out = {};

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
console.log(JSON.stringify(out));
