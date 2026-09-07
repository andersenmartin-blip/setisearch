# Historical-input restoration log scope

The original runtime input roots in the saved continuation package were absent.
No new M43T calibration or injection evaluation was run before restoration.

The initial two-source extraction attempt used the original sequential bounded
transport. It was interrupted to accelerate recovery of the already published
byte ranges. A six-request recovery attempt was then interrupted; its partial
progress is retained in `mirror_restoration_initial.log`. The final helper uses
at most 16 concurrent requests for one source, retaining the original eight-MiB
per-request limit, 30-second timeout and strict remote identity/range checks.
The original generic range implementation permits at most 16 workers. This
operational helper does not change the pinned extraction or scientific code.

`mirror_restoration.log` includes a connection-timeout traceback and the resumed
recovery. Each segment must match its original published SHA-256 before reuse
or acceptance. Only after all segments validate does the helper reproduce the
historical canonical cache index. The original extractor then independently
validates that index, source rows, qualified runtime and full source receipt.
`input_restoration.log` records receipt and full-support array reconstruction.

The `mirror_restore.*.json` files record all exact segment checks and cumulative
request counters for the final completed helper process. They do not measure
network traffic from earlier interrupted processes or all protocol overhead.
The `restore.*.json` files record original receipt identities and all 96 score
array checks. Intermediate mirrors and arrays remain reproducible from the
published segment/source identities; large raw input files are not in Git.

Zero requests reported by `result.json` and `input_reuse.json` refer to the
subsequent numerical experiment only. This continuation did download historical
archive bytes; it added no observing sequence or frequency coverage.
