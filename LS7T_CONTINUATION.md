# Continue after LS7T

The [native HK and source-contract audit](LS7T_CALIBRATION_CONTRACT.md) is
complete for CHEOPS `CH_PR300024_TG000301_V0300`, OBSID 1015522. Start from
PROJECT_STATUS.md, the saved LS7R input, LS7S gain reference and LS7T evidence.

## Carry forward these resolved points

- The appropriate native telemetry is **SCI_RAW_HkExtended**, with separate
  TEMP_FEE_CCD and VOLT_FEE_CCD. Both actual fields are now saved and verified.
  Do not acquire HkDefault as a replacement or map voltage to temperature.
- The unchanged pinned PIPE gain reader on actual HK gives about **1.94545
  electrons/ADU**. Against centered physical temperature, its median scale
  differs by about **−0.57027%**, with at most **9.134 ppm** in the normalized
  ratio. LS7S's 8.129% value was a different conditional adapter calculation.
- CHEOPSim subtracts the signed temperature offset; common_sw's description
  adds it. Resolve this with a version-relevant mission calibration reference
  or implementation, not a fitted light curve or nominal-value override.
- GAIN_0, BIAS_0 and BIAS describe the conversion around **onboard NLC**.
  Both native headers set NLIN_COR=false. Those NaNs are not, by themselves,
  a reason to demand reconstruction of a disabled operation. Offline detector
  nonlinearity remains active in the physical problem.
- The logged LUT100 operates in uncorrected/corrected **electrons**. Do not
  apply it to summed ADU without the justified gain, bias and stack treatment.

## Finish the missing inputs in one package

Obtain a documented interpretation of native gcoadd and the appropriate
offline nonlinear/stacking operator. The inspected simulator implements only
coadd/mean; generic header descriptions do not settle this. Define CAL
BIAS/RON units and stacking scaling, or derive them from properly scoped
prescan inputs and documented readout behavior. The digital offset 256 ADU
is still distinct from measured bias.

The exact flat V0104, bias V0109, LUT100 V0104, readout V0101, white PSF V0106
and dark/bad maps V0201 remain unavailable as verified content. The archive
rows are already saved. The previously blocked mission reference-bundle
download must not be retried or bypassed. An exact calibration package supplied
through an approved supported channel can be inspected locally. Do not silently
replace reference versions. Check the dark/bad-map starts after this early
observation and the actual early-visit applicability rule.

The flat is listed at 1168.0200 archive MB and bias at 102.1780 MB. Fix a total
transfer bound and inspect headers before selecting planes/regions. Determine
whether the absent aperture V0300 is needed by the eventual estimator; an
aperture-photometry reference is not automatically required for a PSF method.

Once the physical inputs are complete, combine calibration and uncertainty,
target-protected PSF/background training, masks, fitting exclusions, quality
flags and per-exposure integration with **one** prospective evaluation. Freeze
the numerical native-prediction, positive-pulse and nuisance-control requirements
together before opening image pixels. Include 30/60/100-second positive pulses
before correction, displaced/distorted PSFs, compact/hot/cosmic events,
straylight, smear, saturation, gaps and boundaries. Report every lost pulse
and unavailable window; a quiet-looking output alone is not a useful model.

There is no new timestamp or missing-field census to run. Reuse the completed
arithmetic. If the physical-input package cannot be completed, retain the
explicit missing-input outcome; do not relabel a proxy as native qualification.
Do not create another milestone solely to restate the same obstruction.

## Publication and boundaries

Standing SETI publication authorization covers code, metadata, results, logs
and README updates: science work on `m43-support-qualification`, README on
`main`. No routine approval stop is required. Archive-staff messaging is not
authorized. Keep unused TESS sectors and M43 held-out panels closed; LS7P
publication reconciliation remains separate. No unattended work is scheduled.
