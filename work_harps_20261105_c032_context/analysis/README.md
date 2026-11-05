# C032 fixed joint profile diagnostic

Original V2E2-0278 and V2E2-0283 on HD126093 retain exact centers 3869.2975
and 3869.295 air Å, their own June 27 and July 16 discovery references, and
both original orders 2/3 and raw contexts. The fixed common midpoint is
3869.2962500000003 air Å. Its comparison core differs from both original cores.

The first original queue discovery, June 27, fixes the common topocentric anchor
using BERV -18.8519268910592 km/s. No fitted shift, width, continuum or mask.
The established numerical helpers are structurally unchanged from C015/C033.

Fresh scans cover all 144 native order headers. Order 2 loses the positive
reference flank in both discoveries: keep raw-only profiles, finite core
correlations and any blocked surrounding comparisons. Do not borrow order 3
normalization or transfer the previous phase's full-support outcomes.

20 profiles and 64 comparison slots retain every raw/normalized/blocked outcome,
all 40 original-member support records, both original local/baseline mapping
limitations, and both secondary uncertainty flags. Raw containers stay byte exact.

Publish and verify this method before current arithmetic. Then bind ROOT_RELEASE
and execute compare_group.py once. Reconstruct every result with separate scalar
formulas, render and inspect all four fixed figures, and preserve the physical U
labels. Source-index dependencies against C031 and C034 are audited from metadata;
their old arrays are not reread. Reused exposures are not independent validation.

Next metadata route is C035 on HD128582, selected by original queue order using
that target's own six epochs and March discovery. No current outcome chooses it.
Separate implementation and visual review are by the same assistant, with no
independent agent/human review, new observing time or calibrated significance.
