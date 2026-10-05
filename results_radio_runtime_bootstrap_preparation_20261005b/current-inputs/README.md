# Current static inputs for a prospective bootstrap B

This is read-only preparation metadata. No socket or SSL context was created,
no package was installed or imported, no telescope data was read, and no old
spent allocation or scientific gate was changed.

`current-input-metadata.json` records exact current primary Python/source/trust
pins, helper paths, static ELF metadata, and comparisons to the retained input
cohorts. Its SHA-256 is
`635ecf69feb297bd281f7ac00711bf21ec917c733695e9a2f02f27d4b1ef18d0`.

The declared old runtime cohort is still exactly 765 files / 53,792,770 bytes,
with zero changed declared rows. The declared old installer source cohort is
still 479 files / 5,690,699 bytes, with zero changed declared rows (pip 26.2.1).
These cohorts were compared, not re-enumerated, so this is not a claim of a
complete dependency closure or observed native custody.

## Minimal concrete transport inputs

- Canonical primary interpreter:
  `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12`
  (30,894,944 bytes; SHA-256
  `fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7`).
  Current primary bundle is 26.927.11222, Python 3.12.14.
- Python-level native binding support: `ssl.py`, `socket.py`, `selectors.py`,
  and `_sysconfigdata__linux_x86_64-linux-gnu.py` beneath that interpreter's
  `lib/python3.12`. Exact pins are in the report. `_ssl`, `_socket`, `select`,
  `_hashlib` and `zlib` are built-in modules here; there are no separate `_ssl`
  or `_socket` shared objects to pin in `lib-dynload`.
- Static Python ELF metadata has PT_INTERP `/lib64/ld-linux-x86-64.so.2`,
  DT_NEEDED `libpthread.so.0`, `libdl.so.2`, `libutil.so.1`, `libm.so.6`,
  `librt.so.1`, `libc.so.6`, and RPATH `$ORIGIN/../lib`. Actual loader
  resolution is not established by these strings. The retained loader cohort
  and its hashes are listed in the report.
- Explicit platform trust path:
  `/usr/local/share/ca-certificates/nebula-dns.crt` (1,310 bytes;
  SHA-256 `ab6933a81e6f0d142e6d5f58ed465589d899a523c2752055761af11d4ee38f2b`).
  `PIP_CERT` and `SSL_CERT_FILE` point here. Byte provenance is observed as a
  path/hash only; origin or actual TLS verification has not been certified.
- Published adapter source directory:
  `/workspace/scratch/66170938f826/setisearch/results_radio_proxy_transport_integration_20261005a`.
  Actual B must explicitly freeze `proxy_opener.py`, `proxy_contract.py`,
  `native_bindings.py`, unchanged `wheel_io.py`, and `original-plan.json`.
  Their current exact source hashes are in the report. The original plan anchor
  remains `fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25`.

## Usable predecessor functions

In
`/workspace/scratch/a5b2addacbd5/setisearch-20261005/results_radio_runtime_bootstrap_preparation_20261005a/prepare_installer_preread.py`:
`Guard.directory/verify/provenance`, `read_regular`, `selected_pip_paths`,
`static_version`, `seed_copy`, and `write_manifest` are static source snapshot
building blocks. Full `main()` hardcodes A output paths, runtime digest, and
the exact old cohort, and refuses already existing output paths. Do not invoke
it as a B preparation. Copy/adapt the functions into a distinct, independently
pinned B preparation with fresh output destinations and appropriately reset
bounded STATE/START values.

In the adjacent `build_contracts.py`, `canonical`, `pinned_json`, `pin`,
`source_identity`, `row_list`, `checked_limits`, and `wheels_from_plan` are useful
pure validation functions. `build_contracts` hardcodes A prerequisite digest,
paths, activation path, and A schema; it cannot accept a new proxy/trust/runtime
contract unchanged. Preserve the original wheel identities and resource law
while making a distinct B builder. Its predecessor source should remain intact.

In
`/workspace/scratch/d804553c0e89/setisearch-status-20261004/results_radio_runtime_capture_preparation_20261004b/prepare_runtime_preread.py`:
`Guard`, `resolve`, `read_regular`, `select_stdlib`, and `entries` provide the
bounded no-follow source/ancestor pinning and explicit alias identity metadata.
`main()` again hardcodes a previous capture identity/output and must not be
re-run as a successor. The adjacent `elf_metadata.py:parse_elf` is pure byte
metadata parsing; it provides no loader execution or runtime resolution proof.

## Proxy lifetime is a concrete unresolved input

Independent static command observations exposed `PIP_PROXY` endpoints
`http://127.0.0.1:37445`, then `:45781`, then `:34337`. The HTTP(S) proxy variables
change with each command; the CA path/hash remained stable. Exporting an older
URL would make a process use that URL, but would not prove that its listener
still exists or belongs to the same proxy service. No cross-command fixed
platform endpoint is established.

One prospective implementation is to keep a single execution process/session
alive, capture its injected exact proxy URL, freeze/publish/read back the
admission while that process remains alive, then perform the one B invocation
in that same session. This removes the observed port replacement between
commands but does not establish listener lifetime, reachability, kernel/TLS IO
custody, or public admission by itself. Those remain requirements for B.

The report's own final file descriptors use no-follow opens and compare name
and descriptor identity; it does not hold all ancestors. A fresh B snapshot
must use the stronger predecessor Guard functions if claiming ancestor custody.
Scientific gates, holdouts, and old spent allocations remain untouched.
