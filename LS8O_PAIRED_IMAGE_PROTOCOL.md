# LS8O — frozen paired-image diagnostic for all GJ 1132 negative controls

Status: **FROZEN BEFORE IMAGE PAYLOAD ACCESS**.

The public metadata/join result is
`f83c33116e826bd412ed29a9119b94e6ecee7e0c`: **310 unique CAL/COR joins**,
independent audit PASS with **1,423 exact checks**, zero image bytes read.
Source identities, native frame indices, detector offsets and byte ranges
are fixed in `config/ls8o_images.json`. LS8N's five negative representatives
and the absence of positive clusters remain unchanged.

| Representative | L2 and independently joined native frames, stop-exclusive | CAL bytes | COR bytes | Smearing bytes |
|---|---|---:|---:|---:|
| TG000401_N0 | 74:105 | 9,920,000 | 9,920,000 | 49,600 |
| TG000403_N0 | 55:86 | 9,920,000 | 9,920,000 | 49,600 |
| TG000403_N1 | 118:149 | 9,920,000 | 9,920,000 | 49,600 |
| TG000403_N2 | 177:208 | 9,920,000 | 9,920,000 | 49,600 |
| TG000403_N3 | 283:314 | 9,920,000 | 9,920,000 | 49,600 |

Total paired-image payload: **99,200,000 bytes**; smearing payload:
**248,000 bytes**. Native frame indices were established by UTC/MJD/BJD and
exposure-counter joins, not presumed equal to L2 indices. Every context has
31 rows; local events are **14,15,16**, sidebands **0–11 and 19–30**, and guards
**12–13 and 17–18**. Each event sums three 60-second integrations.

## Unchanged image method and classification

Use the byte-unchanged `seti_repeater.cheops_image_pair.analyze` function:
SHA256 `54255f3b8a21ebb4c279243ce152b1501549f588630833d862657bc96131463f`.
The independent auditor's event_map, regression, columns_projection and
rebuild function ASTs are identical to LS8L's; only paths and the required
metadata-join count change. No noise weighting from LS8M is transferred.

Construct CAL, COR and DELTA=COR-CAL temporal event maps over the common
finite pixel mask, from sideband-only local linear fits. Sum all three event
rows. Retain C0 and C1, radius <=25 aperture, 30<radius<=40 background annulus,
radius>35 smearing regression, and the same brightness, displacement and
combined spatial bases. Centers use sideband centroids and measured detector
offsets, without adjustment to the event.

Classification order is unchanged:

1. **CORRECTION_LINKED:** complete apertures and matching COR/L2 signs in
   both conventions, with |DELTA/COR| or |column-DELTA/COR| >=0.5 in both.
2. Otherwise **SPATIALLY_STRUCTURED:** complete apertures and matching signs,
   available COR fits, displacement explained energy >=0.8 and advantage
   over brightness >=0.2 in both conventions.
3. Otherwise **UNRESOLVED_WITHIN_FIXED_SCOPE**.

Unavailable or rank-deficient fits remain unavailable. These labels are
descriptive gates, not a unique physical-cause or astrophysical/artificial
origin determination. Positive synthetic brightness pulses are retained in
the tests even though the native L2 sample contains only negative controls.

## Acquisition, verification and stop

Run seven inherited synthetic tests plus **two three-row known-answer tests**
before payloads. Require exact HTTP 206 ranges, lengths, source ETags and
Content-Disposition; verify the entire metadata manifest before acquisition.
Permit at most three identical-range retries for transport failures only;
identity/contract mismatches stop immediately. Retain original compressed
payloads, receipts and all failures.

The independent raw-struct/long-double/scalar audit rechecks joins, masks,
maps, fits and every classification at unchanged relative 2e-8, native absolute
1e-6 and dimensionless absolute 1e-8 tolerances. Publish every case and audit,
including unresolved/failing outcomes. Figures use retained outputs and cannot
change classification.

Stop at the five fixed contexts. If all close under the two descriptive gates,
close GJ 1132 and prepare an independent rank-3 HD 136352 pair/header freeze.
If any remains unresolved, preserve it and state its specific limitation before
any separately frozen retained-data diagnostic. Do not widen rows, radii,
visits or products to seek closure. No detector/candidate/coverage qualification
is added. Raw imagettes, reserved TESS/M43 panels and the unsent technical
calibration request remain separate.
