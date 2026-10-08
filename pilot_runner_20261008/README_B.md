# Separate corrected fresh B pilot gate

`run_pilot_b.py` is a new, inert operational wrapper. The original A runner,
schema, and historical validation records remain unchanged. No source/control
values, numeric pipeline imports, searches, or HTTP requests occur in preparation.

Only the complete, distinct, frozen 142-case `VAL_B` bank can now admit sky values.
It must have all nine checks true, no missing/failed outcomes, and a saved
`PASS_EXPLORATORY_SCOPE_ONLY` summary that matches recomputation from all pinned
outcomes. The exact B bank SHA256 is
`93b425038ef9ec178610a1f17856258b0bf726b2e326430db85d4240e48ce46c`.

Before any NumPy/scientific import or `np.load`, this wrapper also requires the
closed A summary/outcomes and the one permitted operational correction's completed
two-case independent `DEV_RUNTIME` proof. Historical A is recomputed with its
original frozen bank and summarizer, and must remain `FAIL_CLOSED`, incomplete,
with exactly its two diagnostic timeout failures and all original checks intact.
Neither its failed realizations nor its eligibility results are rerun or replaced.
The fresh B/A/DEV runtime identities and seeds must be disjoint.

## Exact CLI syntax

```bash
python /workspace/scratch/4763d9b286ba/pilot_runner_20261008/run_pilot_b.py \
  --admission /ABSOLUTE/PATH/primary_pilot_b_admission.json \
  --source-manifest /workspace/scratch/4763d9b286ba/pilot_source_20261008/primary/source_manifest.json \
  --reader-result /ABSOLUTE/READER/OUTPUT/value_read_result.json \
  --validation-summary /ABSOLUTE/PATH/fresh_val_b_summary.json \
  --validation-outcomes /ABSOLUTE/PATH/fresh_val_b_outcomes.json \
  --correction-proof /ABSOLUTE/PATH/dev_runtime_correction_proof.json \
  --failed-validation-a-summary /ABSOLUTE/PATH/validation_a_complete_summary.json \
  --failed-validation-a-outcomes /ABSOLUTE/PATH/validation_a_complete_outcomes.json \
  --output /ABSOLUTE/NEW/PRIMARY/PILOT/OUTPUT
```

`ADMISSION_SCHEMA_B.json` gives the exact required admission fields. Its status
is still `ADMITTED_PRIMARY_PILOT_ONLY`; `fresh_validation_panel` is exactly
`VAL_B`, `fresh_validation_case_count` is 142, and `operational_correction_count`
is exactly 1. The other ordinary source, reader, selected-file, code, output,
canonical claim, and whole-job budget fields have the original meanings.

The `sha256` map additionally requires `failed_validation_a_cases`,
`failed_validation_a_summary`, `failed_validation_a_outcomes`, and
`correction_proof`. The A case-bank hash is a frozen scientific constant. The
actual closed A summary/outcome hashes and completed correction-proof hash are
supplied in the published admission; no prospective placeholder proof digest is
hardcoded. `validation_cases`, `validation_summary`, and `validation_outcomes`
refer exclusively to B. `runner` refers to `run_pilot_b.py`.

## Correction proof schema

The admitting process aggregates the committed two-case DEV runtime results.
The proof must contain:

| Field | Required value |
|---|---|
| `status` | `PASS_OPERATIONAL_DEVELOPMENT_ONLY` |
| `panel` | `DEV_RUNTIME` |
| `complete` | true |
| `case_count_expected`, `case_count_observed` | 2 each |
| `scientific_files_unchanged` | true |
| `failed_validation_a_summary_sha256` | Actual admission-bound closed A summary digest |
| `failed_validation_a_outcomes_sha256` | Actual admission-bound closed A outcomes digest |
| `case_bank_sha256` | `2bef79ec3c17568243672c1ec65c9ca2baeb8066dcc4ab6842039f6d4f2a94d1` |
| `scientific_sha256` | Exact frozen `detector`, `dev_helpers`, and `contract` digests |
| `case_ids` | Both exact runtime identities below, without duplicates |
| `case_results` | Exactly two successful committed records, one per runtime identity |

The exact runtime identities are
`SETI_RADIO_PILOT_20261008_DEV_RUNTIME:single_row_transient:000` and
`SETI_RADIO_PILOT_20261008_DEV_RUNTIME:single_row_transient:001`.
Each `case_results` record requires its `case_id`, `panel: DEV_RUNTIME`,
`status: COMPLETED_CASE_ONLY`, `caps_passed: true`,
`no_retry_or_redraw: true`, and a 64-character lowercase hex
`artifact_manifest_SHA256`. Additional provenance fields can be retained.

## Unchanged execution and display

After all B and historical/correction prerequisites pass, the original source
and reader gates verify the same six native `16 x 7838` float32 arrays, absolute
frequency/channel mapping, file hashes before loading and native value hashes
after loading. The reader result must bind this B summary, never failed A.

The fixed six-panel waterfall and its display receipt precede the first
scientific search. The native arrays, fixed full-band display, row-median dB,
eight-channel maxima with the final partial group, actual row edges/gaps, and
one historical visit labels retain the original policy. The frozen detector,
4096 reference carriers, 5415 drifts, all six maps, all raw ON hits/OFF
dispositions, thresholds, normalization, and output helper bytes are unchanged.

The pilot ID and canonical claim filename are the same as the original runner:
`primary_HD189733_cadence85030_chunk152_20261008`. An existing claim or output is
refused. This new wrapper cannot authorize a second telescope pilot invocation.
Whole-job CPU, 1800-second wall ceiling, 4-GiB RSS/address-space ceiling,
signal watchdogs, guarded finalization, and retained failure receipts are unchanged.
