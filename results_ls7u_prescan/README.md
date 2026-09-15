# LS7U electronic-reference evidence and reproduction

The [findings](../LS7U_ELECTRONICS_FINDINGS.md) report the primary virtual
prescan result and the separately scoped PIPE blank-reference supplement.
The native target images remain unread; this packet contains electronic
reference arrays. Input remains NOT_READY_FOR_TARGET_IMAGE_STUDY.

## Saved artifacts

| Artifact | Purpose |
|---|---|
| [Primary protocol](../LS7U_PRESCAN_PROTOCOL.md), protocol_identity.json | Fixed primary scope and identity before prescan acquisition |
| [Supplement](../LS7U_BLANK_SUPPLEMENT.md), blank_reference/protocol_identity.json | Exploratory input-mapping scope, specified before blank acquisition |
| acquisition.json, prescan_bytes_*.bin.gz | Exact primary HTTP ranges, response identity and lossless bytes |
| summary.json, prescan_frame_statistics.csv.gz | Primary estimates, every unit comparison and all 432 frames |
| blank_reference/acquisition.json, blank_reference/prescan_bytes_*.bin.gz | Exact blank-reference ranges; the shared saver retains its prescan filename prefix |
| blank_reference/summary.json, blank_reference/blank_frame_statistics.csv.gz | Original PIPE results, scalar clipping trace and all 432 frames |
| source_identities.json, pipe_statistics.py, THIRD_PARTY.md | Pinned sources and original licensed PIPE dependency |
| calibration_contract.json | Updated physical-input decision and unresolved conditions |
| verification.json, verification.log, blank_reference/verification.log | Actual verification outputs and clean offline reproduction |

The four retained ranges total 4,164,480 bytes: 17,280 header bytes plus
4,147,200 electronic-array bytes. Lossless gzip uses deterministic mtime=0.
Each acquisition manifest records compressed and uncompressed SHA-256,
range offsets, HTTP 206 response identity and the original object ETag.
No expiring signed download URL or credential is retained.

## Reproduce from the repository root

Use Python 3.12 with NumPy, Astropy and the dependencies of the existing
LS7R acquisition helper. This run used Python 3.12.14, NumPy 2.5.3 and
Astropy 8.0.1. The verifier makes no network request.

```bash
python3 scripts/ls7u_verify.py
```

It checks saved ranges and both original FITS checksums, runs both assessments
in fresh temporary output directories, compares all four derived files
byte-for-byte and writes verification.json. Individual commands are:

```bash
python3 scripts/ls7u_acquire_prescan.py --offline
python3 scripts/ls7u_assess_prescan.py
python3 scripts/ls7u_acquire_blank.py --offline
python3 scripts/ls7u_assess_blank.py
```

The assessments reuse LS7R's saved native headers and timestamp metadata,
LS7S's saved CAL values and pinned PIPE reader, and LS7T's already measured
HK gain diagnostics. Those historical artifacts are retained on this branch.
Only the reviewed original PIPE function ASTs execute. The blank test uses
an empty HDU 1 with the actual NEXP and the original blank extension at HDU 2;
it is not a full native FITS product or PIPE extraction.

Primary arithmetic includes no clipping. The supplement independently checks
the original function's ten global clipping iterations and reports their effect.
Neither test opens target pixels or measures a source detector's response.
The supplement was chosen after the primary result and is labelled accordingly.

Both acquisition scripts also support exact bounded retrieval when the saved
ranges are absent. They require identical original ETag, size, native headers
and HTTP 206 ranges and never fall back to a full file. The previously blocked
mission reference-bundle action is outside this packet and must not be retried
or bypassed.
