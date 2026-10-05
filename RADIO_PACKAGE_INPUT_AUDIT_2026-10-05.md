# Radio package-input audit — 5 October 2026, 15:14 UTC

The independent radio pilot remains **NOT STARTED**. This continuation resolves the current input question through metadata and existing artifact inspection. It performs no new acquisition, installation, h5py/hdf5plugin import, telescope read, activation or experiment. An ancillary inventory process did load an existing VTK HDF5 shared library for symbol-availability inspection; that observation is disclosed below and supplies no scientific runtime qualification.

## Verified continuation source

Current public science checkpoint: `81019826761463da7720d105c0acc7a5f516931e` on `m43-support-qualification`.

Two locally retained inputs were compared with the complete file bodies retrieved at that immutable public commit. Their byte counts and intrinsic Git blob identities agree:

| Retained input | Bytes | SHA-256 | Public Git blob |
|---|---:|---|---|
| `results_radio_runtime_bootstrap_preparation_20261005b/original-plan.json` | 24,739 | `fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25` | `d3aab19fdf575bca46115d084b3e5d549bb04092` |
| `results_radio_runtime_bootstrap_preparation_20261005b/transport-unresolved-inputs.json` | 1,662 | `96ba324c495bf9edbacba1e70cd3cd29db88646753716549935514cb8c7b2b04` | `ec1636d677cdb49eadf341d6dc50afd3cf6bc7e2` |

The local checkout itself is older and contains newer unpublished working-tree copies. Its HEAD is not represented as the current public checkpoint. No historical working tree or spent scope was modified. These two-file checks confer no complete source/runtime/custody qualification.

## Current observed package inputs

Read-only observations at **2026-10-05T15:14:15.412153+00:00**:

- Primary Python: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python`, metadata version **3.12.14**.
- Installed distribution metadata reports NumPy **2.3.5**. It reports no installed `h5py` or `hdf5plugin`. These are metadata observations; neither of those packages was imported.
- `/workspace/scratch/66170938f826/radio-runtime-bootstrap-20261005b/wheelhouse` contains only the original NumPy filename with size **0 bytes**.
- `/workspace/scratch/d804553c0e89/radio-runtime-bootstrap-20261005a/wheelhouse` likewise contains only that NumPy filename with size **0 bytes**.
- The retained B administrative preservation manifest contains one wheel-archive payload: the NumPy file, `raw_bytes=0`, `matches_original=false`. It supplies no complete package archive.
- Filename searches in the available scratch project copies and selected runtime/cache roots found no complete original h5py/hdf5plugin wheels. This is a scoped search, not proof of whole-filesystem absence.

An ancillary runtime inventory process loaded the existing `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages/vtkmodules/libvtkhdf5-9.3.so` through `ctypes.CDLL` solely to inspect exported symbol availability. It performed no explicit HDF5 operation or observations-data read. Ordinary shared-library loader initialization may have run and was not traced. This was not the admitted h5py/HDF5/plugin runtime and is not a substitute for the unchanged package input cohort, a prospective native scope or a runtime certificate. No alternative reader was adopted.

The inventory agent supplied the following already-executed core command and output for preservation. These are its reported tool transcript, not a new execution or a complete custody receipt:

```python
p = pathlib.Path('/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages/vtkmodules/libvtkhdf5-9.3.so')
lib = ctypes.CDLL(str(p))
for symbol in ['H5Fopen', 'H5Dread', 'H5Dopen2', 'H5Zfilter_avail', 'vtkH5Fopen', 'vtkH5Dread']:
    print('symbol', symbol, hasattr(lib, symbol))
```

```text
symbol H5Fopen False
symbol H5Dread False
symbol H5Dopen2 False
symbol H5Zfilter_avail False
symbol vtkH5Fopen False
symbol vtkH5Dread False
```

Only attribute/symbol lookup was attempted; none of those functions was called. Subsequent static symbol listing found VTK-prefixed exports, without calling them. This limited observation gives no approved HDF5 reader, codec proof or scientific authority.

The installed NumPy metadata cannot replace the unchanged exact three-wheel input cohort or authenticate an isolated future installation.

## Current network permission input

The environment supplied to this session permits named platform/storage hosts: `chatgpt.com`, `git.chatgpt-team.site`, `oaisdmntpr*.blob.core.windows.net`, `oaisdmntpr*aws.s3.*.amazonaws.com`, `oaisdsorpr*.blob.core.windows.net` and `sdmntpr*.oaiusercontent.com`. It does not admit `files.pythonhosted.org`, the original package destination. No new CONNECT, TLS, HTTP or pip request was made to that host.

This is **current supplied permission metadata**, not an observed socket capability, proxy lifetime certificate or explanation of the earlier B timeout. The historical timeout cause remains undetermined. The GitHub connector can read the public repository; that does not authenticate package transport to a different host.

One ancillary Git repository read attempt to the permitted mirror host returned `fatal: could not read Username for 'https://git.chatgpt-team.site': No such device or address`. No credential was searched for or supplied, no repository write was attempted through that route, and it is unrelated to package transport. Public source inspection used the existing GitHub connector.

## Exact missing external input

The unchanged package plan requires these **three complete original archives**, totaling **68,409,067 bytes**:

| Package | Archive bytes | Original SHA-256 |
|---|---:|---|
| numpy 2.3.5 | 16,606,086 | `0d8163f43acde9a73c2a33605353a4f1bc4798745a8b1d73183b28e5b435ae28` |
| h5py 3.16.0 | 5,405,250 | `dfc21898ff025f1e8e67e194965a95a8d4754f452f83454538f98f8a3fcb207e` |
| hdf5plugin 7.1.0 | 46,397,731 | `9d4cf36434819fae53e4da432f0287ebaeb02386ab97b73d261092efbab12247` |

- **numpy-2.3.5-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl**
  - Original source: https://files.pythonhosted.org/packages/b6/23/2a1b231b8ff672b4c450dac27164a8b2ca7d9b7144f9c02d2396518352eb/numpy-2.3.5-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl
  - Expected bytes: 16606086
  - SHA-256: `0d8163f43acde9a73c2a33605353a4f1bc4798745a8b1d73183b28e5b435ae28`
- **h5py-3.16.0-cp312-cp312-manylinux_2_28_x86_64.whl**
  - Original source: https://files.pythonhosted.org/packages/9e/e9/1a19e42cd43cc1365e127db6aae85e1c671da1d9a5d746f4d34a50edb577/h5py-3.16.0-cp312-cp312-manylinux_2_28_x86_64.whl
  - Expected bytes: 5405250
  - SHA-256: `dfc21898ff025f1e8e67e194965a95a8d4754f452f83454538f98f8a3fcb207e`
- **hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl**
  - Original source: https://files.pythonhosted.org/packages/26/56/3f788afb8d7fc451d20a66a64ea58bbe189f6f11780b28ba09148974fb33/hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl
  - Expected bytes: 46397731
  - SHA-256: `9d4cf36434819fae53e4da432f0287ebaeb02386ab97b73d261092efbab12247`

The next concrete prerequisite is an authorized, accessible lossless source for these exact bytes, or a permitted transport capability to their original destination. The existing published wheel custody and offline hash-lock interfaces should be reused. Do not substitute installed packages, different versions, rebuilt wheels or synthetic fixtures.

Supplying archives would resolve package availability only. Before any new installation/capture, prepare the separately bounded prospective scope and readback required by the unchanged protocol. Native HDF5/plugin custody, genuine integrated CAS and the original full source/runtime/session/scientific admission inputs would still require qualification. This audit issues none of those certificates.

## Disposition

- A and B remain **CLOSED_FAILED** with their original reservations, markers, artifacts and failure outcomes unchanged.
- No retry, reset, refund, rearm, C successor, fresh native allocation or automatic activation was created.
- All eleven scientific fields remain pending; telescope spectra and original 112+128 holdouts remain unopened; native8 remains unreserved and 127/24 NOT ACTIVATED.
- HD189733/HIP98505 cadence 85030 and primary neighbor9 remain selected. HD1461 remains HOLD; GJ724 remains untouched reserve.
- LS remains paused; CHEOPS remains UNSENT. No person message, paid service, target change or schedule change occurred.
- Consolidation remains **9 October 2026**. If package access is still missing, record the unstarted pilot and concrete missing inputs at consolidation; no automatic deadline extension.

More synthetic transport tests cannot provide the missing original package bytes or network permission. Continue from this input requirement rather than replaying the closed package attempts.
