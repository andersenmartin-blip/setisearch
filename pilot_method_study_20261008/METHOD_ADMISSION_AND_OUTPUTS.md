# Exploratory method execution, after failed validation

The worker and coordinator are inert preparation. They invoke the original
frozen detector, generator and six-scan geometry only after complete A and B
remain closed failures. This study cannot qualify telescope analysis, change
thresholds, retry a validation identity or reverse either failed gate.

```sh
python -u pilot_method_study_20261008/run_method_study_panel.py --admission ROOT_METHOD_ADMISSION.json
```

The root JSON admission uses `status: ADMITTED_METHOD_STUDY_ROLLING`,
`study_mode: EXPLORATORY_ONLY`, `scientific_change: false`,
`qualification_override: false`, `telescope_values_opened: false`, the public
40-character `public_commit_sha`, the exact ordered 64 `allowed_case_ids`,
and canonical project-absolute
`claim_directory: pilot_protocol_20261008/method_study_claims`.

Its `paths` and `sha256` bind the following prerequisite keys:

| Evidence | Keys |
| --- | --- |
| Original science | `detector`, `dev_helpers`, `generator`, `contract`, `summarizer` |
| Historical identity banks | `development_cases`, `validation_a_cases`, `validation_b_cases`, `runtime_cases` |
| Fresh exploratory bank | `method_cases` |
| Closed A failure | `a_summary`, `a_outcomes` |
| Closed B failure | `b_summary`, `b_outcomes`, `b_resource_receipt`, `b_completion` |
| Independent retained B output audit | `b_integrity_review` |
| Approved method definitions | `scope`, `science_protocol` |
| Actual remaining period resources | `post_b_ledger` |
| Prior period ledger bound by post-B accounting | `post_development_ledger` |

`sha256.runner` binds `run_method_study.py`; `sha256.coordinator` binds
`run_method_study_panel.py`. Paths may be absolute or relative to the root
admission. Original scientific paths and hashes remain mandatory. Both failed
validation summaries are recomputed from their frozen banks and complete
142-case outcomes. `b_completion` is B's `COMMITTED_PANEL.json`, with closed
failure status, exact aggregate hashes, and all children reaped. Methods are
never admitted from a partial running B result.
The independent audit must retain scientific status
`FAIL_CLOSED_NO_PILOT_ADMISSION` while confirming
`integrity_review_status: PASS_RETAINED_COMPLETE_OUTPUT_INTEGRITY`, all 142
observed cases, all 852 retained maps, and exact closed-bank/output hashes.

The post-B ledger must assert `scientific_files_unchanged: true`,
`A_remains_FAIL_CLOSED: true`, `B_remains_FAIL_CLOSED: true`, and
`telescope_values_opened: false`. Root binds its actual whole-child B charges
and retained period capacity after B closes.
Its `remaining_CPU_after_closed_B_s`, `method_aggregate_CPU_allocation_s`,
and `retained_report_reproduction_CPU_s` must exactly match the corresponding
root budget fields. `b_prerequisite_sha256` maps `b_summary`, `b_outcomes`,
`b_resource_receipt`, and `b_completion` to their admitted hashes;
`post_development_ledger_sha256` binds the previous period ledger.

The budget has these fields:

| Field | Bound |
| --- | --- |
| `aggregate_cpu_allocation_seconds` | Root admission, at most 6000 |
| `remaining_cpu_seconds` | Actual period capacity, at least allocation plus retained margin |
| `retained_report_reproduction_cpu_seconds` | At least 2000 |
| `global_cpu_ceiling_seconds` | Unchanged 43200 |
| `max_concurrent_children` | Between 1 and 8 |
| `max_wall_seconds_per_job` | 1800 |
| `max_rss_bytes` | 4294967296 |

Each child receives a separate durable exclusive 250-CPU-second partition
before submission. The CPU guard begins at 235 seconds, leaving 15 seconds
for failure finalization. The wall guard begins at 1790 seconds. Startup,
imports, all six searches, OFF comparisons, hashes and file writes count.
The coordinator charges each whole child through `wait4` and durably closes
its receipt before releasing unused reserved CPU. Unknown accounting consumes
the complete partition. Failed prespecified cells remain failed; other cells
continue only while another entire partition fits. Exhaustion preserves a
partial study with its missing IDs and permits no retry or new budget.

The canonical output is `results/radio_pilot_method_study_20261008`, with
complete original maps, ON hits, OFF dispositions, truth, hashes and localized
recovery for each completed cell. The descriptive aggregate contains valid
denominators, failed/missing IDs, recovery before and after OFF, and groups by
declared ideal score, drift, width, activity and placement. All 64 individual
cell outcomes are retained. There is one independent synthetic realization
per cell; these counts provide a method diagnostic, not a power calibration
or real-data false-alarm bound.

Every aggregate keeps `scientific_gate: EXPLORATORY_METHOD_STUDY_ONLY` and
`qualification: false`, regardless of recovery. Exit zero and the final
`COMMITTED_PANEL.json` status `COMPLETE_EXPLORATORY_METHOD_STUDY_ONLY` mean
only that all 64 exploratory cells and resource receipts completed. Otherwise
the marker says `CLOSED_PARTIAL_OR_FAILED`; retained results remain useful
descriptive evidence without scientific qualification.
