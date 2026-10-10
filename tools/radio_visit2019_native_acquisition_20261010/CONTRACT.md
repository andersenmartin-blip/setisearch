This is source-only preparation. Do not import or execute these scripts until the
coordinating root has frozen actual qualified metadata, clean TREE1 descriptors,
fresh request history, protected-frame evidence, source review, and root GO.

The fixed source set is session AGBT19B_999_31, blc77, 2019-09-29:
HIP98505 0077/0079/0081 and HIP98375 0078, HIP98154 0080, HIP98440 0082.
No time count, frequency geometry, tree depth, chunk size, byte offset, datatype,
or filter parameters are borrowed from earlier visits. The actual dtype must be
little-endian float32 with shape [ntime,1,nchan] and chunks [1,1,nativechan].
All six actual headers must share geometry, filters, frequency and time spacing.
The fixed native ordinal is floor(ceil(nchan/nativechan)/2), chosen from metadata
before amplitudes. A partial midpoint native is explicitly rejected before HTTP.

The future ROOT-relative scope is
tools/radio_visit2019_native_acquisition_20261010/scope.json, with these fields:

* schema: SETI_VISIT2019_ONE_NATIVE_RAW_ACQUISITION_SCOPE_V1
* worker_pin, launcher_pin, common_pin: exact {path,bytes,sha256} source pins
* qualified_metadata_pin: actual qualification result pin
* qualified_execution_pin: exact completed qualification execution receipt pin
* descriptor_manifest_pin: actual clean typed row manifest pin
* prior_source_attempts_pin: current complete known attempted ranges pin
* protected_frames_pin: exact disjoint proof pin
* limits: CPU_seconds 120, wall_seconds 1800, memory_bytes 536870912,
  payload_BODY_bytes 268435456, shared_workspace_bytes 12884901888
* shared_workspace_roots: /workspace/scratch/a8d1e29996d0 and
  /workspace/scratch/5bf3860dacd6, scanned without following symlinks
* output_directory: results/radio_visit2019_native_acquisition_20261010/acquire_once
* source_workers_max: 1
* signal_decode_authorized: false
* retry_resume_or_rerun_authorized: false
* independent_validation_admission: BLOCKED
* original_A_B_status: FAIL_CLOSED
* runtime_package_versions: {h5py: 3.15.1, hdf5plugin: 7.1.0}
* hdf5_version: exact runtime HDF5 version established by root
* exact_expected_payload_BODY_bytes: exact sum of all six actual stored row sizes
* payload_HTTP_request_cap: exact sum of all six actual ntime values
* output_cap_bytes: 2*exact_expected_payload_BODY_bytes + 67108864

Qualification result schema is
SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_RESULT_V1, status
PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY, metadata_eligibility status the same,
all checks PASS, no spectral values or dataset value API, independent validation
BLOCKED. sources[6] have the metadata author's exact typed-attribute fields:
source_id, url, ordered_index, etag, source_file_bytes, shape, chunks,
dtype_string, dtype_itemsize_bytes, creation_filters, root_attributes,
data_attributes, root_attribute_types, data_attribute_types, fixed_midpoint_rule,
native_chunks_along_frequency, metadata_derived_midpoint. Attribute type maps are
bijective with value maps; records retain shape, numpy_dtype_string/kind, exact
hdf5_type_encoded_hex/bytes/sha256. Scalar shape is [].

Descriptor manifest schema is
SETI_VISIT2019_ONE_NATIVE_RAW_DESCRIPTOR_MANIFEST_V1, status
PASS_CLEAN_EXACT_SIX_NATIVE_ROW_DESCRIPTORS_METADATA_ONLY. Fields:
qualification_result_pin; spectral_values_read false; spectral_payload_fetched
false; fixed_midpoint_rule exactly
"floor(n_native_frequency_chunks/2); zero-based; fixed before amplitudes";
typed_index_evidence_pins a finite nonempty exact pin list; sources[6] in source
order. Each source has source_id,url,ordered_index,etag,source_file_bytes,status
COMPLETE_SELECTED_NATIVE_CHUNK_DESCRIPTORS_NO_VALUES_ADMISSION,descriptors[ntime].
Each descriptor is the pure TREE1 author's record unchanged: time_row,
coordinates [row,0,c0,0], file_offset,size,filter_mask,source_channel_start,
logical_channel_count,decoded_full_chunk_bytes,typed_leaf_pointer_evidence,
metadata_traversal,payload_pointer_followed false,HTTP_authorized false.

Prior history schema is SETI_VISIT2019_PRIOR_SOURCE_RANGE_ATTEMPTS_V1, status
PASS_COMPLETE_KNOWN_REQUEST_HISTORY_NO_REPLAY; sources[6] have
source_id,url,ordered_index,etag,source_file_bytes,attempted_ranges_half_open.
Every attempted byte interval is included even if the prior request failed.
New payload ranges must be unique, mutually disjoint, source-bounded, and
disjoint from every prior attempted interval. These inputs are not inferred by
the acquisition runner.

Protection schema is SETI_VISIT2019_PROTECTED_KNOWN_FRAMES_DISJOINT_V1, status
PASS_PROTECTED_KNOWN_FRAMES_DISJOINT; descriptor_manifest_pin and
qualified_metadata_pin match scope; original_A_B_status FAIL_CLOSED and
independent_validation_admission BLOCKED. acquisition_frames is exactly the six
ordered records {source_id,url,source_channel_interval_half_open:[c0,c0+width],
source_ranges_half_open:[all actual row intervals in time order]}.
known_frames is the complete root-proven protected list; each has url and
source_channel_interval_half_open. The runner rejects overlapping channels for
the same frozen source URL; root owns complete registry evidence and the broader
disjoint admission represented by this pinned proof.

Root admission path is results/radio_visit2019_native_acquisition_20261010/
ROOT_ADMISSION.json. Schema SETI_VISIT2019_ONE_NATIVE_RAW_ROOT_ADMISSION_V1,
status PASS_FROZEN_ONE_NATIVE_EXPLORATORY_SOURCE_VALUES_GO. Fields:
scope_sha256,worker_sha256,launcher_sha256,public_freeze_commit,
exploratory_source_values_GO true,protected_known_frames_disjoint true,
prior_source_attempts_complete true,new_payload_BODY_reserved_bytes exact sum,
new_payload_HTTP_request_cap exact count,independent_validation_admission BLOCKED,
original_A_B_status FAIL_CLOSED,source_only_peer_receipt_pin. The peer receipt
must bind scope_sha256 and exact worker_pin/launcher_pin/common_pin, with status
PASS_SOURCE_ONLY_NO_HTTP_HDF5_ARRAYS_OR_VALUES. Root admission and peer receipt
are external to scope to avoid a circular scope hash.

Future invocation from repo root, only after final root freeze/readback/GO:

```sh
PYTHONPATH=/workspace/scratch/a8d1e29996d0/seti_fullpower_work/deps \
PYTHONDONTWRITEBYTECODE=1 \
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python \
tools/radio_visit2019_native_acquisition_20261010/launch_once.py \
--expected-launcher-sha256 LAUNCHER_SHA256 \
--expected-worker-sha256 WORKER_SHA256 \
--expected-scope-sha256 SCOPE_SHA256 \
--expected-root-admission-sha256 ROOT_ADMISSION_SHA256 \
--public-freeze-commit PUBLIC_40HEX_COMMIT \
--root-go-exploratory-source-values
```

Root creates results/radio_visit2019_native_acquisition_20261010 and private
seti_fullpower_work beforehand. Both acquire_once and command_attempt must be
absent. All concurrent source HTTP stages must use the same private
SOURCE_HTTP_GLOBAL_FLOCK.lock. The outer launcher acquires it without waiting.

Each exact GET is attempted once with If-Match, Range, Accept-Encoding identity.
URL, status206, exact Content-Range/Length, strong ETag, encoding and bounds are
validated before reading any response BODY. A complete finite BODY sum is
reserved before the first HTTP. Every read's returned bytes, including exposed
exception partial bytes, are counted and the ledger fsynced before a raw write.
Original complete compressed rows are immediately fsynced, renamed, hashed and
checkpointed. Incomplete .partial files remain evidence; no resume is supported.

After every raw row is durable, serial compact writers use the exact encoded
attribute datatypes and exact original filters, write_direct_chunk, and raw-only
read_direct_chunk SHA roundtrips. Compact shape is [ntime,1,nativechan]. Original
data fch1 is shifted by c0*foff and nchans becomes nativechan; every other original
attribute is preserved. Added provenance attrs: original_source_url,
original_source_etag,original_source_frequency_chunk_origin,
original_source_native_ordinal,original_source_file_bytes. No dataset signal value
API or signal codec decode is called. Each row's first signal decode is deferred
to search. The original compressed rows remain independently retained for root's
durable raw ZIP before search. Whole original source MD5 is never claimed.

Outputs include SOURCE_BODY_LEDGER.json, raw_ranges/*.raw.bin, six compact H5,
ACQUISITION_RESULT.json and EXECUTION_RECEIPT.json. Complete status is
COMPLETE_EXACT_RAW_ROWS_AND_COMPACT_FILES_NO_SIGNAL_DECODE. Result schema is
SETI_VISIT2019_ONE_NATIVE_RAW_ACQUISITION_RESULT_V1; compact_files[6] carry exact
file pins, source_channel0/native ordinal, shape/dtype, raw_rows SHA/filter mask/
source ranges/original origins, original typed metadata, shifted compact attrs,
provenance attrs, closed writer and raw roundtrip flags. No decoded row SHA is
reported. The EXEC schema is SETI_VISIT2019_ONE_NATIVE_RAW_EXECUTION_RECEIPT_V1.
Its resource PASS is separate from the original result status.

The required qualification execution schema is
SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_EXECUTION_V1, status
COMPLETE_CACHE_ONLY_METADATA_QUALIFICATION_NO_VALUES_ADMISSION. It must match
the result's eligibility status, scope/script/public-freeze pins and exact result
SHA256, with resource_caps_satisfied and all_input_end_readbacks_exact true,
HTTP_requests0, no spectral values or dataset value API. An early qualification
result cannot substitute for this closed execution proof. Both qualification
pins are retained in the acquisition result and checked again at the end.
Exposed read-exception partial bytes are charged first, then hashed, written,
flushed and fsynced into the existing .partial file before the exception is
re-raised; its path/size/SHA remain in the failed request record.

command_attempt/COMMAND_RESOURCES.json schema is
SETI_VISIT2019_ONE_NATIVE_RAW_FULL_CHILD_RESOURCE_RECEIPT_V1. The only successful
outer status is PASS_WHOLE_CHILD_RESOURCES_AND_COMPLETE_ACQUISITION, requiring
actual child exit0, wait4 CPU/RSS through process close, combined launcher+child
CPU120, wall1800, memory512MiB, exact closed inner pins and unchanged launch input
pins. Stdout/stderr are bounded, fsynced and drained. All failures preserve the
attempt and do not authorize a retry, independent validation, or a detection.
