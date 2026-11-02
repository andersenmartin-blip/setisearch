This is a distinct **posthoc quality-reference phase**, motivated by the completed May reference's weak continuum. The single candidate is `ADP.2017-05-21T01:01:50.278`, raw progenitor `HARPS.2017-05-20T02:21:45.847`, target HD122640. Its saved average spectrum SNR is 77.8, the highest among the nine unused May 2017 candidates; this does not guarantee better blue-region quality. No unseen line flux enters selection. The completed two-epoch / 24-profile study and all 185 U / 35 M labels remain unchanged.

`CANDIDATE.json` is the exact prior handoff object. `PLAN.json` binds its identity, the nine-product metadata selection, all six discovery BERV values, source hashes and code hashes. `header_tools.py` is a byte-identical copy of the previously checked parser and identity validator. No new archive/documentation requests or scientific array reads were used to prepare this phase.

| Stage | Fixed scope | Hard limits |
| --- | --- | --- |
| Header | Exactly this one product through the verified ESO `/hdr?DpId=` route | One attempt, 30 seconds, 512 KiB, no redirects or retries |
| Optional spectrum | Same exact product through the verified direct-file endpoint, after a separate root release | One attempt, 60 seconds, 16 MiB, no redirects or retries |

The header must pass inherited exact ADP/raw identity, HD122640 target, HARPS, DATE-OBS/MJD, exposure and coordinate checks. It must have `NCOMBINE=1`, `SPEC_RES=115000`, `SPECSYS=BARYCENT` and explicit `HEFS=false`. Extra raw progenitors, missing mode information or invalid coordinates fail closed. The recorded candidate BERV must satisfy **absolute displacement ≥ 10 × c/R = 26.06890939130435 km/s from each of the six discovery BERV values**. All six checks are retained, including repeated discovery exposures. This is a descriptive planning benchmark, not classification or statistical power. It need not extend the already known 40.36348 km/s range.

The header stage writes `HEADER_RESULTS.json` and `SELECTION.json` with the prior comparator's structural fields. A failed request, identity check or displacement gate leaves zero selected products and blocks payload acquisition. A passing header creates exactly one proposed selection, retaining the original response and receipt hashes. It does not itself authorize a spectrum request.

The payload stage independently rechecks the header release, raw response/receipt, fresh parsed identity and six BERV tests before any download. It requires an additional root release that binds these exact outputs and their published bytes. After transfer, it inspects FITS headers only: complete exact provenance, a header-only primary HDU, a one-row binary table, unique WAVE/FLUX/ERR columns with equal positive fixed numeric-real vector lengths, air-Angstrom wavelength and ADU flux. It never accesses `HDU.data`. Failure preserves the bytes and records a failed manifest slot; there is no replacement candidate. The separately frozen comparator must also validate the payload before reading arrays.

Both stages use curl 8.4 or later with `--disable`, fixed HTTPS endpoints, total-time and streaming-byte caps, `--retry 0` and no redirect following. Exclusive `HEADER_STARTED.json` / `PAYLOAD_STARTED.json` markers prevent replay, including after interruption. All transport diagnostics, receipts and response bytes are retained. The acquisition manifest keeps the prior `inputs`, `local_path`, `sha256`, `bytes`, status and receipt fields, with `product_path` / `product_sha256` aliases for the comparison adapter.

The root creates `../PREFLIGHT_FREEZE.json` before the header request. Its `files` mapping uses repository-relative paths and byte/SHA-256 records; it must include all prospective acquisition and comparison methods. All frozen files and historical source hashes are checked at each stage.

`HEADER_RELEASE.json` must contain:

```json
{
  "schema": "HARPS_MAY_QUALITY_HEADER_RELEASE_V1",
  "approved": true,
  "freeze_sha256": "<root-level PREFLIGHT_FREEZE hash>",
  "plan_sha256": "<PLAN hash>",
  "candidate_sha256": "<CANDIDATE hash>",
  "code_hashes": {"acquire.py": "<hash>", "header_tools.py": "<hash>", "prepare_plan.py": "<hash>"},
  "prospective_commit": "<40-character commit>",
  "remote_bytes_verified": true,
  "publication_receipt_path": "<repository-relative receipt path>",
  "publication_receipt_sha256": "<receipt hash>"
}
```

The publication receipt must have `status=PASS_EXACT_REMOTE_READBACK`, the same `commit`, and `files` entries binding the root freeze and every new-phase file listed in that freeze. Existing historical dependencies remain bound by their recorded hashes.

`PAYLOAD_RELEASE.json` uses schema `HARPS_MAY_QUALITY_PAYLOAD_RELEASE_V1` and the same plan/candidate/code/freeze fields, plus `header_release_sha256`, `header_results_sha256` and `selection_sha256`. Its own publication receipt must bind `HEADER_RELEASE.json`, `HEADER_RESULTS.json`, `SELECTION.json` and the original header body/receipt. Its prospective commit is the verified publication before the optional payload. The earlier prospective method publication is revalidated separately through `HEADER_RELEASE.json`.

Only the root executes a released stage:

```bash
python3 work_harps_20261102_may_quality/acquisition/acquire.py header --execute
python3 work_harps_20261102_may_quality/acquisition/acquire.py payload --execute
```

Omitting `--execute` performs no network operation. Never rerun a completed stage to restore evidence. This code does not package payloads, run the comparison, update labels or change the original 300-exposure survey.
