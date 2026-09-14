# Continue after LS7Q

LS7Q's HiPERCAM metadata assessment is complete. The XO-2b run is not ready
for a native pilot. Start with [the findings](LS7Q_OPTICAL_METADATA.md) and
[saved evidence](results_ls7q_metadata/README.md), not a repeated catalogue
sweep. This stage opened no science pixels and did not qualify a detector.

## Next integrated input decision

1. Establish a bounded, documented delivery of the public
   `GTC70-24B / 0004A / 5070352` run and the matching calibration inputs.
   The inspected download has an invalid negative Content-Length and a failed
   byte-range request; do not loop over it or start a blind ~117 GB extraction.
   A successful header request is not proof of a usable raw-data transfer.
2. Resolve the **fast windowed science / slow full-frame bias** mapping and
   **NaI science / rs flat** mismatch using documented calibration identities.
   The QC log supplies bias 5070335 and standards 5070342–5070344 beyond the
   single flat on the calibration page. Only standard 5070343's header has
   been inspected. Header geometry is available; calibrated arrays are not.
3. Check actual per-frame timestamps, skip/dummy flags and channel-dependent
   exposure only after a fixed metadata/acquisition contract identifies the
   required byte subset. Fix the target/reference geometry, defect/saturation
   treatment, noise and pulse-transfer model before opening science pixels.
   Header counts and file-creation times are not observing coverage.
4. If those inputs cannot be established, carry out the secondary **CHEOPS
   metadata** assessment: identify a concrete public visit, its exposure and
   stacking, unstacked/stacked pixel products, correction provenance and
   transfer size. No CHEOPS product has been selected or evaluated here.
5. For a viable product, freeze one integrated acquisition and response
   experiment before native evaluation. State the 30–100-second signal
   hypothesis, spectral channel choices, reference exclusion, injection/
   nuisance controls, native-window endpoint and failure rule together.
   A broadband glint and narrowband optical emission need distinct channel
   expectations. Preserve all failed methods and avoid outcome-selected cuts.

If an archive email is needed to obtain the missing package, prepare its
exact technical request first; contacting a person requires explicit user
authorization. No such message has been sent in LS7Q.

## Separate evidence repair

[LS7P's publication gap](LS7P_PUBLICATION_RECONCILIATION.md) remains open.
Recover its original result packet and verify it before carrying forward its
previously reported numerical audit. Do not repeat the much larger TESS
studies to compensate for missing publication evidence.

## Existing boundaries

No new astronomical candidate, detector adoption, physical sensitivity limit,
or extra observing coverage has been established. LS7O is an availability
obstruction; LS7J/LS7N are separate measured response failures. Unused TESS
sectors and M43 held-out panels remain closed. Work proceeds during active
sessions; no unattended job or notification was scheduled.

Publish code, metadata, result notes and logs on `m43-support-qualification`
and update the concise main overview at useful checkpoints under the existing
standing authorization. The original 14–27 September dates remain work-window
estimates, not deadlines for obtaining a detection.
