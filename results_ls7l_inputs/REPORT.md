# LS7L closed-context engineering and calibration inputs

**Input extraction and independent raw-byte audit completed.**

The packet contains 81,200 camera-4 quaternion rows and 30,594 thermal rows from 26 fixed thermal channels across the two sectors.
All 8,020 saved cadence coverage counts and 4,050 PRF phase images are accounted for.

| Quantity | Result |
|---|---:|
| Saved cadences without quaternion rows in the fixed 20-second bin | 0 |
| Quaternion rows per coverage bin, minimum / maximum | 10 / 10 |
| PRF phase flux sum, minimum / maximum | 0.995947949571 / 1 |
| Raw selected scalar values verified | 1,066,182 |
| Raw PRF and uncertainty values decoded | 1,368,900 |

Read timing_metadata.json for all UTC/TT/TDB calendar comparisons and tables.json for missing values, quality ranges and sampling.
The numeric join follows the mission support TESSVectors convention; absent TIMESYS/TIMEREF, exact exposure timing and estimator kernels remain explicit limits.
Coverage counts are not exposure averages or proof of guide-star independence.
Phase sums are finite-footprint bookkeeping; no phase image is renormalized and uncertainty-entry sums are not variances.
The original mission README and MATLAB exporter are restored under documentation/ with their LS7K hashes.

Next: inspect the exporter, fix absolute detector coordinates and source-phase orientation, then specify the physical response and uncertainty benchmark before native comparison.
There is no detector adoption, added observing coverage, new candidate, or change to prior negative results.
