# M43F: source coverage and channel-mapping preflight

Publish this protocol, executable, tests and hash-pinned configuration before
running the new bank against extraction/cache geometry. M43E qualified the
fixed 1,701-template checkerboard bank geometrically on fresh parameter draws.
It did not qualify telescope source products, channel gathering, caches, scores
or a detection threshold for that bank. This preflight closes or identifies
those transfer requirements before any new spectral evaluation.

## Scope and immutable inputs

Use exactly the M43E checkerboard bank, unchanged coefficient records and
factor basis. Require its passed fresh result and bank hash. Cover all five
M37 windows, all six ON/OFF scans, all 96 integration midpoints and all eight
native filter widths (1,3,5,9,17,33,65,129). Include the full proxy-support
lattice, including its 64 non-score guard bins at each end. The score lattice,
20 Hz association, bank and physical source pointing remain unchanged.

Read only public metadata/results/code. No telescope HEAD or range requests,
spectral arrays, injected data, normalization results or score/cache payloads.
A source geometry or memory estimate is not an attested telescope product.

## Coverage calculation and baseline gate

Reconstruct the exact M43E factor basis/table. Verify all six source definitions
against the immutable M37 source module. On each of the 30 scan/window pairs,
reproduce both M37 93-template raw-filter headrooms exactly against the public
M37 bank-preflight result. Abort on any discrepancy; preserve the old result.

For each new positive template/integration factor F, evaluate q_low*F and
q_high*F on the full support grid, and map them with the frozen nearest-even
rule rint((frequency-raw_zero)/df). Positive F and a monotone lattice make
these exact endpoint extrema bounds for every interior carrier too.
For width w require raw centers in [w//2, N-1-w//2]. Report every width's
worst headrooms, failing template and template/integration counts, and hashes
of complete endpoint and failing-template inventories. No edge truncation or
change to a denominator is allowed.

## Channel-mapping compatibility

The current cache planner explicitly requires factors in [1,2) and the gather
code requires strictly increasing nearest-native indices with steps in {1,2}.
Count violations of that existing factor precondition over the 1,701×96
unique factor rows, and separately by scan/window. These counts alone are a
contract check, not a measurement of every finite-grid collision.

For each of the 30 scan/window pairs, select the first flattened minimum-factor
row and enumerate its entire support-grid mapping. Report the exact step
histogram, mapping hash, duplicate count, and first adjacent carrier pair
mapping to the same raw channel, if any. This is a concrete witness; do not
extrapolate its collision count to every template. Preserve any incompatibility
and do not modify the gather rule, masks or calibration during M43F.

## Proposed extraction footprint, not a source-factory change

For each window calculate a common descending archive-channel interval that
retains the old extraction and covers every bank endpoint in all six scans,
plus the maximum 64-channel filter radius and a fixed two-channel outward
reserve for affine-coordinate rounding. Use integer conversion from the old
ascending geometry; fail if the proposed interval exceeds the original
remote dataset's channel count. Reconstruct the header-affine geometry for
that proposed interval and directly recheck coverage for all six scans.

Publish the exact proposed intervals, channel additions and channel ratios.
Compute raw float32, normalized float32 and frequency float64 bytes, and
compare separately with all current source-factory limits (channel count,
raw bytes, frequency bytes, total product ndarray bytes). Do not silently
raise a cap. Estimate the raw-center cache payload per width and for all eight
widths; exclude file headers, operating-system cache and temporary arrays.
These are dimension arithmetic, not measured full-pipeline memory or runtime.

Report the changed normalization-origin offset modulo 4096. Normalization is
anchored at the extracted ascending channel zero, so enlarging the extraction
can change block alignment and normalized values. Existing cache contents or
old source/threshold receipts must not be presented as reusable merely because
raw frequencies overlap. The new bank also needs new cache identities even
where payload dimensions coincide. No proposed interval is a validated source
product or an amendment to the frozen M37 factory.

## Gate and next action

The legacy source/mapping gate passes only if every 129-channel filter is
covered and all factor rows meet the existing cache precondition. Smaller
width results remain published regardless. A passed preflight still needs
attested source/cache rehydration, score equivalence/false-association tests,
exhaustive real-data anchors and renewed calibration.

If incompatible, stop spectral qualification at this gate, publish concrete
counterexamples and footprint requirements, and implement a separately named,
separately frozen transfer contract. That contract must address every observed
blocker before spectra can provide meaningful validation. Do not masquerade
new geometry as an old M37 source product, suppress duplicated channels, drop
out-of-range carriers or transfer an old threshold by changing constants.
No new user permission is needed for already authorized analysis/publication;
this is a scientific validation boundary, not a new approval requirement.

Tests compare endpoint bounds against exhaustive small-carrier fixtures,
check descending interval expansion, nearest-even half-channel behavior,
source-band limits, literal duplicate witnesses, current cache rejection of
subunit factors, and resource-cap flags. Final verification regenerates the
metadata result, audits identities/counts and directly checks every reported
collision. Report limitations without a sensitivity or technosignature claim.
