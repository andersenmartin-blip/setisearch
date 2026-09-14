# LS7O: reference products exist; the fixed availability contract fails

Completed and independently audited 14 September 2026. **No new native
correction or pulse transfer was measured.** This is an input-availability
result, distinct from the measured response failures in LS7J and LS7N.

## What was established

The official 20-second lists and MAST metadata identify six nearby references
on the science target's CCD in each sector: **twelve products, seven distinct
stars**. Selection used only camera/CCD, Tmag 8–12 and angular distance
0.25–3 degrees, followed by the six nearest. The references lie 1.268–2.483
degrees away. Their geometry surrounds the target in both sectors; their
centroid masks are mutually disjoint and at least 236.916 pixels from it.

The publicly frozen acquisition recovered exactly **48,120 reference rows**
in **120 HTTP ranges, 4,812,000 bytes**. Every selected CADENCENO matches the
science target, and every TIME-TIMECORR spacecraft timestamp agrees exactly
at stored precision. All centroid values and positive quoted errors are
finite. Product ETags, byte ranges, raw bytes and SHA-256 are published.
Whole-product FITS checksums are not established by partial reads.

## Where the fixed experiment stops

LS7O requires all six references to have QUALITY=0 at every event cadence and
every one of the 110 sideband rows used to estimate reference centers/weights.

| Sector | Six usable references at a saved cadence | Event windows with all six quality-zero | Sideband windows with all six quality-zero | Complete available windows |
|---|---:|---:|---:|---:|
| 29 | 2,559/4,010 | 72/210 | 0/210 | 0/210 |
| 32 | 3,105/4,010 | 101/210 | 0/210 | 0/210 |

At least three references are individually usable at every saved cadence.
The all-six, all-sideband condition nevertheless blocks **all 420 windows**.
Of 48,120 reference rows, 45,422 meet the individual finite/error/QUALITY=0
condition. Missing values or time misalignment do not explain the failure.

The observed flags concern optimal-aperture and collateral cosmic rays,
pre-cotrending outlier removal and scattered-light exclusion. Their meanings
are different; a flag is not itself a calibrated centroid-error estimate.
The frozen experiment neither waives flags nor removes stars to obtain a fit.
[Flag attribution and primary documentation](results_ls7o_response/quality_diagnosis.json).

The **840 paired model slots and 12,600 pulse slots are all unavailable**.
There is no new residual-energy ratio, measured pulse distortion or verdict
on whether the proposed reference-driven physical response improves the
science target. Do not interpret blocked slots as measured signal losses.

## Verification and decision

Eleven known-answer tests pass, and a separate inverse-TAN/normal-equation
preflight reproduces reference geometry and synthetic affine motion.
The input audit passes **384,960 exact raw-field comparisons**. **916** native
and aggregate numerical comparisons preserve the static baseline, with a
maximum discrepancy of 2.28e-13. All **155 inherited manifest entries** and
**82 new metadata/input entries** agree. A second scalar raw-byte audit
confirms every quality count, all 420 window attributions and zero evaluated
correction/pulse branches.

The frozen producer's `native_pixel_response_evaluated` stage flag is true
even for this fully blocked run. That flag overstates the branch executed;
the original output is preserved alongside audited
[explicit scope accounting](results_ls7o_response/scope_accounting.json).
The actual evaluated correction and pulse counts are both zero.

Close this exact availability formulation. Available reference products have
now been established; a usable pixel/quality/centroid-response contract has
not. The next useful work concerns the fixed references' pixel-level quality,
cosmic-ray processing and astrometric response, with bounded acquisition only
after its purpose and endpoints are specified. If that cannot support the
needed short-timescale measurement, reassess the optical product choice.
No detector is adopted, observing coverage added or unused sector opened.

Source freeze: `f2d7aef6e82f90a357ec7f54e349cfc2b43953dc`.
Both reference extracts and response result directory were absent then.
The source was publicly verified before acquisition.

[Full report](results_ls7o_response/REPORT.md), [frozen protocol](LS7O_SPEC.md),
[input and response audit](results_ls7o_response/audit.json),
[quality/scope audit](results_ls7o_response/quality_audit.json),
[continuation](LS7O_CONTINUATION.md).
