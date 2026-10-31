# Troubleshooting

Each problem is listed by what Gadfly prints, grouped by where you meet it. A
message from the command line starts with `gadfly:`, and a call that comes back
without an answer is an opening, which `run` counts and names.

---

### Setting up a battery

| You see | What it means, and what to do |
| --- | --- |
| `gadfly: no eGemma key: set EGEMMA_API_KEY_FILE or EGEMMA_API_KEY` | No key is set, and no call was made. Put eGemma's key in a file and name it in `EGEMMA_API_KEY_FILE`, or set `EGEMMA_API_KEY`. |
| `gadfly: EGEMMA_API_KEY_FILE names an empty file` | The file is there but holds no key. Write the key into it. |
| `gadfly: [Errno 2] No such file or directory: ...` | `EGEMMA_API_KEY_FILE` names a file that does not exist. Check the path. |
| `gadfly: no router token: set CODEX_ROUTER_TOKEN or install the router` | The `unified` battery found no token in `CODEX_ROUTER_TOKEN` or in the router's settings file, `~/.codex/unified-router/openrouter.env`. Install the router, or set the variable. |
| `openings: 10 of 10 calls, most often "eGemma could not be reached: ConnectionRefusedError" (10)` | Nothing answers at `EGEMMA_URL`, by default `http://127.0.0.1:8000`. Start eGemma, or point the variable at it. The calls were spent, so run again into a new file. |
| `"the router could not be reached: ..."` or `"the evaluator could not be reached: ..."` | The same for the router, at `http://127.0.0.1:18766`, or for your evaluator, at the frame's `battery.url`. |
| `"eGemma answered 401"` or `"the router answered 401"` | The key or the token is wrong. |
| `"eGemma answered 503 after 3 retries"` | eGemma stayed busy or has no model loaded; the battery waits and retries before it gives up. Check eGemma's own log. |
| `"router diagnostic: openrouter-data-policy"` | No OpenRouter endpoint for that model keeps no data, and the frame does not consent to one that trains on its inputs. Choose another model, or pin endpoints with `battery.endpoints`. |

---

### Running a frame

| You see | What it means, and what to do |
| --- | --- |
| `gadfly: --battery is module:Class (for example midwife.batteries.egemma:EGemma)` | Name the class after a colon. |
| `gadfly: No module named '...'` | The battery's module is imported from the current directory. Run from the folder that holds it, or check its name. |
| `gadfly: this frame asks for the egemma battery, not unified` | A frame names its battery in `battery.kind`, and another battery is another frame. Pass the one it names. |
| `stopped: the plan needs 40 calls; the budget allows 10` | `--calls` is below what the plan needs, and nothing was spent. `gadfly plan` shows the count. |
| `gadfly: records.jsonl exists: kept records are never written over` | Choose a new `--out`. To finish a stopped run, pass its file as `--kept` with a new `--out`. |
| A run stopped partway, by Ctrl-C or a crash | Every record made so far is in its file. Run again with that file as `--kept` and a new `--out`, and only the missing calls are made. |

---

### Reading a verdict

| You see | What it means, and what to do |
| --- | --- |
| `gadfly: a record belongs to another frame` | The records were made under another frame: another file, or this one edited after the run, since any change makes a new hash. Read them with the frame they were made under. |
| `gadfly: a baseline record was made on another body` | The trial's text differs from the one the record was made on. The frame, or the way Gadfly plans it, changed after the run. |
| `gadfly: two records for ... run ...` | The same call is kept twice, usually from two files joined into one. Keep one of them. |
| `unresolved`, with `no agreed level in: ...` | Fewer than `agree` answers matched in those trials: the reader split, or the calls came back as openings. The `openings` line of `run` says which. |
| `unresolved`, with only open checks beside it | Every trial agreed, but a check the category needs is still open. [Reading a verdict](reading-a-verdict.md) explains `carriage` and each check. |

---

### Writing a frame

`gadfly check-frame` names each refusal and where it is, without a call.
[Write a frame](write-a-frame.md#troubleshooting) lists the common ones and how
to fix each.

---

### Developing Gadfly

| You see | What it means, and what to do |
| --- | --- |
| `1 transcript(s), copies or references differ` | A page quotes output the code no longer prints, or a copy, frame view or API section is stale. Run `uv run python tools/doc_outputs.py --write`. |
| `tests/test_kept_runs.py` fails | A change to the verdict rules changed a kept run's category. That is a method change: say so in the docs, and never edit the kept runs. |
| `npm run docs:build` fails on a dead link | A link names a page that does not exist. `test_every_link_lands` finds it, with any heading anchor that does not. |
