// The troubleshooting page's error tables, seen in place as `--json` prints
// each row: built from the rows themselves, the exit statuses table and each
// section's anchor, so nothing is written twice. GitHub shows the tables.
const HELP = 'https://mirzahusadzic.github.io/gadfly/troubleshooting#';
const KEPT = 'gadfly-errors-view';

// each type its exit status, from the page's Exit statuses table
function statuses(page) {
  const table = section(page.querySelector('h3#exit-statuses'));
  const exits = {};
  for (const row of table ? table.tBodies[0].rows : []) {
    for (const code of row.cells[1].querySelectorAll('code')) {
      exits[code.textContent.trim()] = Number(row.cells[0].textContent.trim());
    }
  }
  return exits;
}

// the table a section heading leads, if it has one before the next section
function section(heading) {
  for (let node = heading && heading.nextElementSibling; node; node = node.nextElementSibling) {
    if (node.tagName === 'TABLE') return node;
    if (/^(H2|H3|HR)$/.test(node.tagName)) return null;
  }
  return null;
}

// what Gadfly prints to do opens the second cell, as code
function notes(cell) {
  const first = [...cell.childNodes].find((n) => n.nodeType !== 3 || n.textContent.trim());
  return first && first.nodeName === 'CODE' ? [first.textContent] : [];
}

function said(row, exits, anchor) {
  const objects = [];
  for (const code of row.cells[0].querySelectorAll('code')) {
    const [, type, message] = code.textContent.match(/^(\w+): ([\s\S]*)$/) || [];
    if (!(type in exits)) continue;
    const error = { type, exit: exits[type], message, notes: notes(row.cells[1]) };
    objects.push(JSON.stringify({ error: { ...error, help: HELP + anchor } }, null, 2));
  }
  return objects;
}

function view(page, json) {
  for (const table of page.querySelectorAll('table.gf-errors')) {
    table.classList.toggle('gf-as-json', json);
  }
  for (const button of page.querySelectorAll('.gf-view button')) {
    button.setAttribute('aria-pressed', String((button.dataset.view === 'json') === json));
  }
  try {
    localStorage.setItem(KEPT, json ? 'json' : 'text');
  } catch {
    // a private window keeps no choice: the page still switches
  }
}

export function showErrors(page) {
  const exits = statuses(page);
  if (!Object.keys(exits).length) return;
  for (const heading of page.querySelectorAll('.vp-doc h3[id]')) {
    const table = section(heading);
    if (!table || table.classList.contains('gf-errors')) continue;
    const rows = [...table.tBodies[0].rows].map((row) => [row, said(row, exits, heading.id)]);
    if (!rows.some(([, objects]) => objects.length)) continue;
    table.classList.add('gf-errors');
    const head = document.createElement('th');
    head.className = 'gf-json';
    head.colSpan = 2;
    head.append('As ', Object.assign(document.createElement('code'), { textContent: '--json' }));
    head.append(' prints it, on standard error');
    table.tHead.rows[0].append(head);
    for (const [row, objects] of rows) {
      const cell = row.insertCell();
      cell.className = 'gf-json';
      cell.colSpan = 2;
      for (const object of objects) {
        // each line its own, so a long one wraps under its own text, as the
        // site's code does
        const code = document.createElement('code');
        for (const line of object.split('\n')) {
          const span = Object.assign(document.createElement('span'), { className: 'line' });
          span.style.setProperty('--hang', line.length - line.trimStart().length + 2);
          span.textContent = line;
          code.append(span);
        }
        const pre = document.createElement('pre');
        pre.append(code);
        cell.append(pre);
      }
    }
    const choice = document.createElement('div');
    choice.className = 'gf-view';
    choice.setAttribute('role', 'group');
    choice.setAttribute('aria-label', `Show the ${heading.textContent.trim()} rows as`);
    for (const [name, label] of [['text', 'Text'], ['json', 'JSON']]) {
      const button = Object.assign(document.createElement('button'), { type: 'button' });
      button.dataset.view = name;
      button.textContent = label;
      button.addEventListener('click', () => view(page, name === 'json'));
      choice.append(button);
    }
    table.before(choice);
  }
  let kept = 'text';
  try {
    kept = localStorage.getItem(KEPT) || 'text';
  } catch {
    // no storage: the text view
  }
  view(page, kept === 'json');
}
