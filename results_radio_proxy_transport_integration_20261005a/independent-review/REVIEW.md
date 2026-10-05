# Independent review of inert proxy preparation

Date: 2026-10-05. Reviewed predecessor files copied from
`/workspace/scratch/a5b2addacbd5/setisearch-20261005/results_radio_proxy_transport_preparation_20261005a/`:
`proxy_contract.py`, `test_proxy_contract.py`, `PROTOCOL.md`, and the associated
`RADIO_BOOTSTRAP_RECOVERY_AND_TRANSPORT_2026-10-05.md` report.

## Assessment

The preparation is safe to publish with its stated inert status. It initiates no
network operation and authenticates the original plan's exact raw SHA-256 before
constructing prospective transport data. Parsed synthetic success grants no
service, TLS, runtime or scientific authority. No package-pin, header cap/count,
body-framing or refusal-evidence bypass was found in the supplied parser.

The copied supplied test suite passed all 16 tests. The exact output is retained
in `supplied_tests.log`; `proxy_contract.py`, `test_proxy_contract.py`, and
`original-plan.json` are the copied inputs, not modifications to the predecessor.

## Reproduced findings

1. **Late final read can succeed.** `parse_connect` checks the injected deadline
   before debit/read, but does not check again after receiving the terminating
   blank line. In `reproduce_findings.py`, the final read sets the synthetic clock
   to expired; the function nevertheless returns `PARSED_INJECTED_CONNECT_ONLY`.
   Add a post-receive clock check after retaining returned bytes so refusal
   preserves evidence. Any actual receive adapter must separately limit each
   syscall to the remaining deadline.
2. **Plan-retention comment overstates returned data.** The comment above
   `json.loads(original_plan_raw)` says the entire authenticated plan is retained,
   but that parsed value is discarded. The return value carries only
   `original_plan_sha256`. The original raw-hash authentication is sound; correct
   the comment or make explicit how later integration retains and revalidates the
   whole plan.
3. **Minor status-line strictness.** The parser accepts
   `b"HTTP/1.1 200\r\n\r\n"`, with no space after the status code. Tighten this if
   the intended accepted form requires that space. This does not confer live
   transport authority.

All three pure reproductions and their output are retained in
`reproduce_findings.py` and `findings.log`.

## Review limitations and integration implication

This was a source and synthetic-callback review. No proxy/socket request,
installation, numerical/native scientific import or telescope data access was
performed. The predecessor tree was not changed. Existing published recovery
claims were read for scope; this review did not repeat their full inventories.

The injected line limit does not prove actual socket receive bounds. A future
adapter must demonstrate bounded actual reads and retention of bytes received
before a partial failure; buffered socket readers require particular care
because a logical `readline` bound need not bound hidden prefetch. This is an
adapter integration question, not a new live qualification from these tests.
