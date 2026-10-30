// The charts in the house style (elk layout, neo look), redrawn when the
// palette switches between light and dark.
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.esm.min.mjs";
import elkLayouts from "https://cdn.jsdelivr.net/npm/@mermaid-js/layout-elk@0.2.3/dist/mermaid-layout-elk.esm.min.mjs";

mermaid.registerLayoutLoaders(elkLayouts);

for (const pre of document.querySelectorAll("pre.mermaid-house")) {
  const chart = document.createElement("div");
  chart.className = "mermaid-house";
  chart.dataset.source = pre.textContent;
  pre.replaceWith(chart);
}

async function draw() {
  const dark = document.body.getAttribute("data-md-color-scheme") === "slate";
  mermaid.initialize({ startOnLoad: false, theme: dark ? "dark" : "default" });
  const charts = document.querySelectorAll("div.mermaid-house");
  for (const [index, chart] of charts.entries()) {
    const { svg } = await mermaid.render(`mermaid-house-${index}`, chart.dataset.source);
    chart.innerHTML = svg;
  }
}

let drawing = Promise.resolve();
const redraw = () => (drawing = drawing.then(draw).catch(console.error));
redraw();
new MutationObserver(redraw).observe(document.body, {
  attributes: true,
  attributeFilter: ["data-md-color-scheme"],
});
