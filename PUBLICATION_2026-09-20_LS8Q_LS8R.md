# LS8Q–LS8R publication record — 20 September 2026

Published under the standing authorization for SETI code, data, protocols,
reports and logs in `andersenmartin-blip/setisearch`, science branch
`m43-support-qualification`, with the current overview on main. No messages
were sent to people. The scope is the previously selected rank-3 HD 136352
pair and every signed cluster representative from its unchanged L2 screen.

| Checkpoint | Immutable commit |
|---|---|
| Previous LS8P status and continuation | `db109b68db843ee6d9ac51052372c84329668527` |
| LS8Q exact pair and metadata/header-only freeze | `ec67f47f2e7782d0aed8b7e6be27c9327fa0b43a` |
| LS8Q compatible complete header result | `3cb7624f5044bcdb45293df880f939e4a13352b0` |
| LS8Q exact DEFAULT-L2 byte ranges and unchanged screen freeze | `0a5957d68ca61d0c7a18da9b2b0ef4e8ed1c6c26` |
| LS8Q complete audited signed L2 result | `69108d1939f5a1ed6a466d46f7376ed0f90dc2fb` |
| LS8R all-representative metadata-only join freeze | `7b4a39375dd4050dd24f005009ce7eb19498b01e` |
| LS8R complete metadata joins and exact future image ranges | `223e5fbe65e949d3caffe98372f93e27e494085e` |
| LS8R exact payload, fixed method, tests and workflow freeze | `a4a341b6c6f595984a7eca135cd01b6ca25ddc34` |
| LS8R complete audited image result and all figures | `3f5053ee7d35afed31666b95daf9b3b5029956fc` |

All four workflow runs conclude success, with their scientific statuses
verified separately from the workflow conclusion:

| Run | Preserved result | Scientific status |
|---|---|---|
| [35525729955](https://github.com/andersenmartin-blip/setisearch/actions/runs/35525729955) | `results_ls8q_l2_metadata`, 26 manifest-listed files | PASS_COMPATIBLE |
| [35525919608](https://github.com/andersenmartin-blip/setisearch/actions/runs/35525919608) | `results_ls8q_l2_screen`, 21 manifest-listed files | COMPLETE_AUDITED |
| [35526146822](https://github.com/andersenmartin-blip/setisearch/actions/runs/35526146822) | `results_ls8r_metadata`, 103 manifest-listed files | METADATA_JOINED_IMAGES_CLOSED; independent join audit PASS |
| [35526578463](https://github.com/andersenmartin-blip/setisearch/actions/runs/35526578463) | `results_ls8r_images`, 39 manifest-listed files | COMPLETE_AUDITED |

The metadata-derived configs are committed alongside their result directories.
The original ledger selection, its missing full-response limitation and the
separately dated reconciliation remain unchanged. Selection is based on the
original chronological two-visit ranking, not the observed light curves.

The two L2 products first supplied **40,320 header bytes** with zero table
values. The separate science scope acquired exactly **155,250 table bytes**.
It retains 1,125 rows, 1,923 eligible overlapping windows, zero positive
crossings and 13 negative crossings forming three clusters. Both stable
arithmetic tests and all **23,076 numerical/discrete audit comparisons** pass.

The image preflight read no image values and verified **176 unique exposure
joins and 812 exact checks** for the 88 retained context rows. The separate
payload scope acquired **56,320,000 paired-image bytes plus 140,800 smearing
bytes**, exactly the nine frozen ranges. All nine first attempts succeeded;
no additional range or native calculation was substituted after inspection.

All seven inherited image tests and both new one/two-stack tests pass in the
full workflow checkout before image access. The partial local snapshot lacked
the inherited reference module; that local import limitation is disclosed in
the prospective protocol and did not require a method change. The independent
image audit passes **283,611 numerical comparisons and 481,748 exact checks**,
with zero disagreements at the original tolerances. All three final labels
are **CORRECTION_LINKED**, in both original coordinate conventions.

The image result preserves all compressed raw ranges and receipts, native
event maps, complete diagnostics, independent reference, audit, summary,
three figures, report, next action, execution status, environment, test and
analysis logs, and the checksum manifest. Twenty-four local image-review
files match the immutable manifest, including every receipt, all three
figures, diagnostics, independent reference and logs. The L2 review files
and figure also match their result manifest. Every figure was visually
inspected before the interpretive continuation was written.

This completes and closes the HD 136352 pair under the fixed diagnostic.
The correction label describes coupling to delivered processing; it is not
a unique physical-cause determination. No qualified candidate, detector or
observing coverage is added. No residual study is needed by the predeclared
branch rule. Rank-4 TESS_260647166 remains the next independent CHEOPS pair,
requiring its own metadata and science-byte freezes before any new values.

[Immutable image report](https://github.com/andersenmartin-blip/setisearch/blob/3f5053ee7d35afed31666b95daf9b3b5029956fc/results_ls8r_images/REPORT.md) ·
[Immutable L2 report](https://github.com/andersenmartin-blip/setisearch/blob/69108d1939f5a1ed6a466d46f7376ed0f90dc2fb/results_ls8q_l2_screen/REPORT.md) ·
[Current scientific interpretation and next action](LS8R_CONTINUATION.md) ·
[Current project status](PROJECT_STATUS.md).
