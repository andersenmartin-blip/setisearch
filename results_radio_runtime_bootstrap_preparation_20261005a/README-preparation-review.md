# Independent package-bootstrap preparation review — 5 October 2026

The final engineering preparation has no remaining blocking review findings. The retained freeze reconstructs exactly through the pure builder, passes the gate's pure schema validator, and binds all 492 current repository source files plus the retained 1,244 runtime/installer pins. This review permits only the separately published, single-use package bootstrap described in `PROTOCOL.md`. Complete immutable preparation and activation readback remains a caller prerequisite before its sole genuine invocation.

The bootstrap identity is `7e4a63f99adcb7a9725211960b368db972e92b16c60bdf1a3d5220e49df2d52b`. The freeze is `config/radio_runtime_bootstrap_20261005a.freeze.json`, 555,890 bytes, SHA-256 `7bcdc460afd6cda314c32ece81419ceb2097e8e3caa4c67c99a0bf7b3754d9f6`. The complete original materialization plan remains 24,739 bytes, SHA-256 `fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25`. All wheel fields and the entire offline lock match that plan.

## Review and validation scope

The reviewer read repository source, the original plan, retained prerequisite metadata, all 479 stored installer representations, and the new freeze. It independently verified their bytes and source mappings. It did not read original selected runtime or installed pip content, access the genuine output root, fetch a wheel, invoke the genuine bootstrap or installer, import a scientific package, open telescope data, or activate a scientific allocation. Standard interpreter/library startup and synthetic subprocesses are outside those zero-count statements.

The final independent suites completed under the primary interpreter with `-I -B -S`: 83 gate checks, 55 wheel checks and 22 builder checks, for 160 final checks. The gate suite used an external 45-second timeout and retained a complete exit-0 `Ran 83 tests in 2.025s / OK` summary. A focused stream-overflow check also completed separately. Synthetic tests use fixtures, bounded sleeping/printing subprocesses and explicitly mocked pipeline operations; they do not authenticate the real runtime or consume its allocation.

The installer representation check validated all 473 exact UTF-8 files and six canonical base64 files. Stored bytes total 5,940,913; decoded raw source/data total 5,690,699. Both raw and stored SHA-256/Git blob identities match the frozen prerequisite manifest. Relative seed paths, bytecode exclusion and stored modes match. The actual-data freeze check reread and matched every one of its 492 repository source pins, totaling 7,646,500 bytes, and compared the runtime/seed rows as retained metadata. It then rebuilt the complete canonical freeze without I/O inside the builder and matched `pure-preparation.json` and the exact lock.

## Findings resolved before source freeze

- The exclusive spent record now fsyncs both its file and containing directory. Gate-created directory entries receive parent-directory fsyncs. The published activation and caller's no-retry rule still permanently consume a refused allocation when source admission fails before a local spent entry exists.
- Proc and detached CLI reads now precharge every requested syscall size, including short reads, failed requests and EOF probes. Returned bytes remain separate. ZIP requests enter the regular charge category, while actual returned archive bytes enter the ZIP received category; the report explains this difference.
- Fresh installer copies preserve both pinned 0644 and 0755 modes through explicit `fchmod`. Their full hashes and modes are checked before the sole pip child and again through the final manifest.
- The prospective joined destination inventory rejects cross-wheel file/directory prefixes, case and Unicode aliases, generated-script conflicts, and predicted file/directory count overflow. Storage admission includes three payload copies, archives, seed, bounded acquisition/inspection receipts, samples, terminal evidence and filesystem rounding. It can refuse before pip when the finite estimate does not fit.
- The terminal after-pin JSON is written before the operational hash inventory, so its full hash is included. Only the future manifest and final report are excluded to avoid hash cycles; the caller independently preserves and hashes all final objects.
- Pipes are registered immediately after launch and receive storage admission before reads. A partial write preserves the complete bounded received chunk, hash, written-prefix length and selected file size in failure evidence. Bounded post-kill draining retains available startup output. Whole inspection receipts, including member hashes, are retained separately before the child.

The static wheel helper independently checks the complete archive hash, bounded EOCD/central directory, local-header consistency, member-region continuity, raw DEFLATE end/consumption, length/CRC/hash, path safety, exact RECORD coverage and exact metadata/tags. It neither extracts nor imports members. The gate refuses `.data` installation schemes without a separately reviewed mapping. Pip then receives the fixed offline, no-dependency, hash-required, binary-only, no-bytecode command from the owned wheelhouse and frozen seed.

## Retained diagnostic outcomes

Producer logs 05, 06 and 08 lack complete unittest tails. They are retained and are not counted as passes; their cause was not established. The final producer log 09 and the independent final log contain explicit complete 83-check summaries.

`logs/reviewer-gate-tests-01.txt` is a deliberately instrumented diagnostic invocation that failed six process assertions. Its wrapper called `faulthandler.dump_traceback_later(8, repeat=True)`, which adds a watchdog thread. The exact attribution basis requires a one-thread parent, so it correctly refused that environment and killed/reaped synthetic children. This diagnostic result is not a positive validation. The unmodified source/test pair subsequently passed in the ordinary one-thread invocation retained as `logs/reviewer-gate-tests-02.txt`.

The diagnostic wrapper was:

```python
import faulthandler, runpy, sys
faulthandler.dump_traceback_later(8, repeat=True)
sys.argv = ["results_radio_runtime_bootstrap_preparation_20261005a/test_bootstrap_gate.py"]
runpy.run_path(sys.argv[0], run_name="__main__")
```

## Conditions and qualification limits

Before the genuine invocation, the caller must publish all preparation artifacts, read back their full immutable bodies or lossless representations and decoded identities, verify the original plan, publish only the fresh activation marker as a sole child of preparation, and preserve complete commit/tree/marker/source bindings in the detached witness. This review has not performed those future network actions. A source or configuration change requires reconciliation with these review pins before invocation.

The selected operation remains capped at 300 seconds, 1,536 MiB of logical/allocated artifacts, 3 GiB of parent requested reads, the full unobserved 1 GiB child read reservation, and a joined 4 GiB charged envelope. The direct child has 1 GiB `RLIMIT_AS` and 128 MiB `RLIMIT_FSIZE`. Sampling and prospective calculations provide bounded engineering observations; they do not certify blocked syscall/provider time, transient peaks, escaped descendants, aggregate RSS, crash persistence of all files, or complete pip/implicit loader I/O. A finite reserve cannot guarantee terminal serialization or completion after an adverse refusal; missing reports must remain missing.

Success can establish only `MATERIALIZED_PACKAGES_ONLY / PENDING_RUNTIME_QUALIFICATION`. All 16 original scientific/source authority flags remain false and all 11 scientific fields remain pending. Installed metadata does not authenticate a loaded HDF5 version. Capture A, hosted CAS and capture B remain closed, spent and nonretryable. Targets, cadence, schedule and holdouts remain unchanged; consolidation remains 9 October 2026 without automatic extension.

`preparation-independent-review.json` records the exact reviewed source, configuration, documentation and log pins. The review is an engineering readiness assessment, not an execution/runtime/scientific certificate.
