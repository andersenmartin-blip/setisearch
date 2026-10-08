# Primary pilot runner preparation

Preparation is static only. No source/control array has been opened, generated,
searched, imported, or displayed while preparing these files. The existing
scientific detector and shared output helpers are unchanged. This directory
contains an ordinary runner and a separate fixed display helper.

The runner executes one expressly admitted primary pilot only after a complete,
fresh, pinned 142-case `VAL_A` summary is `PASS_EXPLORATORY_SCOPE_ONLY`, with all
nine checks true and its complete outcomes independently recomputed by the
frozen metadata summarizer. It requires the exact source metadata and reader
code, a completed reader result bound to that source and validation summary,
all 96 source range/roundtrip receipts, and six native selected array declarations.
Every `.npy` file SHA256 is checked before the first `np.load`; each actual
array's native C-order SHA256 is checked afterward against the reader receipt.

The frozen absolute source `fch1_hz`, `df_hz`, start epochs, integration times,
native row count, loaded interval `[159903921,159911759)`, and reference interval
`[159905792,159909888)` are cross-checked between current source metadata and
the control contract. `control_inputs` is only an adapter: actual power arrays
remain native `16 x 7838`, little-endian float32, and read-only. No masks are
introduced. All 4096 reference carriers, 5415 drifts, four widths, six full scan
maps, all raw ON threshold hits, and all three OFF comparisons for every ON hit
are retained through the unmodified detector and `run_dev.save_result`.

## Exact CLI syntax

Invoke from any working directory with absolute paths:

```bash
python /workspace/scratch/4763d9b286ba/pilot_runner_20261008/run_pilot.py \
  --admission /ABSOLUTE/PATH/primary_pilot_admission.json \
  --source-manifest /workspace/scratch/4763d9b286ba/pilot_source_20261008/primary/source_manifest.json \
  --reader-result /ABSOLUTE/READER/OUTPUT/value_read_result.json \
  --validation-summary /ABSOLUTE/PATH/fresh_val_a_summary.json \
  --validation-outcomes /ABSOLUTE/PATH/fresh_val_a_outcomes.json \
  --output /ABSOLUTE/NEW/PRIMARY/PILOT/OUTPUT
```

Only the five `/ABSOLUTE/...` paths are supplied by the admitting process.
The selected array files must be the six ordinary `.selected.npy` siblings of
`value_read_result.json`. Existing output is refused. The admitted canonical
claim filename is `primary_HD189733_cadence85030_chunk152_20261008.json`; exclusive
creation records the invocation before loading any array and survives failure.
The claim path and output path are bound in the published admission. These are
ordinary reproducibility records for this one authorized invocation.

## Admission fields

`ADMISSION_SCHEMA.json` gives the exact field names and required types. The
admitting process writes the receipt after publishing this code and after the
full fresh `VAL_A` PASS. The runner does not create or infer admission.

| Field | Required value |
|---|---|
| `status` | `ADMITTED_PRIMARY_PILOT_ONLY` |
| `pilot_id` | `primary_HD189733_cadence85030_chunk152_20261008` |
| `public_commit_sha` | 40 lowercase hex characters for the public preparation freeze |
| `fresh_validation_panel` | `VAL_A` |
| `fresh_validation_case_count` | 142 |
| `output_directory` | Exact absolute new output path |
| `canonical_claim_path` | Exact absolute canonical claim path ending in the pilot ID plus `.json` |
| `sha256` | Required SHA256 entries listed below |
| `selected_array_file_sha256` | All six scan IDs mapped to SHA256 of each complete `.npy` file |
| `budget.max_wall_seconds_per_job` | Root allocation; runner also caps the whole job at 1800 s |
| `budget.max_rss_bytes` | Root allocation; runner also caps RSS/address space at 4 GiB |
| `budget.remaining_cpu_seconds` | Remaining root CPU allowance before this invocation |
| `budget.exclusive_cpu_allocation_seconds` | CPU allowance reserved for this one invocation |

`sha256` requires `runner`, `waterfall`, `detector`, `dev_helpers`, `contract`,
`source_manifest`, `value_reader`, `reader_result`, `validation_cases`,
`validation_summary`, `validation_outcomes`, and `summarizer`. SHA256 values
refer to complete file bytes, not JSON canonicalization. No hashes are optional.
`selected_array_file_sha256` requires exactly `epoch1_on`, `epoch1_off`,
`epoch2_on`, `epoch2_off`, `epoch3_on`, and `epoch3_off`. Their separate native
C-order value digests come from the admitted reader result.

## Resources and retained outputs

`ITIMER_REAL` and `ITIMER_PROF` watchdogs include admission, hashes, imports,
loads, search, plot, and artifact finalization. CPU accounting starts from whole
process `getrusage`; RSS uses Linux `ru_maxrss`. An address-space limit no larger
than the RSS allowance is also applied. Ten wall seconds and five CPU seconds
are reserved to retain a failure. Native libraries use one thread. A cap failure
closes the outcome; the original reader arrays and existing claim remain.

The output includes the frozen helper's six complete `.npz` scan maps,
normalization metadata, geometry/drift/time arrays, all ON hit records including
complete OFF comparisons, the additional flat `all_OFF_dispositions.json`,
native input provenance, the admission and gate evidence, an outcome, a final
whole-job resource receipt, and artifact hashes. The artifact manifest excludes
itself and the final resource receipt so the latter can include manifest work.

## Fixed display policy

`waterfall.render_waterfall(arrays, contract, output_path)` displays all six
retained native scans in chronological order. The full loaded band is reduced
only for display by maxima across consecutive groups of eight frequency channels;
the last six-channel group remains. Each row uses `10 log10(power / full native
row median)`. Every panel has the predeclared `[-10,+20]` dB color range. Color
saturation and zero-power under-range colors are disclosed in the receipt.
The fixed six-panel PNG and its display receipt are saved immediately after
native-array and geometry verification, before the first scientific search or
candidate judgment. A later search failure retains that early display.

Frequency is kHz offset about the fixed reference band's center. Individual
scan integration edges use actual start epochs and sampling times; proportional
blank gaps retain actual interscan gaps. The label is `ONE historical visit —
3 ON + 3 OFF (3ON3OFF)`. No display reduction, color saturation, or normalization
alters native values, masks, detector output, classifications, or thresholds.

No actual pipeline execution is part of this preparation. Static AST review is
the preparation check; the eventual admitted run produces operational receipts.
