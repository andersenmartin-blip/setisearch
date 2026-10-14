# Geometry-only rounding-cell diagnosis

The former 405-point family was a Cartesian lattice in drift and reference
phase. A bound below half a native channel on the *unrounded coordinate error*
does not guarantee the same rounded channel: a true coordinate may sit much
closer to a half-integer boundary. Matching a four-row native delta response
requires one lattice point inside the intersection of all four rounding strips.
That intersection can be narrow and slanted, and the lattice can miss it.

For a fixed active four-row window, write the source coordinate in row i as
N + (d0 + delta)*t_i/DF + phase. Here N is the original integer source reference
channel plus the frozen injection host offset512; delta is in Hz/s, phase in
native channels, and t_i is the original midpoint-relative time in seconds.
The parameter box is delta in[-4/158,+4/158], phase in[-0.5,+0.5]. A target native
channel k has the strip k-0.5 <= coordinate <= k+0.5. Both endpoints are included
for even k and excluded for odd k, preserving nearest-integer ties-to-even.

This run intersects the four strips with the box using exact rational polygon
clipping. Stored floating constants are interpreted as exact binary rational
numbers. The previous NumPy float64 expression has intermediate rounding;
its stored405 geometries and truth centers are checked separately. The exact
affine model is therefore stated explicitly and is not substituted for an old
result. Closed polygon vertices are closure geometry; endpoint flags separately
specify the actual half-open strips. Every19 truth point is strictly feasible.

## Proposed finite-complete four-row arrangement

1. Enumerate every half-integer line that crosses the parameter box in any
   of the four rows. Each has phase = k+0.5-N-d0*t_i/DF-delta*t_i/DF.
2. Collect exact critical delta coordinates: both box endpoints; every line
   crossing either phase-box edge; every pairwise line intersection inside
   the closed box. Deduplicate and sort all rational values.
3. At each critical delta and each midpoint between consecutive critical
   deltas, sort the in-box phase boundaries plus both phase-box endpoints.
   Evaluate every boundary phase and every open phase-interval midpoint.
4. Round all four exact rational coordinates ties-to-even, then deduplicate
   the resulting four-integer tuples while retaining a parameter witness.
   Include boundary samples: open-cell samples alone can miss tie-only tuples.

Between consecutive critical delta values, line order and incidences do not
change. Every two-dimensional cell and one-dimensional slanted/horizontal
stratum intersects its midpoint vertical slice; critical slices also capture
vertices and vertical box edges. Sampling all phase strata on these slices
therefore covers every rounded four-row tuple of the declared exact affine
family. This is a finite arrangement method, not a claim that any fixed Cartesian
mesh is complete. A later implementation must check its code, limits, parity
boundary behavior, and relationship to legacy float64 semantics before scoring.

Only existing injection truth, coordinate arrays and metadata were analyzed.
No spectral power, normalized residual or observed score member was decoded;
there is no new sky result, observation, sensitivity or FAP. Original arrays and
the former run remain unchanged. The arrangement is proposed, not executed here.
