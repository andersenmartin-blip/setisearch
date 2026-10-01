# Radio native v2 — source worker admission and supervisor integration

**Result: SOURCE_WORKER_LINKED_EXECUTION_BLOCKED.** The prospective source-generation
phase now joins the dedicated supervisor to an independently repeated worker check.
All **126 relevant Python tests pass**. No full-size source or telescope data was
generated, read or analyzed. This is preparation progress; it does not qualify the
eight-input run, scientific execution, host ledger or actual transport.

## What changed

The new standard-library-only
[`radio_native_v2_worker_admission.py`](scripts/radio_native_v2_worker_admission.py)
checks an independently retained SHA256 of the exact canonical admission bundle
including its trailing newline. The bundle binds the prospective plan, original
freeze, supplied public-preread metadata and fixed material paths. It checks the
outer ordinal, source domain and archive prefix, strict field types, original caps,
exact preparation argv and minimal environment, Python executable bytes, and every
materialized code/template file and directory. Missing, extra, altered, aliased,
hard-linked, FIFO and cached-code entries fail. Existing preparation outputs refuse
scope reuse. The bundle is reopened after material reads.

The **supplied public claim remains unverified**: this local checker cannot establish
that an immutable GitHub readback actually occurred. Its successful status is
`LOCAL_SUPPLIED_PREREAD_VALIDATED_EXECUTION_BLOCKED`; publication verification,
complete expected runtime closure, parent environment joins and all execution
authority remain false.

The derived `prepare.py` checks its actual interpreter flags and `sys.orig_argv`
before writing anything. It compiles bounded, hash-checked source buffers directly
instead of using an import loader which could read unchecked `.pyc` files. It
repeats the bundle/material checks and then invokes the independently pinned
materialized fixture's `require_execution_ready()`. The preparation identity and
SHA256-counter source writes are after these checks.

The fixture's prospective source phase now materializes all three derived files,
retains and hashes the per-case bundle, and dispatches the exact preparation role
through the dedicated subreaper. It checks the terminal subreaper receipt before
examining prepared source data. Derived recipe paths and arguments carry the same
bundle binding; unrestricted standalone public recipe regeneration is no longer
claimed.

The supervisor has a read-only admission-check CLI and a separate preparation
dispatch. Before compiling candidate admission or fixture code, it binds their
bytes to independently reviewed literal bootstrap pins. A supplied bundle cannot
choose an executable implementation. Dispatch repeats admission and the fixture
gate before `mkdir` or `Popen`, requires actual isolated interpreter flags and the
minimal environment, and charges validation time to the preparation deadline.
Its fixed preparation controls retain the original 600-second, 192-MiB case and
512-MiB individual-process limits; tiny probe caps are separate.

Subreaper measurements are durably written as pending. Filesystem, reserved final
receipt storage and time checks then determine disposition. The final receipt fsync
and process termination require independent outer observation; the local receipt
does not claim that join.

## Verification

[`verification-summary.json`](results_radio_native_v2_source_worker_integration_20261001b/verification-summary.json)
records the actual read-only preparation audit and refusal controls:

| Check | Actual result |
|---|---|
| Current repository code inventory | 920 files |
| Frozen preparation inputs | 6 files |
| Original Python/NumPy/Git/Node/ELF runtime scope | 1,366 files |
| Runtime plus engineering supplement union | 1,606 files |
| Materialized code and three derived templates | Match current prospective pins |
| Audit and refusal controls | 15.504 seconds |
| Direct derived worker with locally valid supplied claim | Refuses at the fixture gate; no identity, source or new scope entries |
| Dedicated supervisor with the same supplied claim | Refuses at the fixture gate; no preparation child or supervisor scope |

The two local structural controls deliberately use a **synthetic, unverified public
claim** with a placeholder commit. No real execution preread is represented by that
fixture. The separate isolated supervisor read-only check succeeds while preserving
`publication_claim_independently_verified=false`. The actual closure audit uses a
fresh original freezer capture and independently recomputes its named scope; the
synthetic claim is used only to exercise the still-closed worker gates.

A fixed tiny orphan probe reaches terminal ECHILD with two kernel `wait4` receipts.
Independent outer observation covers its supervisor's receipt fsync and termination:
**0.159 seconds**, maximum individual-process RSS **40.31 MiB**. This includes the
observed supervisor launch lifetime; it is not a measurement of source generation,
all descendant wait chains, the outer test driver's own termination, or the original
eight-case shared storage/time allocation.

[`final-tests.log`](results_radio_native_v2_source_worker_integration_20261001b/final-tests.log)
contains **126 tests, all passing in 31.104 seconds**: 18 fixture, 22 admission,
22 supervisor, 23 independent preparation audit, 15 compact verifier and 26 original
freezer tests. Negative controls cover extra actual interpreter options, malicious
cached admission code, FIFO/oversize reads, substituted implementations, stale
bundles, case relabeling, missing closure parts and resource disposition failures.

Historical logs are explicitly labelled. The first combined development run had
59 tests and two failures while dependencies were being refreshed; the pre-review
125-test run subsequently passed. Independent review then found the synthesized
argv and unvalidated `read_bytes()` weaknesses, which were fixed before the final
126-test run and final audit. The earlier blocked snapshots remain intermediate
work; the current prospective revision is
[`20261001d.plan.json`](config/radio_native_v2_compact_eight_input_control_20261001d.plan.json),
with [`the current original local freeze`](config/radio_native_v2_source_worker_integration_20261001b.runtime.json).
Previously published `20261001a` and `20261001b` plans remain historical and unchanged.
This is a preparation revision, not a retry of any executed case.

Reproduce in a **fresh preparation output scope** with:

```sh
PYTHONPATH=src:scripts:tests python -B results_radio_native_v2_source_worker_integration_20261001b/verify_integration.py
```

The verifier refuses differing existing snapshots and exclusive output collisions.
Published evidence is retained rather than overwritten. A later code change needs
another prospective snapshot and reviewed supervisor bootstrap pins.

## Remaining work and project state

The original five blocker categories remain open. This change connects **only the
preparation source role**. Control, caller, command reader/tail, projection and final
verifier admissions still need the same complete pipeline treatment. Complete
runtime/environment closure and a genuinely verified immutable execution preread
remain unjoined. The whole material runner must be independently observed through
final metadata fsync and termination, with authoritative disposition after whole
scope storage/time checks. Actual full-size source/terminal identity evidence has
not been collected.

Next: finish the other worker roles and the outer measurement/finalization join;
publish and verify the exact execution preread; only then permit one fresh eight-input
engineering control under the unchanged original caps. That control would still
precede native physical/recovery/RFI/null checks and the separate 127/24 validation.

All protected workload counters remain zero: native cases/reservations, RNG draws,
telescope/holdout reads, Functions SDK and connector calls. Administrative code
inventory and authorized Git publication are separate from those workload counters.
No external messages were sent. HD189733 selected; HD1461 HOLD; GJ724 reserve;
127/24 **NOT ACTIVATED**; spectra/holdouts unopened; LS paused; CHEOPS UNSENT.
Review 2 October; consolidate 9 October without extension.
