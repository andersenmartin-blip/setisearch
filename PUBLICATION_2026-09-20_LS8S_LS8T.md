# LS8S–LS8T publication record — 20 September 2026

Published under the standing authorization for SETI code, data, protocols,
reports and logs in `andersenmartin-blip/setisearch`, science branch
`m43-support-qualification`, with the current overview on main. No messages
were sent to people. Scope: the previously selected rank-4 CHEOPS target
TESS_260647166, its original two visits and every signed representative.

| Checkpoint | Immutable commit |
|---|---|
| Previous LS8R status and continuation | `bfce990ec7710021e54a81f90027d733e37b4167` |
| LS8S exact pair and header-only freeze | `ff8ec675b51f1869f85dfdf76426f056d938eff7` |
| LS8S compatible complete header result | `282effbcd95efe7c2269f44dd66d53a67c92f469` |
| LS8S exact L2 ranges and unchanged screen freeze | `94437df35db15a774388ce7ebabfcac9913b5bd1` |
| LS8S complete audited signed result | `cc05ba9a55a98bcfe6e1c747820ec4dd3265617f` |
| LS8T both-representative metadata-only freeze | `7ee634cc2eee9f811009acba4cc45ee789261e35` |
| LS8T complete metadata joins and future image intervals | `6960be53f8e5ce008983a85876517b338013b177` |
| LS8T exact payload, fixed method, tests and workflow freeze | `fa63edc7301f18c6de3a5f721b75412e554c55e0` |
| LS8T complete audited image result and both figures | `3e0bd85cee4b191f4bbe82b499977976c1b1484a` |

All four workflows conclude success. Their scientific statuses were checked
separately from that workflow conclusion:

| Run | Preserved result | Scientific status |
|---|---|---|
| [35527649102](https://github.com/andersenmartin-blip/setisearch/actions/runs/35527649102) | `results_ls8s_l2_metadata`, 26 manifest-listed files | PASS_COMPATIBLE |
| [35527847456](https://github.com/andersenmartin-blip/setisearch/actions/runs/35527847456) | `results_ls8s_l2_screen`, 21 manifest-listed files | COMPLETE_AUDITED |
| [35528081825](https://github.com/andersenmartin-blip/setisearch/actions/runs/35528081825) | `results_ls8t_metadata`, 103 manifest-listed files | METADATA_JOINED_IMAGES_CLOSED; join audit PASS |
| [35528254412](https://github.com/andersenmartin-blip/setisearch/actions/runs/35528254412) | `results_ls8t_images`, 30 manifest-listed files | COMPLETE_AUDITED |

Metadata-derived configs are committed alongside their result directories.
The original LS8J census/order, missing full-response limitation and separately
dated complete reconciliation remain unchanged. No target substitution,
census repetition or change in cohort order was made from these outcomes.

The first scope acquired **40,320 header bytes** and no table values,
verifying NEXP=1 and separate 42-/49-second exposure times. The independent
science scope acquired exactly **241,086 table bytes**. The unchanged screen
retains 1,747 rows and 2,004 eligible overlapping windows, with six positive
crossings forming one cluster and two negative crossings forming one cluster.
Both arithmetic tests and **24,048 numerical/discrete audit checks** pass.

Both original signed representatives enter LS8T. The metadata-only audit
passes **120 unique exposure joins and 556 exact checks**, with zero image
bytes. The separate image scope then acquires exactly **38,400,000 paired
image bytes plus 96,000 smearing bytes**. All six range requests succeed
on their first attempts; no identity assertion or transport error is retried
away and no extra interval is substituted.

Seven inherited image tests and two new duration/cadence known-answer tests
pass before payload access. The independent image reconstruction passes
**189,074 numerical comparisons and 321,180 exact checks**, with no
disagreements under the original tolerances. TG000101_N0 is
**SPATIALLY_STRUCTURED**; TG015701_P0 remains
**UNRESOLVED_WITHIN_FIXED_SCOPE**. No outcome is promoted beyond its gate.

The image directory preserves every compressed raw interval and receipt,
native event maps, complete diagnostics, independent reference, audit,
summary, both figures, report, next action, execution status, environment,
test/analysis logs and manifest. **Twenty local image-review files** and
**eight local L2-review files** match their immutable manifests, including
all three figures. Every figure was visually inspected before the
interpretive continuation. No scientific rerun or changed visualization
was used to alter an outcome during review.

The image stage is complete. The positive has complete data and apertures,
but its displacement fit explains only about 75.8%, below the fixed 80%
gate; its pure-brightness fit explains about 2.7%. The remaining limitation
is the unmeasured residual/noise comparison within the fixed image model,
not missing payload. No qualified SETI candidate, detector or observing
coverage is claimed.

The active next step is one separately frozen retained-data residual/noise
study with both original events, duration-matched controls and signed
signal-protection accounting. It has not been run at this checkpoint.
Rank-5 EC 12578-2107 remains a later independent transfer under its own
metadata/science freezes. All previously closed studies, reserved data,
original failures and the unsent calibration request remain preserved.

[Immutable image report](https://github.com/andersenmartin-blip/setisearch/blob/3e0bd85cee4b191f4bbe82b499977976c1b1484a/results_ls8t_images/REPORT.md) ·
[Immutable L2 report](https://github.com/andersenmartin-blip/setisearch/blob/cc05ba9a55a98bcfe6e1c747820ec4dd3265617f/results_ls8s_l2_screen/REPORT.md) ·
[Scientific interpretation and active next action](LS8T_CONTINUATION.md) ·
[Current project status](PROJECT_STATUS.md).
