# Milestone 29 preregistration: HD 11964 b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`d5e6da15f512957e1395fd201636fdc944d35e1c2fc99c70bed33ad10dc7a203`.

## Purpose and boundary

Milestone 29 is a new held-out application of detector v0.5.0. The target is
**HD 11964 / HIP 9094**, with HD 11964 b used only as the motion template. The
primary data are its sole complete compatible GBT L-band alternating
ON/control cadence, archive cadence `--66653`, beginning 2016-12-24 00:29:32
UTC.

Before this commit, only frozen catalogue records, official orbit and host
metadata, HTTP object identities, HDF5 attributes and geometry, timestamps,
and calculated extraction geometry were read. No HD 11964 HDF5 `data` value
was indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The rank 26-30 target order and header qualification rule were committed
before those products were opened. Ranks 26 and 27 were S-band; HD 11964 at
rank 28 is the first compatible host. Rank 29 bet UMi retains one qualifying
L-band cadence for a later milestone, and rank 30 is S-band.

Selection provenance is in `MILESTONE_29_TARGET_SELECTION.md`. The header
screen is GitHub Actions run `32755739577`, artifact `9530790490`, digest
`sha256:9c888d3ef27e622385ded9fd51ad1b3e238910923ee2758f09b9aa84f163fdfd`.
The official metadata query is run `32756178424`, artifact `9530921366`,
digest
`sha256:6285221d1d73a544843c7749b859b08b4cb3227f97b515bcfaf537a6e01bde1f`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP9094 | 57746.020509259260 | 16 | 292.057776128 |
| 2 | control | HIP10172 | 57746.024479166670 | 16 | 292.057776128 |
| 3 | ON | HIP9094 | 57746.028437500000 | 16 | 292.057776128 |
| 4 | control | HIP8092 | 57746.032372685186 | 16 | 292.057776128 |
| 5 | ON | HIP9094 | 57746.036307870374 | 16 | 292.057776128 |
| 6 | control | HIP8144 | 57746.040243055555 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and coverage from 1023.925784044 to
1926.269531250 MHz. Identities, sizes, ETags, sources, times, and geometry are
frozen in `config/hd11964b_heldout_m29.json`.

## Mandatory extraction-coverage proof

`scripts/m14_coverage_preflight.py` evaluated all 21 frozen projected-scale
and phase templates at all six scan times in all five windows. All **630**
checks passed without opening a remote file. The smallest edge headroom is
233,395 channels, approximately 652.098 kHz.

The proof is run `32756473460`, artifact `9531042028`, verified digest
`sha256:e6d66f43f67aa24a73f81683d0d4f0a5d3252cf7eb86ed00bf7316f6445f61d0`.
The result SHA-256 is
`0dc5353dbad82a0ff2b52598b1cefcca75530f0f0be68c1f27c0d14513bb35c4`.

## Target and orbital template

The official composite record supplies RA 01h57m09.22s, Dec -10d14m36.49s,
parallax 29.789 mas, proper motion (-366.957, -242.431) mas/yr, and radial
velocity -9.31811 km/s. The HD 11964 b working orbit has period 1945 days,
semimajor axis 3.16 au, eccentricity 0.041, periastron epoch BJD 2454170, and
longitude of periastron 26 degrees. Its conservative full-projection
periastron drift proxy is 0.00341556 Hz/s at 1425 MHz. The orbit is only a
coordinate-transform template.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, widths
`[1, 3, 5, 9]`, clustering, v0.5 OFF/receiver vetoes, 256 complete scrambles,
and the completeness grid are unchanged. Fixed seeds are `2920260824` for
scrambles and `292120260824` for completeness. The 1200-cluster report cap
exceeds the finite maximum of 1008 retained peaks per window and therefore
cannot truncate the complete disposition record.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m29_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m29_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m29_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m29_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m29_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction fails closed on any identity or geometry mismatch. Detector rules,
thresholds, vetoes, templates, bands, seeds, completeness, and report retention
may not change in response to data. A cluster above the empirical global
threshold survives only if none of the frozen matched-control,
single-adjacent-control, local-control, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 29 as a primary-cadence null result. Any survivor
must remain an unresolved candidate requiring genuinely independent data. No
second qualifying HD 11964 cadence exists in the frozen screen, so this
milestone cannot perform or claim independent recurrence. Any conclusion is
limited to the frozen scope and measured completeness.
