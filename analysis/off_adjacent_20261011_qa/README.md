# Independent saved-map QA

`qa_saved.py` checks the completed adjacent-band original OFF search without
importing the detector or rerunning a drift/width grid. This QA is a separate,
create-only phase; three exact COMPLETE primary receipts must exist first.

## Checks

- All 18 compact sources and all 288 decoded row hashes are authenticated before
  any numerical QA output is created. Headers agree across physical native joins.
- Every one of 1,536 saved maps has the declared precision, 4,096 distinct
  physical carriers, 785 drift values, valid winning widths, and exactly 1,570
  valid hypotheses per carrier. New domains are disjoint from old native171
  OFF domains.
- Every declared raw 4,096-channel core row median is independently recomputed.
- TOP20 and TOP3 are independently reconstructed from all 512 cores per target,
  sorting score descending and absolute channel ascending, then applying greedy
  distance greater than three channels.
- Every deterministic first/midpoint/last/core-max audit and every global TOP3
  audit is checked: 6,153 logical queries in total. Raw503 float32 bits are checked
  against joined source channels, and local501 medians are recomputed with NumPy.
  Row-box sums and queried scores are compared at absolute tolerance `1e-7` and
  relative tolerance `1e-10`.
- Complete output manifests, original source before/after evidence, served
  primary freeze Git blob identities, root admission pins, source descriptor
  identity, and unchanged inputs at QA completion are checked.

The local score audit is conditional on saved full-core residual MAD and
winsorized location. Those parameters are hash-bound and validated but are not
independently refiltered. This is not an exhaustive independent maximization,
S/N or FAP calibration, sky-origin test, or additional observation.

## Metadata-only check

```bash
python analysis/off_adjacent_20261011_qa/qa_saved.py --root . --check-only
```

This imports no numerical modules and opens no H5 or NPZ files.

## Root GO contract

Root writes `analysis/off_adjacent_20261011_qa/ROOT_GO.json` after all three
primary jobs complete and the QA source is publicly frozen and read back. The
fields below are required. SHA256s, commits and admission byte lengths must be
actual current values.

```json
{
  "status": "GO_INDEPENDENT_SAVED_OFF_ADJACENT_QA",
  "qa_sha256": "<qa_saved.py SHA256>",
  "primary_scope_sha256": "<primary scope SHA256>",
  "primary_driver_sha256": "<primary driver SHA256>",
  "primary_public_freeze_commit": "<original 40-character commit>",
  "qa_public_freeze_commit": "<QA 40-character commit>",
  "primary_receipt_sha256s": {
    "primary20170428_HIP97319": "<actual receipt SHA256>",
    "primary20170428_HIP97461": "<actual receipt SHA256>",
    "primary20170428_HIP97663": "<actual receipt SHA256>"
  },
  "primary_admission_pins": {
    "analysis/off_adjacent_20261011/ROOT_GO.json": {
      "bytes": 0,
      "sha256": "<actual primary ROOT_GO SHA256>"
    },
    "analysis/off_adjacent_20261011/PUBLIC_FREEZE.json": {
      "bytes": 0,
      "sha256": "<actual primary PUBLIC_FREEZE SHA256>"
    }
  },
  "CPU_cap_s": 1800,
  "wall_cap_s": 1800,
  "memory_cap_bytes": 3221225472,
  "output_cap_bytes": 8388608
}
```

The primary receipt has no `public_freeze_commit` field. QA authenticates that
commit through exact primary ROOT_GO/PUBLIC_FREEZE bytes and checks the frozen
Git blob identities against current driver, scope and provenance bytes.

## Actual execution

```bash
python analysis/off_adjacent_20261011_qa/qa_saved.py \
  --root . \
  --scope-sha256 <primary-scope-SHA256> \
  --qa-sha256 <qa-source-SHA256> \
  --root-go-sha256 <QA-root-GO-SHA256> \
  --primary-receipt primary20170428_HIP97319=<receipt-SHA256> \
  --primary-receipt primary20170428_HIP97461=<receipt-SHA256> \
  --primary-receipt primary20170428_HIP97663=<receipt-SHA256>
```

Root alone invokes actual QA. Both primary science slot locks must be available.
The separate QA output directory `results/` is created once after full source
authentication. Success produces `INPUT_ADMISSION.json` and `QA_RECEIPT.json`.
Failure after directory creation produces `QA_FAILURE.json`; no science output
is changed or rerun.
