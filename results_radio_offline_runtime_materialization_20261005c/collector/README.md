# Prospective runtime identity input collector

This directory contains prepared code. It authorizes no installation, invocation,
radioanalysis, admission, or spent-scope successor. Root's separate prospective
activation, guard, supervisor, source pins and readback must govern any real run.

`collect_runtime_identity.py` imports only the Python standard library at module
load. Real NumPy, h5py and hdf5plugin imports occur only inside its explicitly
activated CLI. They have not been performed during this preparation.

## Proposed guarded invocation

After separate authorization, installation and validation of the isolated venv,
root can invoke its own supervisor with the following child arguments:

```text
<newvenv>/bin/python -I -B <collector>/collect_runtime_identity.py
  --activate-native-metadata
  --venv-root <newvenv>
  --filter-input <collector>/filter-input.json
  --output <fresh-prospective-output-path>
```

The command here is a description, not an executed or self-authorizing action.
The child must have a clean environment, with OPENBLAS_NUM_THREADS,
OMP_NUM_THREADS and MKL_NUM_THREADS all `1`. HDF5_PLUGIN_PRELOAD must be `::` to
disable automatic HDF5 plugin discovery during availability probes. Root may set
HDF5_PLUGIN_PATH empty or to exactly the new venv's
`lib/python3.12/site-packages/hdf5plugin/plugins`. Dynamic loader and Python search
path override variables must be absent/empty. The single-process seccomp guard,
wall/CPU/RSS limits and full implicit import/loader-read reservation are external
supervisor responsibilities. No `-S` should be used: the isolated venv's own site
directory supplies the newly installed exact cohort.

## Collected inputs and scope

The child reports exact cohort versions NumPy 2.3.5, h5py 3.16.0 and hdf5plugin
7.1.0, runtime/build HDF5 2.0.0, expected venv/module/site roots, before/after
distribution RECORD inventories and native library identities. Three bounded
`/proc/self/maps` snapshots retain raw bytes, parsed mappings, and complete
SHA-256/size/stat identities of sampled mapped files. Native ELF headers and
PT_DYNAMIC DT_NEEDED, SONAME, RPATH and RUNPATH strings are parsed by standard
library code; no native tool, compiler, subprocess or loader probe is used.

Availability and flags for all twelve source-derived plugin filter IDs are
observed before/after hdf5plugin import using only explicit
`h5py.h5z.filter_avail` and `h5py.h5z.get_filter_info` calls. The later observation
must report bitshuffle 32008 available with decoding enabled. The source-derived
filter list is checked against the actually imported plugin's FILTERS mapping.
No `h5py.File`, datasets, telescope sources, RNG or codec compression/decompression
operation is called by collector code. **Package imports do perform their own
native initialization.** h5py initializes HDF5 and reads its version;
hdf5plugin `_utils.py` ends with `register(force=False)` and can register native
filters during import. Those implicit effects are within the future child scope,
not absent or misclassified as mere attribute inspection.

Explicit metadata/native-file reads are bounded to 512 MiB; the canonical JSON
output is bounded to 8 MiB and is created exclusively without overwriting a named
file. Repeated full-file hashes can reuse a cached measurement only after an
unchanged named stat identity check; each reuse is labeled. The collector does
not count or qualify import/loader implicit reads. The parent must conservatively
reserve/monitor those separately.

All qualification/authority flags remain false. A successful output is
`COLLECTED_IDENTITY_INPUTS_ONLY`; it supplies inputs for root's engineering
observation, not full scientific runtime admission. Maps snapshots cannot prove
complete native load history. Named file hashes cannot certify all executed
native code, ancestor namespace closure, source-code closure or memory content.
RECORD hashes of nonnative distribution files are declared expectations, not
verified full byte hashes. No synthetic pass is evidence of native-runtime
correctness or signal-search behavior.

## Preparation verification

`test_collect_runtime_identity.py` runs entirely offline with standard-library
metadata/ELF fixtures and fake package/HDF5 interfaces. Its 13 tests verify ELF
string extraction in both classes and byte orders, malformed-input refusal,
bounded reads, honest hash reuse, non-ELF mapped objects, deleted mapping refusal,
filter registration observations, mismatched version/filter refusal and absence
of scientific data/RNG entrypoints. No real scientific package was imported.

Run already performed during preparation:

```text
python -I -B test_collect_runtime_identity.py
Ran 13 tests ... OK
```

`offline-test-first-failure.txt` preserves the earlier defective metadata-fixture
test and its correction. `offline-tests.log` retains the successful result.
`source-api-evidence/` retains exact inspected Python members from the pinned
plugin/h5py wheels. `source-api-manifest.json` records their byte identities;
`filter-input.json` carries the source-derived filter constants and plugin raw
member pins. No wheel member was executed, imported, compiled, or linked during
that static API inspection.
