# LS8V publication and verification — 21 September 2026

Repository: `andersenmartin-blip/setisearch`; science branch:
`m43-support-qualification`. The standing owner authorization covers the
code, protocols, data, derived results, logs and README update on `main`.

## Immutable sequence

| Stage | Commit | Result |
|---|---|---|
| LS8U parent | `951e8cfd1cf008d259dabfb51534e2bc1fe18b4c` | Previous closed study retained |
| LS8V pair/header freeze | `91dce63e208e126affe519077a9bf571263a8810` | Exact rank-5 pair and header-only budget |
| Header result | `1eb452464982af7bd23e67bca33d429000297a2a` | PASS_COMPATIBLE, zero science bytes |
| Original L2 freeze | `b2b185f8a592e8ae465fa396e96be746e76ecf4c` | 24,012 exact table bytes and unchanged screen |
| First attempt | `d6703a70572eb70c0e028808c8be9e20c73de63e` | Preserved TLS failure before table access |
| Bounded transport recovery freeze | `e3dfd9b6cc82134c770b89469f11e99b1a060f4f` | Same inputs/arithmetic, separate output, finite timeout retries |
| Complete audited result | `94c679a6b460d5911fedc847a656eed630b72d47` | 174 rows, 201 eligible windows, zero signed crossings |

Workflows:
[header preflight 35622410827](https://github.com/andersenmartin-blip/setisearch/actions/runs/35622410827)
completed successfully;
[first attempt 35622872841](https://github.com/andersenmartin-blip/setisearch/actions/runs/35622872841)
failed and remains preserved;
[recovery 35623337391](https://github.com/andersenmartin-blip/setisearch/actions/runs/35623337391)
completed successfully. Both recovery URL requests succeeded on their first
attempt. No science-table request was retried by the wrapper.

## Verification

All 26 header-manifest entries, four first-failure-manifest entries and 20
complete-result-manifest entries were retrieved from their immutable commits
and checked against their SHA256 records. Their manifests were also retained.
Separate scalar FITS-card checks confirmed 87 rows of 138 bytes per visit,
NEXP=1, 60-second EXPTIME/TEXPTIME and inclusive table intervals 20160–32165.

Both existing stable-arithmetic tests pass. The independently implemented
big-endian decoder and scalar equations verify all eligible windows and both
empty signed-cluster sets: **2,412 numerical/discrete comparisons**, zero
disagreements, unchanged relative 2e-8 / absolute 2e-10 tolerances. All retained
tables, ledgers, receipts, summaries, audit, report, transport log, run logs,
environment and figure are included. The figure passed visual inspection.

The public comparison from the LS8U parent through the audited result contains
exactly **67 added files**, with no earlier file modified or deleted. Every
one of those 67 local files matches its independently calculated Git blob
identity in the public comparison. The scientific result tree is
`6037d943963bcd19ddc00fa1252e83aec3d68586`.

The subsequent documentation closure adds LS8V_CONTINUATION.md and this record,
updates PROJECT_STATUS.md and appends the current decision to PROJECT_DIRECTION.md.
The main README receives the same scientific conclusion and GJ 436 continuation.
These editorial updates do not alter any frozen source, output or checksum.

## Scientific state

This is a descriptive null for two predetermined visits, not a sensitivity,
completeness or observing-coverage qualification. No CAL/COR image follow-up is
triggered. The earlier TESS_260647166 positive remains unresolved. Rank-6 GJ 436
is next, beginning with a separate exact-pair/header freeze before science.
Reserved panels remain closed; the separate calibration request remains unsent.

[Audited result](results_ls8v_l2_recovered/REPORT.md) ·
[Scientific interpretation and continuation](LS8V_CONTINUATION.md) ·
[Preserved transport failure](LS8V_TRANSPORT_RECOVERY.md).
