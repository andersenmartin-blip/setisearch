# E prospective raw RECORD repair

D's sole authorized capture ended `FAILED_CLOSED`, before scientific imports,
with `frozen target RECORD relocation row was unused`. D's sources, activation,
result, and installed inputs remain unchanged. Its retained stderr, custody, and
result are copied under `preserved-D/`.

The pinned Python 3.12 `Distribution.files` implementation passes parsed rows
through `skip_missing_files`, retaining only `path.locate().exists()`. Both NumPy
`../../bin/` declarations are absent under the installed `--target` layout, so
that property drops the rows before D's exact relocation handling can use them.
The copied stdlib source preserves the evidence. This repair creates a new E
collector and does not repeat D or install/import any scientific package.

## Admission interface

The CLI adds required `--record-inputs PATH`, retaining every previous required
argument: `--activate-native-metadata`, `--venv-root`, `--filter-input`,
`--record-relocations`, and `--output`. Root owns the distinct single-use E plan,
source/input freezing, guard, complete direct-child supervision, activation, and
bounded runtime metadata capture. No automatic successor is authorized here.

`record-inputs.json` has exact keys `schema`, `venv_root`, and `records`.
Its schema is `seti-installed-raw-record-inputs-v1`; `records` contains exactly
the three cohort names, each with `version` and `record_pin`. A pin contains
exactly `path`, `bytes`, `sha256`, and permission `mode`. Paths are the exact
owned `site-packages/{name}-{version}.dist-info/RECORD` locations. Each metadata
object's concrete `PathDistribution._path` must be that exact directory.

| Distribution | Installed raw RECORD bytes | Raw rows | Presence-filtered rows |
| --- | ---: | ---: | ---: |
| NumPy 2.3.5 | 84,100 | 904 | 902 |
| h5py 3.16.0 | 9,539 | 106 | 106 |
| hdf5plugin 7.1.0 | 2,263 | 26 | 26 |

Authoritative inventory uses the complete pinned raw bytes through
`BoundedReader`; it never invokes `Distribution.files` or `read_text('RECORD')`.
Each read is capped at 1 MiB and charged against the existing 512 MiB explicit
collector read budget. The parser requires strict UTF-8, strict three-column
CSV, at most 12,000 rows, unique canonical finite paths, canonical unpadded
URL-safe SHA-256, canonical sizes no larger than 128 MiB, and exactly one
unhashed self-RECORD row. This exact installed cohort contains no generated
bytecode; empty hash/size fields on other paths fail closed. Missing ordinary
files, aliases, unknown `..` paths, duplicate rows, and incomplete inputs fail.

Only the previously frozen two NumPy relocation rows are permitted. Their raw
hash/size must match the frozen mapping and their actual script bytes, size,
mode, and exact path must match the full script pin. Unknown relocation or an
unused frozen relocation fails. Ordinary nonnative file hashes remain RECORD
expectations; scientific native files retain the original complete-byte ELF
handling and cache identity checks.

The collected inventory retains full raw RECORD base64, whole-file hash,
identity, byte count, complete row count, and each row's original ordinal,
declared path, hash, size, and actual location. The reported stdlib presence
projection is explicitly reconstructed from those retained raw rows in raw CSV
order; it is never the inventory authority. Before/after equality includes the
raw RECORD witness as well as individual file rows.

## Verification performed

All 37 offline tests passed: the existing 13 collector orchestration/metadata
tests, 8 ELF mapping tests, and 16 realistic raw RECORD/relocation cases.
An inert `PathDistribution` fixture reproduces the actual filtering of the two
missing declarations while the new inventory verifies both actual scripts.
A reversed RECORD verifies projection order and ordinal preservation. Other
tests cover missing ordinary rows, malformed CSV/UTF-8, canonical hash/size,
schema, duplicate paths, changed whole-body pins, metadata owner/alias, finite
read/row bounds, unused/unknown relocation, and script byte/mode mismatches.

`metadata_only_preflight.py` also passed against all three actual installed
metadata directories using the current base interpreter with enforced
`-I -B -S`, exact interpreter whole-byte hash, 60-second wall limit, 512 MiB AS,
and 64 MiB explicit read cap. It read 100,835 bytes of selected metadata/script
inputs and 31,035,224 total explicitly charged bytes including interpreter and
collector source. It corroborated the actual stdlib `.files` projection and
verified both script relocations. It launched no installed Python, imported no
scientific module, read no scientific native file bytes, and observed no filters.
Native paths in this preflight are only statted through an explicitly injected
metadata-only reader. The real collector CLI retains its default native reader.

Stdlib metadata version/projection and source-import reads in that preflight
are separate implicit reads, explicitly labelled in the retained report.
Selected integrity, source pins, and this layout preflight confer no native
custody, runtime qualification, scientific execution, spectrum access, CAS, or
certificate authority. Those fields remain false. D's first frozen attempt
and all earlier closed scopes remain closed.
