# LS7M original PRF coordinate acquisition

Specified 14 September 2026 after LS7L and before reading the original MATLAB
model arrays. This continues the coordinate/PRF forward-model work on the
same camera-4 CCDs and twenty closed contexts.

Retrieve exactly the two characterized-prf.mat files named by the already
restored mission exporter for camera 4, CCDs 3 and 4, under the mission
start_s0004 model directories. HEAD returned 5,200,793 and 5,198,689 bytes,
respectively, on this date. Require those sizes and status 200; cap each
download at 16 MB and their combined size at 32 MB, with 30-second request
timeouts. Preserve the original files, response validators and SHA-256 hashes.

Inspect the stored field names, ccdRow/ccdColumn, prfRow/prfColumn and array
shapes. Compare every original values/uncertainties image with its already
sealed FITS counterpart, including explicit identity and transpose checks.
The purpose is coordinate and export interpretation, not selecting a PRF
from native residual outcomes. Record any discrepancy without silently
repairing a previously published input.

The next numerical specification will cover one calibrated interpolation
and exposure family with known-answer checks, finite-stamp flux and explicit
uncertainty. No native pixel-response comparison, detector evaluation or
unused-sector opening occurs in this acquisition. Any later native comparison
requires its own fixed specification before scoring. Standing publication
authorization applies to code, source inputs, measurements and logs.
