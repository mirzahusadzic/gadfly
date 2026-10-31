# Fonts and libraries

Gadfly's code is under Apache 2.0, and the essay's text under CC BY 4.0. The
docs site also ships other people's work, listed here with their licences.
The library itself, the `midwife` package, has no runtime dependencies.

---

### Fonts

The site serves both faces itself, with their licences beside them in
`docs/.vitepress/theme/fonts/` and published with the site.

- **Albert Sans:** the text face, under the
  [SIL Open Font License 1.1](https://mirzahusadzic.github.io/gadfly/notices/albert-sans-OFL.txt).
- **Fraunces:** the headings, under the
  [SIL Open Font License 1.1](https://mirzahusadzic.github.io/gadfly/notices/fraunces-OFL.txt).

---

### The site's code

The site is built with [VitePress](https://vitepress.dev), and its pages run
on these, each MIT-licensed:

- **[VitePress](https://github.com/vuejs/vitepress)** and
  **[Vue](https://github.com/vuejs/core)**, with
  [VueUse](https://github.com/vueuse/vueuse), focus-trap and tabbable.
- **[MiniSearch](https://github.com/lucaong/minisearch)** and mark.js, for
  the site's own search.

---

### Charts

The charts are drawn in the browser by
**[Mermaid](https://github.com/mermaid-js/mermaid)** (MIT) and the libraries
it bundles.

- **ELK**, the Eclipse Layout Kernel, lays the charts out. It ships as
  elkjs, compiled JavaScript under the
  [Eclipse Public License 2.0](https://www.eclipse.org/legal/epl-2.0/); its
  source is at [github.com/kieler/elkjs](https://github.com/kieler/elkjs)
  and [github.com/eclipse/elk](https://github.com/eclipse/elk).
- **DOMPurify** cleans each drawing, under MPL 2.0 or Apache 2.0.
- **Mermaid's other libraries**, among them D3, Cytoscape, Dagre, KaTeX,
  Chevrotain, roughjs, Lodash and Day.js, are under the MIT, ISC, BSD, Apache
  2.0 and Unlicense licences.

Every package the site ships is listed with its version and its licence's
full text in [third-party.txt](https://mirzahusadzic.github.io/gadfly/notices/third-party.txt), which the build writes
from the packages themselves; `package-lock.json` names every package the site
is built from.

---

### Drawn when the site is built

Two libraries work only while the pages are built, and what they draw is part
of the pages; none of their code runs in the browser.

- **[MathJax](https://www.mathjax.org)** (Apache 2.0), through
  markdown-it-mathjax3 (MIT), draws the essay's formulas.
- **[Shiki](https://github.com/shikijs/shiki)** (MIT) colours the code.
