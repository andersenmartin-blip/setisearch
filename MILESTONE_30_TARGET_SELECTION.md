# Milestone 30 target and cadence selection

Status: **FROZEN BEFORE BET UMI SPECTRAL CONTACT**.

Milestone 30 consumes the next untouched qualifying target retained by the
Milestone 29 header-only screen. That screen read public identities, timing,
HDF5 attributes, and geometry, but no spectral dataset values.

## Mechanical target selection

The prior five-target screen resolved ranks 26--30 as follows: ranks 26, 27,
and 30 have only S-band cadence material; rank 28 HD 11964 was consumed by
Milestone 29; rank 29 bet UMi retains one complete L-band cadence and is
therefore selected mechanically for Milestone 30.

bet UMi b supplies the motion template. The archive target is HIP 72607. The
frozen discovery record gives a distance of 38.77472 pc, period 522.3 days,
semimajor axis 1.4 au, eccentricity 0.19, periastron epoch BJD 2453175.3, and
longitude of periastron 307.4 degrees. Its conservative periastron drift proxy
is 0.0294151 Hz/s at 1425 MHz.

## Fixed primary cadence

The sole qualifying bet UMi cadence is archive cadence `--74586`, beginning
at MJD 57584.09893518518 (2016-07-15 02:22:28 UTC). It contains three HIP72607
ON scans alternating with controls HIP72307, HIP73047, and HIP73715.

All six qualifying products share shape `[16, 1, 322961408]`, float32 dtype,
18.253611008 s integration time, 2.793967724 Hz channel spacing, and coverage
from 1023.925784044 to 1926.269531250 MHz. Public URLs, sizes, ETags, sources,
times, and geometry are preserved in
`results_m29_header_screen/header_screen.json`.

The same target also has cadence `--77497`, but its products are centered in
S band and are ineligible under the frozen L-band rule. No second qualifying
L-band cadence exists, so Milestone 30 cannot establish independent
recurrence.

## Frozen provenance and boundary

- discovery result SHA-256:
  `0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`
- Milestone 29 header-screen result SHA-256:
  `81d6df50f94f6970494b57e414a091d234600f9ee04daf76772919412bbed592`
- header-screen workflow run: `32755739577`
- artifact: `9530790490`, verified digest
  `sha256:9c888d3ef27e622385ded9fd51ad1b3e238910923ee2758f09b9aa84f163fdfd`
- `spectral_dataset_values_read` is false for every selected header.

The next permitted action is an exact NASA Exoplanet Archive query for the
selected bet UMi b orbit and host astrometry. Search bands, extraction
geometry, seeds, thresholds, report retention, and detector settings must
then be frozen with a target-specific coverage proof before spectral contact.

