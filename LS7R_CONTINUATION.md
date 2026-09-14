# Continue after LS7R

The [CHEOPS input and temporal assessment](LS7R_CHEOPS_INPUT.md) is complete.
Start from its saved ranges and source identities, not a new catalogue sweep.
File key **CH_PR300024_TG000301_V0300**, OBSID **1015522**, is retained.
There are 3,024 raw 50 × 50 imagettes (two 2.2-second exposures apiece),
432 matching subarrays (fourteen exposures) and 6,048 individual timestamps.
Delivery works and no science image body has been opened.

## One combined calibration and pixel-response study

1. Resolve the exact fifteen REF_APP inputs in the saved calibration-log
   extract, especially gain/bias/readout, linearisation, temperature-dependent
   flat, dark/bad-pixel maps and PSF. Check actual validity intervals and
   array geometry, including why the recorded dark/bad-pixel filenames are
   dated after the observation. Do not substitute a nearby version silently.
   CAL/COR remain ADU products; raw imagettes are not already calibrated.
2. Fix one imagette reduction with its target-excluded background information,
   protected PSF training, uncertainty propagation and per-exposure timing.
   Use the saved individual timestamps and CE joins. Do not replace the
   4.449-second delivered cadence with 2.2 seconds or ignore long gaps.
3. Specify acquisition and evaluation together before opening image pixels.
   A full raw imagette cube is 30,435,840 bytes. Matching 50 × 50 central
   subarray stamps can be read using the saved HDU offsets and (75,75) window
   offset; a bounding-square stamp is not a validated circular/defect mask.
   Include needed calibration/quality inputs and a global transfer bound.
4. Freeze joint 30/60/100-second pulse and nuisance controls before scoring:
   positive source pulses inserted before correction, PSF displacement/shape
   changes, compact/hot/cosmic pixel events, background/stray-light changes,
   readout smear, saturation and context/gap boundaries. Include both native
   residual predictability and pulse preservation. Set numerical requirements
   and the failure branch in the same protocol, rather than serial tiny tests.
5. Report all failed cells and unavailable intervals. A pipeline flag of zero,
   a full idealized pulse peak, or agreement between stack timestamps is not
   proof of native recovery. Do not open another visit merely to replace a
   failed result. Treat this visit as development, with subsequent independent
   qualification separately specified only if justified.

This is the concrete work queue, not a claim that the native protocol has
already been frozen or executed. The current stage established the input
needed to write that protocol; calibration references still require inspection.
Do not run PIPE's tuning/default correction sequence blindly or use a
post-correction digital injection to claim protection by upstream processing.

The COR headers mark cosmic-ray detection/correction N/A. The static pixel
flag map's visit-level saturation definition is not a short-event veto.
Those limitations must be addressed explicitly in the combined protocol.

## Preserved boundaries and publication

LS7Q's HiPERCAM input remains unready without documented delivery/calibration;
do not repeat its failed raw URL or contact an archive person without owner
authorization to send that exact message. LS7P's separate original result
packet remains unverified; follow LS7P_PUBLICATION_RECONCILIATION.md.

No native candidate, qualified detector, physical sensitivity or observing
coverage was added. Unused TESS sectors and M43 held-out panels stay closed.
Publish meaningful combined results on m43-support-qualification and update
the main README under standing authorization. Work occurs in active sessions;
no unattended job or notification has been scheduled.
