# Examples

--8<-- "README.md:examples"

## Review handoff

The [worked example](load-bearing.md#worked-example-from-failed-check-to-review-handoff) of *When meaning is load-bearing*.

```
$ python examples/review_handoff.py
system                       finding                  authority
state projection             carried                  unresolved
summary: fix ready           unresolved               unresolved
drops its openings           coupled but misaligned   unresolved
projection, a record lost    unresolved               -
```

## Refund

```
$ python examples/refund.py records.jsonl
phrase-matcher: coupled but misaligned
  presentation moved it decline -> grant
  no hidden fallback: bypass left it at decline
rule-reader: unresolved
  ablation moved it decline -> grant; held under presentation, 2 shams
  not carried while 1 carriage check is open
  no hidden fallback: bypass left it at decline
```
