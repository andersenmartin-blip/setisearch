# LS8AK publication and verification — 22 September 2026

PG 1343-102's predetermined rank-12 two-visit screen is COMPLETE_AUDITED
and closed as a descriptive null: 176 rows, 231 eligible overlapping windows,
zero crossings and zero clusters of either sign. This record identifies the
immutable scientific sequence and the subsequent editorial closure.

## Immutable scientific sequence

| Stage | Commit | Content |
|---|---|---|
| Inherited closed LS8AI–LS8AJ state | [50bcbf087662e6fa0d7c653b11374795b533ccae](https://github.com/andersenmartin-blip/setisearch/commit/50bcbf087662e6fa0d7c653b11374795b533ccae) | Parent before any LS8AK work |
| Header-only freeze | [d4095e08d24154e59998435588af2cf79fab7a06](https://github.com/andersenmartin-blip/setisearch/commit/d4095e08d24154e59998435588af2cf79fab7a06) | Exact pair, header budget, protocol and acquisition code |
| Header results | [03dc2e9bf9d80d992f63de1f9757ddcb08bbc558](https://github.com/andersenmartin-blip/setisearch/commit/03dc2e9bf9d80d992f63de1f9757ddcb08bbc558) | Both identities, schemas, rows, exposures, receipts and checksums |
| Exact L2 freeze | [be392f4b2c81ab8536d0e76ae37db618601e0018](https://github.com/andersenmartin-blip/setisearch/commit/be392f4b2c81ab8536d0e76ae37db618601e0018) | Exact table ranges, unchanged pinned scorer, independent auditor and report code |
| Audited scientific result | [2e8f732292605e86ec1619236bdef1c68e74fdf2](https://github.com/andersenmartin-blip/setisearch/commit/2e8f732292605e86ec1619236bdef1c68e74fdf2) | Both retained tables, all scores, signed cluster sets, audit, figure and logs |

The final scientific tree is 8d946f501e67d2c9c5e8b967e9b5d959aaad34bc.
The four scientific commits add **62 files**, with no earlier file changed
or removed. All 62 published Git blob identities were independently
recomputed locally from the downloaded bytes. The later closure adds this
record and LS8AK_CONTINUATION.md, prefixes PROJECT_STATUS.md and appends
PROJECT_DIRECTION.md; it does not change the scientific result or method.
The main-branch README receives the current result and next action while
preserving its prior dated history.

## Successful workflows and retained data

| Workflow | Run | Verified conclusion |
|---|---|---|
| Header preflight and transport gate | [35740163885](https://github.com/andersenmartin-blip/setisearch/actions/runs/35740163885) | completed / success |
| Exact L2 screen, independent audit and report | [35740581159](https://github.com/andersenmartin-blip/setisearch/actions/runs/35740581159) | completed / success |

Both visits individually verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and
pipeline 14.1.2. Each header preflight reads 20,160 bytes within its frozen
64-KiB-per-product budget and no table or image bytes. Each L2 row has
138 bytes and 18 columns. The subsequent exact table requests are:

| Product | Rows | Inclusive byte range | Science bytes |
|---|---:|---|---:|
| CH_PR100002_TG008701_V0300 | 86 | 20160–32027 | 11,868 |
| CH_PR100002_TG008702_V0300 | 90 | 20160–32579 | 12,420 |
| Total | 176 | — | 24,288 |

The complete signed result is zero positive and zero negative crossings and
clusters across 231 eligible overlapping windows. No image payload, alternate
aperture or raw imagette is acquired. All four archive URL resolutions succeed
on the first attempt; there is no table retry, source substitution or scientific
rerun. One later GitHub read of an already published header result returned a
disconnected-response error; repeating that read succeeded and all identity
checks passed. It did not repeat any archive acquisition or science calculation.

## Verification scope

- All five inherited URL/transport tests pass before header acquisition; both
  inherited stable L2 tests pass before science-table access.
- The independent scalar FITS-card check agrees with the retained header
  metadata. The independently decoded L2 audit passes 2,772 numerical/discrete
  comparisons, zero disagreements, including complete signed clusters and counts.
- Numerical tolerances are unchanged: relative 2e-8 and absolute 2e-10. The
  largest score difference is 1.5543122344752192e-15; the combined tolerance
  rule, rather than the absolute term alone, is applied to every quantity.
- All 28 metadata and 22 L2 SHA256SUMS entries pass local verification. Both
  manifests, the 50 listed files and all 10 new source/protocol/config/workflow
  files also match their published Git identities: all 62 scientific files.
- The retained light curves and every eligible score were visually inspected
  in results_ls8ak_l2_screen/pg1343102_screen.png. A separate read of the already
  retained second table confirms the early row-10 point and its missing event
  context; no new archive data or changed screening rule is involved.

The null is limited to the 231 eligible windows. Row 10 of the second visit
has STATUS=0 and flux/visit median 1.3445547616059867, but no tested event
interval containing it has the required left context. It remains visible and
available to the unchanged sideband rule. Its cause is unassigned. Scores are
not Gaussian significance, and overlapping windows are not independent trials.
No candidate, sensitivity, detector or qualified-coverage claim is added.

## Continuation

Prepare LS8AL for rank-13 HD 106315. Its exact ledger pair is
CH_PR100041_TG000801_V0300 and CH_PR100041_TG001401_V0300; both ledger
exposures are NEXP=1, EXPTIME=TEXPTIME=41 seconds and pipeline 14.1.2.
Verify their own headers before freezing exact L2 ranges. The same one/two/three
row method would use 41/82/123 seconds if those exposures are confirmed.
These science values remain unopened at this checkpoint.

[Interpretation, limits and exact continuation](LS8AK_CONTINUATION.md) ·
[Audited L2 report](results_ls8ak_l2_screen/REPORT.md) ·
[Current status](PROJECT_STATUS.md).
