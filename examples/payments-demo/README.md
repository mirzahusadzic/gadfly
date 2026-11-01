# The payments demo's kept runs

The frames and Gemma's runs here are copied byte for byte from the
[tendora repository](https://github.com/mirzahusadzic/tendora), commit
e7e254ba, folder `evidence/payments-demo`, with that repository's `NOTICE`,
also copied here; they are under the Apache License, Version 2.0 (`LICENSE`
at this repository's root). Tendora's runs equal that folder's in every
field but `raw`, whose reply here keeps only the answer fields, so every
verdict and observation is the same. The folder's reports are not copied:
Gadfly reads each verdict again from the frame and its runs.

- `frames/` and `runs/`: the payments demo's 31 questions, each read once by
  Tendora's engine (`tendora-*`) and once by Gemma 4 (26B-A4B,
  instruction-tuned) served by eGemma at temperature 0.7 (`gemma-*`). Every
  record names its frame's hash.
- `gemma-temperature-0/`: the same Gemma frames at temperature 0. Each differs
  from its twin by its battery line alone.
- `predictions/`: what each trial of each frame was predicted to give,
  written with each frame before its first call; they are not in the tendora
  repository's folder.

Like every kept run here, they are never edited: when the tendora repository
recorded its demo again, the set here was replaced whole, and the earlier set
stays in this repository's history. `gadfly report FRAME RECORDS` reads any
verdict back with no engine, model or network, and [the watch
view](../../docs/examples/watch.md#the-payments-demo) plays them.
