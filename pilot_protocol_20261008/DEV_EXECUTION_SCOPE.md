# Full-family development — prospective execution scope, 8 October 2026

The approved study runs 7–20 October. The first reference succeeded on 7 October;
its prior failed CI attempt stays closed. This document admits only the new
24-case DEV bank. No sky values or fresh validation realization has been read.
It does not admit VAL_A, VAL_B, either historical holdout, or telescope data.

The separate source metadata traversal was pinned at commit
`a35b5436934b6709151c8ada3ba7da5b74919907`. Source qualification remains separate
from detection qualification. All scientific definitions, code, control recipes,
source geometry and seeds are published together before this DEV invocation.

The first job runs exactly the first DEV strong case on the full 4,096 ON
carriers, all 5,415 drifts and all four widths, with six complete 16-row scans
and the 7,838-channel decoded context. It measures actual wall time, CPU and
RSS; no smaller search is used to qualify feasibility. If that job completes
within the unchanged limits, the remaining 23 distinct DEV cases may be run in
separate jobs, in frozen order. Each command must use a fresh output directory.
Every failure and partial result is retained. No redraw or automatic replay.

```sh
python pilot_engine_20261008/run_dev.py \
  --contract pilot_controls_20261008/control_contract.json \
  --cases pilot_controls_20261008/development_cases.json \
  --generator pilot_controls_20261008/generator.py \
  --summarizer pilot_controls_20261008/summarize.py \
  --freeze-receipt pilot_protocol_20261008/dev_admission.json \
  --case SETI_RADIO_PILOT_20261008_DEV:strong:000 \
  --output results/radio_pilot_dev_20261008/job_000
```

The external admission receipt is written only after immutable public readback.
It gives the public commit, exact six executable/input hashes, allowed DEV IDs
and remaining resource allowance. Subsequent jobs select the next exact frozen
ID, decrement CPU allowance by every completed or failed job's measured CPU,
and use `job_001` through `job_023`. No concurrent job can double-spend allowance.

Limits remain 0 kr, 4 GiB RSS per job, 1,800 seconds per job and 43,200 aggregate
CPU seconds for the new study. The failed CI route's unknown CPU is conservatively
reserved as 4,800 seconds; measured local reference and display CPU is
5.016680829 seconds. This DEV stage reserves at most 38,000 CPU seconds, leaving
additional margin for measured metadata and preparation. Actual charge and
remaining allowance must be updated before any later stage. Engineering's
nominal 256 MiB source allowance remains unverified; it has not been raised.
No source download occurs in this DEV execution.

The runner verifies membership, input hashes, versions and full dimensions
before RNG. It saves each array's exact C-order SHA256, truth recipe, all six
maximum maps with winning drift/width and hypothesis counts, every raw ON hit
with all three OFF dispositions, localized recovery before/after OFF, errors
and measured resources. Raw arrays are reconstructible from fixed recipes and
verified hashes; retaining all generated noise arrays is unnecessary.

DEV outcomes are descriptive development evidence. They never count as fresh
validation or sky evidence. The 142-case VAL_A and reserved independent VAL_B
recipes are pinned but remain unopened. Complete DEV results must be reviewed
before a separate validation execution is admitted. Any later scientific change
must preserve this version and its failures and follow the approved one-change
limit; no results-dependent change is hidden inside this freeze.
