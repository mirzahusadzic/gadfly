// The doll stage: five painted nesting dolls standing over the watch view.
// Each line a doll says is one span, and each span paints one region, so a
// trial that cuts a line lifts that paint off the doll. What the lines fix,
// the drawing keeps: a doll that says its headscarf is red has a red
// headscarf on every visit. What they leave open, the shade of that red,
// where the flowers sit, how many dots, is drawn afresh on each visit.
// The data is written by tools/watch_data.py; every string in it is set as text.
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const RATIO = [1, 0.87, 0.76, 0.65, 0.55]; // each doll's height against the largest's
  const WIDE = 200 / 342; // a doll's width against its height

  // One outline, a tall egg: the head flows into the body with no neck.
  const SIL =
    "M100,8 C140,8 160,38 160,80 C160,108 156,124 158,140 C184,170 196,214 194,250 " +
    "C192,292 176,322 150,332 C132,338 68,338 50,332 C24,322 8,292 6,250 C4,214 16,170 42,140 " +
    "C44,124 40,108 40,80 C40,38 60,8 100,8 Z";

  // The colours a doll's words name, each with a few shades to draw from.
  const SHADES = {
    red: ["#d7262f", "#cf2230", "#dc3036"],
    pink: ["#ef8fb3", "#f29abb", "#ea86ab"],
    "pale pink": ["#f6b3bd", "#f8bdc6", "#f3aab6"],
    yellow: ["#f2c94c", "#f4cf5a", "#efc33f"],
    "pale yellow": ["#f6e7a1", "#f8ebb0", "#f3e294"],
    green: ["#2f8a4a", "#2c8346", "#34914f"],
    blue: ["#2f5bb7", "#2c56ad", "#3462c0"],
    "pale blue": ["#a9cdf0", "#b2d3f2", "#a1c7ec"],
    cream: ["#fbf1dc", "#fcf4e3", "#f9edd3"],
    orange: ["#f28c28", "#f4973a", "#ef8420"],
    teal: ["#2f8a7a", "#2c8374", "#349181"],
    purple: ["#7a4fb3", "#744aab", "#8155bb"],
    lilac: ["#d9c3f0", "#ddc9f2", "#d4bcec"],
    white: ["#ffffff", "#fdfcf7", "#fbfaf4"],
    brown: ["#8a5a2b", "#845527", "#90602f"],
    "light brown": ["#b98a52", "#b3844c", "#bf9058"],
    "dark brown": ["#3a2a1e", "#36261b", "#3e2e21"],
    grey: ["#6f7d8c", "#6a7886", "#748292"],
  };
  const DEEP = { red: "#a9161f", green: "#1d6332", blue: "#1f3f86", yellow: "#c99a12", purple: "#57348a" };
  const IRIS = { blue: "#2f5bd0", brown: "#7a4a22", grey: "#6f7d8c", green: "#3f8f4f" };
  const LEAF = "#7cc36a", LEAF_DEEP = "#3d8f45", BERRY = "#e1262f", SEED = "#f2c531";
  const FACE = "#fbefe2", CHEEK = "#f07d93", WOOD = "#e8cfa5";
  const SLIP = { w: 60, h: 34, turn: -6 }; // the paper, and the hole it fits

  // a small seeded draw, so one visit paints one set
  function rng(seed) {
    let s = seed >>> 0 || 1;
    return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32);
  }

  const svg = (tag, attrs = {}) => {
    const node = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    return node;
  };
  const markup = (text) => {
    const g = svg("g");
    g.innerHTML = text; // shapes built here from numbers and colour tokens only
    return g;
  };

  // ---- the motifs, at any size
  function leaf(x, y, len, angle) {
    return `<path d="M0,0 Q${len * 0.5},${-len * 0.28} ${len},0 Q${len * 0.5},${len * 0.28} 0,0 Z" fill="${LEAF}" stroke="${LEAF_DEEP}" stroke-width="0.8" transform="translate(${x} ${y}) rotate(${angle})"/>`;
  }
  function daisy(x, y, r) {
    let out = "";
    for (let k = 0; k < 8; k++)
      out += `<ellipse cx="${x}" cy="${y - r * 0.55}" rx="${r * 0.3}" ry="${r * 0.52}" fill="#fff" stroke="#e6ddd0" stroke-width="0.8" transform="rotate(${k * 45} ${x} ${y})"/>`;
    return out + `<circle cx="${x}" cy="${y}" r="${r * 0.32}" fill="${SEED}" stroke="#c99a12" stroke-width="0.8"/>`;
  }
  function strawberry(x, y, s, seeds) {
    let out = `<path d="M${x},${y - s * 0.55} C${x + s},${y - s * 0.75} ${x + s * 0.85},${y + s * 0.55} ${x},${y + s * 1.05} C${x - s * 0.85},${y + s * 0.55} ${x - s},${y - s * 0.75} ${x},${y - s * 0.55} Z" fill="${BERRY}" stroke="#9e1520" stroke-width="1"/>`;
    if (seeds)
      for (const [dx, dy] of [[-0.35, -0.2], [0.05, -0.25], [0.4, -0.15], [-0.25, 0.2], [0.2, 0.2], [0, 0.55], [-0.5, 0.15], [0.5, 0.2]])
        out += `<ellipse cx="${x + dx * s}" cy="${y + dy * s}" rx="${s * 0.06}" ry="${s * 0.1}" fill="${SEED}"/>`;
    for (let k = 0; k < 5; k++) {
      const a = -Math.PI / 2 + (k - 2) * 0.6;
      out += `<path d="M${x},${y - s * 0.5} q${Math.cos(a) * s * 0.3},${Math.sin(a) * s * 0.1} ${Math.cos(a) * s * 0.55},${Math.sin(a) * s * 0.45 - s * 0.05}" stroke="${LEAF_DEEP}" stroke-width="${s * 0.16}" stroke-linecap="round" fill="none"/>`;
    }
    return out;
  }
  function cherries(x, y, s) {
    const r = s * 0.42, lx = x - s * 0.42, rx = x + s * 0.4, cy = y + s * 0.35;
    return `<path d="M${lx},${cy - r} Q${x - s * 0.2},${y - s * 0.6} ${x + s * 0.1},${y - s * 0.9} M${rx},${cy - r} Q${x + s * 0.25},${y - s * 0.5} ${x + s * 0.1},${y - s * 0.9}" fill="none" stroke="#4a3018" stroke-width="${s * 0.07}" stroke-linecap="round"/>` +
      leaf(x + s * 0.1, y - s * 0.9, s * 0.7, -20) +
      [lx, rx].map((cx) => `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${BERRY}" stroke="#9e1520" stroke-width="1"/><circle cx="${cx - r * 0.35}" cy="${cy - r * 0.35}" r="${r * 0.22}" fill="#fff" fill-opacity="0.75"/>`).join("");
  }
  function rose(x, y, r, swirl) {
    let out = `<circle cx="${x}" cy="${y}" r="${r}" fill="#d7263f" stroke="#7a0f1a" stroke-width="1"/>`;
    for (let k = 0; k < 5; k++) {
      const a = (k / 5) * Math.PI * 2;
      out += `<path d="M${x + Math.cos(a) * r * 0.85},${y + Math.sin(a) * r * 0.85} A${r * 0.55},${r * 0.55} 0 0 1 ${x + Math.cos(a + 1.2) * r * 0.85},${y + Math.sin(a + 1.2) * r * 0.85}" fill="none" stroke="#ffffff66" stroke-width="${r * 0.08}"/>`;
    }
    if (swirl)
      out += `<path d="M${x},${y} m${-r * 0.15},0 a${r * 0.15},${r * 0.15} 0 1 1 ${r * 0.3},0 a${r * 0.32},${r * 0.32} 0 1 1 ${-r * 0.62},0 a${r * 0.5},${r * 0.5} 0 1 1 ${r},0" fill="none" stroke="#7a0f1a" stroke-width="${r * 0.1}" stroke-linecap="round"/>`;
    return out;
  }
  function cornflower(x, y, r, heart) {
    let out = "";
    for (let k = 0; k < 9; k++)
      out += `<path d="M${x},${y} L${x - r * 0.18},${y - r * 0.75} L${x - r * 0.08},${y - r} L${x},${y - r * 0.85} L${x + r * 0.08},${y - r} L${x + r * 0.18},${y - r * 0.75} Z" fill="#3f6fd8" stroke="#1f3f86" stroke-width="0.8" transform="rotate(${(k / 9) * 360} ${x} ${y})"/>`;
    return out + `<circle cx="${x}" cy="${y}" r="${r * (heart ? 0.28 : 0.2)}" fill="${heart ? "#1a2f6e" : "#3f6fd8"}"/>`;
  }
  function motif(kind, x, y, s) {
    if (kind === "rose") return rose(x, y, s * 0.75, false);
    if (kind === "strawberry") return strawberry(x, y, s, false);
    if (kind === "cornflower") return cornflower(x, y, s * 0.85, false);
    if (kind === "cherry") return cherries(x, y, s * 1.1);
    return "";
  }
  // a motif's fine work, a line of its own: a rose's swirl, a strawberry's
  // seeds, a cornflower's dark heart
  function fine(kind, x, y, s) {
    if (kind === "rose") {
      const r = s * 0.75;
      return `<path d="M${x},${y} m${-r * 0.15},0 a${r * 0.15},${r * 0.15} 0 1 1 ${r * 0.3},0 a${r * 0.32},${r * 0.32} 0 1 1 ${-r * 0.62},0 a${r * 0.5},${r * 0.5} 0 1 1 ${r},0" fill="none" stroke="#7a0f1a" stroke-width="${r * 0.1}" stroke-linecap="round"/>`;
    }
    if (kind === "strawberry")
      return [[-0.35, -0.2], [0.05, -0.25], [0.4, -0.15], [-0.25, 0.2], [0.2, 0.2], [0, 0.55], [-0.5, 0.15], [0.5, 0.2]]
        .map(([dx, dy]) => `<ellipse cx="${x + dx * s}" cy="${y + dy * s}" rx="${s * 0.06}" ry="${s * 0.1}" fill="${SEED}"/>`).join("");
    if (kind === "cornflower") return `<circle cx="${x}" cy="${y}" r="${s * 0.85 * 0.28}" fill="#1a2f6e"/>`;
    return "";
  }
  function bloom(kind, x, y, r) {
    if (kind === "daisy") return daisy(x, y, r);
    if (kind === "tulip")
      return `<path d="M${x},${y + r * 1.1} V${y + r * 0.2}" stroke="${LEAF_DEEP}" stroke-width="${r * 0.14}"/>` + leaf(x, y + r * 0.9, r * 0.9, -40) +
        `<path d="M${x - r * 0.55},${y - r * 0.55} L${x - r * 0.28},${y - r * 0.15} L${x},${y - r * 0.7} L${x + r * 0.28},${y - r * 0.15} L${x + r * 0.55},${y - r * 0.55} Q${x + r * 0.62},${y + r * 0.35} ${x},${y + r * 0.35} Q${x - r * 0.62},${y + r * 0.35} ${x - r * 0.55},${y - r * 0.55} Z" fill="#c81e3c" stroke="#7a0f1a" stroke-width="1"/>`;
    if (kind === "buttercup")
      return [[0, -0.45], [-0.55, 0.15], [0.55, 0.15]].map(([dx, dy]) => {
        const cx = x + dx * r, cy = y + dy * r;
        return [0, 1, 2, 3, 4].map((k) => {
          const a = (k / 5) * Math.PI * 2 - Math.PI / 2;
          return `<circle cx="${cx + Math.cos(a) * r * 0.22}" cy="${cy + Math.sin(a) * r * 0.22}" r="${r * 0.2}" fill="#f6cf2a" stroke="#b8901a" stroke-width="0.7"/>`;
        }).join("") + `<circle cx="${cx}" cy="${cy}" r="${r * 0.1}" fill="#8a6a10"/>`;
      }).join("");
    if (kind === "bluebell") {
      let out = `<path d="M${x - r * 0.1},${y + r * 1.1} Q${x + r * 0.15},${y - r * 0.2} ${x + r * 0.7},${y - r * 0.6}" fill="none" stroke="${LEAF_DEEP}" stroke-width="${r * 0.12}"/>`;
      for (const [t, dx] of [[0.25, 0.05], [0.55, 0.3], [0.85, 0.6]]) {
        const bx = x + dx * r, by = y - r * 0.6 + t * r * 1.2;
        out += `<path d="M${bx - r * 0.22},${by} Q${bx},${by - r * 0.35} ${bx + r * 0.22},${by} L${bx + r * 0.3},${by + r * 0.3} L${bx + r * 0.1},${by + r * 0.22} L${bx},${by + r * 0.32} L${bx - r * 0.1},${by + r * 0.22} L${bx - r * 0.3},${by + r * 0.3} Z" fill="#3f6fd8" stroke="#1f3f86" stroke-width="0.8"/>`;
      }
      return out;
    }
    if (kind === "sunflower") {
      let out = "";
      for (let k = 0; k < 14; k++)
        out += `<ellipse cx="${x}" cy="${y - r * 0.62}" rx="${r * 0.18}" ry="${r * 0.4}" fill="#f6c21c" stroke="#b8901a" stroke-width="0.7" transform="rotate(${(k / 14) * 360} ${x} ${y})"/>`;
      return out + `<circle cx="${x}" cy="${y}" r="${r * 0.38}" fill="#6a3e1a"/><circle cx="${x}" cy="${y}" r="${r * 0.24}" fill="#4a2a10"/>`;
    }
    return "";
  }
  function scallops(y, r, fill) {
    let d = `M0,0 H200 V${y}`;
    for (let x = 200; x > 0; x -= 2 * r) d += ` A${r},${r} 0 0 1 ${x - 2 * r},${y}`;
    return `<path d="${d} Z" fill="${fill}"/>`;
  }
  function paper(scale, y, written) {
    const w = SLIP.w * scale, h = SLIP.h * scale;
    return `<g transform="rotate(${SLIP.turn} 100 ${y})"><rect x="${100 - w / 2}" y="${y - h / 2}" width="${w}" height="${h}" rx="2" fill="#fffef6" stroke="#6d655b" stroke-width="1.4"/>` +
      (written ? `<path d="M${100 - w * 0.36},${y - h * 0.12} h${w * 0.72} M${100 - w * 0.36},${y + h * 0.15} h${w * 0.52}" stroke="#6d655b" stroke-width="${2.2 * scale}"/>` : "") + "</g>";
  }

  // ---- one doll, every region it has drawn once, each tagged with its span
  function draw(doll, place, random) {
    const d = doll.design, shade = (word) => {
      const list = SHADES[word] || SHADES.white;
      return list[Math.floor(random() * list.length)];
    };
    const C = {
      body: shade(d.body), scarf: shade(d.scarf), trim: shade(d.trim), hem: shade(d.hem),
      dots: shade(d.dots.replace(/ polka$/i, "").toLowerCase()), hair: shade(d.hair),
      deep: DEEP[d.scarf] || "#00000055", iris: IRIS[d.eyes] || "#2f5bd0",
    };
    const has = new Set([...doll.lines, ...doll.extra].map((l) => l.id)); // its own, and what its frames add
    const jitter = (v, by) => v + (random() - 0.5) * by;
    const regions = {};
    const id = `doll-${place}-${Math.floor(random() * 1e6)}`;
    const root = svg("svg", { viewBox: "0 0 200 342", role: "img", "aria-label": doll.name });
    const defs = markup(`<clipPath id="${id}-sil"><path d="${SIL}"/></clipPath><radialGradient id="${id}-cheek"><stop offset="0" stop-color="${CHEEK}" stop-opacity="0.85"/><stop offset="1" stop-color="${CHEEK}" stop-opacity="0"/></radialGradient>`);
    const shared = svg("defs");
    shared.append(...defs.childNodes);
    root.append(shared);
    const add = (part, text, into = root) => {
      if (!has.has(part)) return;
      const g = markup(text);
      g.classList.add("d-region");
      g.dataset.part = part;
      regions[part] = g;
      into.append(g);
    };
    root.append(markup(`<path d="${SIL}" fill="${WOOD}"/>`)); // bare wood, under all the paint
    add("body", `<path d="${SIL}" fill="${C.body}"/>`);
    const inside = svg("g", { "clip-path": `url(#${id}-sil)` });
    root.append(inside);
    const two = has.has("motif2"), kind = d.motif;
    add("leaves", leaf(jitter(38, 6), 240, 46, -30) + leaf(jitter(162, 6), 240, 46, -150) + leaf(70, jitter(300, 6), 40, -70) + leaf(130, jitter(300, 6), 40, -110) + leaf(100, 214, 34, -90), inside);
    add("hem", `<rect x="0" y="320" width="200" height="22" fill="${C.hem}"/>`, inside);
    add("seam", `<path d="M0,226 Q100,238 200,226" fill="none" stroke="#00000055" stroke-width="1.6"/>`, inside);
    const at = { motif3: [jitter(148, 8), 300, 22], motif2: [jitter(138, 6), jitter(236, 6), 30], motif: [jitter(two ? 72 : 100, 6), jitter(240, 6), 36] };
    add("motif3", motif(kind, ...at.motif3), inside);
    add("motif2", motif(kind, ...at.motif2), inside);
    add("motif", motif(kind, ...at.motif), inside);
    add("fine", ["motif3", "motif2", "motif"].filter((part) => has.has(part)).map((part) => fine(kind, ...at[part])).join(""), inside);
    const sides = random() < 0.5 ? [[20, 262]] : [[20, 252], [24, 288]];
    add("flowers", sides.map(([x, y]) => bloom(d.flower, x, y, 16) + bloom(d.flower, 200 - x, y, 16)).join(""), inside);
    const front = has.has("motif") ? [96, 296, 21] : [100, 286, 30];
    add("flower", bloom(d.flower, jitter(front[0], 6), front[1], front[2] * ({ buttercup: 1.5, bluebell: 1.6 }[d.flower] || 1)), inside);
    add("trim", scallops(196, jitter(12, 3), C.trim), inside);
    add("scarf", scallops(186, 12, C.scarf), inside);
    const dots = [];
    for (let row = 0, y = 34; y < 172; row++, y += 14)
      for (let x = 100 + (row % 2 ? 8 : 0); x < 196; x += 16) {
        const edge = 140 + 30 * (1 - ((x - 100) / 100) ** 2);
        const face = ((x - 100) / 54) ** 2 + ((y - 100) / 54) ** 2 < 1;
        if (y > edge - 4 || face || random() < 0.45) continue;
        for (const sx of x === 100 ? [x] : [x, 200 - x]) dots.push(`<circle cx="${sx}" cy="${y}" r="3.2" fill="${C.dots}"/>`);
      }
    add("dots", dots.join(""), inside);
    add("face", `<ellipse cx="100" cy="100" rx="50" ry="50" fill="${FACE}"/>`);
    add("hair", `<path d="M51,100 Q48,52 100,50 Q152,52 149,100 Q142,70 100,68 Q58,70 51,100 Z" fill="${C.hair}" stroke="#00000033" stroke-width="1"/><path d="M100,51 Q97,60 100,69" stroke="#00000044" stroke-width="2" fill="none"/>`);
    add("brows", `<path d="M70,80 q12,-7 24,-1 M106,79 q12,-6 24,1" fill="none" stroke="#7a5a3a" stroke-width="1.8" stroke-linecap="round"/>`);
    const lash = (x, side) => [0, 1, 2, 3].map((k) => {
      const a = side < 0 ? Math.PI * (1.05 + k * 0.13) : Math.PI * (1.95 - k * 0.13);
      const [x1, y1, x2, y2] = [x + Math.cos(a) * 13, 100 + Math.sin(a) * 13.5, x + Math.cos(a) * 19, 100 + Math.sin(a) * 19.5];
      return `<path d="M${x1},${y1} Q${(x1 + x2) / 2 - side * 2},${(y1 + y2) / 2 - 2} ${x2},${y2}" fill="none" stroke="#20160f" stroke-width="1.8" stroke-linecap="round"/>`;
    }).join("");
    add("lashes", lash(83, -1) + lash(117, 1));
    const eye = (x) => `<ellipse cx="${x}" cy="100" rx="12.5" ry="13" fill="#fff" stroke="#00000022"/><circle cx="${x}" cy="101.5" r="9.6" fill="${C.iris}"/><circle cx="${x}" cy="101.5" r="4.6" fill="#13213f"/>`;
    add("eyes", eye(83) + eye(117));
    add("glints", `<circle cx="80" cy="97" r="3" fill="#fff"/><circle cx="114" cy="97" r="3" fill="#fff"/>`);
    add("nose", `<path d="M99,113 q-2,5 2,7" fill="none" stroke="#d7a68a" stroke-width="1.6" stroke-linecap="round"/>`);
    add("cheeks", `<circle cx="66" cy="120" r="15" fill="url(#${id}-cheek)"/><circle cx="134" cy="120" r="15" fill="url(#${id}-cheek)"/>`);
    add("lips", `<path d="M90,128 q5,-5 10,0 q5,-5 10,0 q-4,8 -10,8 q-6,0 -10,-8z" fill="#c8323c"/>`);
    // what a doll holds: the blank panel its lost paper leaves, the paper, and
    // on the smallest the paper it says is not its own
    const scale = RATIO[4] / RATIO[place]; // the paper is one size on screen on every doll
    if (has.has("holds")) {
      add("holds", `<g transform="rotate(${SLIP.turn} 100 214)"><rect x="${100 - (SLIP.w * scale) / 2 - 2.5}" y="${214 - (SLIP.h * scale) / 2 - 2.5}" width="${SLIP.w * scale + 5}" height="${SLIP.h * scale + 5}" rx="3" fill="#c99a2e"/><rect x="${100 - (SLIP.w * scale) / 2}" y="${214 - (SLIP.h * scale) / 2}" width="${SLIP.w * scale}" height="${SLIP.h * scale}" rx="2" fill="#fffaf0"/></g>`);
      add("paper", paper(scale, 214, true));
    }
    if (has.has("slip")) {
      add("slip", paper(1, 222, false));
      add("says", paper(1, 222, true));
      add("notmine", `<g transform="rotate(${SLIP.turn} 100 222)"><path d="M118,232 l8,-8 M118,224 l8,8" stroke="#8e2c22" stroke-width="2.6" stroke-linecap="round"/></g>`);
    }
    add("decoy", `<g><path d="M150,58 h40 a8,8 0 0 1 8,8 v18 a8,8 0 0 1 -8,8 h-24 l-10,10 l2,-10 h-8 a8,8 0 0 1 -8,-8 v-18 a8,8 0 0 1 8,-8 z" fill="#fff" stroke="#6d655b" stroke-width="1.4"/><circle cx="160" cy="75" r="2.6" fill="#6d655b"/><circle cx="170" cy="75" r="2.6" fill="#6d655b"/><circle cx="180" cy="75" r="2.6" fill="#6d655b"/></g>`);
    add("shine", `<path d="M62,40 q-12,16 -10,42" fill="none" stroke="#fff" stroke-opacity="0.5" stroke-width="5" stroke-linecap="round"/><path d="M26,210 q-8,34 2,72" fill="none" stroke="#fff" stroke-opacity="0.35" stroke-width="6" stroke-linecap="round"/>`);
    root.append(markup(`<path class="d-halo" d="${SIL}" fill="none" stroke-width="9"/>`));
    add("shape", `<path d="${SIL}" fill="none" stroke="#3a2a22" stroke-width="1.8"/>`);
    return { root, regions };
  }

  // ---- the stage: five dolls over one watch view
  function stage(box, api, data) {
    const random = rng(Math.floor(Math.random() * 2 ** 31));
    const byName = Object.fromEntries(data.dolls.map((d) => [d.name, d]));
    const row = document.createElement("div");
    row.className = "d-row";
    const caption = document.createElement("p");
    caption.className = "d-caption";
    caption.setAttribute("aria-live", "polite");
    const variants = document.createElement("div");
    variants.className = "d-variants";
    box.replaceChildren(row, caption, variants);
    const drawn = data.dolls.map((doll, place) => {
      const fig = document.createElement("button");
      fig.type = "button";
      fig.className = "d-doll";
      fig.style.setProperty("--d-ratio", RATIO[place]);
      const { root, regions } = draw(doll, place, random);
      const name = document.createElement("span");
      name.className = "d-name";
      name.textContent = doll.name;
      fig.append(root, name);
      fig.setAttribute("aria-label", `${doll.name}, ${doll.frames.length ? "asked" : "walked, never asked"}`);
      fig.addEventListener("click", () => select(doll.name, true));
      row.append(fig);
      return { doll, fig, regions, name };
    });
    // what the view plays, what its trial left, and a count that each new
    // pick or frame moves on, so a climb or gate already under way stops
    let current = null, step = null, turn = 0;

    // a doll's own regions, and in the frame it is asked in, what the trial
    // left: the lines a trial cut lose their paint
    function paint(entry, present) {
      for (const [part, g] of Object.entries(entry.regions)) g.classList.toggle("is-cut", !present.has(part));
      entry.name.classList.toggle("is-cut", !present.has("name"));
    }
    function own(entry, extra = []) {
      const present = new Set([...entry.doll.lines.map((l) => l.id), ...extra]);
      paint(entry, present);
    }
    function settle() {
      for (const entry of drawn) {
        const asked = current && entry.doll.name === current.doll;
        entry.fig.setAttribute("aria-pressed", String(Boolean(asked)));
        if (asked && step) paint(entry, step.present);
        else own(entry, entry.doll.name === data.piece.fits && step?.climbed ? ["paper"] : []);
      }
      const from = drawn.find((e) => e.doll.name === data.piece.from);
      if (from) from.regions.says?.classList.toggle("is-gone", Boolean(step?.climbed));
    }

    function unmark() {
      for (const entry of drawn) entry.fig.classList.remove("is-reframed", "is-passing");
    }

    function select(name, byHand) {
      const doll = byName[name];
      if (!doll.frames.length) {
        // a walked doll has no run: the view holds still, and its trials no
        // longer paint the stage
        turn++;
        api.hold();
        unmark();
        current = { doll: name, stem: null };
        step = { present: new Set(doll.lines.map((l) => l.id)), climbed: step?.climbed };
        caption.textContent = `${name} is walked, never asked: no run to play. ${name} says ${doll.lines.length} lines, and none says whether ${name} is a boy or a girl.`;
        variants.replaceChildren();
        settle();
        return;
      }
      api.select(doll.frames[0], byHand);
    }

    // the views' own frame changed, by a doll, a button or the sequence
    function frame(stem, d) {
      turn++;
      unmark();
      const asking = data.frames[stem];
      current = { doll: asking.doll, stem };
      const climbed = stem !== data.order[0];
      step = { present: new Set(d.spans.map((s) => s.id)), climbed };
      caption.textContent = asking.caption;
      const asked = byName[asking.doll].frames;
      variants.replaceChildren(
        ...(asked.length > 1
          ? asked.map((s) => {
              const b = document.createElement("button");
              b.type = "button";
              b.className = "w-run";
              b.textContent = data.frames[s].variant;
              b.setAttribute("aria-pressed", String(s === stem));
              b.addEventListener("click", () => api.select(s, true));
              return b;
            })
          : []),
      );
      settle();
    }
    // a trial played: its cut lifts its paint
    function trial(t, d) {
      if (!current?.stem) return; // a walked doll is picked: nothing it says was cut
      const removed = new Set(t ? t.removed : []);
      step = { ...step, present: new Set(d.spans.map((s) => s.id).filter((id) => !removed.has(id))) };
      settle();
    }

    // between frames, the paper's words climb: each doll above passes them
    // on, until the one whose hole they fit
    async function climb() {
      const mine = turn;
      const route = [...data.piece.passes, data.piece.fits];
      for (const name of route) {
        const entry = drawn.find((e) => e.doll.name === name);
        entry.fig.classList.add("is-passing");
        caption.textContent = name === data.piece.fits
          ? `The paper's words fit ${name}'s hole: ${name} said it holds such a paper.`
          : `${name} passes the paper's words on: ${name}'s hole is for ${name}'s own word.`;
        await wait(reduced ? 300 : 1400);
        entry.fig.classList.remove("is-passing");
        if (turn !== mine) return; // a reader took over: the stage is theirs
      }
    }
    // the gate: the decision climbs to the largest doll, which is reframed,
    // and stays marked so until another doll is picked
    async function gate() {
      const mine = turn;
      const g = data.gate;
      const entry = drawn.find((e) => e.doll.name === g.fits);
      entry.fig.classList.add("is-passing");
      caption.textContent = g.caption;
      await wait(reduced ? 300 : 1400);
      if (turn !== mine) return entry.fig.classList.remove("is-passing");
      entry.fig.classList.replace("is-passing", "is-reframed");
    }
    const wait = (ms) => new Promise((done) => setTimeout(done, ms));

    // the hover names what a region says
    row.addEventListener("pointerover", (e) => {
      const g = e.target.closest(".d-region");
      const fig = e.target.closest(".d-doll");
      if (!g || !fig) return;
      const entry = drawn.find((x) => x.fig === fig);
      const line = [...entry.doll.lines, ...entry.doll.extra].find((l) => l.id === g.dataset.part);
      if (line) caption.textContent = `${entry.doll.name} says \u201c${line.text}\u201d`;
    });

    return { frame, trial, climb, gate };
  }

  window.gadflyDolls = { stage };
})();
