# LS7M findings — calibrated PRF and exposure operator verified

Completed and independently audited 14 September 2026.

**We now have a tested forward operator for calibrated pixel response and
finite exposure.** Ten known-answer tests, all 4,050 phase reconstructions and
144 predeclared calibration cases pass. The independent audit starts from
original MATLAB arrays and uses a separate interpolation/integration route;
maximum flux discrepancy is 1.39e-16. All 113 inherited LS7K/LS7L manifest
entries remain unchanged. [Full result](results_ls7m_response/REPORT.md).

The original files establish the relative axes: 117 samples from -58/9 to
58/9 pixels, with zero at index 58. All fifty values and uncertainty images
equal the FITS exports exactly without transposition. Three nonzero rowShift
annotations were recovered. They do not affect these target kernels; the
implementation rejects a contributing annotated node until its meaning is
established.

Absolute detector-column origin is still ambiguous between mission README
and exporter. Explicit 0/-44-column alternatives change modeled responses
by up to **0.7946% in relative L2 norm** over this synthetic panel. This does
not select a convention or establish absolute accuracy.

The finite table supports all 121 stamp pixels in 42 of 144 cases and only
110 in the others. Sector 32's leftmost column is outside the PRF domain
even for the stationary nominal target. Unsupported responses are flagged,
not filled or renormalized. A native model needs a declared common supported
footprint or an independently justified response extension.

For a 30 ms synthetic pulse crossing a frame boundary, the three readout
placements transmit **10–15 ms** of live pulse duration. Exact engineering
sample timing, readout phase and the fast POS_CORR averaging kernel remain
unknown. Sample counts cannot replace the exposure contract.

Supplied uncertainty entries are propagated with positive weights, not treated
as sector-specific error bars. Calibration already represents a pointing
profile, so use as an instantaneous response plus additional jitter needs
physical justification. Quaternion-to-pixel mapping, DVA/thermal departures,
guide membership and upstream target exclusion remain open.

No native pixel values were opened for this benchmark. There is no new
detector comparison, candidate or observing coverage. This advances the
numerical model while leaving native predictive value untested. LS7J's
negative result and all unused panels remain unchanged.

Primary inputs: mission [PRF README](https://archive.stsci.edu/missions/tess/models/prf_fitsfiles/start_s0004/00README.txt)
and [exporter](https://archive.stsci.edu/missions/tess/models/prf_fitsfiles/start_s0004/export_mat2fits.m),
archived under results_ls7l_inputs/documentation. Original MATLAB source
links/hashes are in [the inventory](results_ls7m_prf_inputs/inventory.json).
These support provenance and conventions, not native model performance.

[Frozen contract](LS7M_RESPONSE_SPEC.md),
[implementation](src/seti_repeater/tess_prf_response.py),
[current continuation](LS7M_CONTINUATION.md).
