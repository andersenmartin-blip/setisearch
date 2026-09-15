# Continue after LS7U

The [electronic-reference assessment](LS7U_ELECTRONICS_FINDINGS.md) is complete
for CHEOPS `CH_PR300024_TG000301_V0300`, OBSID 1015522. Start from
PROJECT_STATUS.md and reuse the retained LS7R metadata, LS7S gain/reference
evidence, LS7T native HK and LS7U electronic arrays and verification.

## Carry forward the measured electronics

The fixed four-column virtual prescan gives **562.089864 ADU/readout bias**
and **7.118046 ADU/readout effective noise**. Its descriptive bias interval
excludes CAL's 563.429993, although bias and noise both agree numerically
within the fixed 1% label under the per-readout ADU hypothesis. This is
numerical unit-scale evidence, not exact CAL reproduction or a total noise
uncertainty budget. Independent-readout scaling is an explicit premise.

PIPE actually selects the eight-column BlankLeft extension. The separately
specified exploratory supplement executes its unchanged estimator and gives
**562.071429 / 7.024590 ADU/readout** after removing 5,284/691,200 electronic
values. CAL RON is 1.500584% higher and fails the same 1% comparison. Reuse
the result; do not try other margins or clipping choices just to reproduce CAL.
Do not apply that electronics clipping to source flux.

Both measured reference extensions are images of electronics, not target
images and not metadata. No science-pixel flat, spatial bias, dark or PSF
calibration follows from them. The ordinary coadd/NEXP=14 prescan scaling
does not establish the imagette gcoadd/NEXP=2 response.

## Finish the remaining physical-input package

Obtain version-relevant evidence for the physical gain-temperature convention
and native gcoadd/offline nonlinear operator. Preserve LS7T's distinction
between actual temperature and the separate voltage field used by the pinned
PIPE gain reader. Its native −0.57027% scale comparison is not the older
8.129% conditional adapter comparison. Onboard NLC is disabled; missing
coefficients for that disabled operation are not alone a blocking requirement.
The offline LUT100 operates in electrons and still needs justified gain,
bias and stack treatment.

The exact flat V0104, bias V0109, LUT100 V0104, readout V0101, white PSF V0106
and dark/bad maps V0201 still lack verified content. The archive rows already
exist. The blocked mission reference-bundle download must not be retried or
bypassed. An exact package delivered through an approved supported channel
can be inspected locally; no archive-staff message is authorized. Do not
substitute a simulator default bundle with unknown version membership.

Inspect actual validity headers and the DRP selection rule for this early
visit. The generic common_sw selector requires UTC within a reference validity
interval; it does not supply an established nearest-future fallback. This
does not prove that DRP used that selector or that its dark was invalid.

The flat is listed at 1168.0200 archive MB and bias at 102.1780 MB. Fix a
total transfer bound before any supported acquisition and inspect headers
before selecting planes. An absent aperture V0300 remains estimator-dependent.
If a protected estimator can demonstrably avoid a particular reference,
justify that requirement change before science evaluation; do not silently
drop a calibration because its delivery is difficult.

Once the physical inputs are adequate, freeze **one combined prospective
study**: calibration and uncertainty; target-protected PSF/background training;
masks, fitting exclusions and quality flags; exact exposure integration;
numerical native-prediction endpoints; 30/60/100-second positive pulses before
correction; and displaced/distorted PSFs, compact/hot/cosmic events, straylight,
smear, saturation, gaps and boundaries. Keep every lost pulse and unavailable
window in the record. Only then open the required target-image ranges.

There is no new timestamp, missing-field or margin census to perform. A next
checkpoint needs an actual new physical input or completed experiment, not
another report of the same missing package. If it cannot be completed, keep
the explicit NOT_READY outcome and identify the remaining delivery/documentation
dependency without calling a proxy native qualification.

## Publication and boundaries

Standing SETI authorization covers code, data, results, logs and README
updates: science on `m43-support-qualification`, README on `main`. No routine
approval stop is required. Keep unused TESS sectors and M43 held-out panels
closed. LS7P's publication reconciliation stays separate; no detector,
candidate or qualified observing coverage is added by LS7U. No unattended
work or external message has been scheduled.
