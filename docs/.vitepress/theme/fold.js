// A long code block's button (markdown.mjs) shows the lines after its first
// twelve, or folds them away again; its label says which it will do.

/** Fold or unfold the block a button closes. */
export function toggle(button) {
  const open = button.getAttribute('aria-expanded') !== 'true';
  button.setAttribute('aria-expanded', String(open));
  [button.textContent, button.dataset.other] = [button.dataset.other, button.textContent];
  // folded from below, the block shrinks past the reader: keep its button in sight
  if (!open && button.getBoundingClientRect().top < 0) button.scrollIntoView({ block: 'nearest' });
}

const bound = new WeakSet();

/** Every fold button on every page, now and after a page changes; bound
 * once to a page, however often it is asked, so a click toggles once. */
export function foldButtons(page) {
  if (bound.has(page)) return;
  bound.add(page);
  page.addEventListener('click', (event) => {
    const button = event.target.closest?.('button.fold');
    if (button) toggle(button);
  });
}
