# Fresh VAL_A operational preparation - 8 October 2026

This preparation adds only a single-case runner. It does not generate or inspect
fresh VAL_A/VAL_B values, alter the scientific detector or generator, or admit
validation execution. Root must first close and review all 24 distinct DEV
cases, review the unchanged scientific method, publish this wrapper and its
bindings, and assign the available resources in a separate VAL_A receipt.

`run_validation.py` reuses frozen `run_dev.py` output/resource helpers. Exact
detector, helper, generator, contract, DEV/A/B recipe and summarizer hashes are
embedded and checked against the immutable public receipt. Complete DEV
outcomes and their saved summary are hash-bound; the DEV summary is recomputed
and must agree before any validation array is generated. DEV, A and B case
identities and seed digests must be disjoint. This runner permits one exact
VAL_A case only; it does not accept DEV, VAL_B, sky data or an `--all` option.

The admission receipt has:

- `status`: `ADMITTED_VALIDATION_A_ONLY`;
- `public_commit_sha`: the immutable published 40-character commit;
- `development_readiness`: `COMPLETE_DEV_REVIEWED_SAME_SCIENCE`;
- `allowed_case_ids`: explicitly admitted fresh VAL_A identities;
- `sha256`: exact `detector`, `dev_helpers`, `runner`, `generator`, `contract`,
  `cases`, `development_cases`, `validation_b_cases`, `development_outcomes`,
  `development_summary` and `summarizer` hashes;
- `budget`: `remaining_cpu_seconds`, `exclusive_cpu_allocation_seconds`,
  `max_wall_seconds_per_job` and `max_rss_bytes`.

An exclusive case allocation is at most 250 CPU seconds. Root may select 240
seconds or a smaller sufficient amount after actual DEV review; this document
does not reserve CPU. Maximum wall time is 1,800 seconds and peak RSS 4 GiB.
Wall/CPU watchdogs retain a flush margin. The global 12-CPU-hour ledger remains
root's responsibility across concurrent jobs; each job returns a full receipt.
No partial/coarse search can count as a completed control.

After publication and admission, a designated first-case command is:

```bash
python3 pilot_engine_20261008/run_validation.py \
  --contract pilot_controls_20261008/control_contract.json \
  --cases pilot_controls_20261008/validation_a_cases.json \
  --development-cases pilot_controls_20261008/development_cases.json \
  --validation-b-cases pilot_controls_20261008/validation_b_cases.json \
  --development-outcomes pilot_protocol_20261008/dev_complete_outcomes.json \
  --development-summary pilot_protocol_20261008/dev_complete_summary.json \
  --generator pilot_controls_20261008/generator.py \
  --summarizer pilot_controls_20261008/summarize.py \
  --freeze-receipt pilot_protocol_20261008/validation_a_admission.json \
  --claim-directory pilot_protocol_20261008/validation_a_claims \
  --case 'SETI_RADIO_PILOT_20261008_VAL_A:strong:000' \
  --output pilot_engine_20261008/validation_runs/val_a_strong_000
```

The two DEV aggregate paths and admission path designate files root must
produce from actual evidence; preparation does not assert those files exist.
The selected output directory must be new. An atomic, exclusive shared claim
is created before generation. Its filename is the full SHA256 of the case
identity. Claims survive failures, preventing redraws/repeats under another
output directory or in concurrent jobs. Never delete a claim to rerun a case.

Each case retains definition, truth, exact synthetic array hashes, all six full
carrier maps, all raw ON hits, complete OFF witnesses/checked counts,
endpoint-localized pre-OFF and final all-active/any-active recovery, errors and
resources. A completed case remains `COMPLETED_CASE_ONLY`; a full 142-case gate
can be evaluated only after every required outcome exists. Failures are
`FAILED_CLOSED` and retained. This wrapper never switches to VAL_B.
