# Fresh G outer gate contract

`gate.py` is inert on import. `--validate-only` performs the authenticated root
config/proof reads and complete current file/inventory readback without creating
the spent marker, importing the supervisor modules, or dispatching a child.
The root must freeze the exact source before running the effectful command and
must independently impose a 120-second external parent wall deadline with exact
direct-parent wait4/cleanup accounting. The gate's own wall backstop begins after
its Python initialization; its byte ledger explicitly excludes that initial
interpreter/loader activity.

CLI (all paths canonical absolute):

```
python -I -B /.../codec16-G/outer/gate.py \
  --config /.../G_CONFIG.json --config-bytes N --config-sha256 SHA \
  --preread-proof /.../G_PREREAD.json --preread-proof-bytes N --preread-proof-sha256 SHA
```

The same CLI with `--validate-only` is read-only. The normal CLI admits one child
only after complete independent pre-readback and exact dispatch admission, then
atomically creates the external exclusive marker. The marker is never removed or
reused after a later failure. The config/proof are authenticated by externally
supplied CLI hashes and do not occur in their own manifest; no cyclic selfhash is
required. Root pre-readback and gate pre/post snapshots describe complete reads
at those times, not continuous runtime-loader custody.

The exact config keys are `schema`, `scope_id`, `roles`, `pinned_files`,
`inventory_roots`, `runtime_prefix`, `cwd`, `artifacts`, `environment`, `budgets`.
The schema is `radio-codec16-outer-gate-G-v1`. The scope ID is
`codec16-control-20261006g`; directory/project identity may be
`radio-codec16-control-20261006g`. `gate.py` exports the exact accepted `BUDGETS`
mapping so the root can copy that mapping rather than transcribing it.

`pinned_files` is sorted by path and contains exact fields `path`, `sha256`,
`bytes`, `mode`, `device`, `inode`, `mtime_ns`, `ctime_ns`. `mode` is full
`st_mode`, including the regular-file type. All paths are canonical regular files;
original modes are retained and checked exactly, without introducing a new
nonwritable-mode requirement. `pin_record(path)` is a metadata-only root helper;
the root must independently read each full file and add its SHA256 after confirming
stable held-file and pathname identity. Empty pinned source logs are supported.

`roles` has these exact distinct independently pinned paths:

| Role | Content |
|---|---|
| `scope` | Root-authored frozen outer scope JSON |
| `dispatch` | Root-authored fresh engineering dispatch JSON |
| `leaf_manifest` | `leaf/LEAF_FILES.json` |
| `leaf_script` | `leaf/run_codec16.py` |
| `plan` | Retained unchanged `PLAN.json` |
| `input_manifest` | Retained unchanged `INPUT_MANIFEST.json` |
| `selection` | Retained unchanged `SELECTED_CODE.json` |
| `python` | Original canonical regular C-prefix `bin/python` |
| `guard` | Copied byte-identical F `leaf_guard` |
| `exec_seal` | Copied byte-identical F `exec_seal.so` |
| `phase2` | Copied byte-identical F `phase2_bootstrap.py` |
| `proc_custody` | Copied byte-identical F `proc_custody.py` |
| `leaf_supervisor` | Copied byte-identical F `leaf_supervisor.py` |

`inventory_roots` is a sorted list of canonical existing nonoverlapping directories.
Each is fully walked before and after each complete hash snapshot, and its entire
regular-file set must equal the pin paths underneath it. Symlinks/special entries
are refused. Use exact runtime/leaf/supervisor source inventories, while individually
pinning other immutable files (including the gate itself and native dependencies).
Keep mutable config/proof/output/marker paths outside these inventories.

`artifacts` has exact keys `root`, `leaf_output`, `output_prefix`, `outer_report`,
`spent_marker`. The root must be a newly created empty directory. Leaf output,
prefix, and outer report must be distinct direct-child paths in it; the leaf output
directory must not exist (the controlled producer creates it). The spent marker
must be a distinct absent path outside the artifact/inventory roots, in an existing
parent. Its allocated/logical bytes are counted within the outer 8MiB and total
192MiB ledger even though the marker is stored externally. All artifact directories,
including the root directory, are included in storage snapshots.

`environment` is an explicit string mapping, not inherited. It requires
`PYTHONDONTWRITEBYTECODE=1`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`,
`MKL_NUM_THREADS=1`, and `NUMEXPR_NUM_THREADS=1`. Other root-approved environment
entries can be included in the frozen mapping.

The proof has these exact fields and values:

```json
{
  "schema": "radio-codec16-preread-G-v1",
  "config_sha256": "SHA256 of exact config bytes",
  "scope_id": "codec16-control-20261006g",
  "pinned_files_sha256": "SHA256(canonical(config.pinned_files))",
  "all_reads_complete": true,
  "readback": ["the exact full pinned_files list"],
  "read_bytes": "integer sum of every pin.bytes"
}
```

`canonical(value)` is exported: UTF8 JSON with sorted keys and separators `,`/`:`
plus exactly one trailing newline. Proof currentness is also independently checked
by the gate reading the entire manifest itself before consuming the marker.

The separate dispatch schema is unchanged from the retained producer. It binds
exact pinned plan/input/selection hashes, frozen runtime prefix, scope ID and SHA
of root-authored `scope`. It is separate from the unchanged draft plan's
`execution_enabled:false` preparation history. The gate executes retained exact F
module source bytes and passes internally derived isolated leaf argv to `run_leaf`.

Fixed envelope: parent 120 seconds (110 active plus 10 final) and separate 2GiB
explicit reads; one child 90 wall seconds/80 CPU seconds/512MiB address space with
512MiB opaque read reservation; 192MiB artifact cap (184MiB leaf plus 8MiB outer).
F pin and proc reads have explicit 32MiB/16MiB sub-budgets and are added to the
parent ledger, as are actual received stdout/stderr bytes. F does not expose the
exact guard-status read length, so a labelled 4096-byte guard-read reservation is
added. Sampling is frozen at 0.5 seconds so retained raw custody plus two 1MiB
streams fits the small outer allocation more reliably. Custody is stored once;
the outer report includes an independently reread custody hash and compact summary.

Successful output means only `CONTROLLED_CODEC16_PARTIAL_HANDOFF_OBSERVED`:
sixteen deterministic source-shaped rows and one engineering partial handoff out
of twelve required complete handoffs. Exact raw F custody, full post file readback,
receipt dispatch/scope/runtime/row/handoff checks and HDF5 output rehashes are
required. Telescope provenance, archive spectral data, full native graph, complete
native I/O custody, complete codec certification and science remain unqualified.

Pure test command: `python -I -B codec16-G/outer/test_gate.py`. The tests do not
call `run_leaf`, the producer, subprocess, or scientific/native imports.
