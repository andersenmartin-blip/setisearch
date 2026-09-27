# Score ancestry and immutable local restart — 27 September 2026

**A concrete score-reconstruction integrity gap is reproduced and a separate
guarded handoff passes 26 new tests. Telescope execution remains blocked.**
This reopens engineering under the latest continuation's specific-risk rule;
it does not reopen the four closed motion studies or any scientific evaluation.

## Demonstrated gap and scoped repair

A fresh local cadence produces 48 score vectors and 48 native-cache inventory
entries. Reconstructing the old `ScoreStore` with one finite cell changed from
−0.768373489 to +0.231626511 recomputes its own vector IDs. The unchanged legacy
`NativeRun.validate_store` and `checked_vectors` accept it even though its
retained native-cache score digest still describes the original numbers.
The new boundary rejects this exact mismatch. No detector or calibration was
called and no corruption of a published result has been established.

`score_handoff_radio` reconciles every scan/width digest in template order,
checks the actual typed source inventory and context, and seals owned immutable
bytes together with complete provenance. All **4,752 score cells and all 48
legacy vector identities** remain bit-exact. This is ancestry and handoff
evidence, not a repeat of the old normalization/score arithmetic qualification.
The already published three-template codec interface bank is reproduced at its
existing identity; no new physical template or search bank is constructed.

The opt-in `GuardedRun` wraps the old numerical producer and rejects ordinary
self-attesting stores at both downstream entry points. Existing modules remain
byte-for-byte unchanged for reproducibility. Therefore old callers do **not**
acquire the new protection automatically. Future integrations must explicitly
select the guarded path and preserve an independently retained receipt pin.

## Local checkpoint and failure evidence

The complete checkpoint is **44,192 bytes**: a 28-byte format prefix, 25,156-byte
canonical receipt and 19,008 bytes of uncompressed float32 vectors. Reopening
through a fresh run object reproduces the sealed store exactly. Receipt SHA-256:

`cf4a0a54781d2d8285e8d2252bfce2fadef0649a1ba0ddebe99c445c0b24a7c1`

| New boundary exercised | Result |
| --- | --- |
| Stale cache hashes, mixed/missing/reordered inventory, invalid vectors | Rejected |
| Wrong independently held pin or changed context | Rejected |
| Altered bytes, truncation, trailing data, oversized lengths, noncanonical JSON | Rejected |
| Symlink, FIFO, directory or already existing final file | Refused |
| Two concurrent writers to the same final name | Exactly one confirmed winner |
| Process exit before atomic installation | No final checkpoint |
| Process exit after installation or directory fsync | Explicit pinned recovery succeeds |
| File/directory fsync error or lost acknowledgement | No success returned; installed bytes are inspected explicitly |
| Mutation during read or insufficient modeled capacity | Rejected |

The writer uses a same-directory temporary file, file fsync, exclusive hard-link
installation and directory fsync; it never overwrites an existing final name.
The loader uses bounded lengths, an explicit binary layout and a caller-supplied
receipt hash, with no pickle or archive extraction. A newly calculated hash from
the file itself is not a substitute for that external pin.

Limits: the tests cover local POSIX behavior, injected I/O failures and actual
child-process exits, **not power loss, remote storage or adversarial control of
the process/filesystem**. A trusted producer and separately preserved pin remain
assumptions. Hash reconciliation is not independent numerical verification.
The new 32-MiB payload/2-MiB receipt ceilings and modeled additional buffers are
engineering bounds, not measured process RSS or qualified telescope capacity.
No remote admission, retry quota, telescope gate or scientific permission is
issued by checkpoint success.

## Retained attempts and unchanged science

The first baseline probe used the wrong return-value unpacking in its helper;
the first qualification attempt shadowed `unittest.TestCase.run` with a fixture
attribute. Both harness errors and their frozen source snapshots are retained.
The second qualification attempt passes all 26 tests in 2.737 seconds, with zero
socket, detector and calibration attempts. No failed science outcome was tuned.

One fresh fixture identity was constructed three times across the probe and two
qualification attempts: **294,912 generated local native values cumulatively**,
within the frozen 393,216 limit. This is one cadence, not three independent
controls. No original acquisition ledger was reused or reset. All fifteen
pinned prior inputs are verified unchanged before and after qualification.
The [protocol](RADIO_SCORE_HANDOFF_2026-09-27_PROTOCOL.md), configuration, code,
tests, failures and passing evidence are covered by
`RESULTS_MANIFEST_RADIO_SCORE_HANDOFF_2026-09-27.sha256`.

The original preparation remains under `HOLD_POINTING_PROVENANCE_UNRESOLVED`;
HD1461/HIP1499 cadence 71139 and the three approximately 34.23-arcminute ON
declination discrepancies are unchanged. The exhausted synthetic acquisition
ledger and empty prospective telescope genesis retain their original hashes.
All five execution blockers and the frozen 3-calibration / 24-case /
one-evaluation / zero-remedy limits persist. No spectrum, new metadata request,
source request, telescope reservation, physical bank or scientific trial was
added. The small conditional temporal remainder is still not full physics.

Primary remains `neighbor9`; M43AI stays failed/closed and the original 112+128
M43AF holdouts are untouched. M15 GJ581/M33 HD3651 remain unresolved. LS8BD–LS8BE
remain paused, LS8BF unopened and CHEOPS unsent. No external message, paid
service, booking, delegation or automation extension occurred.

## Exact continuation

This score-handoff/restart scope is closed; do not rerun its unchanged fixtures
as progress or count its local checkpoint as live durable admission. Its guarded
API and independently retained receipt pin are explicit obligations for any
future integration. The historical unguarded path remains evidence only.

No unblocked HD1461 telescope step is established. A useful next scientific step
still needs genuinely new same-scan RAW/FIL/log/file-specific conversion evidence
for AGBT16A_999_189 ON 0015/0017/0019, plus evidence-backed source/observer physics
and the concrete independent live admission/transport capability. Do not repeat
closed catalogue/code/login probes, expand the conditional parameter box, build
the huge bank, run the fresh panel or invent another generic hardening task.
Reopen work only for a named new input or a demonstrable implementation risk with
a bounded prospective scope. Preserve the current target and all dispositions;
the period is still consolidated on 9 October, without extending the plan.
