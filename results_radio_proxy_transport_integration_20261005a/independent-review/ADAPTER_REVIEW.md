# Independent review of initial inert adapter

Date: 2026-10-05. Read-only review of initial
`adapter-work/proxy_opener.py`, the revised parser and copied `wheel_io.py`.
Exact reviewed source and pure reproduction scripts/logs are retained in
`adapter_snapshot/`. This review did not use network bindings, install packages
or access telescope data.

Two material issues were reproduced and reported to the implementer and parent:

1. **Refused second use destroys primary-attempt evidence.** After a CONNECT407
   failure retained its full raw prefix, a second call to the same opener
   replaced that prefix with empty bytes and replaced the primary failure text
   with the repeated-call refusal. The shared receipt is mutated by the
   repeated invocation's exception handler and `finally`, despite no second IO.
   Refuse second/reentrant use before the primary-attempt handler and preserve
   its receipt, using separate refusal data if needed. See
   `adapter_snapshot/reproduce_second_use.py` and `second_use.log`.
2. **Observed body bytes on post-receive refusal are absent from the budget's
   actual receive counter.** A fake body read returns `b"abc"`, then expires the
   synthetic deadline. The adapter retains three bytes in the refusal receipt,
   but calls `budget.record_received` zero times. Successful body reads are
   recorded by `wheel_io` after returning; that path never runs on this refusal.
   Record refused observed bytes once without double counting successful reads.
   Requested-byte precharge is unaffected. See
   `adapter_snapshot/reproduce_refused_body_accounting.py` and
   `refused_body_accounting.log`.

The initial implementation addresses the predecessor findings: post-read clock
checks retain returned bytes before refusing, the plan-retention comment now
states the hash-only receipt accurately, and CONNECT requires a post-code space.
The `recv(1)` line reader avoids hidden buffered read-ahead. Partial CONNECT/HTTP
prefixes are retained outside the line parser on timeout/receive failure.

These findings apply to the retained initial snapshot. This file does not claim
that later revisions still contain them, or certify actual native proxy/TLS
transport. Final supplied adapter tests were still being written at review time.
