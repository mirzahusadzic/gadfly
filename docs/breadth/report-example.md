# Example report

This is the output of the prototype report command on the refund records. It
keeps the category, evidence and obligations distinct.

```text
frame: refund-receipt (6a788e8843504c0828dc1dc8c236c349e8f9750c0cd2d52b2d124d2bb9580e9e)
records: 7  planned calls: 7
stopped: no
overall: carried
  no-receipt: ablation moved it decline -> grant; held under presentation, 2 shams
  shared obligation: no hidden fallback: bypass left it at decline
no-receipt: carried
  level baseline: decline
  level repeat: decline
  level ablation: grant
  level sham-1: decline
  level sham-2: decline
  level presentation: decline
  level bypass: decline
  evidence: ablation moved it decline -> grant; held under presentation, 2 shams
  obligation: no hidden fallback: bypass left it at decline
```
