// The watch view (docs/public/javascripts/watch.js) mounted without a
// browser, its first frame still loading: tests/test_docs.py runs it and
// reads what each control did when pressed before there was a frame to play.
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
    };
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
  querySelector() {
    return null;
  }
  remove() {}
}

const root = new Node();
root.dataset.frames = 'upgrade';
root.dataset.names = 'upgrade';
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
  querySelectorAll: (selector) => (selector === '.gadfly-watch' ? [root] : []),
};
globalThis.window = { matchMedia: () => ({ matches: false }) };
globalThis.location = { search: '', href: 'https://example.test/watch' };
globalThis.history = { state: {}, replaceState() {} };
globalThis.fetch = () => new Promise(() => {}); // the first frame never arrives
globalThis.IntersectionObserver = class {
  observe() {}
  disconnect() {}
};
globalThis.ResizeObserver = class {
  observe() {}
};
(0, eval)(readFileSync(resolve(ROOT, 'docs/public/javascripts/watch.js'), 'utf8'));

const bar = root.children.find((n) => n.className === 'w-bar'); // the view names its parts by className
const player = bar.children.find((n) => n.className === 'w-player');
const pressed = {};
for (const button of player.children) {
  try {
    button.click();
    pressed[button.textContent] = 'nothing';
  } catch (error) {
    pressed[button.textContent] = `${error.name}`;
  }
}
console.log(JSON.stringify(pressed));
