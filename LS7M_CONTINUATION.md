# LS7M continuation — numerical response family complete

Completed 14 September 2026. Start from [LS7M_FINDINGS.md](LS7M_FINDINGS.md)
and the [audited response benchmark](results_ls7m_response/REPORT.md).

## Next integrated work

Specify the observable-to-pixel physical contract, then freeze and evaluate
one native response comparison on the same twenty closed contexts. The
interpolation and exposure arithmetic is verified; do not repeat phase
censuses or create another metadata-only milestone without a concrete risk.

1. Trace camera/SC quaternion component order, rotation direction, reference
   and focal-plane geometry through primary mission sources. Derive the
   small-angle detector Jacobian from these definitions, not a fitted sign
   or gain on native residuals. The exact POS_CORR averaging kernel remains
   unknown. If an instantaneous mapping cannot be justified, limit the
   experiment to supplied cadence-level displacement and state that it cannot
   test subcadence physical pointing.
2. Account for calibration blur, absolute field origin and time alignment.
   The arrays settle relative axes but not the 44-column discrepancy. Retain
   declared coordinate alternatives without selecting by native fit. The PRF's
   inherited pointing blur is not known to be separable from trajectory blur.
   State which response is approximated and which claims remain unavailable.
   Never silently identify quaternion samples with integration centers.
3. Fix the footprint using calibration geometry alone. Sector 32's leftmost
   stamp column lies beyond the PRF table; the operator returns NaN there.
   A common supported mask across the declared motion range, or independently
   derived response extension, must precede native scoring. Do not zero-fill
   missing tails or phase-normalize after inspecting results.
4. Freeze the full two-sector comparison: amplitude/reference, uncertainty,
   pulse protection, nuisance handling, outside-event samples and endpoints.
   Engineering observables are not automatically independent of target flux.
   Guide membership and weights are unavailable; report the upstream limit.
   DVA and thermal deformation need their own declared interpretation.
5. Combine the comparison, meaningful new tests, independent audit and report
   in one useful work package. Only then assess native prediction improvement
   and signal/control readiness for future unused-data qualification. A new
   physical model is a separately named test, not an empirical gain/sign/lag/
   profile retry of the failed LS7J rule.

No unused TESS sector or M43 held-out panel is opened by the numerical pass.
Existing counts and negative results remain intact. Standing authorization
covers continued work and publication on the science branch, with README
updates on main; a fresh publication approval is not needed.

## Reproduction and restart

Active work starts from the latest m43-support-qualification head. For
reproduction only, use an isolated checkout of the source freeze, where
results_ls7m_response does not yet exist:

~~~bash
git checkout b6fea2889d792d6c1980335f5e83b27c54ca22c7
python -m pip install -r requirements_ls7g.txt
PYTHONPATH=src python -m unittest discover -s tests -p test_ls7m_prf_response.py -v
python scripts/ls7m_response_benchmark.py
python scripts/ls7m_review_response.py
~~~

Recorded Python: 3.12.14. Scripts refuse to overwrite completed results. The
operator uses published FITS images and recovered coordinates. The audit
restores the two exact original MATLAB files if absent, under frozen sizes
and hashes (10,399,482 bytes total). It needs no 1.41 GB engineering download.

Acquisition freeze: `99c2cc107d2c621ec015ef8b6de1ba5803ffd1b3`.
Numerical source freeze: `b6fea2889d792d6c1980335f5e83b27c54ca22c7`.
Execution logs and independent audit are in results_ls7m_response. No
unattended continuation is scheduled between active sessions.
