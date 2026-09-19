# LS7Y independent-audit correction for degenerate smearing predictor

The third LS7Y execution completed the frozen evaluator. Publication then
stopped in the independent audit before any result commit.

The saved SCI_COR_SmearingRow predictor in the selected bounded contexts is
constant, with the evaluated rows equal to zero. The evaluator uses
`numpy.linalg.lstsq` for the predeclared two-parameter diagnostic
`DELTA = alpha + beta*SMEAR`. A zero predictor makes the normal-equation
determinant exactly zero; NumPy therefore returns the minimum-norm least-
squares solution. The first independent audit used the ordinary closed-form
two-parameter inverse and asserted a nonzero determinant.

This correction changes only that audit implementation. For an exactly
constant predictor x=c, the independent audit now uses the analytic minimum-
norm solution to alpha + beta*c = mean(y):

- alpha = mean(y)/(1+c^2)
- beta = c*mean(y)/(1+c^2)

For c=0 this is alpha=mean(y), beta=0. The residuals are y-mean(y). For a
nonconstant predictor, the original scalar normal-equation solution remains
unchanged.

The evaluator commit, byte ranges, contexts, finite-pixel amendment, aperture
definitions, map calculations, classification gates and all LS7Y scientific
outputs are unchanged. The already visible evaluator outcome is not used to
select or tune an audit tolerance or scientific rule. Publication still
requires the full independent audit to pass.
