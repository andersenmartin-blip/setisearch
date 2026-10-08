# One saved method result in a fresh process

This command is available only after the complete64-case method panel has
durably closed. It verifies one saved case's maps, retained threshold hits,
compatible OFF witnesses, localized recovery, loss-stage labels, original
artifact hashes and resource closure. It generates no synthetic arrays, calls
no detector search and opens no telescope source data. It does not reproduce
raw preprocessing or the original numerical scores from raw power.

The bounded command opens six retained maps for exactly one frozen identity.
Its receipt has `PASS_BOUNDED_SAVED_RESULT_VERIFICATION`, distinct from the full
64-case integrity audit. It never qualifies a sky pilot or changes A/B failures.

Run from the restored project layout with the original admission bytes intact:

```sh
prlimit --as=4294967296 --cpu=60 -- timeout 120s env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 python pilot_protocol_20261008/review/audit_retained_method.py --admission pilot_method_study_20261008/method_study_admission.json --case-id SETI_RADIO_PILOT_20261008_METHOD_STUDY:method_signal:000 --output pilot_protocol_20261008/review/METHOD_SAVED_CASE_000_REPRODUCTION.json
```

When the project has been restored beneath a different absolute root, append
`--recorded-project-root /workspace/scratch/4763d9b286ba`. This explicitly maps
only admitted prerequisite paths beneath that recorded root to the current
project root. Every restored file must match its original admitted SHA256.
Paths escaping either root are rejected. Admission and claim bytes remain
unchanged; the new receipt records every original/restored path and hash.
The current-workspace command needs no rebasing flag.

The command bounds address space at4GiB, process CPU at60 seconds and wall time
at120 seconds. Capture whole-process usage and retain any failure. This file is
a documented future reproduction command; it is not a scheduled invocation or
a claim that reproduction has already occurred.
