# Watch a run

Gadfly checks whether an answer really rests on one line of evidence: it
hides or changes the evidence in a few fixed ways, asks again each time, and
compares the answers with the first one. Here is a real run, played one trial
at a time: on the left, exactly what Gemma read in that trial; on the right,
what it answered, what that shows, and the checks filling in until the
verdict. Press play, or click any trial.

<div class="gadfly-watch" data-frames="upgrade,07-sql-rule,09-sync-sms,11-eu-clause,12-payroll-access,10c2-incident-both"></div>

The view plays the runs kept in `examples/runs/`, written for it by
`tools/watch_data.py`, and every prompt it shows is checked against the digest
its records carry. On GitHub the view does not run; `examples/read.py` reads the
same runs back as text.
