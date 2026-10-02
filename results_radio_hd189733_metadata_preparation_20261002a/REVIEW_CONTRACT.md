# Prospective HD189733 metadata candidate — review contract

This candidate is staged only under `/tmp/seti-prospective-source-metadata/`.
It does not change a repository source, existing contract, source guard, result,
control scope, private ledger or marker. No integration or publication is claimed.

`prospective_source_metadata_radio.py` exports two pure functions:

```python
build_prospective_source_contract(
    raw_files, expected_file_pins, *, expected_source_inventory_sha256,
    evidence_checkpoint=CHECKPOINT, intended_code_runtime_binding=None,
    scientific_certificate_pin=None, joined_transport_certificate_pin=None,
    reservation_store=None, cumulative_limits=None, trial_protocol_pin=None,
)
validate_prospective_source_metadata(
    outputs, expected_output_pins, raw_files, expected_file_pins, *,
    expected_source_inventory_sha256, evidence_checkpoint=CHECKPOINT,
)
```

Every raw-file pin is exactly `{bytes: int, sha256: str}`. The caller must supply
these pins independently; a dictionary Boolean, local hash selected after a
change, checkpoint string or returned digest is not public authority. The sample
input custody authenticates the matrix's 19 raw Git-blob pins at immutable local
checkpoint `58e7a883bf8ccf7951e8365f658d7b6645f161e4`, plus six supplemental current
implementation Git-blob pins. Those inputs are metadata or source text only;
source text is hashed, never imported or executed. No fresh public readback or
execution-runtime match is claimed. External publication/custody remains a
separate caller requirement.

The exact 25-path closure includes all eight `source_radio.IMPLEMENTATION_PATHS`
and `acquisition_radio.py`. Old reader and search pins differ, and filter and
acquisition pins are absent in the original preparation; all four differences
are retained as blockers/ancestry rather than silently inherited.

The builder returns canonical UTF-8 bytes for three separate documents:

| Key | Schema | Boundary |
|---|---|---|
| `prospective_wrapper` | `radio-prospective-source-metadata-wrapper-v1` | Distinct top-level artifact; nested source-contract-v1 fields only; never a loadable active source contract |
| `admission_matrix` | `radio-new-source-admission-matrix-v1` | Every current missing admission requirement remains `missing-not-admitted` |
| `provenance_rebinding` | `radio-prospective-source-provenance-rebinding-v1` | Original raw source/window/bank ancestry; new executable source SHA is null; no admitted executable rebinding |

All three retain `PROSPECTIVE_TELESCOPE_ACCESS_BLOCKED`, exact false authority
flags, zero workload counters and stop date 2026-10-09. The nested three gates
all remain pending. Historical inactive session ceilings are preserved without
new allocation. Actual HDF5 runtime, scientific/transport certificates, trial
protocol, cumulative limits, reservation store, public ledger revision and fresh
allocation remain explicitly missing. Supplying any future runtime/certificate/
allocation argument is refused, including a `{status: passed}` Boolean proxy or
even a purported GitHub location. This candidate has no active-admission API.

The validator authenticates separately supplied output pins and recomputes raw
evidence/geometry/clock closure without invoking the builder. Shared pure
canonicalization and semantic observation helpers are used; this is a separately
callable checking path, not a claim of independent algorithm implementations.
Canonical comparisons preserve integer/float/Boolean distinctions. Duplicate
JSON members, nonfinite numbers, noncanonical output, unknown output fields,
missing/extra inputs or output files, and budget excess are refused.

The reconstruction checks the six ordered ON/OFF scans and retained headers,
original source inventory, three roles, 288 unique scan/row/chunk identities,
65,536 channels per extraction, exact normalization blocks and frequency
convention. The clock uses `Fraction` of decoded JSON int/float values, preserving
the original binary-float header interpretation and rational start/midpoint/end
clock; its known bank digest is
`807e59e40311d623231a13f05bd3bdf4801e83bacd90aae5f9f3b28380f02c48`.
The bank remains recorded-topocentric linear ±4 Hz/s in 0.1 steps, 81 scored
carriers over 226.84027347621408 Hz, and widths 1/3/5/9/17/33/65/129. Historical
bank identities and factor hashes are authenticated and their provenance is
rechecked; factor bytes are **not** regenerated, scored or numerically requalified.
The inactive 127-reference/24-evaluation proposal retains EMPTY/inclusive-rank,
tie, recipe/count and no-execution semantics; no values, outcomes or certificate
are computed.

Input bounds are 512 KiB per file and 2 MiB total; output bound is 256 KiB per
document. These are closed metadata parser bounds, not changed control/source
workload caps. The constructor and validator have no filesystem, network,
runtime-probe, subprocess, acquisition, genesis, RNG, science or LS API. Only
standard-library `fractions`, `hashlib`, `json`, `math` and `re` are imported.

`test_prospective_source_metadata_radio.py` uses staged retained metadata and
bounded in-memory tampering. Forty-two tests cover actual known clock/identity pins,
current implementation closure, unchanged searched scope, missing dependencies,
wrong source/last OFF/ETag, overlap, session drift, clock rounding/type changes,
expanded rate/width/frame, fake bank identity, weakened rank/EMPTY/ties,
incomplete/spent proposal, Boolean certificate/runtime/ledger proxies, coherent
rehashed output forgery, unknown fields, malformed JSON, exact file budgets and
side-effect barriers. No deterministic source/codec/scientific fixture is rerun.

Integration, if separately reviewed, should add a new metadata component and
tests without editing the old preparation binder, receiver provenance APIs or
live source guards. Preserve the failed engineering attempt and spent marker.
No integration can promote this wrapper into telescope/native/127/24 authority;
later qualified runtime/transport/scientific/protocol/allocation admission needs
a distinct interface and reviewed immutable evidence. LS stays paused; spectra,
holdouts and reserved native inputs remain unopened; stop 9 October with no
automatic extension or restart.
