# Continue after LS7S

The [electronic calibration audit](LS7S_CALIBRATION_FINDINGS.md) is complete.
The same CHEOPS visit `CH_PR300024_TG000301_V0300`, OBSID 1015522, remains the
development target. No science image or photometric field has been examined.
Start from PROJECT_STATUS.md and the saved LS7R ranges plus LS7S evidence.

## Resolve the physical calibration contract, then one native study

1. Reuse the verified **gain V0109** reference and the pinned PIPE source.
   Establish the native HK temperature-field mapping and gain-offset formula
   from mission documentation or a verified mission-calibration implementation.
   LS7S's centered/literal-PIPE comparison differs by about 8.129% in absolute
   scale but about 1 ppm after median normalization. It is a conditional
   adapter diagnostic, not proof of an upstream bug or permission to select
   whichever convention produces better residuals.
2. Resolve the raw imagette **gcoadd** contract versus subarray **coadd**.
   The individual `GAIN_0`, `BIAS_0` and `BIAS` fields are all NaN. Four voltage
   fields and CCD temperature are available at the individual timestamps;
   these do not by themselves establish the onboard transformation. Check
   the meaning, units and NEXP scaling of the constant CAL/COR BIAS/RON values.
   Do not treat the SEM digital offset 256 as the bias 563.429993.
3. Obtain the exact required mission **flat V0104, LUT100 V0104, bias V0109,
   readout V0101, PSF V0106, dark/bad maps V0201** through an approved supported
   delivery mechanism. Their exact archive rows are saved. The browser's
   mission download was URL-policy blocked; do not repeat or bypass that
   blocked action. A locally supplied exact calibration package can be read
   and checked. The known small official PIPE package contains the exact gain
   reference, not the full mission calibration set. Its `nonlin.txt` is not
   an accepted replacement for LUT100.
4. The flat is listed at 1168.0200 archive megabytes and the bias at 102.1780.
   Establish a concrete total transfer bound before any new transfer. Prefer
   documented access to exact relevant planes/regions when available; do not
   invent a byte-offset geometry before inspecting the reference headers.
   The archived dark/bad-map starts are 8.3126 days after the observation.
   Resolve the early-visit applicability rule and actual headers rather than
   silently choosing a different version. The aperture V0300 was not found
   in the query; classify whether it is necessary for the chosen PSF pipeline
   rather than using it as a gratuitous requirement.
5. Combine calibration/noise propagation and protected PSF/background
   development with one prospective acquisition/evaluation specification.
   Specify exact source/reference masks, valid circular footprint, fitting
   exclusions and training partitions, frame flags, gain/readout/linearity,
   per-exposure integration, and an explicit invalid-input branch. No
   default PIPE optimization or tuned PSF library has been adopted.
6. Before native pixel evaluation, freeze numerical signal/control/native
   requirements together: 30/60/100-second positive pulses before correction,
   nominal/displaced/distorted PSFs, compact/hot/cosmic events, stray-light
   changes, smear, saturation, gaps and context boundaries. Preserve native
   scene noise, report all lost signals and unavailable windows, and require
   useful native residual prediction as well as pulse preservation. Thresholds
   cannot be responsibly finalized while the physical operator is unresolved.

Do not rerun LS7R's timestamp-only pulse census or the LS7S field census merely
to create another milestone. Reuse their unchanged arithmetic. Advance by
resolving the missing physical inputs; keep failures and no-data cases explicit.
A later independent visit is considered only after the complete development
study warrants a separately fixed qualification.

## Publication and boundaries

All LS7S code, reference data, metadata ledgers, provenance, findings and logs
are within the owner's standing public GitHub authorization. Continue on
`m43-support-qualification` and update README on `main` at useful checkpoints.
No new routine approval is required. No message to archive staff is authorized
by this continuation. LS7P's original result recovery remains a separate task;
unused TESS sectors and M43 held-out panels stay closed. No unattended work
or notification has been scheduled.
