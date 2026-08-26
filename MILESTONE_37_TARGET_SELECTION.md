# Milestone 37 target and cadence selection

Status: **FROZEN BEFORE HD 156668 / HIP84607 SPECTRAL CONTACT**.

Milestone 37 reuses the already published Milestone 36 HDF5-header screen.
That screen read archive records, object identities, HTTP metadata, HDF5
attributes, timing, and geometry for discovery-extension ranks 36--40. It did
not index or read any HDF5 spectral dataset value. This selection step makes no
new remote telescope request.

## Mechanical target selection

Milestone 36 consumed the lowest qualifying extension rank, rank 36. Applying
the same frozen ascending-rank rule to the remaining results makes rank 37 the
unique next target; no scientific result or spectral value enters the choice.

| Extension rank | Host | Published header-screen result | Milestone 37 status |
|---:|---|---|---|
| 37 | HD 156668 | one complete compatible L-band cadence | **selected** |
| 38 | HD 1461 | one complete compatible L-band cadence | retained for later |
| 39 | 51 Peg | no qualifying cadence | ineligible |
| 40 | tau Boo | no qualifying cadence | ineligible |

HD 156668 b supplies the motion template. The archive target is `HIP84607` at
24.3323 pc. Its frozen discovery record has period 4.6455 days, semimajor axis
0.05 au, eccentricity 0.0, nominal periastron epoch BJD 2454718.57, and
nominal longitude of periastron 36 degrees. The conservative frozen
periastron drift proxy is 8.712783061646705 Hz/s at 1425 MHz. Because the
composite eccentricity is zero, the periastron epoch and longitude are used
only as a reproducible coordinate-transform convention; they are not treated
as physically measured orbital orientation.

## Fixed primary cadence

The only qualifying rank-37 cadence is archive cadence `--85168`, beginning at
MJD 57470.581099537034 (2016-03-23). It is a six-scan ABABAB sequence with
sources:

1. `HIP84607`
2. `HIP84607_OFF`
3. `HIP84607`
4. `HIP84607_OFF`
5. `HIP84607`
6. `HIP84607_OFF`

The start-to-start cadence span is 1650.000000349246 seconds. All six fine
HDF5 products have shape `[16, 1, 264503296]`, float32 dtype,
17.986224128-second integrations, 2.835503418452676 Hz channel spacing, and
coverage from 1126.4648465855034 to 1876.46484375 MHz. Their public URLs,
sizes, ETags, sources, times, and complete header geometry are already
preserved in `results_m36_header_screen/header_screen.json`.

At the frozen drift proxy, one integration spans approximately 55.267106
channels (156.710069 Hz). The established boxcar bank
`[1, 3, 5, 9, 17, 33, 65, 129]` therefore includes the next wider template.
Exact motion-plus-width guard coverage must still pass a target-specific
metadata-only preflight before any spectral contact.

## Prospective complete-retention requirement

Milestone 36 showed that detector v0.5's top-15/top-three collector does not
prove complete above-threshold retention. Its value of 2016 is only the
arithmetic ceiling on records emitted before clustering under that stop, and
the 2200 report cap only shows that this already limited list would not be
truncated again. Neither value is a completeness bound or may determine the
Milestone 37 outcome.

Before any Milestone 37 spectral value is read, detector v0.6.0, its tests,
and its protocol must be frozen separately. The normative result must use the
final calibrated operational threshold produced by the same primary
execution. Every score cell at or above that threshold must either be retained
or be assigned, under a prospectively frozen deterministic coverage rule, to
a retained representative, with a machine-verifiable unaccounted count of
zero. Every normative retained record must receive its own frozen
physical-veto disposition; cluster summaries and any reproduced v0.5 list are
non-normative.

No reporting or capacity gate may truncate the normative record. Any capacity,
enumeration, evidence, or verification failure invalidates the run and yields
no scientific conclusion. The detector protocol, not this metadata selection,
will freeze the exact retention/NMS construction, tie rule, evidence schema,
and capacity values.

## Frozen provenance and boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 36 header-screen result SHA-256:
  `45bd84cad0c83e8079ad3fe204ca827c7213954f43121599fbeac893252db19b`
- Milestone 36 target-selection document SHA-256:
  `89834f2f1fcb72ddba602765e5bbc090977b79f9878eedf44c4d32df0c0ff47c`
- Milestone 36 header-screen protocol commit:
  `71d2e032f12b63c7d66bf4400663c403bfc8511d`
- canonical header-screen result commit:
  `ee24e87944c27d7b47e7b6fccc764b958945318a`
- completed Milestone 36 boundary commit:
  `ced77e735f4e1aea13a237def9adba75372d34a0`
- completed Milestone 36 verification receipt SHA-256:
  `9efde86fd305a1f86610992c6ca2a34eb11010f55a703936a548414e206e10ab`
- the verified Milestone 36 outcome is
  `PRIMARY_CADENCE_NULL_AFTER_COMPLETE_RETENTION_AUDIT`
- every reused header records `spectral_dataset_values_read: false`
- the screen records `spectral_payload_inspected: false`
- no HD 156668 / HIP84607 spectral dataset value has been extracted, plotted,
  summarized, calibrated, scored, or searched.

The next permitted action is one exact selected-record query against the NASA
Exoplanet Archive. Its result must be atomically published with provenance.
After that, the target-specific coverage proof and the detector v0.6.0
preregistration must be frozen in separate commits before any spectral value
is read. This cadence cannot by itself establish independent recurrence.
