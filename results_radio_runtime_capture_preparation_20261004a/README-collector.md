# Bounded runtime metadata collector preparation — 4 October 2026

This collector is prepared for a separate, fresh metadata capture. Importing
`collector.py` does not capture the host. Its default, absent-contract and
public-scientific modes refuse before touching a capture backend. No genuine
capture has been run by these development tests. The original scientific
materialization plan remains PENDING with all sixteen authority flags false.

The parent gate, its published source/readback proof, fresh activation and
one-shot engineering reservation authenticate and bound a future invocation.
The child consumes the independently pinned, detached admission witness;
contract inputs cannot contain their own publication commit or activation hash.
It checks that witness against the raw collector-contract pin, plan pin and
capture identity. JSON assertions alone authenticate no service or CAS law.

The stdout-only CLI is:

```
python -I -B -S collector.py --contract PATH --contract-sha256 SHA256 \
  --plan PATH --plan-sha256 SHA256 \
  --admission-witness PATH --admission-witness-sha256 SHA256
```

Contract, plan and witness inputs are bounded, sole-link, regular 0644 files.
Every traversed directory and final file uses held nofollow descriptors and
held/named identity checks. Selected inventory files have exact external size,
SHA256, mode and role pins; their before/after observations must agree. The
collector and ELF helper themselves must occur in that selected code inventory.
The helper executes only the authenticated bytes already read from its held
file, so isolated Python does not rely on ambient script-directory imports.

The exact collector-contract fields are `schema`, `evidence_domain`,
`capture_identity`, `capture_authorized`,
`externally_bound_publication_required`, `activation_required`, `plan_sha256`,
`python_path`, `python_sha256`, `files`, `imports`, `import_paths`,
`loader_paths`, `distributions`, `missing_paths` and `limits`.
The schema is `radio-runtime-metadata-capture-contract-v1`. Each file has
`path`, `role`, `bytes`, `sha256`, `mode`; a static distribution has `name`,
`metadata_path`, `wheel_path`, `record_path`, `expected_version`. Those three
static distribution paths must be selected pinned files. The pure validator
retains the original Python 3.12.14 / cp312 / Linux x86_64 / little endian /
glibc >= 2.28 target and NumPy 2.3.5, h5py 3.16.0, HDF5 2.0.0 and hdf5plugin
7.1.0 targets. Host mismatches are recorded; they cannot replace these targets.

Actual metadata contracts require `imports: []`: native imports are deferred
until a separately authenticated complete pre-import closure exists. A narrow
static NumPy METADATA/WHEEL/RECORD observation reports distribution identity,
tags and RECORD row count. It imports no package and traverses no RECORD member
path, and cannot prove complete package custody or a loaded runtime identity.
Missing-path observations refer only to the exact externally listed paths at
the before/after observation points; they claim no whole-filesystem absence.

The collector observes Python executable bytes/hash, version, Linux release,
architecture, endianness, libc and isolation flags. It preserves exact raw
`/proc/self/maps` text plus its parsed address, permissions, offset, device and
inode fields before and after. Selected ELF metadata is extracted by the pure
bounded helper: ELF64 little-endian x86_64, PT_INTERP, DT_NEEDED, SONAME, RPATH
and RUNPATH. It runs no `ldd`, `readelf`, loader, native helper or external
binary. Truncation, overflow, ambiguous file-backed mappings and unsupported
loader-extension tags fail closed.

Dependency observations match only compatible selected files actually mapped
with matching inode/device identity. Duplicate compatible mappings are
AMBIGUOUS; missing mappings are UNRESOLVED. Separately allowlisted selected
loader-directory candidates remain candidates. This is no loader trace,
RPATH/RUNPATH emulation, cache/default search-order proof, transitive closure
certificate or peak-memory measurement. RUNPATH remains direct-dependency
metadata. The result never issues ScientificFreeze, a scientific runtime
certificate, a codec case-law certificate or a CAS certificate.

All fixed ceilings can only be lowered: 2,048 selected files, 64 MiB per file,
512 MiB explicit read bytes, 1 MiB per maps snapshot, 4,096 module origins,
4 MiB result bytes, 1,024 ELF program headers, 4,096 dynamic entries, 512
extracted strings and 64 KiB aggregate extracted string bytes. Admission
reserves two complete file passes and two maximum maps snapshots plus actual
CLI input bytes. The read ledger charges contract/plan/witness bytes, selected
file-content reads and proc maps reads. Retained artifacts have a separate
parent cap. Implicit Python loader, kernel, metadata-stat and provider IO are
outside this explicit application-content accounting scope.

A completed observation returns `OBSERVED_METADATA_ONLY`, with inner
`PENDING_MISSING_INPUTS` or `PENDING_FULL_CLOSURE`. `authority` and
`original_materialization_plan_authority` preserve the original sixteen false
flags with their explicit original-plan scope. A separate
`engineering_capture_authorized` field describes only the fresh external
metadata gate; it grants no scientific execution, allocation, native8 slot,
archive acquisition, source-session reuse or qualification.

The current synthetic checks pass: **23 collector tests and 17 pure ELF tests**.
They exercise pin/schema/target substitutions, absent and public authority,
detached witness linkage, missing runtime packages and version mismatches,
no actual native import, isolated execution of the pinned helper, before/after
file and path drift, symlink/hardlink/directory/FIFO refusal, ancestor symlinks,
zero-length regular metadata and empty-byte hashes, read/result caps, map
overflow, ambiguous and unresolved dependencies, static
RECORD nontraversal, and bounded ELF truncation/overflow/string/dynamic laws.
All fixtures are tiny and disjoint from scientific cases and closed controls.

The first collector run exposed acceptance of a 65-bit exclusive map end
address; its exact source/test snapshot and failing log are preserved. The
second collector failure exposed an overstrict positive file-size law that
excluded legitimate zero-length stdlib metadata files. The corrected law accepts
nonnegative exact integer sizes and the empty-byte SHA256, while resource caps
and CLI payload sizes remain positive. Its failing source/test/log are retained.
The first ELF run found a fixture NUL-index error; its failing fixture and source
snapshot remain preserved. These are development failures, not live attempts.
No wheel download/install, archive request, HDF5 dataset, spectrum, holdout,
scientific RNG draw, live service call or workflow activation occurred here.
