# Run your own

!!! abstract "This step"
    - **Teaches:** the method every example followed, and which trial answers
      which question.
    - **Frame:** yours.
    - **After:** [Paths](paths.md).

## Which trial answers which question

| You want to know whether... | Declare | Step that shows it |
|---|---|---|
| the decision rests on this evidence at all | `ablation` (always there) | [Your first frame](../first-frame.md#2-cut-the-line-ablation) |
| the answer is stable before comparing it | `repeat` | [Your first frame](../first-frame.md#3-ask-again-repeat), [Quorum](quorum.md) |
| any cut would move it, or only this one | `sham` | [Your first frame](../first-frame.md#4-cut-something-harmless-shams) |
| the names matter rather than the meaning | `presentation` | [Your first frame](../first-frame.md#5-rename-presentation) |
| where a line sits matters | `placement` | [Misaligned](misaligned.md) |
| it rests on the evidence through the connection you claim | `bypass`, with `allowed.bypass` | [Bypass](bypass.md) |
| the reader can move at all, so that cooled means something | `control` | [Cooled](cooled.md), [A frame built wrong](built-wrong.md) |
| it rests somewhere else too | `cumulative` | [Cumulative](cumulative.md) |
| it moves the way the promise says | `allowed.ablation` | [Misaligned](misaligned.md) |
| several cases of one promise read alike | several `inputs` | [Several inputs](inputs.md), [Paths](paths.md) |
| a finer cut tells more | another frame at another `grain` | [Grain](grain.md) |

## The method

1. **Write the frame.** Start from the example closest to your decision, and
   run `uv run gadfly check-frame my-frame.json` until it is accepted. Define
   every label in the instruction.
2. **Write the prediction first.** For each trial, the answer you expect and
   how sure you are, and the verdict that follows. Write it down before the
   first call, as `examples/PREDICTIONS.md` was, and keep it beside the frame.
3. **Plan.** `gadfly plan` prints the trials and the calls, and costs nothing.
4. **Run, keep, report.** Keep every record; the records are the evidence, and
   a report reads them without a model.
5. **Set the result against the prediction.** A wrong prediction stays in.
6. **Run it more than once** when the result matters, and read each run as one
   draw.
7. **Never edit a frame after its runs.** A frame that asked the wrong question
   gets a new version beside it, with the reason, and the old one keeps its runs.

With eGemma on this machine (its key in `EGEMMA_API_KEY` or
`EGEMMA_API_KEY_FILE`):

```bash
uv run gadfly plan examples/09-sync-sms.json   # 40 calls
uv run gadfly run examples/09-sync-sms.json --battery gadfly.batteries.egemma:EGemma \
    --calls 40 --out my-run.jsonl
uv run gadfly report examples/09-sync-sms.json my-run.jsonl
```

This reads a kept frame fresh, without adding to its runs. Each kept run was
made by `examples/climb.py`, which runs a frame against eGemma and keeps the run
beside the others. A reader other than the one recorded (another model, another
revision, another temperature) is a new experiment: write its predictions down
first. [Batteries](../batteries.md) covers other readers, and
[Write a frame](../write-a-frame.md) every field.
