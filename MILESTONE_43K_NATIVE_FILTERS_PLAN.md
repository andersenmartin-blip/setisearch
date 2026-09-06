# M43K — exhaustive wider native-filter values

## Question and scope

M43J exhausted the 1,701-template/carrier domain at width one. M43I exercised
all eight widths but sampled the whole bank locally and exhausted only two
selected template vectors. Here we exhaust the remaining native filtering
component: does EVERY valid native-center value match an independently accessed
window sum at widths 3,5,9,17,33,65,129 for both existing M43H sources?

This is a separately named native-filter endpoint, not a redefinition of M43J's
full integrated-score endpoint. Native filter values are reused by many template
and carrier combinations. Computing the direct window once per native center
avoids repeating that same work billions of times. It does not itself evaluate
all wider-filter integrated score vectors, and those must not be claimed as run.

## Freeze and inherited identities

Publish this plan, the exact configuration, scheduler/reference and tests before
M43K evaluation. Freeze M43I's source/cache code, M43J's result, the M43E bank and
fixed factors, and the two M43H first-epoch ON/OFF source receipts at 1412.5 MHz.
Require every recreated source/cache identity and payload digest to equal M43I.
Use the existing verified products; no additional remote requests are required.

## Prescribed checks

For each source and each of the seven widths:

1. Build the unchanged receipt-bound M43I native cache. Rehydration verifies
   the native and normalized source products against the pinned telescope receipt.
2. Visit all 16 integrations in order. For N=1,132,270 native channels and
   h=width//2, compare every center from h through N-h-1, including both edges.
3. The separate oracle materializes integer-indexed windows directly from the
   normalized row, using chunks of 2,048 centers. It does not call the production
   filter, sliding-window view, convolution or a cumulative sum. Float32 window
   reduction, binary64 sqrt(width), cast to float32 are the frozen numerical rule.
4. Require finite exact equality, no tolerance. Record each complete reference
   row digest and require it to match the corresponding cache row digest.
5. Bound the full bank's native centers using positive finite factors, strictly
   increasing proxy frequencies, and direct binary64 nearest-even endpoint
   coordinates. Multiplication by positive factors, subtraction, positive division
   and nearest rounding are nondecreasing on this finite domain. Endpoint bounds
   therefore show that every interior mapping falls inside the audited native
   domain, including repeated mappings. This is a coverage argument, not a new
   exhaustive integrated-score evaluation or an independent mapping implementation.
6. Reproduce M43I's all-bank local integrated-score digest at its frozen 53
   carriers (17 at each support edge, 17 at center and two collision carriers).
   The unchanged gather performs its normal source/cache integrity checks.

The denominator is 32 × sum(N-width+1) over the seven widths: 253,620,352 native
filter values in 224 row/width checks and 14 source/width checks. Separately,
1,262,142 already prescribed local integrated cells are reproduced. These are
computational checks, not independent trials or detections. The oracle shares
the formula and NumPy with production; it is not independent scientific replication.

## Resources, failure and interpretation

Process one source/cache and one oracle row/chunk at a time. The widest indexed
reference window has 2,048×129 float32 elements. Temporary index arrays are
chunked too. The inherited 512 MiB adapter-owned ndarray cap excludes the oracle,
caller arrays, process RSS and OS caches; no claim of measured RSS is made.
No full bank-by-carrier matrix or complete second reference cache is retained.

Tiny synthetic tests exercise all widths, production and reference block halos,
one-ULP corruption at edges and block boundaries, dtype/shape/row order changes,
and the monotonic endpoint argument against an explicitly enumerated small grid.
The real run uses the actual M43H rehydration gate. The full M43-family suite is
required. Write a sealed checkpoint after each source/width passes; stop and retain
any failure. Publish an amendment before numerical or endpoint changes. The runner
recomputes on restart rather than trusting self-sealed progress to skip checks.

Passing closes the native filtering component across its full valid channel
domain for these two sources and seven widths. M43J still supplies exhaustive
integrated-score evidence only at width one. M43I still supplies wider-score
anchors. These complementary results do not automatically constitute a calibrated
full detector. Later gates must settle the remaining integrated-score coverage,
additional real epochs/windows, stack behavior and fresh null/injection calibration.
No candidate ranking, detection threshold or astrophysical conclusion is produced.
