# Continue after LS8R

The fixed HD 136352 paired-image study is **complete and closed**.
All three negative representatives are **CORRECTION_LINKED** under the
prospectively fixed diagnostic. Result commit:
`3f5053ee7d35afed31666b95daf9b3b5029956fc`.

LS8Q found **zero positive threshold crossings in 1,923 eligible overlapping
windows**. Its 13 negative crossings formed the three clusters followed
here. No event is promoted to a SETI candidate, and no detector or additional
observing coverage is qualified.

## Complete image outcome

DELTA is the temporal event map of COR minus CAL. The table reports the
signed source-aperture sum ratio, retaining both original coordinate
conventions and their unchanged apertures.

| Representative | Event stacks | DELTA/COR C0 / C1 | COR brightness explained C0 / C1 | COR displacement explained C0 / C1 | Fixed outcome |
|---|---:|---:|---:|---:|---|
| TG000901_N0 | 1 | 0.575222 / 0.558559 | 10.5057% / 10.4830% | 27.3182% / 27.3182% | CORRECTION_LINKED |
| TG000901_N1 | 1 | 0.741593 / 0.736533 | 10.4503% / 10.4334% | 18.5184% / 18.5180% | CORRECTION_LINKED |
| TG000101_N0 | 2 | 0.791461 / 0.813813 | 10.3399% / 10.3303% | 24.0101% / 24.0081% | CORRECTION_LINKED |

All six source apertures are complete, have valid COR denominators and
match their original negative L2 signs. Every direct DELTA/COR ratio is
above the frozen 0.5 threshold, so all three pass the first gate in both
conventions. No coordinate choice, alternative aperture or relaxed
threshold was needed. The column-projected ratios are smaller and do not
supply the closure; the direct aperture-sum criterion already passes.

This identifies a material contribution from the difference between the
delivered processing products. **It does not identify one physical
correction component or prove the absence of source variability.** The
ratios concern signed aperture sums, not fractions of total pixel energy
or independently assigned fractions of physical cause. CAL/COR maps can
look similar on the common pixel scale while their signed sums differ.
All six smearing regressions are rank deficient and remain explicitly
unavailable; do not convert that missing fit into a causal explanation.

Each stack combines 26 approximately 1.7-second exposures into 44.2 seconds
of integration. The first two events span one delivered stack; the third
spans two, about 88.4 seconds. These data do not resolve the individual
1.7-second exposures. L2 scores retain their original descriptive meaning;
they are not calibrated Gaussian significances.

## Scope, independent audit and visual review

The metadata-only stage verified **176 unique CAL/COR joins** for all 88
fixed context rows and passed **812 exact checks** without reading image
values. A separate payload freeze fixed all identities and byte intervals
before acquiring exactly **56,320,000 image bytes plus 140,800 smearing
bytes**. The nine range requests each succeeded on their first attempt.
All receipts, source hashes, raw compressed ranges and maps are retained.

The unchanged image diagnostic keeps 12 sideband rows and two guards each
side, the native one/two-stack event sum, both coordinate conventions, the
r<=25 aperture, 30<r<=40 annulus, original templates and decision order.
LS8P covariance weights and hypothetical subtraction are not applied.

**Nine known-answer tests pass before image access.** The independent
struct/long-double/scalar-normal-equation audit passes **283,611 numerical
comparisons and 481,748 exact checks**, with zero disagreements at unchanged
tolerances. It verifies joins, range identities, raw floats, masks, maps,
fits and final labels. LS8Q separately passes both stable-arithmetic tests
and all **23,076 numerical/discrete comparisons**.

All three original CAL/COR/DELTA figures have been downloaded from the
immutable result, checksum verified and visually inspected. They retain
the common full-frame signed scale per event and both fixed apertures;
no rescaling, cropped reanalysis or visual choice feeds the classifications.

**Close the HD 136352 pair here.** No unresolved branch remains under this
fixed diagnostic. Do not launch a residual study, acquire extra visits or
reopen these outcomes merely because the descriptive label is not a unique
physical explanation. All earlier failures and closed studies remain intact.

## Next action: independent rank-4 TESS_260647166 transfer

Continue with the unchanged reconciled LS8J ledger, without repeating the
population census or reordering hosts. TESS_260647166 is the archive target
name of the next **CHEOPS** pair; this does not open reserved TESS sectors.
The cohort has seven eligible visits, of which only the first two are selected:

| Pair order | Exact file key | Existing start MJD | Ledger NEXP | Ledger integration per row |
|---|---|---:|---:|---:|
| 1 | CH_PR300046_TG000101_V0300 | 58918.7572349357 | 1 | 42 s |
| 2 | CH_PR100031_TG015701_V0300 | 58958.3675973350 | 1 | 49 s |

The ledger ranks cohorts by the time of their second eligible visit, then
their first visit and name. These start dates therefore preserve the
original ordering. The exposure entries above are existing ledger metadata;
the new products' exact headers and science values remain unopened.

1. Freeze this exact pair and a bounded metadata/header-only preflight.
   Preserve request receipts, headers, source identities and schema. Verify
   each visit's exposure keywords separately: their ledger cadences differ.
   Stop on incompatibility rather than replacing the target or borrowing
   HD 136352's byte ranges or exposure tuple.
2. After compatible headers, separately freeze the exact DEFAULT-L2 ranges.
   Transfer the unchanged stable LS8K scorer and independent auditor with
   one/two/three-row windows, original eligibility, sidebands, guards,
   endpoints and signed clustering. Do not turn these image labels into a
   new screen cut or a trained veto.
3. Publish the full signed result and denominators. Any indicated image
   follow-up first needs its own metadata joins and exact payload freeze,
   retaining every signed representative. A null closes the pair under the
   existing rule without adding visits or changing thresholds.

No next-target headers, tables or pixels were opened during LS8Q/LS8R.
Standing research and publication authorization continues without another
per-stage permission request. Collaboration remains deferred. Closed GJ 1132
and WASP-189 work, reserved TESS/M43 data and the unsent raw-imagette
calibration request remain unchanged; that separate calibration gate is
still NOT_READY.

[Image report and all three figures](results_ls8r_images/REPORT.md) ·
[Independent image audit](results_ls8r_images/audit.json) ·
[L2 result and scope](LS8Q_CONTINUATION.md) ·
[Frozen image protocol](LS8R_PAIRED_IMAGE_PROTOCOL.md) ·
[Publication identities](PUBLICATION_2026-09-20_LS8Q_LS8R.md).
