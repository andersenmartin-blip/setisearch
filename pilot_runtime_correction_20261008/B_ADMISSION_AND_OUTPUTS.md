# Prospective fresh B operational admission

This preparation performs no array generation or scientific search. The
unchanged fresh B manifest is admitted only after the original complete A
outcomes remain `FAIL_CLOSED` and the two new, committed `DEV_RUNTIME` cases
have supplied `PASS_OPERATIONAL_DEVELOPMENT_ONLY`. The single correction
changes resource allocation, never scientific modules or case recipes.

Invoke the coordinator once, after the reviewed public freeze and root receipt:

```sh
python -u pilot_runtime_correction_20261008/run_validation_b_panel.py --admission ROOT_B_ADMISSION.json
```

The master admission is a JSON object with these required fields:

| Field | Required value |
| --- | --- |
| `status` | `ADMITTED_VAL_B_ROLLING` |
| `correction_number` | `1` |
| `scientific_change` | `false` |
| `public_commit_sha` | Reviewed public 40-character Git commit |
| `allowed_case_ids` | All 142 original B IDs, in original order |
| `claim_directory` | Project absolute `pilot_protocol_20261008/validation_b_claims` |
| `paths` and `sha256` | Bind each prerequisite below |
| `sha256.runner` | New `run_validation_b.py` hash |
| `sha256.coordinator` | New `run_validation_b_panel.py` hash |

The prerequisite path keys are `detector`, `dev_helpers`, `generator`,
`contract`, `summarizer`, `development_cases`, `validation_a_cases`,
`validation_b_cases`, `runtime_cases`, `a_summary`, `a_outcomes`,
`runtime_proof`, and `correction_ledger`. Each has an exact SHA256 in the
admission. Paths may be absolute or relative to that admission file; the
scientific modules must resolve to their original project files. Original
scientific hashes, all case-bank hashes, and the failed A aggregate hashes
are hard-pinned by the worker. The two fresh runtime proof records must
also resolve to the canonical `results/radio_pilot_dev_runtime_20261008/case_000`
and `case_001`, with complete original maps, recovery, resources and valid
durable artifact manifests.

`budget` contains `aggregate_cpu_allocation_seconds` (root's exact remaining
admission, from 1830 through 22000), `remaining_cpu_seconds` (at least that
allocation), `global_cpu_ceiling_seconds: 43200`, `max_concurrent_children: 8`,
`max_wall_seconds_per_job: 1800`, and `max_rss_bytes: 4294967296`.
The exact aggregate allocation must follow the actual completed runtime
development receipts and retained planning reservation; this document
does not authorize or calculate a fresh global budget.

Before the first child the coordinator durably creates its once-only claim
and the complete ordered 142-identity slot plan. Each next child receives a
new exclusive 1800-CPU-second reservation before submission, and only that
child's single case ID. The whole-child CPU meter includes startup, imports,
search, OFF rescans and file finalization. The worker's guard starts at 1785
CPU seconds and 1790 wall seconds. The coordinator uses `wait4` without any
earlier reap to charge the entire child, then closes its receipt before
refunding unused capacity. Unknown accounting charges the full partition.
It never retries failed identities and never regenerates A. Failures remain
in the original complete B summary; insufficient capacity stops new
admission and leaves B failed closed.

The fixed output is `results/radio_pilot_val_b_20261008`. It includes the
full plan, per-case admission/reservation/closure/command/log, all original
maps and hits, `outcomes.json`, unchanged-gate `summary.json`,
`resource_receipt.json`, `rolling_cpu_ledger.json`, and `COMMITTED_PANEL.json`.
Qualification requires the coordinator to exit zero and the final marker
to say `COMPLETE_PASS_EXPLORATORY_SCOPE_ONLY`, with all 142 observed cases,
all children reaped, `cpu_budget_passed: true`, and exact bound aggregate
file hashes. A missing final marker, failed durable flush, failed receipt,
or scientific gate failure supplies no pilot authorization.

The root runtime proof schema is `panel: DEV_RUNTIME`,
`status: PASS_OPERATIONAL_DEVELOPMENT_ONLY`, exact counts 2/2,
`complete: true`, `scientific_files_unchanged: true`, exact fresh `case_ids`,
`case_bank_sha256`, failed A summary/outcome hashes, and frozen hashes under
`scientific_sha256` for detector, helpers, generator, contract and summarizer.
Its exactly two `case_results` each carry `case_id`, `panel: DEV_RUNTIME`,
`status: COMPLETED_CASE_ONLY`, `artifact_manifest_SHA256`,
`caps_passed: true`, `no_retry_or_redraw: true`, and `output_directory`.
It reports operational development completion, not a new scientific gate.
