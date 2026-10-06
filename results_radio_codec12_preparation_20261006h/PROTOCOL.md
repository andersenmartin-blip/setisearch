# Prospective complete controlled-codec protocol

## Fixed evidence scope

The only prospective payload scope is controlled source-shaped data for
HD189733/HIP98505 cadence 85030.  It is not telescope data and cannot establish
telescope provenance, sensitivity, recovery performance, RFI behavior or a
scientific result.

The producer order is fixed:

1. calibration: `epoch1_on`, `epoch1_off`, `epoch2_on`, `epoch2_off`,
   `epoch3_on`, `epoch3_off`;
2. validation: the same six labels in the same order.

Each handoff must contain exact role/scan, receiver context and bank SHA-256,
16 native-descending selected-row hashes and 16 normalized-row hashes.  The
calibration extraction is `[167215104,167280640]` in chunk 159.  Validation is
`[164069376,164134912]` in chunk 156.  Both use the exact declared pipeline
`[[32008,1,[0,3,4,0,2]]]`, source shape `[16,1,264503296]`, chunks
`[1,1,1048576]` and dtype `<f4`.

The deterministic numerator is

`409600 + 256*handoff_index + ((i*17+chunk*31+row*13)%4093) + 128*((i//4096)%17)`

divided by 4096 and cast to little-endian float32.  The exact binary handoff salt
makes all 12 constructions distinct.  It is a controlled engineering pattern,
not an astrophysical/noise model and uses no PRNG.

## Metadata laws

All 22 law names and accept/reject outcomes in `PLAN.json` are fixed in the exact
order required by `scientific_admission.py`.  The current checkpoint reproduces
those outcomes using the exact pure filter guard and a dataset object that
refuses payload indexing.  Future native execution must repeat them in its own
receipt and preserve the current source-only observation.

## Future execution boundary

This checkpoint cannot dispatch.  A future execution requires, before a child
exists:

- immutable producer, wrapper, outer supervisor, configuration and complete
  input/read manifests;
- full public readback and independent source review;
- isolated exact runtime and before/after inventory;
- marker-only one-shot activation with an expected-head publication lease;
- complete process/descendant identity, wait4, native-loader and terminal-IO
  custody;
- explicit cumulative reservation accounting.

The proposed—not reserved—future envelope is 600 wall seconds, 540 CPU seconds,
1 GiB address space, 768 MiB RSS, 400 MiB leaf output plus 48 MiB outer reserve,
4 GiB explicit parent reads plus 1 GiB opaque child reads.  There are at most 24
HDF5 files and each is capped at 16 MiB, so their joint ceiling is 384 MiB.  Each
compressed chunk is capped at 5 MiB.  Handoffs and rows are sequential; no full
16.9 GB logical dataspace may be materialized.

## What completion would and would not mean

A successful independently reviewed control may support a controlled codec
certificate.  It still does not admit spectra.  Authentic joined hosted
profiles, a complete native/runtime graph, actual scientific CAS, fresh
source/pilot/session identities, recovery/RFI/null gates, and the separate
127-reference/24-evaluation allocations remain required.  The original
preparation contract remains preparation-only.
