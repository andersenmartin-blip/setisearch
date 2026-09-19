# Continue after LS7V

The [actual reduction-log reconciliation](LS7V_CALIBRATION_RECONCILIATION.md)
is complete for CHEOPS `CH_PR300024_TG000301_V0300`, OBSID 1015522. Reuse
the retained LS7R metadata, LS7S gain/reference evidence, LS7T native HK,
LS7U electronics measurements and LS7V original log and reconciliation.

## Immediate continuation: obtain the missing physical input

The additional DRT and IASW repository leads did not provide the missing
documentation. The concrete next action is the prepared
[technical clarification request](CHEOPS_CALIBRATION_REQUEST.md), with an
[exact input manifest](CHEOPS_REQUIRED_INPUTS.json): four required reference
versions, a conditional PSF input and three operator/applicability questions.
The official technical contact has been checked. The message is **unsent**;
there is no pending reply or scheduled contact.

The owner can send the ready text through their chosen channel or supply
relevant mission documentation and exact reference files directly. Assistant
contact requires explicit authorization and a supported communication tool.
After input arrives, resolve the actual operators and file applicability,
then freeze the integrated study below. Until then this image study is
blocked on external input. Preserve LS7V as the latest scientific result;
the request preparation is operational work, not a new numbered milestone.

## Resolved requirements

The executed calibration module is **14.0.1**, within overall reduction
14.1.2. Its bright-mode, 230 kHz, main-channel script 6 uses **default bias
563.43 and default RON 7.13 ADU/frame** at reported CCD temperature −40 °C.
The CAL/COR constants exactly equal the binary32 representations of these
defaults. The LS7U differences are now understood as measurements compared
with defaults. Do not change a margin estimator or repeat those measurements
to force agreement.

The spatial BiasFrame V0109 correction was **skipped**, even though that
reference is named in the header and input log. Its content is not needed
to reproduce an unapplied correction. Any different raw estimator must
still justify how it handles physical pixel-dependent bias. ReadOut V0101
is not needed merely to discover the now-known scalar bias/RON defaults;
only concrete additional operator requirements can justify requesting it.

Keep the earlier distinction between disabled onboard NLC and required
offline linearization. Neither missing coefficients for a disabled operation
nor a reference filename alone proves an applied-calibration dependency.

## Remaining concrete inputs

Resolve the exact gain-temperature convention and the imagette gcoadd/
offline nonlinear operator with version-relevant mission documentation or
implementation. The log's approximate gain of 2.0 electrons/ADU does not
define an exact formula or rounding rule. Preserve LS7T's actual voltage/
temperature distinction and the separate meanings of its native −0.57027%
comparison and the earlier conditional 8.129% calculation. Do not infer final
CAL/COR pixel units solely from the gain log; their headers still say ADU.

Obtain verified contents for the exact flat V0104 and offline LUT100 V0104,
plus dark/bad maps V0201 with the actual early-visit applicability rule.
The dark MAP correction was explicitly applied; its archived date remains
after the observation. The white PSF V0106 is needed if the selected method
depends on it; a protected alternative must justify its different input
requirements before target-image evaluation. Aperture V0300 remains dependent
on the estimator rather than automatically mandatory for PSF fitting.

The previously blocked mission reference-bundle download must not be retried
or bypassed. An exact package delivered through an approved supported channel
can be inspected locally. No archive-staff message is authorized. A simulator
default bundle of unknown version membership is not a justified substitute.
The listed flat is 1168.0200 archive MB: establish an explicit total transfer
bound and inspect headers before selecting regions or planes.

Once the necessary inputs are established, freeze **one integrated study**
covering calibration/uncertainty, protected PSF/background training, masks,
exposure integration, numerical native-prediction requirements, positive
30/60/100-second pulses injected before correction and the complete nuisance
set. Preserve compact/hot/cosmic events, PSF displacement/distortion, straylight,
smear, saturation, gaps, boundaries, lost pulses and unavailable windows.
Only then evaluate the required target-image ranges.

Do not reopen completed timestamp/field/margin censuses or repeat unsuccessful
generic searches without a new lead. A next checkpoint needs new physical
documentation/input or an actual prospective study. If those dependencies
remain unavailable, report that dependency rather than another status-only
milestone or a proxy qualification.

## Publication and boundaries

Standing authorization continues for all SETI code, data, reports and logs
on `m43-support-qualification`, plus README updates on `main`. No routine
publication approval is needed. Unused TESS sectors and M43 held-out panels
remain closed, and LS7P reconciliation remains separate. Its explicit reconstruction is now
[verified and documented](results_ls7p_response/REPORT.md); it supplies none
of the missing CHEOPS physical inputs. No unattended work,
external message, detector adoption, candidate or new qualified observing
coverage is created by LS7V.
