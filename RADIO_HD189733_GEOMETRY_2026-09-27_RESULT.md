# HD189733: widened geometry and separate window identity contract

The retained HD189733 metadata exposes a concrete incompatibility with the old
HD1461 setup. Under the declared nominal circular model, the earlier 129-channel
width and 16,384-channel extraction length do not cover the intended domain.
The smallest adequate values **among the tested choices** are **257 channels**
and **65,536 channels**. This is a design result, not scientific qualification.

## Conditional model and its limits

The [scope](RADIO_HD189733_GEOMETRY_2026-09-27_SCOPE.md) was written before the
offline calculation. Inputs are the retained catalogue's nominal period
2.21857567 days, radius assumption 0.03126 AU, eccentricity zero, all orbital
phases, a stationary observer and first-order Doppler normalization at the first
ON integration midpoint. The calculation uses the actual six-scan header clocks
and an upper reference frequency of 1425.85 MHz. No new remote data were fetched.

Writing `V = 2πa/P`, the phase-uniform displacement bound at relative time `t` is
`2 ν V |sin(πt/P)| / (c − V)`. The maximum absolute relative time is well below
half a period, so the same monotonic expression covers the continuous cadence
interval. This uses ordinary floating-point arithmetic; it is not a formally
outward-rounded certificate. A catalogue semimajor axis is used as the declared
emitter-radius assumption, not proven actual emitter kinematics.

| Retained quantity | Result |
| --- | ---: |
| Nominal velocity amplitude | 153,287.332115 m/s |
| Phase-uniform displacement bound | 46,085.050660 Hz |
| Phase-uniform integration-sweep bound | 430.044496 Hz |
| Integration sweep in native channels | 151.664249 |
| Explicit phase-zero integration-sweep witness | 429.824609 Hz |
| Old 129-channel width | 365.779941 Hz |
| Required half-window guard, including carrier-grid/filter margins | 46,589.770268 Hz |
| Available half-guard for 32,768 channels | 46,454.052505 Hz |
| Available half-guard for 65,536 channels | 92,910.940512 Hz |

The explicit witness shows insufficiency of the old width within this conditional
model; an upper bound alone would not prove that. The selected width includes one
additional channel in the sweep comparison. Window guards also include the fixed
99-carrier-grid extent, half filter width and interpolation margin. Compared
widths were only 129/257 and lengths only 16,384/32,768/65,536. There was no search
over telescope spectra or tuning against a failed evaluation.

**Still missing:** source-parameter uncertainty, a defensible emission-location
domain, observer motion, a full error budget, a qualified finite motion bank and
recovery coverage. Catalogue nominal values do not supply these. This result does
not assert detectability or actual-source completeness.

## Exact prospective geometry

For each anchor (1400.5, 1412.5, 1425 MHz), the fixed rule selects the nearest
complete HDF5 chunk centre whose full 65,536-channel interval stays within
1399.65–1425.85 MHz; ties use the lower chunk index. Indices below are half-open,
and frequency endpoints are the first/last channel centres, not channel edges.

| Role | Native interval | Chunk index | Low frequency (Hz) | High frequency (Hz) |
| --- | --- | ---: | ---: | ---: |
| Calibration | [167215104,167280640) | 159 | 1402140020.024552 | 1402325844.7410803 |
| Validation | [164069376,164134912) | 156 | 1411059742.5220742 | 1411245567.2386024 |
| Pilot | [159875072,159940608) | 152 | 1422952705.852104 | 1423138530.5686321 |

The [full geometry](results_radio_hd189733_geometry_2026-09-27/window_geometry.json)
contains 18 source/role groups, **288 disjoint source/ETag/time/feed/chunk
identities**, and **48 normalization blocks** (16 per role). These are distinct
frequency payloads in one cadence; they are not independent observations, nor a
fresh development/control panel by themselves.

The modelled extracted float32 volume is **72 MiB** across all three roles.
Decoding complete native chunks would process **1.125 GiB**; this is not a wire
download estimate. The existing reader's modelled buffer bound is **94 MiB**,
excluding native-library and operating-system overhead. Compressed wire cost and
runtime have not been measured for these payloads.

## Separate v2 binding, with all scientific gates retained

The unchanged legacy API correctly rejects the new geometry with
`prospective window geometry changed`: its contract fixes 16,384 channels and
four normalization blocks. A separate
[v2 metadata builder](src/seti_repeater/window_identity_radio_v2.py) now binds
the widened design under externally supplied SHA-256 pins. It validates every
source URL/size/ETag, time row, chunk and interval; recomputes header-derived
frequency endpoints; checks normalization partitions; and rejects shared chunks
across roles. It has no extraction, scoring or admission operation.

**Eight new tests pass**, including altered ETags/sources, shifted intervals,
duplicated time rows, normalization gaps and cross-role chunk reuse even after
embedded hashes are recomputed. The [raw test log](results_radio_hd189733_geometry_2026-09-27/window_v2_tests.log)
and [verification](results_radio_hd189733_geometry_2026-09-27/window_v2_verification.json)
are retained. Old tests and closed trial panels were not rerun.

The resulting [identity contract](results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json)
has content digest `64dfa0f50252a86953b45c112687da9386147c0e70ad0d2a686efc5592f05ffa`
and status **IDENTITIES_BOUND_SCIENTIFIC_AND_EXECUTION_GATES_PENDING**.
Both spectral admission and threshold transfer remain false. Neither the old
HD1461 preparation nor the new HD189733 preparation was changed to ready.

**Continue next:** qualify the source-specific motion/width and observer domain,
freeze fresh development/calibration/evaluation identities and the new numeric
transfer/recovery/RFI/null protocol, and connect the source-specific codec/runtime
evidence and cumulative execution ledger. Publish the integrated prospective
protocol before opening spectra. Preserve all triggers and failures. Neighbor9
remains primary; no scientific trial, telescope spectral read or external message
occurred in this geometry/binding work.
