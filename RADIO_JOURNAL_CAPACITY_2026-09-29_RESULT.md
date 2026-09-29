# Journal capacity and lossless history — 29 September 2026

**The current full-snapshot history design does not fit its 8-MiB ledger
allocation. A read-only lossless alternative now passes; its writable remote
integration remains unqualified.** No new Gaussian draws or cases were consumed.

This follows the completed [two-case Gaussian/native measurement](RADIO_GAUSSIAN_ENGINEERING_2026-09-29_RESULT.md).
Its measured score archives are small enough for the proposed per-case score
allowances. The independent cumulative-history calculation exposes another
resource obligation before any larger reference or scientific execution.

## Exact lower bound, not an observed 151-case run

The unchanged 127/24 proposal and compact phase budget were used only as metadata.
The calculation includes 151 case bindings, five minimum compact artifacts per
case, one consume, one scientific RNG-start and one finish event. It deliberately
uses zero artifact byte lengths and zero elapsed times in receipt fields and
one-character publication locations/revisions. Physical/gate artifacts are
omitted. Actual receipts can only increase these byte counts.

| Quantity | Canonical bytes / count |
|---|---:|
| Initial manifest/document | 68,498 bytes |
| Events / immutable versions | 1,208 / 1,209 |
| Latest snapshot lower bound | 631,825 bytes |
| All retained snapshot versions lower bound | **423,359,705 bytes** |
| Ledger reservation | **8,388,608 bytes** |
| Minimum excess over ledger reservation | **414,971,097 bytes** |
| Existing artifact reservations + history lower bound + failure reserve | **1,488,712,921 bytes** |
| Unchanged total evidence ceiling | **1,073,741,824 bytes** |

The initial document alone repeated once per revision requires 82,814,082 bytes.
The complete lower bound first exceeds the ledger allocation after zero-based
case 11. Looking only at the last snapshot would conceal the problem.

These are logical uncompressed canonical evidence bytes. This is **not** a
measurement of Git pack storage, compression or future delta protocols, and
it does not prove that all future representations are too large. It does prove
that the currently modelled complete raw snapshot history cannot be called
qualified under the published allocation. No resource ceiling has been raised.

The new capacity calculator reports a blocking lower bound or an explicit
NOT_QUALIFIED result; being below a lower bound never grants readiness. Nine
new tests include exact agreement with all actual immutable file sizes in
small durable histories, conservative receipt-size growth, ordering, integer
caps, cumulative limits and absence of allocation changes.

## Lossless archival repair demonstrated on the closed engineering history

A separate read-only format stores the final append-only event stream once,
plus the original digest and exact length of **every** historical revision.
Validation requires independently pinned original revision hashes, the archive
hash, complete contiguous version ordering, intact event chain and bounded
encoded/decoded sizes. It returns original canonical documents only; it does
not construct a lease, writable store or restart right. Partial consumption
states remain partial consumption states.

Applied once to the immutable published history at
`d201b56c12918073eb4d473a9f0215beff0493d6`:

- **19/19** original versions restored byte for byte, including the genesis,
  both consumption records and all intermediate RNG/artifact/finish states.
- **101,825 original bytes → 10,854 archive bytes** (89.34% smaller).
- Every original revision remains published; none was removed or rewritten.
- Thirteen new corruption/capacity/authority tests pass. Combined with the nine
  capacity tests, **22 new checks pass**.

Artifacts and complete input/code pins are in
[results_radio_journal_capacity_2026-09-29](results_radio_journal_capacity_2026-09-29).
The compact history contains journal receipts, not source or score payloads.
Those remain in the original Gaussian engineering archive. This one measured
encoding is not an upper-bound qualification for 151 cases.

## Exact continuation

Before a larger Gaussian/native physical/recovery/RFI/null allocation, implement
and prospectively qualify **incremental durable history storage and immutable
readback** using a bounded event/checkpoint representation. Bind every new event
to its predecessor and all original revision digests, count unique retained
archive bytes plus artifacts and transport overhead cumulatively, and enforce
capacity before mutation. Test interrupted publication, lost response, concurrent
append, incomplete prefixes, archive corruption and fresh-client read-only
recovery. Do not convert restored history into execution authority or erase old
snapshots. A new live engineering namespace must have a separate published
allocation, exact input/runtime pins and finite call/byte/time ceilings.

Then freeze the still-missing integrated Gaussian reference, native physical,
recovery/RFI/null and remote-publication experiment with genuinely new engineering
identities. The native threshold needs its actual same-law reference units;
old deterministic fixtures cannot be relabelled. Keep reserved scientific
127/24 cases NOT ACTIVATED and do not retest the two closed Gaussian cases.

This work does not consume a scientific evaluation or diagnosis allocation.
Primary neighbor9, selected HD189733/85030, HD1461 pointing hold, GJ724 untouched,
M43AI failed/closed, original M43AF 112+128 unopened, M15/M33 unresolved, LS pause
at LS8BD–LS8BE, LS8BF untouched and CHEOPS UNSENT all remain. No telescope spectra,
external messages, new target sequence or plan extension. Consolidate 9 October.
