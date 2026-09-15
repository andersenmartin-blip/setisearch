# LS7T: physical calibration source and native HK contract

Written 2026-09-15 before acquiring the new instrument table. Continues LS7S
at science commit `e46d73c13cdb1ec7c93c1e4668fc70caa70e576a`.

The fixed visit is `CH_PR300024_TG000301_V0300`, OBSID 1015522. Only its
already inventoried `SCI_RAW_HkExtended` product may be acquired: exact file
`CH_PR300024_TG000301_TU2020-03-09T04-54-45_SCI_RAW_HkExtended_V0300.fits`.
The pinned PIPE reader requires this product, not HkDefault. The mission
schema contains separate TEMP_FEE_CCD and VOLT_FEE_CCD fields.

Use the existing public DACE download contract with verified HTTP 206 ranges,
consistent object identity and exact lengths. Allow at most 5,000,000 retained
header/table bytes, at most 64 FITS header blocks per HDU, and no image data.
Reject unexpected table types, variable-length heaps, product identity,
oversized requests, ignored ranges or changed objects. No full-file fallback.
If access fails, retain the failure and continue from public source evidence.
This visit-housekeeping request is distinct from the previously policy-blocked
mission reference-bundle download; do not retry or bypass that blocked action.

Inspect only schema, timestamps and the five gain inputs plus the separate
CCD-voltage field. Compare the pinned PIPE reader with explicit interpretations
of the verified V0109 gain reference. Audit timestamps before any alignment
with LS7R. Compare exact matching timestamps if available; do not silently
extrapolate or switch time scales. Resolve what can be resolved from the data,
and preserve disagreement between source implementations.

Pin CHEOPSim `d5bfcfdae596ae1b85576dced7d55baecbc7da4d` and common_sw
`1e45b3be84edd18a60e9a0ea8ef65444dfa2a254`; record inspected file identities
and permanent source links. Public source inspection is not a DRP 14.1.2 run.
Do not redistribute unlicensed upstream source files; store source provenance
and original analysis. GPL PIPE files are already preserved in LS7S.

Implement only explicit diagnostic arithmetic and invalid-input checks. Do not
choose gain, coaddition, nonlinear or noise conventions using target residuals.
Do not acquire native science pixels, prescan pixel values, PSF training data,
or photometric fields. Do not repeat LS7R's pulse/timing census or LS7S's
missing-field census. No recovery, candidate, coverage or detector claim is
available from this checkpoint. The integrated native study remains conditional
on a complete physical calibration contract and its prospective requirements.

Publish code, small instrument-table evidence, findings and updated continuation
under the owner's existing SETI authorization. No archive-staff contact.
