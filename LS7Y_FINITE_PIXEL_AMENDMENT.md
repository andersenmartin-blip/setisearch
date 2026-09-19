# LS7Y finite-pixel availability amendment — 19 September 2026

The first execution of the frozen LS7Y evaluator stopped before producing any
candidate summary because the first bounded L1 subarray context contains one or
more non-finite pixel values. The original implementation incorrectly asserted
that every pixel in every 200 x 200 frame had to be finite.

This is an implementation/availability correction, not a scientific-rule
change. The parent LS7X candidates, image contexts, products, byte ranges,
aperture radius, two coordinate conventions, temporal sidebands, event rows,
spatial diagnostics and descriptive classification gates remain unchanged.
No LS7Y score, map diagnostic or classification was available when this
amendment was written.

The protocol already required finite values only. The exact missing-pixel
semantics are now frozen as follows before rerunning:

1. **Frame aperture sums.** For CAL, COR and DELTA, a radius-25 aperture sum is
   available only if every pixel selected by that convention is finite in that
   frame. If any selected pixel is non-finite, that frame/convention/product
   sum is unavailable. No NaN is replaced, interpolated or treated as zero.

2. **Temporal aperture diagnostic.** A CAL/COR/DELTA temporal event-excess
   diagnostic is available only when all 31 fixed context-frame aperture sums
   are available. The smearing-row aperture sum must likewise be finite in all
   31 frames.

3. **Per-pixel event maps.** A pixel is eligible separately for CAL and COR only
   if its value is finite in all 24 fixed sideband frames and all three fixed
   event frames. DELTA-map comparisons use the intersection of CAL and COR
   eligible pixels. Ineligible pixels are represented as NaN and excluded from
   sums, norms and regressions; their counts are reported explicitly.

4. **Central completeness gate.** The descriptive LS7Y classification may be
   `CORRECTION_LINKED` or `IMAGE_LOCALIZED_NOT_CORRECTION_DOMINATED` only if
   every radius-25 pixel under both C0 and C1 is eligible in both CAL and COR
   event maps and the complete 31-frame temporal aperture diagnostics are
   available. Otherwise the classification is
   `AMBIGUOUS_IMAGE_FOLLOWUP`.

5. **Full-frame and r35 diagnostics.** Sums and L1 norms are over the common
   eligible CAL/COR pixel set only. The eligible counts and fractions are part
   of the result. Column coherence is computed from the common finite DELTA map;
   a column component is defined only over eligible pixels in that column and
   is compared on the same eligible mask.

6. **Frame-level DELTA/smearing regression.** As already specified, only pixels
   with finite DELTA and finite smearing predictor are used outside r=35. The
   number of fitted pixels is retained for every frame.

No spatial repair, interpolation, alternate aperture, neighboring frame, other
visit or raw imagette is opened to compensate for missing pixels. The same
independent audit requirement remains in force.
