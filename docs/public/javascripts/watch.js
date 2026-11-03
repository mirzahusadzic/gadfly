// The watch view: one kept run, played one trial at a time. On the left is
// exactly what the reader read in that trial, with what the trial hid or
// changed marked (for a crossing, what the maker was given and what it
// wrote); on the right, its answers, how they compare with the first answer,
// and the checks filling in until the verdict. Each page plays its own
// examples, named in data-frames and data-names; the payments demo's page
// picks its questions from data-group. Over rung 22's frames, data-dolls
// stands the doll stage on top (dolls.js): the dolls pick the frame, and play
// the climb between them. The data is written by tools/watch_data.py from the
// kept runs; every string in it is set as text.
(() => {
  const script = document.currentScript;
  const base = new URL("../assets/watch/", script.src);
  const version = new URL(script.src).search; // the page's version of this script and its data
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const STEP_MS = 3800;

  // What each kind of trial does, and what it asks, in plain words.
  const TRIALS = {
    baseline: ["Baseline", "Ask with everything there.", "What does {reader} say?"],
    repeat: ["Repeat", "Ask again, with nothing changed.", "Is it the same answer?"],
    ablation: ["Ablation", "Hide the line under test.", "Does the answer change?"],
    "each-anchor": ["One line alone", "Hide one line under test, keep the others.", "Is this line needed on its own?"],
    cumulative: ["Cumulative", "Hide that line, and more.", "Does the answer change now?"],
    sham: ["Sham", "Hide a harmless line instead.", "This should not change the answer."],
    presentation: ["Presentation", "Swap some names for others.", "This should not change the answer."],
    placement: ["Placement", "Move a line somewhere else.", "This should not change the answer."],
    inversion: ["Inversion", "Turn the line's meaning around.", "The answer should turn too."],
    "input-inversion": ["Input inversion", "Turn what is asked around.", "The answer should turn or open."],
    bypass: ["Bypass", "Keep the line, but hide the link that ties it to this case.", "Does the answer change too?"],
    control: ["Control", "Hide everything that matters.", "The answer should change now."],
  };

  // The checks a verdict needs, each answered by one kind of trial. Those
  // marked `always` are needed for "carried", so they show even when the
  // frame never ran their trial. One line alone is evidence, never a check.
  const CHECKS = [
    { kind: "repeat", ask: "Same answer when asked twice?" },
    { kind: "ablation", ask: "Does hiding the line change the answer?" },
    { kind: "sham", ask: "Do harmless cuts leave it alone?", always: true },
    { kind: "presentation", ask: "Do new names leave it alone?", always: true },
    { kind: "placement", ask: "Does moving a line leave it alone?" },
    { kind: "inversion", ask: "Does turning the line around turn the answer?" },
    { kind: "input-inversion", ask: "Does turning what is asked turn the answer?" },
    { kind: "bypass", ask: "Does hiding the link change it too?", always: true },
    { kind: "cumulative", ask: "Does hiding more change it?" },
    { kind: "control", ask: "Can the reader change its mind at all?" },
  ];

  const SAY = {
    carried: "The answer really rests on that line, through the link that ties it to this case.",
    cooled: "The answer does not need that line. Something else decides it.",
    "coupled but misaligned": "The line matters, but changing things pushes the answer where it should not go.",
    unresolved: "Gadfly cannot tell yet.",
    "outside scope": "The owner has said this is not theirs to promise.",
  };
  // carried while the link it rests through was never cut: a frame that names
  // the category with that check open says so
  const UNLINKED = "The answer really rests on that line. The link that ties it to this case was not tested.";

  // Names in the frames' prose (calls, files, snake_case names) are set as code.
  const CODE = /[\w.]+\([^()]*\)|[\w./-]+\.(?:py|txt|md|json|toml|ya?ml)\b|\b(?:[a-z][a-z0-9]*\.)*[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g;
  const cache = new Map();

  function said(finding) {
    const open = finding.obligations.some((o) => o.startsWith("no hidden fallback"));
    return finding.category === "carried" && open ? UNLINKED : SAY[finding.category] || "";
  }

  const el = (tag, cls, content) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (content instanceof Node) node.append(content);
    else if (content != null) node.textContent = content;
    return node;
  };

  // Text with its code names set as code, and any of `marks` highlighted,
  // inside code or out.
  function rich(text, marks = []) {
    const out = document.createDocumentFragment();
    const words = marks.filter(Boolean).sort((a, b) => b.length - a.length).map(escape);
    const pattern = words.length ? new RegExp(`(${words.join("|")})`, "g") : null;
    const marked = (target, piece) => {
      if (!pattern) return target.append(piece);
      piece.split(pattern).forEach((part, i) => target.append(i % 2 ? el("mark", "w-renamed", part) : part));
    };
    let last = 0;
    for (const match of text.matchAll(CODE)) {
      marked(out, text.slice(last, match.index));
      const code = el("code");
      marked(code, match[0]);
      out.append(code);
      last = match.index + match[0].length;
    }
    marked(out, text.slice(last));
    return out;
  }
  const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const word = (label, slot) => el("span", `w-word is-${label == null ? "none" : slot[label]}`, label ?? "no label");

  // Only the highlights, no code styling: the left panel shows the prompt as
  // the reader got it, plain text.
  function plain(text, marks = []) {
    const out = document.createDocumentFragment();
    const words = marks.filter(Boolean).sort((a, b) => b.length - a.length).map(escape);
    if (!words.length) return out.append(text), out;
    text.split(new RegExp(`(${words.join("|")})`, "g")).forEach((part, i) => out.append(i % 2 ? el("mark", "w-renamed", part) : part));
    return out;
  }

  // The answer key, in the instruction's own words: "Gemma must answer merge if
  // ..., hold if ...", each answer in its colour. A reader told no
  // instruction (an engine that answers by its own rules) gets a line that
  // says so, with the words its answers read as.
  function key(d, slot, run) {
    const p = el("p", "w-key");
    const reader = run.reader || d.reader || "Gemma";
    if (run.instruction === null) {
      p.append(`${reader} is sent the statements and the question, not an instruction; its answer reads as `);
      d.labels.forEach((label, i, all) => p.append(i ? (i === all.length - 1 ? " or " : ", ") : "", word(label, slot)));
      p.append(".");
      return p;
    }
    const instruction = run.instruction ?? d.instruction;
    const at = instruction.indexOf("Answer ");
    if (at < 0) {
      p.append(`${reader} must answer with one word: `);
      d.labels.forEach((label, i) => p.append(i ? ", " : "", word(label, slot)));
      return p;
    }
    const sentence = instruction.slice(at + "Answer ".length);
    const names = d.labels.map(escape).join("|");
    const listed = answers(sentence, names);
    if (listed) {
      const list = el("dl", "w-key-list");
      for (const item of listed.items) {
        // an answer no call gave has no slot of its own, and reads as neutral
        const seen = item.label in slot ? slot : { ...slot, [item.label]: "u" };
        if (item.label) list.append(el("dt", null, word(item.label, seen)), el("dd", null, item.condition));
        else list.append(el("dd", "w-key-note", cap(item.text)));
      }
      const out = document.createDocumentFragment();
      out.append(el("p", "w-key", `${reader} must answer${listed.lead ? ` ${listed.lead}` : ""}`), list);
      return out;
    }
    // a label before " if ", or quoted before " if " or " for "
    const pattern = new RegExp(`\\b(${names})(?= if |' (?:if|for) )`, "g");
    p.append(`${reader} must answer `);
    let last = 0;
    for (const match of sentence.matchAll(pattern)) {
      p.append(sentence.slice(last, match.index), word(match[0], slot));
      last = match.index + match[0].length;
    }
    p.append(sentence.slice(last));
    return p;
  }
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

  // The answers an instruction lists after "Answer ", one a row, so a reader
  // need not dig them out of a sentence: "a if ..., b if ...", or a lead
  // ("the question ...:" or "... else.") and then answers, each a label,
  // bare or quoted, with what it is for, and any line that names none
  // ("the one person they make the answer"). Null when fewer than two
  // answers are named, and the sentence is shown as it is.
  function answers(sentence, names) {
    const body = sentence.replace(/\.$/, "");
    const cut = body.search(/: |\. /);
    const lead = cut < 0 ? "" : body.slice(0, cut);
    const rest = cut < 0 ? body : body.slice(cut + 2);
    // a quoted answer starts a row even when no call gave it
    const label = `(?:'[^']+'|(?:${names}))`;
    const parts = rest.split(new RegExp(`(?:, or |, |; )(?=${label}(?:$| |,|;))`));
    const items = parts.map((part) => {
      const m = part.match(new RegExp(`^(?:'([^']+)'|(${names}))(?: ((?:if|for) .+))?$`));
      return m ? { label: m[1] ?? m[2], condition: m[3] ?? "" } : { text: part };
    });
    return items.filter((item) => item.label).length < 2 ? null : { lead, items };
  }

  // a script of the view's own, beside it and at its version, loaded once
  const scripts = new Map();
  function fetchScript(name) {
    if (!scripts.has(name))
      scripts.set(
        name,
        new Promise((done, fail) => {
          const tag = document.createElement("script");
          tag.src = new URL(`${name}${version}`, script.src).href;
          tag.onload = done;
          tag.onerror = () => fail(new Error(name));
          document.head.append(tag);
        }),
      );
    return scripts.get(name);
  }

  async function fetchFrame(stem) {
    if (!cache.has(stem)) {
      cache.set(
        stem,
        fetch(new URL(`${stem}.json${version}`, base)).then((r) => {
          if (!r.ok) throw new Error(`${stem} (${r.status})`);
          return r.json();
        }),
      );
    }
    return cache.get(stem);
  }

  // The decision labels take the categorical slots in the frame's order;
  // an answer that decides nothing ("unclear", or the frame's own neutral
  // words) is the neutral grey.
  function slots(labels, neutral = ["unclear"]) {
    const map = {};
    let next = 0;
    for (const label of labels) map[label] = neutral.includes(label) ? "u" : "abc"[next++];
    return map;
  }

  function trialName(trial) {
    const [name] = TRIALS[trial.kind] || [cap(trial.kind)];
    const n = trial.id.match(/-(\d+)$/);
    return n ? `${name} ${n[1]}` : name;
  }

  // ---- what one trial's answers say, against the first answer
  // How the calls of one trial answered in this run, as one line: the answer
  // word itself, in its colour, and how many of the run's asks gave it.
  function agreement(calls, level, agree, slot) {
    const tally = new Map();
    for (const c of calls) tally.set(c.answer, (tally.get(c.answer) || 0) + 1);
    const line = el("p", "w-agree");
    if (level == null) {
      line.append("In this run the answers split, ");
      [...tally].sort((a, b) => b[1] - a[1]).forEach(([label, n], i, all) => {
        line.append(word(label, slot), ` ${n} ${n === 1 ? "time" : "times"}${i < all.length - 1 ? " and " : ". "}`);
      });
      line.append(`Gadfly needs ${agree} alike, so none counts.`);
      return line;
    }
    const n = tally.get(level);
    line.append(
      word(level, slot),
      calls.length === 1
        ? " the one time it was asked in this run."
        : n === calls.length
        ? ` all ${n} times it was asked in this run.`
        : ` ${n} of the ${calls.length} times it was asked in this run, enough to count.`,
    );
    return line;
  }

  function comparison(trial, level, first, data, reader) {
    if (trial.kind === "baseline") return "Every other trial is compared with this answer.";
    if (level == null || first == null) return "With no agreed answer here, there is nothing to compare.";
    const was = `With everything there, ${reader} said ${first}.`;
    if (level === first) {
      const still = {
        repeat: "Asked again, it says the same.",
        ablation: "The line was not needed for this answer.",
        "each-anchor": "The other lines carry it without this one.",
        cumulative: "Even with more hidden, it holds.",
        sham: "A harmless cut changed nothing, as it should.",
        presentation: "New names changed nothing, as they should.",
        placement: "Moving the line changed nothing, as it should.",
        inversion: "Turning the line around did not turn the answer, which it should.",
        "input-inversion": "Turning what is asked around did not change the answer, which it should.",
        bypass: "So something else still carries the answer.",
        control: "Even with everything that matters hidden. Maybe it is not reading at all.",
      };
      return `${was} It still says ${first}. ${still[trial.kind] || ""}`.trim();
    }
    const now = `${was} Now it says ${level}.`;
    if (trial.kind === "ablation" && Array.isArray(data.allowed.ablation) && !data.allowed.ablation.includes(level)) {
      return `${now} Hiding the line changed it, but to an answer the frame does not allow here.`;
    }
    if (trial.kind === "input-inversion" && Array.isArray(data.allowed.inputInversion) && !data.allowed.inputInversion.includes(level)) {
      return `${now} It changed, but to an answer the frame does not allow here.`;
    }
    if (trial.kind === "inversion" && Array.isArray(data.allowed.inversion) && !data.allowed.inversion.includes(level)) {
      return `${now} It turned, but to an answer the frame does not allow here.`;
    }
    if (trial.kind === "bypass" && Array.isArray(data.allowed.bypass) && !data.allowed.bypass.includes(level)) {
      return `${now} It changed, but the frame expected ${data.allowed.bypass.join(" or ")}.`;
    }
    const moved = {
      repeat: "Asked again, it changed, so the answer is not steady.",
      ablation: "Hiding the line changed the answer.",
      "each-anchor": "This line is needed on its own.",
      cumulative: "Hiding more changed it.",
      sham: "A harmless cut changed it, which it should not.",
      presentation: "New names changed it, which they should not.",
      placement: "Moving a line changed it, which it should not.",
      inversion: "Turning the line around turned the answer, as it should.",
      "input-inversion": "Turning what is asked around changed the answer, as it should.",
      bypass: "Hiding the link changed it too.",
      control: `So ${reader} does change its mind when it should.`,
    };
    return `${now} ${moved[trial.kind] || ""}`.trim();
  }

  // The answer each check has after the trials played so far: yes, no, split
  // (a trial with no agreed answer), "not tested", or not yet.
  function checks(data, finding, playedIds) {
    const first = finding.levels.baseline;
    const kinds = new Set(data.trials.map((t) => t.kind));
    return CHECKS.filter((c) => kinds.has(c.kind) || c.always).map((c) => {
      const trials = data.trials.filter((t) => t.kind === c.kind);
      if (!trials.length) return { ...c, answer: "not tested" };
      const played = trials.filter((t) => playedIds.has(t.id));
      if (!played.length) return { ...c, answer: "not yet" };
      const levels = played.map((t) => finding.levels[t.id]);
      if (first == null || levels.some((l) => l == null)) return { ...c, answer: "can't tell" };
      const changed = levels.map((l) => l !== first);
      const allowed = (key, l) => !Array.isArray(data.allowed[key]) || data.allowed[key].includes(l);
      let answer;
      if (["sham", "presentation", "placement", "repeat"].includes(c.kind)) answer = changed.some(Boolean) ? "no" : "yes";
      else if (c.kind === "ablation" && changed[0] && !allowed("ablation", levels[0])) answer = "yes, the wrong way";
      else if (c.kind === "bypass" && changed[0] && !allowed("bypass", levels[0])) answer = "no";
      else if (c.kind === "inversion") answer = changed[0] && allowed("inversion", levels[0]) ? "yes" : "no";
      else if (c.kind === "input-inversion") answer = changed[0] && allowed("inputInversion", levels[0]) ? "yes" : "no";
      else answer = changed.every(Boolean) ? "yes" : "no";
      return { ...c, answer: played.length < trials.length && answer === "yes" ? "so far yes" : answer };
    });
  }

  // Where the statements list starts, from its lines' tops and bottoms and
  // the height it shows, so the line under test is always in view: at the
  // first of every line under test and the changed line nearest them, when
  // they all fit; else at the first line under test, when every one fits;
  // else at a line under test the trial changed; else at the higher of a
  // line under test and the changed line nearest it, when the two fit
  // together; else at that line under test.
  function settle(rows, height) {
    const tests = rows.filter((r) => r.test);
    const changed = rows.filter((r) => r.changed);
    const top = (group) => Math.min(...group.map((r) => r.top));
    const tall = (group) => Math.max(...group.map((r) => r.bottom)) - top(group);
    const every = changed.map((line) => [...tests, line]).sort((a, b) => tall(a) - tall(b))[0] ?? tests;
    if (tests.length && tall(every) <= height) return top(every);
    if (tests.length && tall(tests) <= height) return top(tests);
    const touched = tests.find((r) => r.changed);
    if (touched) return touched.top;
    if (!tests.length) return changed.length ? changed[0].top : 0;
    let best = { test: tests[0], top: tests[0].top, span: Infinity };
    for (const test of tests) {
      for (const line of changed) {
        const top = Math.min(test.top, line.top);
        const span = Math.max(test.bottom, line.bottom) - top;
        if (span < best.span) best = { test, top, span };
      }
    }
    return best.span <= height ? best.top : best.test.top;
  }

  function why(category, list, reader) {
    if (category !== "unresolved") return null;
    if (list.some((c) => c.answer === "can't tell")) return "Some answers split, so a check cannot be read.";
    const bypass = list.find((c) => c.kind === "bypass");
    if (bypass?.answer === "not tested") return "Nobody tried hiding the link, so one check was never made.";
    if (list.find((c) => c.kind === "control")?.answer === "no") {
      return `${reader} never changed its mind, so Gadfly cannot tell whether it is reading at all.`;
    }
    if (bypass?.answer === "no") return "Hiding the link did not change the answer, so something else may carry it.";
    if (list.some((c) => c.answer === "not tested")) return "One check was never made.";
    return "One check is still open.";
  }

  function mount(root) {
    const listed = (value) => (value || "").split(",").map((s) => s.trim()).filter(Boolean);
    const stems = listed(root.dataset.frames);
    const names = listed(root.dataset.names);
    const state = { stem: null, data: null, input: null, run: 0, step: 0, timer: null };
    // a link may open one example and one of its runs: ?example=stem&run=n
    const asked = new URLSearchParams(location.search);

    // ---- pickers: a page's own examples as buttons, named as its frames are,
    // and none when it has one; the payments demo's many questions in a list
    const bar = el("div", "w-bar");
    const frameSelect = el("select", "w-select");
    frameSelect.setAttribute("aria-label", "Question");
    const examples = el("div", "w-runs");
    examples.setAttribute("role", "group");
    examples.setAttribute("aria-label", "Example");
    stems.forEach((stem, i) => {
      const b = el("button", "w-run", names[i] || stem);
      b.type = "button";
      b.dataset.stem = stem;
      b.addEventListener("click", () => load(stem));
      examples.append(b);
    });
    const inputSelect = el("select", "w-select");
    inputSelect.setAttribute("aria-label", "Case");
    const runs = el("div", "w-runs");
    runs.setAttribute("role", "group");
    runs.setAttribute("aria-label", "Run");
    const field = (name, control) => {
      const wrap = el("label", "w-field");
      wrap.append(el("span", "w-field-name", name), control);
      return wrap;
    };
    const caseField = field("Case", inputSelect);
    const runField = field("Run", runs);

    // ---- the player, and the strip of trials
    const player = el("div", "w-player");
    const back = el("button", "w-btn", "Back");
    const play = el("button", "w-btn w-play", "Play");
    const next = el("button", "w-btn", "Next");
    for (const b of [back, play, next]) b.type = "button";
    player.append(back, play, next);
    const exampleField = root.dataset.group ? field("Question", frameSelect) : field("Example", examples);
    exampleField.classList.toggle("is-wide", Boolean(root.dataset.group));
    exampleField.hidden = !root.dataset.group && stems.length < 2;
    bar.append(exampleField, caseField, runField, player);
    const ask = el("div", "w-ask");
    const strip = el("div", "w-strip");
    const top = el("div", "w-top");
    top.append(strip);

    // ---- the two panels
    const stage = el("div", "w-stage");
    const doc = el("section", "w-doc");
    const side = el("section", "w-side");
    stage.append(doc, side);
    // the doll stage: the dolls are the picker, and play the frames in order
    const dollBox = root.dataset.dolls ? el("div", "w-dolls") : null;
    if (dollBox) exampleField.hidden = true;
    root.replaceChildren(...(dollBox ? [dollBox] : []), bar, ask, top, stage);
    let hooks = {};
    const story = { on: false, order: [] }; // on once the stage stands
    // the stage draws beside the view and never stops it: should it fail,
    // it is taken away, and the frames play on without it
    const unstage = (error) => {
      hooks = {};
      story.on = false;
      dollBox?.remove();
      console.error(error);
    };
    const staged = (call) => {
      try {
        call();
      } catch (error) {
        unstage(error);
      }
    };

    frameSelect.addEventListener("change", () => load(frameSelect.value));
    inputSelect.addEventListener("change", () => {
      state.input = inputSelect.value;
      compare();
    });
    back.addEventListener("click", () => {
      story.on = false;
      stop();
      show(Math.max(0, state.step - 1), true);
    });
    next.addEventListener("click", () => {
      story.on = false;
      stop();
      show(Math.min(last(), state.step + 1), true);
    });
    play.addEventListener("click", () => (state.timer ? ((story.on = false), stop()) : start()));

    const last = () => state.data.trials.length; // the step after the last trial is the verdict

    // the address says what is shown once the reader picks it, so a reader
    // can link to it
    function remember() {
      const url = new URL(location.href);
      url.searchParams.set("example", state.stem);
      url.searchParams.set("run", String(state.run + 1));
      history.replaceState(history.state, "", url);
    }

    async function load(stem, run = 0, quiet = false) {
      stop();
      state.stem = stem;
      frameSelect.value = stem;
      for (const b of examples.children) b.setAttribute("aria-pressed", String(b.dataset.stem === stem));
      root.classList.add("is-loading");
      try {
        state.data = await fetchFrame(stem);
      } catch (error) {
        stage.replaceChildren(el("p", "w-error", `Could not load ${error.message}.`));
        return;
      } finally {
        root.classList.remove("is-loading");
      }
      const d = state.data;
      state.input = d.inputs[0].id;
      state.run = Math.min(Math.max(run, 0), d.runs.length - 1);
      inputSelect.replaceChildren(...d.inputs.map((x) => new Option(x.id, x.id)));
      caseField.hidden = d.inputs.length < 2;
      const readers = d.runs.every((r) => r.reader);
      runField.querySelector(".w-field-name").textContent = readers ? "Reader" : "Run";
      runs.setAttribute("aria-label", readers ? "Reader" : "Run");
      staged(() => hooks.frame?.(stem, d));
      runs.replaceChildren(
        ...d.runs.map((r, i) => {
          const b = el("button", "w-run", readers ? r.reader : String(i + 1));
          b.type = "button";
          b.addEventListener("click", () => {
            state.run = i;
            compare();
          });
          return b;
        }),
      );
      restart(quiet);
    }

    // it plays once it is first in view, from the first trial
    let seen = false;
    const view = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting)) return;
        seen = true;
        view.disconnect();
        if (state.data && state.timer === null && state.step === 0) start();
      },
      { threshold: 0.25 },
    );
    view.observe(root);

    function restart(quiet = false) {
      stop();
      if (!quiet) remember();
      [...runs.children].forEach((b, i) => b.setAttribute("aria-pressed", String(i === state.run)));
      show(0, true);
      if (seen) start();
    }

    // another run, reader or case of the same example: the same trial through
    // its answers, so the two can be compared; playing goes on, a pause holds
    function compare() {
      const playing = state.timer !== null;
      stop();
      remember();
      [...runs.children].forEach((b, i) => b.setAttribute("aria-pressed", String(i === state.run)));
      show(Math.min(state.step, last()), false);
      if (playing) start();
    }

    function start() {
      if (state.step >= last()) show(0, true);
      play.textContent = "Pause";
      state.timer = setTimeout(function tick() {
        if (state.step >= last()) {
          stop();
          return onward();
        }
        show(state.step + 1, true);
        state.timer = setTimeout(tick, reduced ? STEP_MS / 2 : STEP_MS);
      }, reduced ? STEP_MS / 2 : STEP_MS);
    }

    // on the doll stage, once a frame has played to its verdict, the next in
    // the order: the climb of the paper's words, the next frame, or the gate
    async function onward() {
      if (!story.on) return;
      try {
        for (let i = story.order.indexOf(state.stem) + 1; i < story.order.length; i++) {
          const next = story.order[i];
          if (next === "climb") await hooks.climb?.();
          else if (next === "gate") return await hooks.gate?.();
          else return story.on ? await load(next, 0, true) : undefined;
          if (!story.on) return;
        }
      } catch (error) {
        unstage(error); // the stage goes; the frames play on without it
      }
    }

    function stop() {
      clearTimeout(state.timer);
      state.timer = null;
      play.textContent = state.data && state.step >= last() ? "Play again" : "Play";
    }

    // ---- one step: a trial, or at the end the verdict
    function show(step, animate) {
      state.step = step;
      root.classList.toggle("no-motion", reduced || !animate);
      const d = state.data;
      const run = d.runs[state.run];
      const finding = run.findings.find((f) => f.input === state.input);
      const slot = slots(d.labels, d.neutral);
      const first = finding.levels.baseline;
      const atVerdict = step >= d.trials.length;
      const played = new Set(d.trials.slice(0, atVerdict ? d.trials.length : step + 1).map((t) => t.id));
      back.disabled = step === 0;
      next.disabled = step >= last();

      // the strip: every trial, with its agreed answer once it has played
      strip.replaceChildren(
        ...d.trials.map((trial, i) => {
          const b = el("button", "w-step");
          b.type = "button";
          if (i === step) b.setAttribute("aria-current", "step");
          b.append(el("span", "w-step-name", trialName(trial)));
          const level = finding.levels[trial.id];
          const answer = played.has(trial.id)
            ? el("span", `w-step-answer is-${level == null ? "none" : slot[level]}`, level ?? "split")
            : el("span", "w-step-answer is-pending", "…");
          b.append(answer);
          b.addEventListener("click", () => {
            story.on = false;
            stop();
            show(i, true);
          });
          return b;
        }),
        (() => {
          const b = el("button", "w-step w-step-verdict");
          b.type = "button";
          if (atVerdict) b.setAttribute("aria-current", "step");
          b.append(el("span", "w-step-name", "Verdict"), el("span", "w-step-answer is-pending", atVerdict ? finding.category : "…"));
          b.addEventListener("click", () => {
            stop();
            show(last(), true);
          });
          return b;
        })(),
      );
      const current = strip.querySelector('[aria-current="step"]');
      if (current) {
        const [box, at] = [strip.getBoundingClientRect(), current.getBoundingClientRect()];
        if (at.left < box.left || at.right > box.right) strip.scrollLeft += at.left - box.left - (box.width - at.width) / 2;
      }

      const trial = atVerdict ? null : d.trials[step];
      drawAsk(d, slot, run);
      drawDoc(trial, d, run);
      drawSide(trial, d, run, finding, slot, first, played);
      staged(() => hooks.trial?.(trial, d));
      follow();
    }

    // the question, and the words the reader may answer with and what each
    // means; for a crossing, what the maker is told to write first
    function drawAsk(d, slot, run) {
      const question = d.inputs.find((x) => x.id === state.input).text;
      // the role and the key together are the whole instruction, word for word
      const role = d.instruction.slice(0, Math.max(0, d.instruction.indexOf("Answer "))).trim();
      // who read it, then the model's id as its records name it, on one line
      const by = el("p", "w-by");
      by.append(
        d.madeBy ? (d.madeBy === d.readBy ? `Made and read by ${d.readBy}` : `Made by ${d.madeBy}, read by ${d.readBy}`) : `Read by ${d.readBy}`,
      );
      const models = [...new Set([d.makerModel, d.model].filter(Boolean))];
      if (models.length) {
        by.append(" (");
        models.forEach((model, i) => by.append(i ? ", " : "", el("code", "w-model", model)));
        by.append(")");
      }
      ask.replaceChildren(
        el("p", "w-question", rich(question)),
        ...(role ? [el("p", "w-role", role)] : []),
        key(d, slot, run),
        ...(d.maker
          ? [
              el("p", "w-caption w-maker", `What ${d.maker} is told to write first, from the lines alone and never the question`),
              el("p", "w-role", d.makerInstruction),
            ]
          : []),
        ...(d.readBy ? [by] : []),
      );
    }

    // the left panel: the reader's prompt, with this trial's changes marked;
    // for a crossing, the maker's, then what it wrote in the trial's first call
    function drawDoc(trial, d, run) {
      const reader = run.reader || d.reader || "Gemma";
      const given = d.maker || reader;
      const shown = trial ?? d.trials[0];
      const prompt = d.prompts[`${state.input}/${shown.id}`];
      const [body, question] = prompt.split("\n\n---\n\n");
      const bodyLines = body.split("\n");
      const textOf = Object.fromEntries(shown.order.map((id, i) => [id, bodyLines.length === shown.order.length ? bodyLines[i] : null]));
      const ids = shown.kind === "placement" ? shown.order : d.spans.map((s) => s.id);
      const marks = shown.renames.map(([, to]) => to);

      const lines = el("ol", "w-lines");
      ids.forEach((id, i) => {
        const span = d.spans.find((s) => s.id === id);
        const hidden = shown.removed.includes(id);
        const li = el("li", "w-line");
        li.style.setProperty("--i", i);
        if (span.anchor) li.classList.add("is-anchor");
        if (hidden) li.classList.add("is-hidden");
        if (shown.moved === id) li.classList.add("is-moved");
        li.append(el("span", "w-line-text", plain(hidden ? span.text : textOf[id] ?? span.text, marks)));
        const tags = el("span", "w-tags");
        if (span.anchor) tags.append(el("span", "w-tag is-anchor", "line under test"));
        if (hidden) tags.append(el("span", "w-tag is-hidden", "hidden"));
        if (shown.moved === id) tags.append(el("span", "w-tag is-moved", "moved here"));
        if (tags.childElementCount) li.append(tags);
        lines.append(li);
      });

      const verb = d.maker ? "was given" : "read";
      const parts = [el("p", "w-caption", trial ? `What ${given} ${verb} in this trial` : `What ${given} ${verb}, with everything there`), lines];
      if (d.maker) {
        const calls = run.calls.filter((c) => c.input === state.input && c.trial === shown.id).sort((a, b) => a.n - b.n);
        const first = calls[0];
        const made = el("p", "w-made", first?.made == null ? `${d.maker} wrote nothing in this call.` : plain(first.made, marks));
        if (first?.cut) made.append(" …");
        const times = calls.length === 1 ? "in its one call" : `in the first of ${calls.length} calls`;
        parts.push(el("p", "w-caption w-made-caption", `What ${d.maker} wrote from it ${times}, which ${reader} read`), made);
      }
      parts.push(el("p", "w-asked", plain(question, marks)));
      doc.replaceChildren(...parts);
    }

    // a long list fills the left panel and scrolls itself, never the page, to
    // where settle() starts it in the part of the list the window shows below
    // the site's top bars (all of it when the window shows none); room after
    // the last line lets a line near the end come up to the top
    function follow() {
      const lines = doc.querySelector(".w-lines");
      if (!lines) return;
      lines.style.paddingBottom = "";
      if (lines.scrollHeight <= lines.clientHeight) return;
      const rows = [...lines.children].map((li) => ({
        top: li.offsetTop,
        bottom: li.offsetTop + li.offsetHeight,
        test: li.classList.contains("is-anchor"),
        changed: li.matches(".is-hidden, .is-moved") || li.querySelector("mark.w-renamed") !== null,
      }));
      const box = lines.getBoundingClientRect();
      const bars = [".VPNav", ".VPLocalNav"].map((s) => document.querySelector(s)?.getBoundingClientRect().bottom ?? 0);
      const from = Math.max(box.top, 0, ...bars);
      const shown = Math.min(box.top + lines.clientHeight, window.innerHeight) - from;
      const [skip, height] = shown > 0 ? [from - box.top, shown] : [0, lines.clientHeight];
      const top = Math.max(0, settle(rows, height) - skip);
      const short = lines.clientHeight - (lines.scrollHeight - top);
      if (short > 0) lines.style.paddingBottom = `${short}px`;
      lines.scrollTop = top;
    }
    // the panel follows the right column's height and the window's width
    new ResizeObserver(follow).observe(doc);

    // the right panel: this trial's answers and what they show, then the checks
    function drawSide(trial, d, run, finding, slot, first, played) {
      const parts = [];
      if (trial) {
        const reader = run.reader || d.reader || "Gemma";
        const [, does, asks] = TRIALS[trial.kind] || ["", trial.kind, ""];
        const head = el("div", "w-head");
        head.append(
          el("p", "w-caption", `${trialName(trial)}, trial ${d.trials.indexOf(trial) + 1} of ${d.trials.length}`),
          el("p", "w-does", does),
          el("p", "w-asks", asks.replace("{reader}", reader)),
        );
        const calls = run.calls.filter((c) => c.input === state.input && c.trial === trial.id).sort((a, b) => a.n - b.n);
        const level = finding.levels[trial.id];
        const answers = el("div", "w-answers");
        answers.append(el("p", "w-caption", `${reader} answered`), agreement(calls, level, d.agree, slot));
        const compare = el("p", "w-compare", comparison(trial, level, first, d, reader));
        parts.push(head, answers, compare);
      }

      const list = checks(d, finding, played);
      const box = el("div", "w-checks");
      box.append(el("p", "w-caption", trial ? "Checks so far" : "The checks"));
      const ul = el("ul");
      for (const c of list) {
        const li = el("li", trial && c.kind === trial.kind ? "is-now" : null);
        const kind = c.answer.replace(/^so far /, "").replace(/,.*$/, "").replaceAll(" ", "-").replace("'", "");
        li.append(el("span", "w-check-ask", c.ask), el("span", `w-answer is-${kind}`, c.answer));
        ul.append(li);
      }
      box.append(ul);
      parts.push(box);

      if (!trial) {
        const v = el("div", "w-verdict");
        v.append(el("p", "w-caption", `The verdict for ${state.input}`), el("p", "w-category", finding.category), el("p", "w-say", said(finding)));
        const reason = why(finding.category, list, run.reader || d.reader || "Gemma");
        if (reason) v.append(el("p", "w-reason", reason));
        const words = el("details", "w-words");
        words.append(el("summary", null, "In Gadfly's words"));
        const ul2 = el("ul");
        for (const e of finding.evidence) ul2.append(el("li", null, rich(e)));
        for (const o of finding.obligations) {
          const li = el("li", "is-open", el("span", "w-open", "Still open"));
          li.append(" ", rich(o));
          ul2.append(li);
        }
        words.append(ul2);
        v.append(words);
        if (run.findings.length > 1) {
          const all = el("div", "w-cases");
          all.append(el("p", "w-caption", `Across all ${run.findings.length} cases, this run reads ${run.overall}`));
          for (const f of run.findings) {
            const chip = el("button", "w-case", `${f.input} ${f.category}`);
            chip.type = "button";
            chip.setAttribute("aria-pressed", String(f.input === state.input));
            chip.addEventListener("click", () => {
              state.input = f.input;
              inputSelect.value = f.input;
              stop();
              show(last(), false);
            });
            all.append(chip);
          }
          v.append(all);
        }
        parts.unshift(v);
      }
      side.replaceChildren(...parts);
    }

    const group = root.dataset.group
      ? fetchFrame(root.dataset.group).then((index) => {
          for (const x of index.examples) frameSelect.append(new Option(x.title, x.stem));
        })
      : Promise.resolve();
    if (dollBox) {
      Promise.all([fetchScript("dolls.js"), fetchFrame(root.dataset.dolls)])
        .then(([, data]) =>
          staged(() => {
            hooks = window.gadflyDolls.stage(dollBox, {
              select(stem) {
                story.on = false; // a doll picked by hand ends the sequence
                load(stem);
              },
              hold() {
                story.on = false; // a walked doll picked: the view holds still
                stop();
              },
            }, data);
            story.order = data.order;
            story.on = true;
            if (state.data) {
              hooks.frame(state.stem, state.data);
              show(state.step, false);
            }
          }),
        )
        .catch(() => dollBox.remove()); // the frames still play without the dolls
    }
    group
      .catch(() => {}) // the page's own examples still play
      .then(() => {
        const wanted = asked.get("example");
        const known = [...stems, ...[...frameSelect.options].map((o) => o.value)];
        const first = stems[0] ?? frameSelect.options[0]?.value;
        if (known.includes(wanted)) load(wanted, Number(asked.get("run") || 1) - 1, true);
        else if (first) load(first, 0, true);
      });
  }

  for (const root of document.querySelectorAll(".gadfly-watch")) mount(root);
})();
