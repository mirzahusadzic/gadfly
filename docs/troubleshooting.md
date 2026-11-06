# Troubleshooting

Each problem is listed by what Gadfly prints. A refusal prints what the last
line of a Python traceback would, its class, which says what to fix and gives
the exit status, and what went wrong, then on the next line what to do; a
warning, for what a run did not do as asked though it went on, prints the same
way. With `--json` a refusal is one object on standard error and a warning sits
under `warnings` in the run's result, as each table below can show on the site.

---

### Exit statuses

The status says what happened without a word read, and the first line of a
refusal says it in words, so a script, a person and another model read it
alike.

| Exit | Type | What it means |
| --- | --- | --- |
| 0 | none | done |
| 1 | `OpeningWarning` | every call came back with no answer, so nothing was read |
| 2 | `UsageError` | the command or the call asks for what cannot be done, and nothing was spent |
| 3 | `StoppedWarning` | a run stopped before its plan's end, so its records are partial and `--kept` finishes them; or `firm` stopped before its verdict was firm |
| 4 | `FrameError` | the frame is refused |
| 5 | `RecordsError` | records or a report are not this frame's run |
| 6 | `BatteryError` | the battery cannot be made, set up or reached |
| 7 | `FileNotFoundError`, `FileExistsError`, `PermissionError`, `IsADirectoryError`, `NotADirectoryError` | a file or a folder cannot be read or written |
| 70 | any other | a bug in Gadfly, which prints its traceback |
| 130 | `KeyboardInterrupt` | stopped by Ctrl-C |
| 141 | none | the program reading its output stopped reading (`\| head`), so the command ended quietly, as any Unix tool does |

---

### UsageError

The command or the call asks for what cannot be done, and nothing was spent.
When Gadfly prints what to do, it opens the second column.

| You see | What to do |
| --- | --- |
| `UsageError: the plan needs 40 calls; the budget allows 10` | `gadfly plan shows the calls a whole run needs`. `--calls` is below the plan, so no file was made. |
| `UsageError: unrecognized arguments --stop` | `gadfly run --help shows its arguments`. Flags are named in full, since a shortened one would change meaning when a longer one is added. |
| `UsageError: --battery is module:Class (for example midwife.batteries.egemma:EGemma)` | Name the class after a colon. |
| `UsageError: the plan has no trial 'controll'` | `gadfly plan lists its trials`. Name one of them with `--only`. |
| `UsageError: battery 'egemma' does not take calls at once` | Leave out `--parallel`, as this battery takes one call at a time. |
| `UsageError: - reads standard input, which is a terminal` | `pipe the file in, or name it`. |
| `UsageError: standard input is read once` | `name - for one file at most`. |
| `UsageError: --json and --out - both print to standard output` | `choose a file for --out`. |
| `UsageError: the token budget (0) is spent` | `--token-budget must cover one call's --output-tokens`. Nothing was spent and no file made. |
| `UsageError: frame 'Mirza' has no span 'nope'` | Name with `--span` one of the spans of the frame `--from` names, by its id. |
| `UsageError: frame 'Mirza' offers no kind for its decision to climb as` | `name one under offers`. A decision climbs as a piece of the kind its frame offers; without `offers` it climbs as none. |
| `UsageError: frame 'Kiran' has no label 'maybe'` | Name with `--decision` one of the frame's labels. |
| `UsageError: missing one of --span, --decision` | `gadfly walk --help shows its arguments`. The piece is one of the spans of the frame `--from` names, or its decision read as a label: name one with `--span` or `--decision`, not both. `successor` also takes `--text`, so it says `missing one of --span, --decision, --text`. |
| `UsageError: missing --from` | `name the frame the piece was found in`. `successor` was given `--span` or `--decision` without the frame they come from. |
| `UsageError: missing --kind` | `a --text piece fills only a hole of its own kind`. Name its kind with `--kind`, as the hole the piece fills names it. |
| `UsageError: --from and --text cannot be given together` | `a piece is a text of its own, or one found in the frame --from names`. Give `--text` and `--kind` alone, or `--from` with `--span` or `--decision`. |
| `UsageError: --kind is given without --text` | `a piece found in a frame is of its span's kind, or the kind its frame offers`. Leave out `--kind`, or give the piece as `--text`. |
| `UsageError: --decision and --span cannot be given together` | `gadfly walk --help shows its arguments`. The piece is a span of the frame `--from` names, or its decision: name one. |
| `UsageError: --span and --text cannot be given together` or `UsageError: --decision and --text cannot be given together` | `gadfly successor --help shows its arguments`. The piece is a span or the decision of the frame `--from` names, or a text of its own with `--kind`: name one. |
| `UsageError: missing --battery` or `UsageError: missing frames` | `gadfly run --help shows its arguments`. A flag or a file the command needs was not given; its help names each, and a mistyped flag is named as unrecognized instead. |
| `UsageError: frame 'Kiran' has no span 'nope' to place the piece after` | `name one of its spans, the line the piece amends`. `--after`, or `after` in Python, names a span of the frame the piece fills. |
| `UsageError: frame 'Kiran' has no hole 'nope'` | Name with `--hole` one of the frame's `holes`; `gadfly walk` names the holes a piece fits. |
| `UsageError: hole 'paper' is of kind 'kiran-paper', and the piece is of kind 'paint'` | A piece fills only a hole of its own kind. Choose the piece the walk found fitting, or another hole. |
| `UsageError: --set 'standing' is given 'three', which is not JSON` | `give the value as JSON, quoted for the shell`. A text is JSON in double quotes, so the shell needs them kept, as in `'"text"'`. |
| `UsageError: a run needs 24 calls; --calls allows 10` | `gadfly plan shows the calls a run needs`. `firm` asks whole runs only, and with no run kept it had nothing to read, so nothing was spent and no file made. |
| `UsageError: --firm is a share above 0, up to 1` or `UsageError: firm is a share above 0, up to 1` | Give the share of draws that must read each input alike, such as 0.95; the second is `until_firm`'s, in Python. |
| `UsageError: --most is a whole number of runs, at least 1` or `UsageError: most is a whole number of runs, at least 1` | Give the most runs to read, kept ones included; the second is `until_firm`'s, in Python. |
| `UsageError: folder 'runs' keeps 6 runs, more than --most reads` | `raise --most, or move the earliest runs out`. Only the latest run decides, and every run kept is read. |
| `UsageError: kept holds more runs than most lets until_firm read` | `give it the latest runs only, or raise most`. The same, in Python. |
| `UsageError: frame 'Kiran' asks each trial once, so a run has no calls to draw again` | `give it a quorum of 2 or more`. Whether a verdict is firm is read from its calls drawn again, so a frame asked until firm is asked lightly, but more than once a trial. A walk given calls counts each fit's successor so, and a second note names the fit. |
| `UsageError: a walk's budget is a whole number of calls, at least 1` | Give `--calls`, or `calls` in Python, as the calls the walk's fits may take, or leave it out to count nothing. |
| `UsageError: --space is given without --vectors` or `UsageError: space is given without vectors` | `--space names the space to order by, among the vectors --vectors gives`. Give both, or neither; the second is `walk`'s, in Python. |
| `UsageError: file 'vectors.jsonl' is not UTF-8 text` | Save the vectors as UTF-8. In Python, `read_vectors` names them `the text given`, or by the `path` it is given. |
| `UsageError: file 'vectors.jsonl' cannot be read as JSON at line 3` | Correct that line; each line is one JSON object. |
| `UsageError: file 'vectors.jsonl' holds a vector that is not {text, space, values} at line 3` | Give each line exactly `text`, `space` and `values`. |
| `UsageError: file 'vectors.jsonl' keys a vector by 'abc' at line 3, which is no SHA-256` | `text is the SHA-256 of the exact text, 64 lowercase hex digits`. A vector stands for a whole text, named as a span's `source` names it. |
| `UsageError: file 'vectors.jsonl' names space 'e: 128' at line 3, not one plain name` | A space id is a non-empty string of UTF-8 text, with no line break and no colon followed by a space; Gadfly prints it, and only compares it. |
| `UsageError: file 'vectors.jsonl' holds values that are not a list of numbers at line 3` | Give `values` as a non-empty list of numbers. |
| `UsageError: file 'vectors.jsonl' holds text '9f86d081...' in space 'e128' twice, at lines 1 and 4` | `a text has one vector in a space; even the same values twice are refused`. Keep one of them; the vectors are refused whole, never the last taken. |
| `UsageError: the vectors hold 2 spaces, 'e128', 'e768'` | `name the one to order by, since a cosine compares two vectors of one space only`. Give `--space`, or `space` in Python. |
| `UsageError: the vectors hold no vector in space 'e64'` | `they hold 'e128'`. Name one of the spaces the vectors hold. |
| `UsageError: the vectors hold no vector` | `give vectors, or leave them out`. The file is empty, or holds blank lines only. |
| `UsageError: made holds a record where a run belongs` | `give each run's records as a list, made=[records]`. In Python, `walk` takes a crossing's runs, each a list of its records, as `until_firm` takes kept runs. |
| `UsageError: frame 'Kiran' declares most 3, and 5 is asked` | `a frame that declares how many runs it reads is read so; leave most out`. The frame's `standing.most` is part of its hash, so `--most`, or `most` in Python, may only repeat it. |
| `UsageError: --most is given without --calls` | `--most counts the runs each fit may take against the calls --calls gives`. Give both, or neither. |
| `UsageError: a successor that asks the same question is read from its own runs` | `name the folder that keeps them with --runs; gadfly firm makes them`. Only a reframing is read against no category, with no runs. |
| `UsageError: folder 'runs' keeps no run of the successor` | `gadfly firm asks it, and keeps each run there`. A run is a file named by its place, `1.jsonl` and on. |
| `UsageError: file 'withhold.json' is not UTF-8 text` | Save the withhold set as UTF-8. In Python, `read_withhold` names it `the text given`, or by the `path` it is given. |
| `UsageError: file 'withhold.json' cannot be read as JSON` | Correct the file; a withhold set is one JSON object. |
| `UsageError: file 'withhold.json' is not a withhold set` | `a withhold set is a JSON object with the parts always and training, each listing names, lines (SHA-256) or patterns, as lists of strings`. Give only those parts and lists, each string non-empty. |
| `UsageError: file 'withhold.json' lists a line that is no SHA-256` | `each line is the SHA-256 of its normal form, 64 lowercase hex digits`. A line's normal form is its words joined by single spaces; `midwife.withhold.line_sha256` gives it. |
| `UsageError: file 'withhold.json' holds a pattern that is no regular expression` | The note quotes what Python's `re` module said. Correct the pattern, or escape it with `re.escape` to match the text as written. |

---

### FrameError

The frame is refused as written, and Gadfly never repairs it.
`gadfly check-frame` prints each refusal as a `FrameError` and where it is,
without a call, and [Write a frame](write-a-frame.md#troubleshooting) lists the
common ones.

| You see | What to do |
| --- | --- |
| `FrameError: file 'frame.json' is not JSON at line 2, column 1 (Expecting value)` | Correct the file at that place; a frame is plain JSON. |
| `FrameError: file 'frame.json' is not UTF-8 text` | Save the file as UTF-8. |
| `FrameError: span 'r2' does not hash to its source` | `its text hashes to '...'; it must be byte for byte the text that crossed`. The span's text was changed after it crossed, or `source.sha256` names another text. |
| `FrameError: span 'r2' names a source that is not {sha256, from}` | `sha256 is 64 lowercase hex digits; from, if given, says where the text came from`. |
| `FrameError: the body has no span 'r9'` | `anchors name spans of the body`. Name as anchors only the ids of its spans. |
| `FrameError: required influence is tested by ablation, and none is declared` | `set ablation to true`. |
| `FrameError: frame 'Kiran' rests on its holes alone, so no trial has an anchor to cut` | `fill a hole first, in the frame midwife.recoil.successor drafts`. A frame whose anchors are all holes is walked by [recoil](recoil.md), never planned or run. |
| `FrameError: the body holds no span` | `a frame's evidence is one span or more`. Holes stand in for anchors, never for the evidence. |
| `FrameError: the body has no span 'nope'` | `the successor of frame 'Kiran' is checked as any frame is`. `gadfly successor` checks its draft before it prints or writes it, and a `--set` value made it what the parser refuses: correct that value, or leave it out and finish the draft by hand. |
| `FrameError: standing says quorum, agree and, optionally, stable and most` | Give `standing` only those keys. |
| `FrameError: standing.most is a whole number of runs, at least 1` | `it is the most runs asking until firm reads; leave it out for the default`. |
| `FrameError: holes name span 'paper', which the body has` | `a hole is what the body lacks`. Give the hole an id no span has. |
| `FrameError: holes lists what the body is missing, each an id and a kind` | `a hole may also say what it is read for, under about, and its salience`. Each hole is an object with a non-empty `id` and `kind`, and may add a non-empty `about` and `salience`, nothing else. |
| `FrameError: hole 'paper' has salience 'maybe', which is neither consider nor defer` | `consider, the default, asks a fit of it; defer keeps the fit unasked`. |
| `FrameError: frame 'refund' would send withheld text, a name, in trial 'baseline' for input 'r1'` | `its battery may train on what it reads; read it with a reader that keeps no data, or take the text out of the frame`, or, for the `always` part, `no call may carry it`. The message names where and what kind, never the text. `gadfly check-frame --withhold` lists every prompt that holds some. |

---

### RecordsError

The records, or a report, are not what this frame's run made, so no verdict is
read from them.

| You see | What to do |
| --- | --- |
| `RecordsError: a record belongs to another frame` | The records were made under another frame: another file, or this one edited after the run, since any change makes a new hash. Read them with the frame they were made under. |
| `RecordsError: a record of trial 'baseline' was made on another body` | The trial's text differs from the one the record was made on. The frame, or the way Gadfly plans it, changed after the run. |
| `RecordsError: a record is a JSON object` or `RecordsError: a record's trial is not a str` | A line of the records file is not a record Gadfly wrote: another file, or one edited by hand. |
| `RecordsError: file 'records.jsonl' is not JSON at line 3, column 1 (Expecting value)` | That line is not a record; the file was cut short or edited. |
| `RecordsError: a record's usage counts are not whole numbers` | A run keeps usage as whole counts by name, so something else wrote this record. |
| `RecordsError: a record's served is not a str` | The same for what the battery said it served. |
| `RecordsError: file 'records.jsonl' is not UTF-8 text` | The file was written by another tool or edited in another encoding. Save it as UTF-8. |
| `RecordsError: two records for input 'pr', trial 'baseline', run 2` | The same call is kept twice, usually from two files joined into one. Keep one of them. |
| `RecordsError: a kept record of trial 'baseline' was made from another prompt` | A record passed as `--kept`, or kept in a `--runs` folder, was made with a prompt this frame does not plan for that call. Resume only from the records this frame's own run made. |
| `RecordsError: file 'kept.jsonl' holds a lone surrogate at line 3` | `no file can hold it; correct or drop that record, then run again`. That record holds text, often from another tool, that cannot be written back, and nothing was spent. |
| `RecordsError: file 'runs/3.jsonl' holds 1 of a run's 24 calls` | `a run cut short is never read as firm; move it out of the folder`. A battery, a budget or Ctrl-C cut that run short; `firm` reads whole runs only. |
| `RecordsError: a kept run is not whole, so its verdict cannot be read as firm` or `RecordsError: a kept run holds no records` | `give whole runs only, and leave out one that stopped short`. The same, from `until_firm` in Python, which takes each run's records as a list. |
| `RecordsError: a made run holds no records` | `give each run's records as a list`. A `--made` file, or a run given to `walk` as `made` in Python, is one run of a crossing frame. |
| `RecordsError: a made record names frame '7e1c0a9d...', which is not among the frames given` | `give the crossing frame whose records they are`. A walk climbs to a crossing only as one of its frames. |
| `RecordsError: frame 'rollback-from-cause' is no crossing, so its records made no artefact` | `give the records of a crossing frame, whose battery kind is crossing`. Another battery's `raw` is its reader's answer, whatever it holds, so it links no frame. |
| `RecordsError: the records of frame 'rollback-from-cause' hold no artefact its maker made` | `give the records of a crossing frame, whose maker made one for each call`. The records are another battery's, or every call opened before its maker made anything. |
| ``RecordsError: a portfolio reads `gadfly report --json` documents, and this is not one`` | Each file `portfolio` reads is the output of `gadfly report --json`. |

---

### BatteryError

The battery cannot be made, cannot serve this frame as it is set up, or cannot
reach what it needs, and no call was made.

| You see | What to do |
| --- | --- |
| `BatteryError: no eGemma key` | `name a file that holds it in the environment variable EGEMMA_API_KEY_FILE, or set EGEMMA_API_KEY`. |
| `BatteryError: file '/Users/you/.egemma/key' is empty` | `the environment variable EGEMMA_API_KEY_FILE names it; write eGemma's key into it`. |
| `BatteryError: the router takes no data policy` | `update the router, so that each call reaches only endpoints that keep no data`. The `unified` battery sends each call under the router's deny data policy, and the router's `GET /health` does not list it. |
| `BatteryError: the router at 'http://127.0.0.1:18766/health' could not be asked what it takes` | `start the router, or install it`. The `unified` battery asks the router, before any call, whether it takes the deny data policy. |
| `BatteryError: the router takes no endpoint pins` | `update the router, or leave battery.endpoints out`. The `unified` battery pins a frame's endpoints through the router's own header, and the router's `GET /health` does not list it. |
| `BatteryError: battery.endpoints lists 1 to 16 endpoint tags` | `each a tag the router knows, with no comma, space or control character in it`. |
| `BatteryError: the router takes no fallback policy` | `update the router, or leave battery.fallback out`. The `unified` battery keeps a Claude model's calls on Anthropic's API through the router's own header, and the router's `GET /health` does not list it. |
| `BatteryError: the router takes no thinking budget` | `update the router, or leave battery.thinkingBudget out`. The router's `GET /health` does not list thinking budgets. |
| `BatteryError: battery.fallback is 'none' or left out` | The one policy the router takes is `none`, which keeps a Claude model's calls on Anthropic's API. |
| `BatteryError: battery.thinkingBudget is a whole number of tokens from 1,024 to 999,999` | Anthropic takes a budget from 1,024 tokens. Write it as a number, not a string. |
| `BatteryError: battery.fallback applies only to an anthropic/ model` | `the router keeps only Claude's calls on Anthropic's API; leave it out`. The same holds for `battery.thinkingBudget`. |
| `BatteryError: battery.reasoning and battery.thinkingBudget cannot both be set` | `a thinking budget replaces the effort, which the router then does not send; keep one`. |
| `BatteryError: battery.thinkingBudget 2048 is not below each answer's cap of 64 tokens` | `raise --output-tokens above the budget, or lower the budget`. The cap holds the thinking and the answer both. In a crossing, a note says which side's share is too small. |
| `BatteryError: no router token` | `set the environment variable CODEX_ROUTER_TOKEN, or install the router`. The `unified` battery found no token in the variable or in the router's own settings file. |
| `BatteryError: this frame asks for battery 'egemma', not 'unified'` | A frame names its battery in `battery.kind`, and another battery is another frame. Pass the one it names. |
| `BatteryError: 'midwife.frame:parse' is not a battery` | `a battery has a name, check() and observe()`. The name after the colon is found, but it is not a battery class or object. |
| `BatteryError: module 'tests.fixtures.refund' has no 'NoSuchReader'` | The module was found, but not the class named after the colon. Check its spelling and case. |
| `BatteryError: module 'mine' could not be imported` | `it said "No module named 'mine'"`. The battery's module is imported from the current directory. Run from the folder that holds it, or check its name. |
| `BatteryError: battery 'mine:Reader' could not be made` | `it said "__init__() missing 1 required positional argument 'key'"`. The class was found, but making it with no arguments failed, in its own words. A battery the command line makes takes none: read what it needs from the environment or a file. |
| `BatteryError: the evaluator's address must not hold a user or password` | A battery's address names a user or a password. Gadfly refuses it without repeating it; take the credentials out of the address. |
| `BatteryError: the evaluator's address 'http://127.0.0.1:99999' has no valid port` | `a port is a number from 0 to 65535`. |
| `BatteryError: battery.timeout is a number of seconds, up to 3600` | The `local-json` battery's whole-call deadline is missing a positive number, or asks for more than an hour. |
| `BatteryError: battery.reasoning is true or false` | The `egemma` battery reads `"reasoning": true` to let Gemma think first; Gemma has no levels. |
| `BatteryError: battery.reasoning is one of none, minimal, low, medium, high, xhigh, max` | The `unified` battery passes `battery.reasoning` to the model as an effort, one of these words. |
| `BatteryError: battery.readings is 'tab', a reading after each statement's first TAB` | The `tendora` battery's `readings` flag takes one value, `"tab"`: each statement line is its text, a TAB, then its reading. Leave the key out to send the statements alone. |
| `BatteryError: span 's2' has nothing before its TAB in trial 'presentation', but each statement's reading follows its text` | With `"readings": "tab"`, a span holds its statement, a TAB, then its reading; this one has nothing on one side of its TAB, so no call was made. Write both sides, or no TAB for a statement sent without a reading. |
| `BatteryError: battery.reader names kind 'egemma', not 'unified'` | `this crossing was made with another; make one with Crossing(maker, reader)`. `Crossing()` makes and reads through the router; for another maker or reader, make the crossing in Python and name it with `--battery yourmodule:crossing`. |
| `BatteryError: input 'q1' holds the line that parts a body from its input` | `the maker reads what comes before the last '---' line; keep such lines out of inputs and renamings`. |
| `BatteryError: battery.maker.instruction says what the maker writes` | The `crossing` battery's maker line has no instruction of its own to write the artefact by; the frame's instruction is the reader's. |

---

### File errors

A file or a folder the command names cannot be read or written, and nothing
was spent. These are Python's own errors, said in plain words.

| You see | What to do |
| --- | --- |
| `FileNotFoundError: file 'frame.json' does not exist` | Check the path, or the file that the environment variable `EGEMMA_API_KEY_FILE` names. |
| `FileNotFoundError: folder 'runs' does not exist` | `make it, or choose another --out`. |
| `FileNotFoundError: folder 'kiran-runs' does not exist` | `make it, or choose another --runs`. `firm` keeps a frame's runs in a folder you make, so that two frames never share one. |
| `FileNotFoundError: folder 'kiran-runs' does not exist` | `name the folder gadfly firm kept the successor's runs in`. `gate` reads the runs `firm` kept. |
| `FileNotFoundError: folder 'kiran-runs' does not exist` | `name the folder gadfly firm keeps the frame's runs in`. `plan --runs` counts the runs `firm` kept there as made. |
| `PermissionError: folder 'kiran-runs' cannot be written` | `choose another --runs`. `firm` adds each new run to the folder. |
| `NotADirectoryError: 'notes.txt' is a file, not a folder` | `--runs names the folder that keeps the frame's runs`. |
| `PermissionError: folder 'runs' cannot be written` | `choose another --out`. The folder is not yours to write. |
| `IsADirectoryError: 'runs' is a folder, not a file` | Name the file in the folder, not the folder. |
| `NotADirectoryError: path 'notes.txt/frame.json' runs through a file, not a folder` | A part of the path that should be a folder is a file. Check the path. |
| `FileExistsError: file 'records.jsonl' exists already` | `kept records are never written over; choose a new --out, or finish it with --kept`. To finish a stopped run, pass its file as `--kept` with a new `--out`. |
| `FileExistsError: file 'kiran.json' exists already` | `a frame is never written over; choose a new --out`. `gadfly successor` writes a new file only; without `--out` it prints the frame. |

---

### KeyboardInterrupt

Ctrl-C stops a run, or `firm`, and every record made so far is already in its file.

| You see | What to do |
| --- | --- |
| `KeyboardInterrupt: stopped by Ctrl-C after 12 calls; they are in file 'records.jsonl'` | `finish with --kept 'records.jsonl' and a new --out`. Only the missing calls are made, and the new file holds the whole run, to report as one. A crash leaves the file the same way. |
| `KeyboardInterrupt: stopped by Ctrl-C after 5 calls; they went to standard output` | `finish with them as --kept and a new --out`. Keep what the pipe received, then finish the run from it. |
| `KeyboardInterrupt: stopped by Ctrl-C after 0 calls, and no record was kept` | Nothing was made and no file written; run it again when you are ready. |
| `KeyboardInterrupt: stopped by Ctrl-C after 24 calls; each run made is whole and kept` | It stopped between two runs, so every file in the folder is a whole run, and `firm` asked again reads them as runs made. |
| `KeyboardInterrupt: stopped by Ctrl-C after 2 calls; the run cut short is in file 'kiran-runs/3.jsonl'` | `a run cut short is never read as firm; move it out of the folder`. The runs before it are whole and kept, and `firm` asked again reads them as runs made. |

---

### OpeningWarning

Calls came back with no answer, as openings: each is kept, and reads as no
answer. The run goes on, and `run` and `firm` exit with 1 only when every
call did.

| You see | What to do |
| --- | --- |
| `OpeningWarning: 10 of 10 calls came back as openings, most often 'eGemma could not be reached (ConnectionRefusedError)' (10 times)` | `nothing was read; run again into a new file once it answers`. Nothing answers at `EGEMMA_URL`, by default `http://127.0.0.1:8000`: start eGemma, or point the variable at it. |
| `OpeningWarning: 24 of 24 calls came back as openings, most often 'the reader could not be reached (ConnectionRefused)' (24 times)` | `nothing was read; ask again once it answers`. `firm` says it for each run it asked, and exits with 1 when every call it made came back so. |
| `"the engine's reply does not say which readings it took"` or `"the engine's reply names other readings than were sent"` | With `"readings": "tab"`, Tendora's engine must list in `served.readings` exactly the statements it was sent a reading for; an engine that does not take readings answered from the bare statements, so no label is read. Run an engine that takes them. |
| `"line 3 of the statements has nothing before its TAB, so the engine was not asked"` | A crossing's maker wrote a statement line with nothing on one side of its TAB, so that call was not sent. The maker's instruction should ask for the text, a TAB, then the reading, on every line. |
| `"the router could not be reached (...)"` or `"the evaluator could not be reached (...)"` | The same for the router, at `http://127.0.0.1:18766`, or for your evaluator, at the frame's `battery.url`. |
| `"eGemma answered 401"` or `"the router answered 401"` | The key or the token is wrong. |
| `"eGemma answered 503 after 3 retries"` | eGemma stayed busy or has no model loaded; the battery waits and retries before it gives up. Check eGemma's own log. |
| `"the router refused model 'ultra-spark/deepseek-v4.1-flash-1017', whose provider trains on its inputs"` | The router's own list says this model's provider trains on its inputs, and the call went under the deny data policy. Choose another model, or name this one under `trainsOnInputs` to send it there. |
| `"Anthropic's API refused the call ('credits'), and the battery line keeps it there"` | With `fallback` or `thinkingBudget` in the battery line, the router keeps a Claude model's calls on Anthropic's API, and Anthropic refused this one for the reason quoted, such as the key, its credits or a spend limit. Fix the key or the account, then run again into a new file. |
| `"the router reports 'anthropic-request-rejected'"` | Anthropic refused the request as written. With `thinkingBudget`, the model takes no budget, as later Claude models think adaptively. Choose a model that takes one, or leave the budget out. |
| `"battery.thinkingBudget 2048 is not below each answer's cap of 64 tokens"` | A call made past `run`, such as a crossing's maker given its half of the cap, had no room for the budget, so no request was made. Raise `--output-tokens`. |
| `"no endpoint that keeps no data serves this model (the router's provider setting); naming it under trainsOnInputs allows one that may train"` | No endpoint the router may use for that model keeps no data, and the frame does not consent to one that trains on its inputs. Choose another model, or pin endpoints with `battery.endpoints`. |
| `"a cap of 64 output tokens leaves no room for a thought beside the answer's 64"` | With `"reasoning": true`, the `egemma` battery keeps 64 of each call's output tokens for the answer. Raise `--output-tokens`, to 4160 for a whole thought; no request was made. |
| `"eGemma answered 422"` | eGemma refused the request as written. With `"reasoning": true`, an eGemma older than its reasoning change does not know the field: update eGemma. |
| `"the maker made nothing ('the call ended incomplete')"` | The `crossing` battery's maker ran out of its half of the cap before the artefact was written, and the reader was not asked. Raise `--output-tokens`, so that half of it holds the maker's thought and its text. |
| `"the reader gave no label ('the call passed its timeout')"` | The `crossing` battery's reader gave no answer to read; its own reason is quoted, as any battery's opening would read. The artefact it was given is kept in the record's raw answer. |
| `"the maker's report of what it spent is not a count of tokens"` | A maker of your own reported its spend as something other than whole, non-negative counts, so the reader was not asked and the call is charged the maker's whole share. |
| `"the maker spent the call's whole cap"` | The maker reported spending all of the call's output tokens, so none were left for the reader. Raise `--output-tokens`. |

---

### StoppedWarning

The run stopped before its plan's end, so its records are partial, and `run`
exits with 3. The records made are kept, and `--kept` finishes them; `firm`
exits with 3 too, its verdict not yet firm.

| You see | What to do |
| --- | --- |
| `StoppedWarning: the run stopped after 3 of 8 calls; the token budget (30) is spent` | `finish with --kept 'records.jsonl' and a new --out`. Raise `--token-budget` first. |
| `StoppedWarning: the run stopped after 2 of 21 calls; the battery stopped the run ('the key was refused')` | `finish with --kept 'records.jsonl' and a new --out`. The battery or its maker raised `StopRun`: its harness failed, not the frame, and the call it stopped left no record. Fix what the reason names, then finish the run. |
| `StoppedWarning: the run stopped after 1 of 8 calls; the battery reported 900 output tokens for a call capped at 64` | `finish with --kept 'records.jsonl' and a new --out`. The battery spent more output tokens on one call than `--output-tokens` allows, and that call's record is kept. A battery that writes before it answers spends tokens on the whole call: set `--output-tokens` to what a whole call may spend. |
| `StoppedWarning: asking stopped after 1 of at most 5 runs, its verdict not yet firm; the budget covers no further run of 24 calls` | `raise --calls or --token-budget, and ask again with the same --runs`. `firm` starts no run its budget cannot cover whole, and the runs it made are kept as runs made. |
| `StoppedWarning: the run stopped after 1 of 24 calls; the battery reported 65 output tokens for a call capped at 64` | `the run cut short is in file 'kiran-runs/1.jsonl'; move it out of the folder`. As for `run`, the battery spent past `--output-tokens`; that run is never read as firm. |

---

### Reading a verdict

A verdict that reads unresolved is a finding, not an error, and `report` exits
with 0.

| You see | What it means, and what to do |
| --- | --- |
| `unresolved`, with `no agreed level in ...` | Fewer than `agree` answers matched in those trials: the reader split, or the calls came back as openings. The run's `OpeningWarning` says which. |
| `unresolved`, with only open checks beside it | Every trial agreed, but a check the category needs is still open. [Reading a verdict](reading-a-verdict.md) explains `carriage` and each check. |

---

### Developing Gadfly

| You see | What it means, and what to do |
| --- | --- |
| `1 transcript(s), copies or references differ` | A page quotes output the code no longer prints, or a copy, frame view or API section is stale. Run `uv run python tools/doc_outputs.py --write`. |
| `tests/test_kept_runs.py` fails | A change to the verdict rules changed a kept run's category. That is a method change: say so in the docs, and never edit the kept runs. |
| `npm run docs:build` fails on a dead link | A link names a page that does not exist. `test_every_link_lands` finds it, with any heading anchor that does not. |
