# Restore CA, 1 November 2026

CA is closed. Do not describe a pending background job. Continue from the
final summary, numerical reviews and preserved original data.

The evidence archive `SETI_FORTSAETTELSE_CA_2026-11-01_EVIDENCE.zip` contains
all CA inputs, scripts, outputs and reviews, plus the exact parent BZ archive
under `parents/`. Verify every file against `ARCHIVE_MANIFEST_CA.json` before
using it. First extract the nested BZ archive into the same repository root,
then retain CA's separate `work_ca/` tree. BZ files are unmodified.

Read in order:

1. `RADIO_PROGRESS_CA_VOYAGER_2026-11-01.md` and `work_ca/FINAL_SUMMARY_CA.json`.
2. `work_ca/new_data/RESULT_CA_VOYAGER.json`, `PROVENANCE_SOURCE_HASHES.json`
   and `work_ca/review/VOYAGER_REVIEW_CA.json`.
3. `work_ca/diagnosis/SCORE_DECOMPOSITION_CA.json` and
   `work_ca/review/DIAGNOSIS_REVIEW_CA.json`.
4. `work_ca/DATA_SOURCE_SEARCH_CA.json` to avoid repeating the bounded source checks.

The public code/results live on `radio-bp-paired-controls-20261031` in
`andersenmartin-blip/setisearch`; main README points to the finished report.
The external `SETI_CA_DELIVERY_INDEX_2026-11-01.json` identifies the result
commit, evidence filename, byte size and SHA-256. The evidence can be resolved
by exact filename if its Library ID is not present in the continuation context.

## Scientific interpretation

- Five author-selected Voyager1 power stamps from one historical observation,
  9,344 samples; 391,044 fully supported tracks. These are newly acquired for
  this project, not new telescope observations or blind stellar coverage.
- Four of five fixed reference checks pass. Zero-based hit3 (displayed as
  fourth stamp) differs by 2.75 endpoint channels and remains FAIL.
- The source labels Voyager1, and author notebook/reference metadata agree.
  Raw unselected observation provenance is not independently reconstructed.
- The initial scope's carrier/sideband wording is not an independently verified
  physical identification of each stamp. Report only five selected structures.
- The original production result retains its pre-review status. Final audit
  authority is the separate bound review and FINAL_SUMMARY_CA.json.
- Earlier production/review attempts are recorded; only the stable closed
  result and successful final review count. Do not replace FAIL history.

## Priority next work

First seek a complete new original stellar ON/OFF power sequence, or normal
permitted access to HIP43223/65143 OFF5. The nested BZ evidence includes
`work_bw/recovery/RESUME_SPEC_BW.json`; full BB/BC/BE checks remain necessary.
The original archive count486 and technical coverage268.50128173828125MHz-visits
are unchanged; missing OFF5 prevents full HIP44295-cadence qualification.

The retained Voyager file also permits a bounded next investigation of linear
versus seticore tree-based paths for the fourth stamp. The preselected reference
is not ground truth. Do not change the completed CA tolerance after seeing its
result or use this selected fixture as false-alarm/sensitivity calibration.
Any detector proposal needs a separate stated scope and appropriate controls.

The BZ diagnostic is posthoc: local background contributions account for much
of the observed negative/positive drift difference in the selected paths.
Only two carrier locations per rate group were used; no population inference.
