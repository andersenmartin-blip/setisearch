# LS7K instrument-response input protocol

Specified 14 September 2026, after the closed LS7J negative result.

## Purpose and boundary

Establish which mission inputs can support a physically specified response
model for the same twenty TESS contexts. This stage restores missing timing
and detector-coordinate metadata, inspects mission PRF calibration, and
inventories engineering products. It does not fit or apply a new correction,
evaluate a detector, select an outcome-dependent gain/sign/lag/profile, or open
an unused sector. LS7J and its thresholds remain closed.

The accompanying provenance assessment separates documented facts, direct
file measurements and unresolved assumptions. Documentation was inspected
before this acquisition; this is an input inventory, not a blind scientific
qualification. The complete source commit precedes acquisition, and its SHA
and source-file checksums are included in the result.

## Fixed inputs and acquisition

1. Restore the exact two light-curve products from LS7J by their frozen byte
   counts and SHA-256 hashes. Use only the ten existing 401-cadence contexts
   in each sector, with the unchanged anchors, cadence IDs and aperture.
   Save TIME, TIMECORR, TIME minus TIMECORR, CADENCENO and QUALITY, along with
   complete primary, light-curve and aperture headers. Verify TIME and
   POS_CORR1/2 against the original LS7J extraction. No interpolation occurs.
2. Restore all 25 PRF grid files for camera 4/CCD 3 and all 25 for camera 4/CCD 4
   in the mission's start_s0004 directory. Exact filenames and grid coordinates
   are fixed in config. There is no selection based on an astronomical result.
   Save original FITS bytes, URLs, hashes, headers, image shapes, finite counts,
   minima, maxima and sums. Inspect the primary and uncertainty images without
   resampling, renormalizing, discarding negative values or fitting a source.
   Record validity failures explicitly. File sizes are capped at 2 MB.
3. Read the documented engineering directory index once (8 MB cap). Record
   links whose sector token is exactly 29 or 32 and whose product is a
   quaternion or engineering FITS file. Preserve all matching versions.
   This stage inventories links only; it does not download or align engineering
   time series or infer an uninspected cadence or time reference. If listing
   fails, save that failure as missing evidence.
4. Read the two published PRF documentation/export resources solely to record
   retrieval provenance (URL, size and SHA-256), without republishing their
   text. A failure here does not silently remove the corresponding question.

Each network request has a 60-second timeout. Up to four independent PRF
downloads may run concurrently. Missing calibration files are reported, not
substituted from another sector/version or hidden by reducing a denominator.

## Coordinate and timing contract

TIME is the original barycentric TDB timestamp. The documented subtraction
TIME minus TIMECORR gives the spacecraft light-arrival timestamp in the same
BJD reference system. This conversion prepares a later engineering join;
LS7J already joined motion and pixel samples by identical cadence IDs, so it
does not demonstrate a defect in LS7J's timing.

Save the physical alternate WCS and compare its pixel-to-detector mapping
against a separately calculated linear transform. Save celestial target
coordinates projected through the aperture WCS as a nominal geometric anchor.
Do not use flux centroids or outcomes to choose the PRF grid, and do not apply
the documented 44-column convention difference automatically. The correct
relation between the actual calibration headers and science WCS must be
resolved before evaluating a response.

No statement that successive POS_CORR entries are independent 20-second
measurements follows from their presence at every cadence. Exact estimator,
reference epoch, averaging kernel, covariance and target participation remain
separate provenance questions unless a direct source establishes them.

## Verification and deliverable

A separate audit reopens both original light curves, verifies the 8,020 saved
rows and raw motion values, independently recomputes timing, checks all acquired
PRF identities and arrays against the inventory, and checks the physical WCS
by direct arithmetic. Recheck the existing LS7J and input manifests. Tracked
historical files must remain unchanged.

Publish scripts, protocol, documentation assessment, original PRFs, timing
extracts, FITS headers, complete availability inventory, audit, logs and source/
result checksums. Report input acquisition separately from scientific readiness.
Even a complete input packet cannot establish a calibrated detector, independent
pointing measurement or pulse protection under an upstream estimator.

The exit is a concrete response-input contract and next implementation scope.
If calibrated PRFs are usable, the next work is a separately specified
coordinate/PRF forward-model benchmark on closed data, with explicit uncertainty
and upstream signal dependence. It is not an LS7J retry or automatic unseen-data
qualification. Publication uses the standing owner authorization.
