# LS7Z implementation clarification — common template-fit domain

Frozen 19 September 2026 before any LS7Z numerical evaluation.

The LS7Z protocol defines brightness, shift and combined template fits on
eligible r<=25 pixels, while spatial derivatives additionally require finite
neighboring template pixels. To make the three explained-energy values directly
comparable, all three fits use one identical fixed domain:

- pixel is inside r<=25 under the current C0/C1 convention;
- the COR event-excess value E is finite;
- the sideband profile P is finite;
- both central-difference templates Dx and Dy are finite.

Thus the brightness-only fit does not gain pixels unavailable to the shift
fit. The number and fraction of retained fit pixels are reported.

For L2 coordinates, the FITS table is decoded at its declared storage types and
then converted to float64 for LS7Z calculations. This is a new LS7Z diagnostic
definition, not an attempt to reproduce LS7Y's binary32 mean convention. C0 and
C1 are still both carried through and no convention is selected from outcome.

No threshold, radius, template, input byte or interpretation boundary is
changed by this clarification.
