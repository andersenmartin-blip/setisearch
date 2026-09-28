# HD189733: receiver-coordinate bank and fresh control identities

On **28 September 2026**, the active HD189733/HIP98505 cadence 85030 preparation
advanced from the completed widened-window identities to a bounded received
linear-drift bank. **69,984 factor comparisons and 14 new tests pass.**
This qualifies arithmetic and conditional support geometry, not telescope
admission, signal recovery, planetary completeness or a scientific result.

## An explicit ordinary-radio scope

The [prospective scope](RADIO_HD189733_RECEIVER_2026-09-28_SCOPE.md) fixes 81
rate labels from −4 to +4 Hz/s in 0.1 Hz/s steps. This is a search in **recorded
topocentric frequency and header-clock time**, not an orbital prediction or a
barycentric correction. A possible signal must have a linear received track over
the whole approximately 32-minute cadence. Curved paths, frequency jumps and
other drift rates remain outside the qualified model. Zero drift is included;
it is not automatically a reason to discard a trigger.

The finite scope is motivated by ordinary narrowband searching, including the
±4 Hz/s scope reported by [Price et al. (2019)](https://seti.berkeley.edu/listen2019/BL1327stars.pdf)
and the [official turboSETI description](https://github.com/UCBerkeleySETI/turbo_seti).
Our whole-cadence linearity restriction and neighbor9 pipeline are our own;
the cited searches' sensitivity or results are not transferred. Source and
observer motions are represented only through their combined received track.
No claim that all emitters near HD189733 lie in this family is made.

This prospective choice **does not alter the earlier nominal planet study**.
That circular model still requires width 257 among its tested choices. It is not
the adopted model for this receiver-coordinate preparation. The original
65,536-channel extractions, three frequency chunks and both preparation-only
contracts remain unchanged. Neighbor9 and its native widths
`[1,3,5,9,17,33,65,129]` are unchanged. No failed evaluation motivated this change;
no new-source evaluation has occurred.

For window centre C and rate label r, the factor is `F(t)=1+r*t/C`; at carrier q,
the frequency is `q*F(t)` and the actual drift is **q*r/C**, not exactly r away
from C. The maximum deviation from the nominal ±4 labels is below 0.000000324 Hz/s.
Time zero is the first ON midpoint. Exact rational conversions of the retained
binary64 headers preserve all 96 integration start/mid/end times; there is no
MJD string roundtrip or assumed astrometric epoch conversion.

## Coverage and numerical checks

Each of three distinct banks has 81×96×3 factors. Every factor was compared
against an independent exact-rational formula. The largest supported-carrier
arithmetic bound, including additional rounding allowances, is
**6.35e−7 Hz**, below the prospectively fixed **1e−4 Hz** allowance.

For a continuous rate label in [−4,+4], a reference carrier inside the scored
span and intrinsic signal support no wider than one channel, the largest filter
has the following conservative geometric bounds:

| Quantity | Bound |
| --- | ---: |
| Required half-support, including rate/carrier quantization, integration sweep, intrinsic support and bin rounding | ≤138.032898 Hz |
| Available half-support at width 129 | 181.472219 Hz |
| Required extraction half-span, including all support carriers and ±100 Hz receiver neighborhood | ≤8134.394048 Hz |
| Available extraction half-span | 92910.940512 Hz |

Exact numerators/denominators for every term are retained in
[arithmetic_and_containment.json](results_radio_hd189733_receiver_2026-09-28/arithmetic_and_containment.json).
This is **containment, not power recovery**. Smaller filters have no claimed
continuous-family coverage. Finite exposure, normalization losses, channelizer
response and the detector's actual end-to-end response still require controls.
Header-number arithmetic does not certify the telescope's absolute clock or
frequency calibration.

The new [ReceiverBank type](src/seti_repeater/receiver_bank_radio.py) binds the
external source/window pins, role, exact clock, rate bank and immutable factor
payload. It cannot be passed as an orbital DirectFactors object. Fourteen new
tests cover stale pins, roles, drift sign, zero/anchor factors, overlapping clocks,
nonpositive durations, immutable payloads, type separation and permission flags.
The [raw test log](results_radio_hd189733_receiver_2026-09-28/new_tests.log) is retained;
unchanged old pipeline tests were not rerun.

## Exact searched reference-carrier spans

There are **81 scored carrier centres** per role and nine additional support
bins on each side. Each reference-carrier span is only **226.840273 Hz**;
the approximately 186 kHz extraction is not all searched. Frequencies below
refer to the first ON midpoint; tracks then drift within the extraction.

| Role | Low carrier (Hz) | High carrier (Hz) |
| --- | ---: | ---: |
| Calibration | 1402232817.5449278 | 1402233044.3852012 |
| Validation | 1411152540.0424500 | 1411152766.8827233 |
| Pilot | 1423045503.3724797 | 1423045730.2127530 |

The [postflight scope audit](results_radio_hd189733_receiver_2026-09-28/scope_postflight.json)
checks the existing **288 disjoint native-chunk identities** across those roles.
All roles still belong to one observing date; this is not independent temporal
replication. No development telescope window has been allocated or opened.

## Fresh identities, unchanged failure gates and cumulative limits

The [control reservation](results_radio_hd189733_receiver_2026-09-28/control_identity_reservation.json)
contains **six development, three calibration and 24 evaluation identities**.
Their SHA-derived namespaces and 64-bit seeds are mutually distinct and do not
collide with configured identifiers found in **271 configuration files**.
No held-out input payload was read. Identifier uniqueness does not establish
statistical independence or fully specify a future random-data renderer.

The 24 evaluation recipes retain the existing 10 ON-signal / 10 matched ON/OFF /
two single-adjacent-OFF / two noise-null allocation, injection width/power values,
association rule and numerical recovery/RFI/null gates. Rate labels are assigned
prospectively in the fixed cycle [−4,−2,0,2,4], with carrier offset zero. Six
development identities reserve separate off-grid rates. Renderers and numerical
calibration/transfer settings are **not frozen by this reservation**.

The old unexecuted panel is archived and inactive: its **three calibrations,
24 cases, one evaluation, zero remedies** ceiling transfers prospectively to the
new source instead of being doubled. All these counters remain zero. No detector,
calibration, injection, native null or pilot was executed. The six additional
development reservations also remain unexecuted and cannot be used to retune
an exposed evaluation.

The new factor tables occupy 559,872 bytes in total; a future score store is
modelled at 1,539,648 bytes per role. The existing pipeline array formula gives
53,366,656 bytes per role, excluding reader, decoder, OS and other native memory.
This is a model, not a source-specific runtime or peak-memory benchmark. The
arithmetic/identity qualification took 14.856 seconds in Python 3.12.14 / NumPy
2.3.5. No telescope network request or spectral value was used. The literature
lookup is separately recorded and has no known total wire-byte count.

Fifteen prior invariant pins, the new source preparation, old exhausted acquisition
ledger and empty telescope genesis were verified unchanged. M43AI stays failed
and closed; original 112+128 M43AF holdouts remain untouched. HD1461's pointing
hold, unresolved M15 GJ581 and M33 HD3651, all older dispositions, paused LS,
untouched LS8BF and unsent CHEOPS persist. No external message was sent.

## Exact continuation

Receiver-bank arithmetic, conditional containment and fresh identity reservation
are complete. **Do not repeat this qualification or the alternate metadata run.**
The next concrete task is a receiver-specific downstream numerical adapter,
with explicit rate metadata and externally pinned bank/window identities. The
old orbital-specific downstream context cannot simply be relabelled or supplied
with invented orbital parameters. Reuse unchanged neighbor9 numerical kernels,
but retain a distinct receiver-provider type and source provenance.

Before executing any reserved control case, freeze its finite-exposure renderer,
normalization, exact calibration/null construction and cross-window numeric
transfer. Then execute the fixed recovery/RFI/null gates once, preserving all
triggers, vetoes, losses and failures. Source-specific codec/runtime handoff and
a published, verified integrated prospective protocol with cumulative resource
and trial accounting remain necessary **before telescope spectra**. The bank
report is not an authorization to open them. No automatic target substitution,
new schedule or extension beyond 9 October is authorized.
