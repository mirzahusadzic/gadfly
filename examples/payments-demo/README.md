# The payments demo's kept runs

The frames and runs here are copied byte for byte from the tendora
repository, commit 41fb275, folder `evidence/payments-demo`, with that
repository's `NOTICE`, also copied here; they are under the Apache License,
Version 2.0 (`LICENSE` at this repository's root). Its reports are not
copied: Gadfly reads each verdict again from the frame and its runs.

- `frames/` and `runs/`: the payments demo's 31 questions, each read once by
  Tendora's engine (`tendora-*`) and once by Gemma 4 (26B-A4B,
  instruction-tuned) served by eGemma at temperature 0.7 (`gemma-*`). Every
  record names its frame's hash.
- `gemma-temperature-0/`: the same Gemma frames at temperature 0. Each differs
  from its twin by its battery line alone.
- `predictions/`: what each trial of each frame was predicted to give,
  written with each frame before its first call; they are not in the tendora
  repository's folder.

Like every kept run here, they never change. `gadfly report FRAME RECORDS`
reads any verdict back with no engine, model or network, and
[the demo page](../../docs/demo.md) plays them.
