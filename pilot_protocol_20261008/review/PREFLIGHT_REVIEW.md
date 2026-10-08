# Independent prospective feasibility review — 8 October 2026

Scope: read-only code/protocol and source metadata. No pilot values, held-out
controls or prior closed jobs are opened or executed by this reviewer.

## Reuse of working local reference

The existing ordinary local Python route completed a known authentic reference
and remains the working route. No third engineering route is needed or permitted.
Reuse the small numeric `drift_grid` and nearest-channel scoring concept; reuse
`read_header` only for the exact supported 32-bit one-IF little-endian FIL format.

The present reference `scan` assumes one file's first midpoint, common channel
origin/spacing and contiguous time offsets. For a six-scan ON/OFF cadence,
freeze a common absolute reference time and reference-frequency band. For each
file/time row map the hypothesis via
`round((f_ref + drift*(t_absolute-t_ref) - fch1_file)/foff_file)` with consistent
Hz or MHz units. Preserve real inter-scan gaps. Do not concatenate scan rows as
if contiguous. Do not combine separate per-scan maximum-over-drift scores and
describe them as one common frequency/drift hypothesis. OFF vetoes must evaluate
the exact same fixed hypothesis at the OFF scan's timestamp.

## Source transfer feasibility

- A 4,096-channel decoded array is not a source-byte measurement. A narrow HDF5
  hyperslab still requires every intersected compressed chunk. Budget the
  six scans, full drift/filter/matching halos, metadata, HTTP block prefetch,
  rereads/retries and actual received bytes together against the 2GiB pilot cap.
- Inspect dataset shape, type, chunks and filter pipeline without slicing its
  values. `get_chunk_info_by_coord` can retrieve stored chunk size/file location
  metadata for every halo-intersected chunk before decoding. Sum those sizes,
  with explicit I/O overhead and a hard received-byte cap.
- A byte-range server must actually return matching 206/Content-Range responses.
  A 200 response to a Range request must be closed without reading a giant body.
  File size alone neither proves nor rules out partial-read feasibility.
- Ordinary h5py wheels do not include ros3; do not assume HTTP URLs work through
  that driver. An already supported measured range/file-like route may be used;
  lack of one is a source feasibility block, not permission for another runtime
  rescue campaign. HDF5 filters must be available before actual payload decoding.
- Metadata/acquisition hashes pin source identity and chronology. Source fetching
  or compressed bytes alone must not be described as spectrum analysis; actual
  decoding/scoring waits for the frozen protocol and fresh-control gate.

## Qualification and accounting

The fresh 32 noise cadences test only their explicitly declared synthetic noise
law unless separately collected real-background data are used. They cannot
establish a sky false-alarm probability or robust empirical RFI rejection. Keep
development, any rank calibration references, fresh validation and sky pilot
identities disjoint. Preserve empty final results as genuine zero outcomes.

Signal recovery counts require correct localization and survival through the
full fixed OFF rule. Report preliminary ON hits and final recovery separately,
including single-ON activity, repeated activity, edge/mask losses and drift.
Always retain raw ON hits even when they are not repeated.

Resource totals include failed attempts and presentation work, rather than
only successful detector invocations. The former CI route's source byte count
and CPU are missing; report that uncertainty instead of claiming a complete
period total. The local reference analysis used3.747761CPU-s and its separate
presentation1.268920CPU-s; download/preparation timing is outside those receipts.

The accompanying `resource_ledger_bounds.json` reserves the unknown failed-CI
source transfer at its256MiB cap under the unchanged4.25GiB aggregate allowance.
The nominal256MiB engineering allowance remains UNVERIFIED; it is neither
certified nor silently increased. After the known67,109,246B local source and
root-reported384B preflight, conservative remaining source allowance is
4,227,857,666B before future headers. With a full2GiB first pilot, a second
pilot is limited to2,080,374,018B minus subsequent source/metadata transfers.
CI CPU is unknown; full20minute timeout times the officially documented public
Ubuntu runner's4vCPU is a4800CPU-second reservation, not a measured total.

## Prospective science refinement, reviewed conceptually

The science author and root chose a coupled OFF compatibility family: evaluate
every OFF global frequency/drift/width hypothesis whose predicted frequency
differs from the ON candidate by no more than the declared width-plus-channel
tolerance at BOTH endpoints of the ON scan. The intersection of these endpoint
bounds determines allowable reference-frequency indices for each OFF drift.
Any compatible OFF score above its frozen threshold supplies a veto witness.
This avoids hiding a compatible interference track behind an unrelated larger
per-carrier maximum, and respects inter-scan time gaps. Expanded OFF carrier
coverage and decoded drift/filter halos must be metadata-derived and checked.

The author also replaced full drift-by-width score cubes with streamed
per-carrier maximum/argmax maps, complete hit classifications and statically
reproducible control seeds/recipes/hashes. This addresses the8GiB disk constraint;
actual output sizes still need measuring at execution. These choices are not
yet a review of a final written contract or an executed validation panel.

Official HDF5/h5py documentation checked8Oct:
- https://docs.h5py.org/en/stable/high/dataset.html#chunked-storage
- https://docs.h5py.org/en/stable/high/file.html#python-file-like-objects
- https://api.h5py.org/h5d.html#get_chunk_info_by_coord

This is an initial review of concrete design constraints, not a passed pilot
source gate. It will be reconciled with the actual prospective source/protocol.
