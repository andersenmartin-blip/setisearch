# M43C: diagnose the remaining active-epoch coverage gap

Freeze code, configuration and this plan publicly before running the new
diagnostic. M43B's 167 supported and 345 unsupported truths are already known.
This is a retrospective, metadata-only engineering diagnosis. No bank,
tolerance, activity association, threshold or spectral data are changed.

## Fixed method

Reconstruct the same historical factor basis and 93-template table. For ALL
512 truths reproduce the exact active-only M43B plan inventory hash and cell
count. Use every integration of every active epoch, one fixed carrier and
one fixed template throughout.

For each template with positive factors a_i and truth track y_i, calculate
the continuous carrier interval at 20 Hz:

    lower = max_i ((y_i - 20) / a_i)
    upper = min_i ((y_i + 20) / a_i).

Also calculate the unconstrained continuous minimax residual. Intersecting
the per-integration carrier intervals implies

    e_min = max(0, max_i,j (a_j*y_i - a_i*y_j)/(a_i+a_j)).

At a maximizing pair a minimizing carrier is (y_i+y_j)/(a_i+a_j).
Compute this descriptive quantity using NumPy longdouble on the rounded
binary64 truth track, then directly evaluate its residual. It is not a formal
real-arithmetic certificate. Require pair expression and evaluated residual
to agree within 0.001 Hz. This fixed 0.001 Hz guard only marks uncertain
diagnostics; it never relaxes the 20 Hz candidate rule.

## Template and truth classification

Exact M43B-supported cells always retain the label supported. For zero-cell
templates, classify in this order:

1. Continuous minimum residual >20.001 Hz: incompatible track shape.
2. Minimum residual within 0.001 Hz of 20 Hz: numerical boundary unresolved.
3. A feasible carrier interval lies wholly outside the score grid (separated
   by >0.001 Hz): outside carrier range.
4. A feasible interval intersects the grid range but contains no grid point:
   carrier-grid gap. Boundary separations within 0.001 Hz remain unresolved.
5. A nominally feasible interval contains a grid point yet exact support is
   absent: numerical boundary unresolved; do not force a scientific cause.

For an unsupported truth, any unresolved template makes the truth unresolved.
Otherwise a grid-gap template takes precedence over outside-range templates;
outside-range takes precedence over all-template track incompatibility.
This identifies an available continuous solution when one exists. Publish the
template-cause counts, best continuous residual/template/carrier, every truth
classification, activity subgroup counts, and fixed residual quantiles
(0,25,50,75,100 percent). Do not optimize tolerance or select a replacement bank.

Tests use aligned tracks, mutually incompatible integration constraints,
a solution outside the carrier range, a gap between sampled carriers, and
the diagnostic numerical guard. Check minimax residuals independently against
a dense sampled objective on small synthetic cases. Production regression
remains covered by unchanged frozen modules and exact M43B plan replay.

## Decision and limits

If track incompatibility dominates, adding carrier samples alone cannot cure
those cases; future bank design must address track shapes at fixed tolerance.
If grid gaps dominate, a separately frozen carrier-grid refinement is justified
for study. Neither outcome is evidence of improved recovery, sensitivity or a
technosignature. Real-data scoring and false-association controls remain later
gates. Do not discard any of the original 512 truths.
