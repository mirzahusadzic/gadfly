# Examples

--8<-- "README.md:examples"

## Review handoff

The [worked example](load-bearing.md#worked-example-from-failed-check-to-review-handoff) of *When meaning is load-bearing*.

```
$ python examples/review_handoff.py
system                       finding                  authority
state projection             carried                  carried
summary: fix ready           cooled                   cooled
drops its openings           coupled but misaligned   carried
projection, a record lost    unresolved               -
```

## Refund

```
$ python examples/refund.py records.jsonl
phrase-matcher: coupled but misaligned
  presentation moved it decline -> grant
rule-reader: carried
  ablation moved it decline -> grant; held under presentation, 2 shams
  no hidden fallback: bypass left it at decline
```
