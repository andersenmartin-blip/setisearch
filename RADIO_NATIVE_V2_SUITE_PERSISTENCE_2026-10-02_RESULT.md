# Radio native v2 — immutable suite persistence and prospective transition

**PREPARATION_VERIFIED_EXECUTION_BLOCKED.** The earlier 401-test run passed its tests but exited 1 when its postlude tried to create an existing final-summary alias. That original failure, summary and aliases remain retained. A new publisher now writes immutable, separately named attempts; capture selects one attempt with an externally supplied raw SHA256. A passing JSON alone does not establish publisher exit or grant execution authority.

Two actual fifteen-module runs each passed **419 tests**, with zero failures, errors or skips, and each exited **0**, including persistence. All **946 source/test/wrapper pins** remained identical within and between runs. The second run also preserved the first summary and a deliberately synthetic legacy alias. Attempt 1 took 215.020875 seconds; attempt 2 took 213.944900 seconds. A duplicate attempt number exited 1 before bootstrap or tests, preserving the existing evidence.

The 18 new publisher tests cover no-clobber publication, concurrent destination creation, short writes, interrupted fsync/cleanup, malformed or false passing summaries, selected digest and current source drift, path/root replacement and symlink/hardlink refusal. Failed publication retains existing evidence and fails the caller; selection is a point-in-time content/source check. Late cleanup failures do not constitute proof that no final file exists. Actual clean publisher exits are recorded separately.

## Fresh blocked snapshot p

Plan p and the fresh complete runtime snapshot contain **928 repository code files, 38 inputs and 1,366 runtime files**. Capture, launcher preflight and machine preparation audit pass in the actual exact ten-value environment with Python `-I -S -B`. Attempt 2 is selected by raw SHA256 `7bd34cf4a85dd5e77199e3eafd1b6cbdc6dcfe26fbcbf5549b2ed63bf3e4150b`; its 244,807 raw bytes are an explicit freeze input. No shared alias is used for selection.

The registered 33-file control remains unchanged. Plan p has the same bytes as plan o because the registered control source did not change; its distinct path and newly captured complete freeze bind the new preparation publisher and selected tests. This is a fresh blocked snapshot, not a new invocation. All five execution blockers remain. The synthetic `final-suite-summary.json` is explicitly **not a test result**.

[Persistence evidence](results_radio_native_v2_suite_persistence_20261002a/suite-persistence-verification.json), [fresh capture](results_radio_native_v2_suite_persistence_20261002a/preparation-capture.json) and [machine audit](results_radio_native_v2_suite_persistence_20261002a/preparation-verification.json) are retained. These new checks are self-review and machine audit, not an independent human review.

## Prospective c activation candidate remains unregistered

A separately held candidate changes only four transition constants, two spent-history tuples and three equality guards to membership checks. It preserves refusal of **both** historical a and b marker paths and activation commits. The production activation module remains b and unchanged.

The first adapter mistakenly loaded the production b module into the original test fixture; its retained result contains three failures. Its 13 baseline tests must not be counted as c qualification. A distinct corrected adapter substitutes only the two fixture loader lines in held test bytes, proves candidate object identity, and passes **16 tests**, including three historical-spent checks. Both attempts and the diagnosis remain retained. The successful adapter uses the actual exact ten-value environment and `-I -S -B`; all five candidate input pins stay unchanged. Temporary test Git markers are inert fixtures. No project c marker, ledger, claim or control was created.

## Original ledger observation and remaining integration

The original b ledger remains exactly one 496-byte spent record, raw SHA256 `f28120ed840a8052589890548a30a825ed1d320a8fcbef7b590d8e67b7358e50`. Its source observer, activation receipt and spend witness were fetched at public commit `a4c3fb6bf11eaf6c716a64f57f95123716f5dd0e` and matched local raw content and Git blob identities before observation.

The existing observer was compiled from these held, externally pinned source bytes and only `observe_spend_storage` was called. An active audit hook refused mutation opens, mutation operations, network and subprocess operations during observation. Six malformed in-memory witness variants were rejected. Original directory/record identities, modes, sizes, allocation, modification/change stamps and record digest matched before and after; access times are not an immutability claim. Current ledger overhead is **4,592 logical bytes / 8,192 allocated bytes**, covering directory and record. This is read-only point-in-time preparation; it grants no spend or future lifetime authority.

[The observation](results_radio_native_v2_suite_persistence_20261002a/historical-ledger-read-only-observation.json) and [public input readback](results_radio_native_v2_suite_persistence_20261002a/historical-ledger-public-input-readback.json) define the current historical inputs. The original one-record observer correctly rejects adding a new claim to that root. Before any prospective control, worker admission and spending must be reviewed together for a **separate fresh private ledger**, preserving the original root. Historical and new ledger rows plus retained failed-scope storage must be authenticated, checked for inode/path aliases, charged once under unchanged caps, and observed through the entire protected workload. A complete new freeze, execution preread, public activation readback and whole-lifetime resource/runtime joins are still required. This integration is not yet implemented or admitted.

## Scientific and period status

Original b remains CLOSED_FAILED with **0/8 completed engineering cases**, its 107 original files / 70,168,047 bytes retained and its claim permanently spent. No additional protected control, native/scientific case, telescope read, full-size source generation, RNG draw or external person message occurred in this preparation.

HD189733 remains selected; HD1461 HOLD; GJ724 reserve. Spectra and holdouts remain unopened; native8 unreserved; 127/24 NOT ACTIVATED; LS paused; CHEOPS UNSENT. Source/native/scientific admission, transport and cumulative quotas remain blocked. The work period ends **9 October 2026**, without automatic extension, restart or target change.
