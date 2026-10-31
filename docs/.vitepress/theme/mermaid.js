/** Draws Mermaid diagrams one at a time: Mermaid's configuration is global,
 * and each diagram's own `config:` block applies to its drawing only. Mermaid
 * and its ELK layout load on the first diagram a page shows. */
let loaded;
let queue = Promise.resolve();
let count = 0;

const load = async () => {
  const [{ default: mermaid }, { default: elk }] = await Promise.all([
    import('mermaid'),
    import('@mermaid-js/layout-elk'),
  ]);
  mermaid.registerLayoutLoaders(elk);
  return mermaid;
};

/** The diagram's SVG, drawn and measured inside `container`, so its labels
 * are sized with the styles they are shown with. */
export function draw(source, { dark, container }) {
  loaded ??= load();
  const job = queue.then(async () => {
    const mermaid = await loaded;
    mermaid.initialize({
      startOnLoad: false,
      theme: dark ? 'dark' : 'default',
      securityLevel: 'strict',
      suppressErrorRendering: true,
      // Drawn at its own size; the page fits it to its box, the dialog shows it whole.
      flowchart: { useMaxWidth: false },
    });
    const { svg } = await mermaid.render(`diagram-${++count}`, source, container);
    return svg;
  });
  queue = job.catch(() => {});
  return job;
}
