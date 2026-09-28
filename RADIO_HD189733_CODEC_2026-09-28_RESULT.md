# HD189733 filter admission and full-chunk runtime — 28 September 2026

**The source reader now rejects a changed filter pipeline before payload
acquisition. A source-shaped local fixture decodes bit-exactly under the
retained HD189733 filter declaration. Telescope access remains blocked.**
This continues from method checkpoint
`1f9a1513498a0496b9c2e8857f76c89d13c9df65`, under a
[new bounded codec scope](RADIO_HD189733_CODEC_2026-09-28_SCOPE.md).
No source request, telescope spectrum, reserved scientific control or new
calibration/evaluation allocation was consumed.

## Demonstrated reader gap and enforcement

Inspection found that `source_radio._extract_bound_source` recorded HDF5
filters but did not compare them to `observed_hdf5_filters` in the source
definition. ETag, shape and chunk checks were already present; they did not
implement this separately declared filter contract.

The new `hdf5_filter_contract_radio.py` validates an exact ordered sequence of
filter ID, flags and client-data integers. Display-name text is ignored.
`source_radio.py` invokes it at both dataset opens: before chunk discovery/
prefetch and before native-row extraction. A missing or malformed telescope
declaration fails before the live identity request. Local fixtures without a
declaration retain their earlier path. The new module is a required code pin
for a future source contract; old preparation documents remain unchanged.

**12 focused tests pass**, including wrong version/element-size/block/compressor
fields, missing/extra/reordered filters, changed flags, noninteger metadata,
no identity lookup on a missing declaration, no chunk discovery on a first-open
mismatch and no row read after a second-open change. These test new admission
behavior; the old generic codec/acquisition suite was not rerun as progress.

## Source profile and changed fixture scope

All six retained HD189733 definitions share the following profile:

| Property | Exact source metadata used |
|---|---|
| Filter ID / flags | 32008 / 1 |
| Filter client data | `[0,3,4,0,2]` |
| Dataset shape | `[16,1,264503296]` |
| Chunk shape | `[1,1,1048576]` |
| Dtype / decoded bytes per full chunk | float32 / 4,194,304 |
| Populated fixture chunk positions | 159, 156, 152, each at all 16 rows |
| Extracted archive intervals | `[167215104,167280640)`, `[164069376,164134912)`, `[159875072,159940608)` |

The prior generic codec fixture used 4,096-channel chunks and an 8,513-channel
extraction. This work addresses the actual source's 256-times-larger chunks,
three precise 65,536-channel extractions and legacy declaration. It does not
reopen the already closed generic test package.

The single deterministic arithmetic texture is specified in
`scripts/radio_hd189733_codec_profile.py`. Its large logical HDF5 dataset is
sparse; only 48 complete chunks are populated. No Gaussian noise, signal
injection or independent cadence was generated. The local encoder reports
client data `[0,4,4,0,2]`. Its compressed bytes were copied by direct-chunk writes
into a second local file carrying exactly `[0,3,4,0,2]`, while the optional
filter was temporarily unregistered in the isolated fixture process. Plugin
search paths and the actual decoder were restored before reading. Both files
contain the same 48 compressed payloads with filter mask zero.

This construction tests the current decoder on current-encoder payloads under
the retained source declaration. **It does not reproduce the original archive
encoder or validate an actual archive payload.** It also does not qualify
unexercised per-chunk filter-mask combinations or grant source provenance.

## Preserved oracle failure and corrected reconciliation

The original fixture execution generated both files and decoded the first role,
then stopped in its comparison oracle: a reversed NumPy view was not C-order,
as required by the unchanged normalizer. The original script, input pins and
full error remain in `fixture01/` and `fixture_execution.log`. Its execution
status remains **FAILED_ORACLE_C_ORDER**. It was not restarted or replaced.

The separately scoped
[retained-file reconciliation](RADIO_HD189733_CODEC_RECONCILE_2026-09-28_SCOPE.md)
makes only the oracle block layout contiguous, preserving the float32 bits and
element order. Two new tests reproduce that layout failure and verify the
correction plus invalid-input rejection. They pass. The reconciliation reads
the same retained files, verifies every compressed chunk against its original
receipt, and persists decoded/normalized row receipts incrementally. It does
not regenerate a fixture or consume a new scientific identity. Rechecking
the first role recovers incomplete evidence; it is not new independent data.

| Retained-fixture check | Verified result |
|---|---:|
| Distinct populated chunks | 48 |
| Compressed payload/hash comparisons, across both files | 96 |
| Full decoded float32 cells, bit-exact | 50,331,648 |
| Extracted native cells, bit-exact | 3,145,728 |
| Ascending normalized cells, bit-exact | 3,145,728 |
| New filter/layout tests | 12 + 2 passed |
| Original execution + corrective reconciliation | 2.111537401 s |
| Reconciliation peak process RSS | 103,067,648 bytes |

The normalization comparison reuses the unchanged normalizer on independently
selected and ordered expected rows. It verifies codec/selection/orientation
handoff, not a new independent proof of the normalization arithmetic. No
recovery, RFI, significance, detector or candidate-search claim is made.

Runtime: Python 3.12.14, NumPy 2.3.5, h5py 3.16.0, HDF5 2.0.0 and hdf5plugin
7.1.0 on little-endian x86_64. Thirty runtime binary files and the interpreter
are fingerprinted. The existing installation was inspected and bound; no new
package installation or paid service was used.

## Durable evidence and exact continuation

`results_radio_hd189733_codec_2026-09-28/` preserves the source profile, runtime
and input pins, all compressed/decoded/normalized receipts, both test logs,
the original error and corrective result. The two complete HDF5 files are
losslessly retained in `retained_hdf5_fixtures.tar.xz` (2,501,892 bytes). Each
extracted member was verified against its original SHA256. The separate pack
operation took 17.511137563 s with 108,265,472-byte peak RSS; it is not another
codec experiment. No evidence was discarded.

The original HD189733 preparation remains
`98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1`, not-ready.
The source reader changed deliberately; a later executable protocol must pin
the guarded reader and its new dependency. The earlier unactivated
[127/24 proposal](RADIO_WHOLE_CADENCE_NULL_2026-09-28_PROTOCOL_PROPOSAL.md)
is a historical method/budget proposal, not an executable freeze matching this
new reader. Do not edit old receipts, old source contracts or failed attempts
to make them current. All fifteen preserved old invariant pins remain intact.

**Next:** integrate the explicit whole-cadence reference into a distinct
downstream threshold/retention/rank certificate path, and qualify a codec-to-
receiver/native receipt handoff with case/noise-law/source identities. The
new decoder fixture and filter guard are reusable evidence; do not rerun
their unchanged tests or the closed original generator. Reference arithmetic
and fixture decoding do not by themselves establish either remaining boundary.
Before any new 127/24 values, require a fresh authorized allocation and a
published/read-back executable freeze with all current code/runtime pins.
The old failed attempt, its 24 unopened evaluations and its completed diagnosis
remain closed. No new diagnosis or remedy allocation was created here.

Even a later synthetic pass still requires the integrated prospective
acquisition/trial admission before telescope spectra. Source provenance and
per-cadence receipt checks must remain specific to HD189733. HD1461's hold,
untouched GJ724, M43AI's failure, original M43AF holdouts, unresolved M15/M33,
LS pause and unsent CHEOPS persist. No external messages, no target switch and
no extension beyond the plan's 9 October consolidation.

API references checked 28 September 2026: official
[h5py direct-chunk interface](https://api.h5py.org/h5d.html),
[hdf5plugin registration documentation](https://hdf5plugin.readthedocs.io/en/stable/usage.html)
and [HDF5 filter API](https://portal.hdfgroup.org/documentation/hdf5/latest/group___h5_z.html).
The raw-chunk read/write operations bypass codec transformation; ordinary
dataset reads after restoring the plugin perform the decoding. Installed
3.16.0 docstrings were also inspected because the online low-level reference
currently identifies a development version. Literature/API wire bytes are
unknown and are not represented as telescope acquisition bytes.
