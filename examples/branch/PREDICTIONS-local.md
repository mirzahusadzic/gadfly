# Third local run: predictions

Written before any call. Run 2 read carried, but its maker never thought:
the eGemma server had lost the start of every prompt in its window layers
(fixed in eGemma f360e9f, which the server on :8000 now runs). This run is
run 2 with that one change: the same frame, 22-local.json, the same
Gadfly code (a72fe76), `--output-tokens 8000`, 24 calls.

- **Verdict:** carried, every cell 3 of 3 as in run 2 and one turn.
- **Served:** "made by <gemma>@<rev> (thinking on), read by <gemma>@<rev>
  (thinking off)" on every record. **No opening.**
- **Making:** two steps, each after a thought that runs to its 3,488-token
  room (about a minute each), so the run takes about 2 to 3 minutes.
- **Steps:** the method's parts in at most eight lines, naming the belief
  to keep out.
