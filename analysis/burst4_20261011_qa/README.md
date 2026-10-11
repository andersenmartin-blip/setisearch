# Independent four-row burst QA

This separate create-only phase checks all 288 completed combined maps, 1,161
selected raw4x503 winning-score queries, and 144 decoded OFF source rows. It
imports no detector and reruns no window/drift/width grid.

Full-core normalization retains all 16 rows. For each four-row audit, QA uses the
saved median/MAD/location parameters at its four absolute source row indices.
NumPy independently recomputes raw501 local medians and divides the selected
four-row width-box sum by **sqrt(4*width)**. A full16 context score has a different
denominator and is not expected to equal the burst score.

QA independently recomputes all 4,608 raw4096 core row medians, validates every
winning window/index/width and full count 2,226 per carrier, reconstructs pooled
96-core TOP20/TOP3 rankings, and checks canonical outputs and byte pins. Full-core
residual MAD/location remain hash-bound saved parameters; this QA does not
independently refilter them or validate exhaustive argmax/tie order.

Metadata-only check:

```bash
python analysis/burst4_20261011_qa/qa_saved.py --root . --check-only
```

Actual execution requires three COMPLETE primary receipts and a separate pinned
`analysis/burst4_20261011_qa/ROOT_GO.json`, written by root after public QA freeze:

```json
{
  "status": "GO_INDEPENDENT_SAVED_BURST4_QA",
  "qa_sha256": "<QA source SHA256>",
  "primary_scope_sha256": "<primary scope SHA256>",
  "primary_driver_sha256": "<primary driver SHA256>",
  "primary_public_freeze_commit": "<primary commit>",
  "qa_public_freeze_commit": "<QA commit>",
  "primary_receipt_sha256s": {
    "primary20170428_HIP97319": "<receipt SHA256>",
    "primary20170428_HIP97461": "<receipt SHA256>",
    "primary20170428_HIP97663": "<receipt SHA256>"
  },
  "primary_admission_pins": {
    "analysis/burst4_20261011/ROOT_GO.json": {
      "bytes": 0,
      "sha256": "<actual SHA256>"
    },
    "analysis/burst4_20261011/PUBLIC_FREEZE.json": {
      "bytes": 0,
      "sha256": "<actual SHA256>"
    }
  },
  "CPU_cap_s": 600,
  "wall_cap_s": 900,
  "memory_cap_bytes": 2147483648,
  "output_cap_bytes": 4194304
}
```

Primary ROOT_GO must carry `public_freeze_commit`; PUBLIC_FREEZE contains `commit`,
`new_maps_executed_yet: 0`, and served files with `path`, `exact: true`, and
`git_blob_sha`. All lengths and hashes above must be actual values.

Root alone runs numerical QA after three closed jobs:

```bash
python analysis/burst4_20261011_qa/qa_saved.py \
  --root . \
  --scope-sha256 <scope-SHA> \
  --qa-sha256 <QA-source-SHA> \
  --root-go-sha256 <QA-GO-SHA> \
  --primary-receipt primary20170428_HIP97319=<receipt-SHA> \
  --primary-receipt primary20170428_HIP97461=<receipt-SHA> \
  --primary-receipt primary20170428_HIP97663=<receipt-SHA>
```

Success writes `results/QA_RECEIPT.json` with status
`PASS288_BURST4_MAPS1161_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN`.
This pilot samples 96 cores per target; it adds duration hypotheses on existing
data, without new bandwidth, observation, independent replication, or SNR/FAP
calibration. Both primary slot locks must be available.
