# Milestone 23 complete over-threshold disposition audit

Status: **FROZEN AFTER THE PRIMARY REPORT-CAP SATURATION AND BEFORE THE AUDIT RERUN**.

The primary HD 33564 search is reproducible and its strongest reported cases
are physically vetoed, but the 1400 MHz candidate list saturated the frozen
50-cluster output cap while the 50th case remained above the global threshold.
This audit resolves that output boundary without changing the search.

## Frozen input and sole configuration difference

The primary configuration is
`config/hd33564b_heldout_m23.json`, SHA-256
`c36f73c812d4d863e059979573775aac20ef5a2ec38aafc30b9c2abe2629edf7`.
The audit configuration is
`config/hd33564b_m23_complete_audit.json`, SHA-256
`0af0f6a23308fab5cc83a6bdef9f8e1a7a7e6ac2fc477ab96762a6ad68acb05b`.
Its sole byte-level scientific configuration difference is:

- `search.candidate_reporting.max_report_clusters`: **50 -> 500**.

All telescope identities, scan times, extraction ranges, orbital templates,
activity subsets, spectral widths, S/N rules, empirical scrambles, seeds,
completeness injections, clustering, OFF vetoes, and receiver-frame vetoes
remain unchanged. The increased value changes only how many already-formed
clusters are preserved in the output.

## Fixed audit procedure

1. Re-extract only primary cadence `--71505`; cadence `--71747` remains closed.
2. Require the 30 extracted-slice SHA-256 values to match
   `DATA_MANIFEST_M23.sha256` exactly after ignoring directory prefixes.
3. Rerun detector v0.5.0 with the audit configuration and the original seeds.
4. Require the global result, five ON maxima, five OFF maxima, five empirical
   null summaries, and the first 50 clusters in every window to reproduce the
   primary `results_m23/search_summary.json` numerically and categorically.
5. Require every window's reported cluster count to equal its pre-limit
   cluster count; the fixed cap of 500 exceeds the primary maximum of 297.
6. Count every cluster above the unchanged operational threshold and preserve
   its automatic v0.5 disposition.

## Stopping rule

If every over-threshold cluster receives `rfi_veto_off_source`,
`rfi_veto_single_adjacent_off`, `rfi_veto_local_off_source`, or
`rfi_veto_receiver_frame_alias`, Milestone 23 closes as a no-survivor result
and the independent cadence remains unopened.

If any over-threshold cluster has `follow_up_required`, its exact hypothesis
and a candidate-local morphology protocol must be committed before primary
cutouts are inspected. Only a case still unresolved after that review may
trigger a separately frozen targeted recurrence test on cadence `--71747`.

Arithmetic-family and width flags remain context only and are never promoted
to physical vetoes.
