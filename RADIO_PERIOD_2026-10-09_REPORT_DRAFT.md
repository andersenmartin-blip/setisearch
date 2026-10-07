# Radio period report: draft for 9 October 2026

**DRAFT — evidence through 7 October 2026, not final period closure.**

The independent radio pilot planned for 26 September–9 October has not run.
No new telescope spectrum has been scored in this period's selected pilot.
The current result is a bounded failure to reach scientific execution, with
reusable component evidence and explicit requirements for a future attempt.
It supplies no detection, rejection of a sky signal, empirical search sensitivity
or new disposition for an earlier unresolved candidate.

This reader-facing draft is based on immutable checkpoint
`af5b25a97f35d112a9917acb96f7a1eb09c4fa3f` on
`m43-support-qualification`. It summarizes existing outcomes without rerunning
their workloads, auditing every underlying artifact anew, opening telescope
values or reserving scientific work. Final consolidation remains **9 October**;
the newest branch and intervening authorized results must be reconciled then.

## Plan outcome

The [original plan](https://github.com/andersenmartin-blip/setisearch/blob/af5b25a97f35d112a9917acb96f7a1eb09c4fa3f/RADIO_TWO_WEEK_PLAN_2026-09-26.md) required an independent
ON/OFF sequence, a frozen primary screen and recovery/interference/null gates,
a bounded pilot, follow-up of survivors and a readable period report. It
explicitly allowed a bounded failure report if access or scientific gates failed.

| Obligation | Available evidence as of 7 October | Outcome |
| --- | --- | --- |
| Select independent observations from metadata | HD189733/HIP98505, cadence 85030, AGBT16A_999_97 scans 0003–0008 selected under the authorized metadata ordering | Selected; metadata eligibility does not establish measured pointing calibration or spectral admission |
| Freeze and qualify the source-specific primary screen | Geometry and receiver bank retained; primary remains neighbor9; original source preparation remains non-executable | Incomplete |
| Establish recovery, interference and null behavior | Three synthetic calibrations and one bounded diagnosis completed | Calibration failed its frozen finite-support prerequisite; evaluation runs and opened evaluation values are zero |
| Qualify execution and decoding | Bounded process-IO evidence, one actual controlled sixteen-row handoff and later source-only preparations | Useful partial evidence; complete runtime/codec/transport/durable scientific admission remains absent |
| Run the independent telescope pilot | No selected pilot spectrum scored | Not completed |
| Follow every surviving pilot cluster | No pilot-derived trigger or cluster inventory exists | Unassessed |
| Report outcome and continuation | Q inventory and this readable draft | Draft complete; latest-state final consolidation remains due 9 October |

The failure concerns the ability to run the specified experiment. It is not a
negative astronomical observation.

## What changed, and what those changes establish

The [original calibration result](https://github.com/andersenmartin-blip/setisearch/blob/af5b25a97f35d112a9917acb96f7a1eb09c4fa3f/RADIO_HD189733_PANEL_2026-09-28_RESULT.md)
preserves all three failed calibrations and the one permitted diagnosis.
The 201 finite and 180 empty shifted maxima are **381 correlated resamplings**,
not independent controls. No settings were changed after failed calibration.
Independent diagnosis reproduced every empty/nonempty outcome: some shifts
had no compatible hypothesis with at least two active epochs simultaneously
above S/N 3. This is legitimate no-eligible-hypothesis probability mass,
not missing computation. The frozen certificate required every conditional
maximum to be finite, so these completed realizations could not qualify it.
Discarding empty rows would not establish a calibrated false-alarm tail.
A future method contract must explicitly handle this outcome under a fresh,
prospectively scoped and disjoint calibration/evaluation allocation.
The later 127-reference/24-evaluation proposal remains inactive: its 151
proposed identities have zero generated values, executed cases or charged
allocations. Keep that proposal separate from the earlier closed conditional
evaluation-attempt allocation, which remains charged despite zero evaluations.

F established bounded same-child kernel-IO observations for a deterministic
control. [G](https://github.com/andersenmartin-blip/setisearch/blob/af5b25a97f35d112a9917acb96f7a1eb09c4fa3f/RADIO_CODEC16_2026-10-06G_RESULT.md) then genuinely encoded,
transferred and bit-exactly decoded all sixteen controlled chunks, checked the
selected 65,536-channel row intervals against independent construction, and ran
the maintained normalization. It bound **one calibration epoch1_on handoff**.
That is controlled codec evidence, not an archive measurement or the required
twelve-handoff certificate. G used no archive spectral read, network request,
RNG draw or scientific case.

H–P added retained source definitions, producer/transport interfaces, loader
event models and tests. Such tests can establish the stated source behavior.
They cannot establish actual native callbacks, complete loader custody,
positive production acknowledgments or telescope data analysis. Historical
test cohorts and corrections remain distinguishable; their passing counts
are not aggregated into independent scientific trials.

[Q closure preparation](https://github.com/andersenmartin-blip/setisearch/blob/af5b25a97f35d112a9917acb96f7a1eb09c4fa3f/RADIO_CLOSURE_2026-10-07_PREPARATION.md) authenticates
232 retained report/metadata bodies (3,374,885 bytes), including 214 root RADIO
reports at its completed-P input checkpoint. Eleven new administrative audit
tests passed, final-source reconstruction matched three output bodies, and six
decisive original JSON bodies received complete immutable readback.
That inventory supports a reproducible account of reported outcomes; it does
not independently requalify every historical runtime or archive.

## Why execution remains blocked

Two concrete input/access failures remain:

- [K original-byte recovery](https://github.com/andersenmartin-blip/setisearch/blob/af5b25a97f35d112a9917acb96f7a1eb09c4fa3f/RADIO_RUNTIME_RECOVERY_2026-10-06K_RESULT.md)
  verified 902 original files / 88,333,667 bytes in fresh storage, but
  **136 original members / 211,319,131 expected bytes** remain missing or
  mismatched. These include h5py/hdf5plugin, their libraries and metadata,
  two scripts, NumPy RECORD and original pyvenv.cfg. Original archive transfers
  failed with HTTP 502; regenerated files are not original-byte recovery.
- [M observation](https://github.com/andersenmartin-blip/setisearch/blob/af5b25a97f35d112a9917acb96f7a1eb09c4fa3f/RADIO_MAPPING_KERNEL_2026-10-06M_RESULT.md) stopped at
  `ns/pid` with EACCES before maps, auxv, executable or vDSO reads.
  Its failed operation is closed without retry. Source tests do not supply
  the denied observer capability.

The original metadata preparation still has eleven missing diagnostic labels
and six false authority flags. These labels belong to an inert historical
constructor; they are not an interface to fill in to activate science.
The [authoritative production-gate audit](https://github.com/andersenmartin-blip/setisearch/blob/af5b25a97f35d112a9917acb96f7a1eb09c4fa3f/results_radio_proc_io_control_20261006f/AUTHORITATIVE_GATE_AUDIT.md)
distinguishes them from the maintained typed scientific validators.

A future native continuation requires genuinely new authentic missing runtime
inputs, permitted observer access and independently complete current-runtime,
mapping/content, kernel, collector dependencies, startup/descendant and terminal
evidence. It must first publish and read back a distinct integrated executable
outer with cumulative one-shot bounds. Telescope access additionally requires
the source/protocol, codec/runtime, recovery/interference/null, genuine hosted
transport, actual durable publication/reservation and fresh allocation gates.
Obtaining package bytes and observer access alone would not resolve the
calibration-contract failure or complete those scientific obligations.

## Tested scope and sensitivity limits

The selected sequence has ON scans 0003/0005/0007 and paired OFF scans
0004/0006/0008. Existing extraction geometries have 65,536 channels; they are
not newly authorized search bands. The inactive proposal scores only
81 carriers across 226.840273 Hz in each synthetic calibration/validation role,
with 81 linear rate labels from −4 to +4 Hz/s, eight widths and four
two-or-three-epoch activity subsets. It is not a scan of every extraction channel.

There is **no empirical telescope recovery curve, flux/EIRP limit, measured
sky false-alarm rate, pilot missed-injection census or search-based rejection**
from this unexecuted pilot. Barycentric, curved-track and planetary completeness
are unestablished. Digital synthetic and controlled codec checks do not fill
those gaps. Earlier unresolved events retain their earlier dispositions.

## Resource accounting

The **2,920 seconds / 5,512 MiB** figure reconciles sixteen selected,
permanently charged reservation envelopes. It is neither measured use nor
complete period history. The artifact reservation subtotal is 5,779,750,912 bytes.
Contents-C was refused before admission; its prospective envelope remains
charged separately from admitted execution.

Five process-address-space guard controls and K's separate administrative copy
envelope are outside that subtotal. Address space is not artifact storage.
H's proposed 600-wall/540-CPU-second, 448-MiB-artifact and
4-GiB-parent+1-GiB-opaque-read scope remains **unallocated**.
Whole-period measured resource totals remain **unknown**, not zero.
No reservation is refunded, reset or silently reused.

## Preserved dispositions and finalization

HD189733/HIP98505 cadence85030/neighbor9 remains selected.
HD1461/HIP1499 cadence71139 stays on its pointing-provenance hold; GJ724/HIP91608
cadence73005 is untouched reserve. Original 112+128 M43AF holdouts remain
unopened. Native8 is unreserved; 127/24 is inactive; M43AI stays failed/closed;
M15/M33 and earlier unresolved cases retain their dispositions. LS is paused
at LS8BD–LS8BE with LS8BF untouched; CHEOPS is UNSENT. The old synthetic
acquisition ledger remains closed/exhausted.

On **9 October**, read the newest branch status, direction and plan; reconcile
any intervening authorized evidence; finalize this report with the actual
period-end outcome and complete evidence links; update main's overview; and
close the blocked route for this period. Do not relabel this 7 October draft
as the final report before that review.

The supported current decision is to close this blocked route for the period
closure if its required inputs/capabilities remain unavailable. A subsequent
search or named method/information study needs its own prospective scope.
No extra target, external person message, paid observation, retry of a closed
scope or automatic plan extension follows this draft.
