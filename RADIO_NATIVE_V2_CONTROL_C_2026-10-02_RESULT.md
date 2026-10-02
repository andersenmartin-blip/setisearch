# Distinct c engineering control — 2 October 2026

The single c engineering invocation is **CLOSED_FAILED, 0/8 completed, permanently spent**. It exited with process code 1 after admission and durable consumption, before any case workload. The retained driver traceback identifies a cold-start phase contradiction: the fixture creates the exact eight empty case directories, but the admitted measurement driver's control-role check still requires `cases` to be absent. No retry, resume, cleanup, rearm or second invocation was performed.

## Immutable preparation and publication sequence

| Checkpoint | Commit | Evidence |
| --- | --- | --- |
| Integrated preparation | `e422fa4bb61778a5861c4376fd694c37c9208cf6` | Unchanged plan r, runtime freeze and 49 material files; prior 541-test preparation pass |
| P: distinct c preread | `f033690f163e10287bfe00a4733edef8ed6c9543` | Exact 25-field proof; 171 unique preparation files / 6,815,970 raw bytes authenticated by fresh public GETs; 46 metadata-tool tests passed |
| A: single activation marker | `f514d782a0f807223e4bc47cb0b330b4b46a198f` | Sole parent P; sole Git delta is a new c marker; all six forbidden authority/retry fields false |
| B: fixed launch sidecars | `051d6f69bfab9f5989009faf871de5048693ca2f` | Sole parent A; 11 metadata files / 39,196 raw bytes; four exact input descriptors |

The execution checkout remained exactly A while public B sidecars were held at their fixed local paths. Root public GETs verified all 11 B files and all four raw inputs. An independent machine-agent review additionally GET-verified the config, all four inputs, marker, marker-checkout receipt, B branch/tree/parent identities and local HEAD A. These are machine checks, with prior component authorship disclosed; no independent human review is claimed.

The fixed config is 1,123 raw bytes, SHA256 `462456127bcbc7a4e90cd0dcafb62cca7b6e47d9d445868730f5346a781ac33f`, Git blob `98df5207ef1d6630beda240f959335939af95409`. The activation public readback is 582 raw bytes, SHA256 `8e82df2207171080df6b645b70b7063b7ae147a076098876fa113983738884d2`. The separate read-only marker checkout check completed the activation-only runtime custody phase without consuming an invocation.

## Exactly one actual invocation

The caller exclusively created an empty, process-owned private c journal with mode 0700, outside the fresh control scope. It then used the pinned Python executable, exact `-I -S -B` fixed launcher argv, independent public config SHA256 and exactly ten public environment values. The retained [start record](results_radio_native_v2_control_activation_20261002c/single-launch-start.json) records UTC start `2026-10-02T19:11:40Z`; the fixed launcher was invoked once. The bootstrap and external stdout/stderr are retained separately from the measured control scope.

The private journal contains exactly one permanent 496-byte record, `spent-c585a1bc62abf3f7245e2916777ee3cf7529d0cdbca14613093593078b546c76.json`, SHA256 `95b17d2aee22bfb27089a5571236dcee2d186dc4746b5b12b6b9538e695d505f`. It binds A, the exact c scope and activation receipt, with `one_invocation_spent=true` and `state=SPENT_BEFORE_WORKLOAD`. A [byte-exact public copy](results_radio_native_v2_control_activation_20261002c/public-c-spend-record-copy.json) is retained; the private journal itself is excluded from publication.

Fresh activation-time runtime/preflight, historical observation and durable consumption progressed far enough to create the c scope, materialize all 49 frozen files, and launch the admitted measurement driver. This does not turn preparation labels or false lifetime fields into scientific or whole-control qualification.

## Observed failure and its limits

The actual [driver stderr](results_radio_native_v2_compact_control_20261002c/measurement-driver-stderr.log) ends with:

```text
ValueError: Existing role output/scope reuse refused: .../results_radio_native_v2_compact_control_20261002c/cases
```

In the retained sources, `run_control` precreates `cases` and all eight ordinal directories before starting the driver. Driver admission calls worker `_validate_role_phase`, which applies `_absent` to `cases` for role `control`. Admission fails before finalizer driver-identity output. The fixture observer consequently reports `Required direct-child identity was never verified`; the outer launcher then reports `Observed control child failed or emitted unexpected stderr`. These wrapper errors are consequences of the retained admission traceback, not evidence of a completed case.

The frozen admission unit fixture removes `cases` when constructing successful synthetic control material. Its existing scope-reuse test expressly rejects an empty `cases` directory. That test shape does not cover the integrated fixture's newly reserved eight-directory hierarchy; the retained independent diagnosis identifies this coverage gap without running or modifying the failed control.

All eight directories are empty. There is no deterministic source generation, case result, successful driver identity or control completion report. The outer fixture child was reaped with exit 1 and retained complete pipe output; its observed lifetime was 6.414507330 seconds and wait4 maximum RSS 46,551,040 bytes. The failed launch disposition records 24.926409126 elapsed seconds from its admission anchor. The driver's own retained observation records 0.925 seconds, exit 1, an unverified reported identity and incomplete descendant qualification. These are observations of this failure, not a successful lifetime/resource join.

The terminal scope inventory contains 68 files and 21 directories, 3,853,729 logical file bytes and 4,087,808 allocated bytes, excluding the separately accounted private c journal. All 49 materialized frozen source files match their originals. All 1,002 prior production source/test/wrapper pins remain unchanged. The prior 541 tests and new 46 preread tests remain preparation evidence; no test pass is substituted for this actual failed integration.

The independent storage review includes directory sizes: the c scope is 3,939,745 logical bytes, and its separate journal adds 4,592 logical / 8,192 allocated bytes. Charging historical b, both journals, the c scope and final reservations yields 74,501,086 logical / 74,883,072 allocated bytes; the largest of the eight allocations is 9,312,635.75 logical / 9,360,384 allocated bytes. These stable terminal observations are below the unchanged 192 MiB per-case and 1,536 MiB whole-control storage caps. They do not establish unobserved transient peaks or complete lifetime qualification.

## Preserved historical and scientific state

Original b remains **CLOSED_FAILED, 0/8, permanently spent**. Its scope plus original journal remain 70,254,559 logical and 70,496,256 allocated bytes; its original 496-byte private spend record remains SHA256 `f28120ed840a8052589890548a30a825ed1d320a8fcbef7b590d8e67b7358e50`. Independent read-only ledger and storage reviews are retained alongside the c failure diagnosis.

Native reservations/executions, scientific cases, telescope reads and RNG draws remain zero. Native binding, hosted ledger join, hidden HTTP bytes, complete resource measurement and terminal observer's own future termination remain unqualified. HD189733 remains selected; HD1461 HOLD; GJ724 reserve; spectra and holdouts unopened; native eight unreserved; 127/24 inactive; LS paused; CHEOPS UNSENT. No person-directed messages were sent. Stop remains **9 October 2026**, without extension, restart or target change.

The next engineering preparation must reconcile control-role admission with the fixture-created exact empty eight-case hierarchy, while preserving refusal of populated, unexpected or unsafe state. It needs a meaningful cold-driver regression and a distinct immutable source/runtime preparation before any new prospective activation. Neither b nor c may be repaired in place or rerun.

## Publication readback

All **87 terminal-evidence/status files / 4,551,544 raw bytes** match complete public raw content and Git blobs at [immutable `5eae7e5`](https://github.com/andersenmartin-blip/setisearch/commit/5eae7e5428f08a1ec0aa481216a15b60c1b49fdf), tree `77ef3a936ae999d49c33fcbe08d50ddadb2caa48`, sole parent B. The over-1-MiB admission bundle required a complete decoded raw Git-blob GET because the contents endpoint returned its blob identity with empty content; that adapter disposition is retained and is not a public-byte mismatch.

The main README is updated at [`dc8d9d0`](https://github.com/andersenmartin-blip/setisearch/commit/dc8d9d0f59691d8eac63ca9aa9cb8eae224b8cb1), with complete 50,384-byte content and Git-blob readback matching. The [root terminal readback](results_radio_native_v2_control_activation_20261002c/public-terminal-readback.json), [adapter disposition](results_radio_native_v2_control_activation_20261002c/public-terminal-readback-adapter-disposition.json) and [main README readback](results_radio_native_v2_control_activation_20261002c/main-readme-public-readback.json) are retained. Publication does not grant authority or rearm c.

An [independent machine-agent terminal public review](results_radio_native_v2_control_activation_20261002c/independent-terminal-public-review.json) verifies 20 critical immutable public files / 1,071,014 raw bytes, including the main README, retained driver trace, frozen phase sources, spend copy and current outcome documents. It finds no claim corrections, distinguishes its selected-file review from root's full 87-file readback and discloses prior supervisor authorship. No new invocation or protected-state repair occurred.

## Retained evidence

- [Terminal record](results_radio_native_v2_control_activation_20261002c/single-launch-terminal.json), [scope inventory](results_radio_native_v2_control_activation_20261002c/terminal-scope-inventory.json), [source preservation](results_radio_native_v2_control_activation_20261002c/post-terminal-source-preservation.json).
- [Independent B readback](results_radio_native_v2_control_activation_20261002c/independent-sidecar-public-readback.json), [root B readback](results_radio_native_v2_control_activation_20261002c/sidecar-public-readback.json), [marker receipt](results_radio_native_v2_control_activation_20261002c/marker-checkout-receipt.json).
- [Independent failure diagnosis](results_radio_native_v2_control_activation_20261002c/independent-terminal-failure-diagnosis.json), [ledger review](results_radio_native_v2_control_activation_20261002c/independent-terminal-ledger-review.json), [storage review](results_radio_native_v2_control_activation_20261002c/independent-terminal-storage-review.json).
- [Outer closed failure](results_radio_native_v2_compact_control_20261002c/compact-control-launch-closed-failure.json), [fixture closed failure](results_radio_native_v2_compact_control_20261002c/outer-closed-failure.json), [driver observation](results_radio_native_v2_compact_control_20261002c/measurement-driver-observation.json).
