// The watch view: one kept run, played one trial at a time. On the left is
// exactly what the reader read in that trial, with what the trial hid or
// changed marked; on the right, its answers, how they compare with the first
// answer, and the checks filling in until the verdict. The data is written by
// tools/watch_data.py from the kept runs; every string in it is set as text.
(() => {
  const script = document.currentScript;
  const base = new URL("../assets/watch/", script.src);
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const STEP_MS = 3800;

  // What each kind of trial does, and what it asks, in plain words.
  const TRIALS = {
    baseline: ["Baseline", "Ask with everything there.", "What does Gemma say?"],
    repeat: ["Repeat", "Ask again, with nothing changed.", "Is it the same answer?"],
    ablation: ["Ablation", "Hide the line under test.", "Does the answer change?"],
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
  // frame never ran their trial.
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

  // Names in the frames' prose (calls, files, snake_case names) are set as code.
  const CODE = /[\w.]+\([^()]*\)|[\w./-]+\.(?:py|txt|md|json|toml|ya?ml)\b|\b(?:[a-z][a-z0-9]*\.)*[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g;
  const cache = new Map();

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
  // ..., hold if ...", each answer in its colour.
  function key(d, slot) {
    const p = el("p", "w-key");
    const at = d.instruction.indexOf("Answer ");
    if (at < 0) {
      p.append("Gemma must answer with one word: ");
      d.labels.forEach((label, i) => p.append(i ? ", " : "", word(label, slot)));
      return p;
    }
    const sentence = d.instruction.slice(at + "Answer ".length);
    const pattern = new RegExp(`\\b(${d.labels.map(escape).join("|")})(?= if )`, "g");
    p.append("Gemma must answer ");
    let last = 0;
    for (const match of sentence.matchAll(pattern)) {
      p.append(sentence.slice(last, match.index), word(match[0], slot));
      last = match.index + match[0].length;
    }
    p.append(sentence.slice(last));
    return p;
  }
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

  async function fetchFrame(stem) {
    if (!cache.has(stem)) {
      cache.set(
        stem,
        fetch(new URL(`${stem}.json`, base)).then((r) => {
          if (!r.ok) throw new Error(`${stem} (${r.status})`);
          return r.json();
        }),
      );
    }
    return cache.get(stem);
  }

  // The decision labels take the categorical slots in the frame's order;
  // "unclear" is the neutral grey.
  function slots(labels) {
    const map = {};
    let next = 0;
    for (const label of labels) map[label] = label === "unclear" ? "u" : "abc"[next++];
    return map;
  }

  function trialName(trial) {
    const [name] = TRIALS[trial.kind] || [cap(trial.kind)];
    const n = trial.id.match(/-(\d+)$/);
    return n ? `${name} ${n[1]}` : name;
  }

  // ---- what one trial's answers say, against the first answer
  // How the calls of one trial answered, as one line: the answer word itself,
  // in its colour, and how many times it came.
  function agreement(calls, level, agree, slot) {
    const tally = new Map();
    for (const c of calls) tally.set(c.answer, (tally.get(c.answer) || 0) + 1);
    const line = el("p", "w-agree");
    if (level == null) {
      line.append("The answers split, ");
      [...tally].sort((a, b) => b[1] - a[1]).forEach(([label, n], i, all) => {
        line.append(word(label, slot), ` ${n} ${n === 1 ? "time" : "times"}${i < all.length - 1 ? " and " : ". "}`);
      });
      line.append(`Gadfly needs ${agree} alike, so none counts.`);
      return line;
    }
    const n = tally.get(level);
    line.append(word(level, slot), n === calls.length ? ` all ${n} times.` : ` ${n} times out of ${calls.length}, enough to count.`);
    return line;
  }

  function comparison(trial, level, first, data) {
    if (trial.kind === "baseline") return "Every other trial is compared with this answer.";
    if (level == null || first == null) return "With no agreed answer here, there is nothing to compare.";
    const was = `With everything there, Gemma said ${first}.`;
    if (level === first) {
      const still = {
        repeat: "Asked again, it says the same.",
        ablation: "The line was not needed for this answer.",
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
      cumulative: "Hiding more changed it.",
      sham: "A harmless cut changed it, which it should not.",
      presentation: "New names changed it, which they should not.",
      placement: "Moving a line changed it, which it should not.",
      inversion: "Turning the line around turned the answer, as it should.",
      "input-inversion": "Turning what is asked around changed the answer, as it should.",
      bypass: "Hiding the link changed it too.",
      control: "So Gemma does change its mind when it should.",
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

  function why(category, list) {
    if (category !== "unresolved") return null;
    if (list.some((c) => c.answer === "can't tell")) return "Some answers split, so a check cannot be read.";
    const bypass = list.find((c) => c.kind === "bypass");
    if (bypass?.answer === "not tested") return "Nobody tried hiding the link, so one check was never made.";
    if (list.find((c) => c.kind === "control")?.answer === "no") {
      return "Gemma never changed its mind, so Gadfly cannot tell whether it is reading at all.";
    }
    if (bypass?.answer === "no") return "Hiding the link did not change the answer, so something else may carry it.";
    if (list.some((c) => c.answer === "not tested")) return "One check was never made.";
    return "One check is still open.";
  }

  function mount(root) {
    const stems = root.dataset.frames.split(",").map((s) => s.trim());
    const state = { data: null, input: null, run: 0, step: 0, timer: null };

    // ---- pickers
    const bar = el("div", "w-bar");
    const frameSelect = el("select", "w-select");
    frameSelect.setAttribute("aria-label", "Example");
    for (const stem of stems) frameSelect.append(new Option(stem, stem));
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

    // ---- the player, and the strip of trials
    const player = el("div", "w-player");
    const back = el("button", "w-btn", "Back");
    const play = el("button", "w-btn w-play", "Play");
    const next = el("button", "w-btn", "Next");
    for (const b of [back, play, next]) b.type = "button";
    player.append(back, play, next);
    bar.append(field("Example", frameSelect), caseField, field("Run", runs), player);
    const ask = el("div", "w-ask");
    const strip = el("div", "w-strip");
    const top = el("div", "w-top");
    top.append(strip);

    // ---- the two panels
    const stage = el("div", "w-stage");
    const doc = el("section", "w-doc");
    const side = el("section", "w-side");
    stage.append(doc, side);
    root.replaceChildren(bar, ask, top, stage);

    frameSelect.addEventListener("change", () => load(frameSelect.value));
    inputSelect.addEventListener("change", () => {
      state.input = inputSelect.value;
      restart();
    });
    back.addEventListener("click", () => {
      stop();
      show(Math.max(0, state.step - 1), true);
    });
    next.addEventListener("click", () => {
      stop();
      show(Math.min(last(), state.step + 1), true);
    });
    play.addEventListener("click", () => (state.timer ? stop() : start()));

    const last = () => state.data.trials.length; // the step after the last trial is the verdict

    async function load(stem) {
      stop();
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
      state.run = 0;
      inputSelect.replaceChildren(...d.inputs.map((x) => new Option(x.id, x.id)));
      caseField.hidden = d.inputs.length < 2;
      runs.replaceChildren(
        ...d.runs.map((_, i) => {
          const b = el("button", "w-run", String(i + 1));
          b.type = "button";
          b.addEventListener("click", () => {
            state.run = i;
            restart();
          });
          return b;
        }),
      );
      restart();
    }

    function restart() {
      stop();
      [...runs.children].forEach((b, i) => b.setAttribute("aria-pressed", String(i === state.run)));
      show(0, true);
      start();
    }

    function start() {
      if (state.step >= last()) show(0, true);
      play.textContent = "Pause";
      state.timer = setTimeout(function tick() {
        if (state.step >= last()) return stop();
        show(state.step + 1, true);
        state.timer = setTimeout(tick, reduced ? STEP_MS / 2 : STEP_MS);
      }, reduced ? STEP_MS / 2 : STEP_MS);
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
      const slot = slots(d.labels);
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
      strip.querySelector('[aria-current="step"]')?.scrollIntoView({ block: "nearest", inline: "nearest" });

      const trial = atVerdict ? null : d.trials[step];
      drawAsk(d, slot);
      drawDoc(trial, d);
      drawSide(trial, d, run, finding, slot, first, played);
    }

    // the question, and the words Gemma may answer with and what each means
    function drawAsk(d, slot) {
      const question = d.inputs.find((x) => x.id === state.input).text;
      // the role and the key together are the whole instruction, word for word
      const role = d.instruction.slice(0, Math.max(0, d.instruction.indexOf("Answer "))).trim();
      ask.replaceChildren(
        el("p", "w-caption", "The question"),
        el("p", "w-question", rich(question)),
        ...(role ? [el("p", "w-role", role)] : []),
        key(d, slot),
      );
    }

    // the left panel: the reader's prompt, with this trial's changes marked
    function drawDoc(trial, d) {
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

      doc.replaceChildren(
        el("p", "w-caption", trial ? "What Gemma read in this trial" : "What Gemma read, with everything there"),
        lines,
        el("p", "w-asked", plain(question, marks)),
      );
    }

    // the right panel: this trial's answers and what they show, then the checks
    function drawSide(trial, d, run, finding, slot, first, played) {
      const parts = [];
      if (trial) {
        const [, does, asks] = TRIALS[trial.kind] || ["", trial.kind, ""];
        const head = el("div", "w-head");
        head.append(
          el("p", "w-caption", `${trialName(trial)}, trial ${d.trials.indexOf(trial) + 1} of ${d.trials.length}`),
          el("p", "w-does", does),
          el("p", "w-asks", asks),
        );
        const calls = run.calls.filter((c) => c.input === state.input && c.trial === trial.id).sort((a, b) => a.n - b.n);
        const level = finding.levels[trial.id];
        const answers = el("div", "w-answers");
        answers.append(el("p", "w-caption", `Gemma answered`), agreement(calls, level, d.agree, slot));
        const compare = el("p", "w-compare", comparison(trial, level, first, d));
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
        v.append(el("p", "w-caption", `The verdict for ${state.input}`), el("p", "w-category", finding.category), el("p", "w-say", SAY[finding.category] || ""));
        const reason = why(finding.category, list);
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

    load(stems[0]);
  }

  for (const root of document.querySelectorAll(".gadfly-watch")) mount(root);
})();
