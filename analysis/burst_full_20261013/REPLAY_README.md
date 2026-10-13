# Portable saved-data replay: NEW2010 outputs only

The saved replay uses Python 3.12 and NumPy 2.3.5 only. It does not import
h5py, hdf5plugin, SciPy, the producer, or the original detector. Install the
single dependency from REPLAY_REQUIREMENTS.txt in an isolated environment.

The arithmetic helpers are an exact narrow copy from the publicly frozen
qa_v2.py (SHA256 ccc7f96d079653d04df5a679af2192173a8e1281c80a3d21b995d5a3dd847cd5).
The copied helper block SHA256 is
1ecf7341951a768dbd0ad5d541eaa121dd1a349aac8c7ddfc9a88049284ae53d.
This is a portable application of the same independently written QA arithmetic;
it is not an additional independent implementation.

## What the modes establish

`scalar` reproduces 10,050 queried scores from saved raw float32 arrays of shape
4×503, using direct local 501-channel medians and the saved full-16-row
normalization parameters. The replay checks the saved row sums, score, rounded
centers, inclusive box support, and declared winner/DC identity. It is
conditional on the saved normalization and audited tuples. Their membership
in the original maps and their original telescope bit provenance are bound
through complete producer receipts and the PASS main QA receipt, not rerun
against the original HDF5 telescope files.

`full_dc` performs those same 10,050 scalar checks and independently reproduces
normalization plus both unrestricted and per-hypothesis DC-clean maxima for
all 4,096 carriers in each of the 18 retained raw 16×12,096 DC frames. It checks
winning width/window/drift/counts and the nine explicit EMPTY records. It does
not exhaustively remax the other 1,992 new cores.

This package concerns the 2,010 new maps. It does not reproduce the reused 288
pilot maps, full 766-domain global rankings, or six-scan context. An extended
scientific delivery must include their separate byte closures and receipts.
None of these scores are calibrated SNR/FAP or qualified SETI detections.

## Source-only checks

```
python seti_burst_full/saved_replay.py --check-only
python seti_burst_full/package_replay.py --check-only
```

Both checks import only the standard library and read no numerical payload.
Existing producer, main QA, pilot files, and outputs are never overwritten.

## Freeze and prepare sequence

Publish and read back saved_replay.py, package_replay.py, this README and
REPLAY_REQUIREMENTS.txt first. REPLAY_CODE_FREEZE.json must have:

- status PASS_PUBLIC_FREEZE_SAVED_REPLAY_CODE_READBACK
- replay_sha256, package_sha256 and the 40-hex public_commit

A root-authored REPLAY_PREPARE_GO.json must have:

- status GO_PREPARE_FULL_SAVED_DATA_REPLAY_METADATA_ONLY
- replay_sha256, code_freeze_sha256 and main_qa_receipt_sha256

After all 21 original shards are COMPLETE and the original qa_results receipt
is PASS, prepare the exact closure from code and JSON metadata only:

```
python seti_burst_full/saved_replay.py --root ROOT --prepare   --code-freeze-sha256 CODE_FREEZE_SHA --prepare-go-sha256 PREPARE_GO_SHA   --main-qa-receipt-sha256 MAIN_QA_SHA
```

The command creates fresh REPLAY_SCOPE.json. It reports exact scalar/full mode
required bytes and the complete NEW2010 closure bytes. Preparation does not
open any NPZ or original HDF5 file. It binds every producer output declaration
to the original main-QA input hashes and the complete shard receipts.

Publish/read back that scope. REPLAY_FREEZE.json must have status
PASS_PUBLIC_FREEZE_SAVED_REPLAY_SCOPE_READBACK, scope_sha256, replay_sha256 and
public_commit. REPLAY_ROOT_GO.json must have status GO_SAVED_REPLAY_SCALAR or
GO_SAVED_REPLAY_FULL_DC, matching mode, scope_sha256, replay_sha256,
freeze_sha256 and resource fields CPU_cap_s=600, wall_cap_s=900,
memory_cap_bytes=2147483648, output_cap_bytes=8388608.

```
python seti_burst_full/saved_replay.py --root ROOT --run --mode scalar   --scope-sha256 SCOPE_SHA --freeze-sha256 FREEZE_SHA --root-go-sha256 GO_SHA
```

Use `--mode full_dc` with its matching GO for the larger replay. Use a fresh
`--output seti_burst_full/OTHER_NEW_OUTPUT` for each separately authorized run.
No automatic retry/resume or overwrite is performed. Failures remain recorded.
The measured CPU/wall/RSS and exact tested subset are in REPLAY_RECEIPT.json.

## Archive and fresh extraction

REPLAY_PACKAGE_GO.json must have status GO_PACKAGE_NEW2010_PORTABLE_REPLAY,
package_sha256, scope_sha256, freeze_sha256, CPU_cap_s=600, wall_cap_s=900 and
memory_cap_bytes=2147483648. Package only after primary/QA slots are released:

```
python seti_burst_full/package_replay.py --root ROOT --create   --scope-sha256 SCOPE_SHA --freeze-sha256 FREEZE_SHA --root-go-sha256 PACKAGE_GO_SHA
```

The archive contains all new-map output bytes plus frozen provenance and
replay source/admission files. It contains no telescope HDF5 source files.
It is verified by streaming every payload SHA256 and ZIP CRC. Creation has a
1,250 MiB archive cap and an 8 GiB allocated-workspace cap.

For extraction, use a separate root-authored GO file with status
GO_VERIFY_EXTRACT_SAVED_REPLAY_ARCHIVE, package_sha256, archive_sha256,
scope_sha256, mode, and the same CPU/wall/memory resource fields. Point
`--root-go` to this file. Select a fresh output root under the workspace:

```
python seti_burst_full/package_replay.py --root ROOT --verify-extract   --archive ARCHIVE --archive-sha256 ARCHIVE_SHA --scope-sha256 SCOPE_SHA   --mode scalar --root-go seti_burst_full/REPLAY_EXTRACT_GO.json   --root-go-sha256 EXTRACT_GO_SHA --output-root ROOT/fresh_saved_replay
```

Every payload is streamed and verified, but only the selected replay subset
is written. The scalar subset omits all 2,010 map NPZ files; full_dc additionally
extracts only the 18 affected maps and raw frames. The extraction receipt names
this intentionally partial root and its exact byte/member census. Run the
replay there with the archived matching root GO, exact hashes and a fresh
output directory. This avoids duplicating the full archive's map storage.

Dependency wheels are not bundled by this recipe. Once numpy==2.3.5 is
installed, replay makes no network requests. The original source attribution,
source row hashes and nine compact declarations remain in frozen metadata;
the original telescope HDF5 files are not required for the saved-data replay.

### One extended full-delivery archive

To include the unchanged 288 pilot maps and their normalizations, pilot actual
QA/context artifacts, and final aggregate/context/report outputs in the same
archive, provide a root-authored explicit extras manifest. Its schema is
SETI_FULL_BURST_EXTENDED_DELIVERY_EXTRA_PINS_V1, status
READY_FULL_DELIVERY_EXTENSIONS, pilot_maps=288 and files is an array of exact
{path, bytes, sha256} pins. Root PACKAGE_GO must additionally bind
extras_manifest_sha256. The file allowlist accepts paths under seti_burst_on
or seti_burst_full with extensions py/json/md/txt/npz/csv/png/pdf/jsonl. It
rejects HDF5, ZIP archives, pyc files and log files. Primary-scope external
frozen text pins remain included even when outside those extras prefixes.
Each of the 288 pilot map/normalization pins is required. The pilot QA source
and PASS receipt, context source/QA, and saved CONTEXT_PROFILES are required.
Report files in a delivery directory are allowed through exact file pins.

```
python seti_burst_full/package_replay.py --root ROOT --create \
  --extras-manifest seti_burst_full/FULL_DELIVERY_EXTRA_PINS.json \
  --output seti_burst_full/SETI_FULL_BURST_DELIVERY.zip \
  --scope-sha256 SCOPE_SHA --freeze-sha256 FREEZE_SHA \
  --root-go-sha256 PACKAGE_GO_SHA
```

The resulting canonical manifest lists every new, pilot and extension payload.
The SHA256/CRC verifier checks the exact expanded member set. Selective fresh
extraction still writes only the NEW2010 scalar/full_dc replay subset; extra
pilot/global/context artifacts are verified and included, but saved_replay.py
does not claim to numerically replay them. No intermediate new-only ZIP is
needed.
