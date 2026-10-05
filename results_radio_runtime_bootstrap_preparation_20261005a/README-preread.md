# Bounded static installer prerequisite snapshot — 5 October 2026

The single original invocation of `prepare_installer_preread.py` completed with exit 0. It read and checked the unchanged 765-file runtime cohort from capture B and preserved the current installer source basis. This is a static prerequisite snapshot. It did not import pip, run an installer, inspect ELF structures, access wheels or a package index, import NumPy/HDF5, open telescope data, activate a scope or reserve a new live allocation. All 11 scientific qualification fields remain pending.

## Invocation and immutable outputs

```text
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 -I -B -S results_radio_runtime_bootstrap_preparation_20261005a/prepare_installer_preread.py
```

The complete stdout and stderr are retained together in `logs/installer-preread-01.log`. The reader creates its manifest and installer basis exclusively. Existing output names cause a closed failure rather than replacement or replay. No second original preread was invoked.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `prepare_installer_preread.py` | 21,745 | `35bd21189038ca9f05b7d4786ee4eba545b37ff4329207eb38e2f9617388de04` |
| `installer-preread.json` | 1,275,913 | `3e154b784424c215867b9d3a091e3e92ed8c1229a3b1ba7f838074c6e36bb1dc` |
| `logs/installer-preread-01.log` | 720 | `d1cba65af101dde4d6a1a4869650d8b409511571b8b86cdc54a7b4d980e6c7c3` |

The manifest Git blob is `da7a232510cd26fa716eca42de891aad79b76b7c`. The reader and manifest are frozen after this invocation; explanatory documentation is outside their source identity.

## Exact runtime and source basis

| Explicit selected content | Files | Raw bytes |
| --- | ---: | ---: |
| Unchanged capture-B runtime cohort | 765 | 53,792,770 |
| Pip source/data and its sole matching dist-info directory | 479 | 5,690,699 |
| Two comparison inputs | 2 | 448,001 |
| Total explicit regular content returned | 1,246 | 59,931,470 |

All 765 current runtime rows match the retained path, raw length, SHA-256, Git mode and filesystem mode. The source input pins are the original materialization plan (`fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25`) and capture-B prerequisite manifest (`b5fe9e7b6cba36d726ecfe4c9bcd3d7bd5ff884cd1a3f6ecd7cb999005d27cac`). The JSON output includes the full 765 current runtime rows and their newly observed source identities; their native bytes were hashed without parsing or importing them.

The sole installer directory was `pip-26.2.1.dist-info`. Version `26.2.1` was obtained statically from its raw `METADATA` and checked against the single top-level `__version__` string assignment in the AST of the already-read `pip/__init__.py`. Pip was not imported, executed or queried for its version.

The basis comprises all selected sole-link regular files below the current `pip` directory and that one dist-info directory. The reader rejected symlinks, hard-linked selected regular files and special entries, held source ancestor descriptors with no-follow opens, compared each file's descriptor/name identity before and after the full read, and rechecked all 144 held source ancestors at the end. The identities include device, inode, mode, length, link count, mtime and ctime. This records the selected namespace and read interval; it does not establish a provider-wide immutability certificate.

## Lossless publication and future seed mapping

The repository basis stores 473 files as their exact original UTF-8 bytes and six non-UTF-8 Windows launcher resources as canonical base64 plus one newline. Those six resources were read and preserved as data; they were not executed. Total stored representation size is 5,940,913 bytes.

Each installer row records:

- The absolute original `path`, raw `bytes`, `sha256`, `mode`, `git_blob` and `source_identity`.
- The seed destination in both `relative_path` and `seed_relative_path`.
- The stored file in both `repository_artifact_path` and `repository_path`.
- Its `stored_encoding`, stored/repository byte length, SHA-256 and Git blob, plus stored Git mode.

Raw source Git blobs and base64 representation Git blobs are deliberately separate. For `stored_encoding=base64`, full repository readback must validate the representation pins, decode strictly, and then validate the decoded raw length, SHA-256 and Git blob against the source pins. For `stored_encoding=utf8`, the stored bytes are the source bytes. The mapping retains every original seed path, including dist-info data; no selected installer file is omitted.

Forty-five ambient bytecode entries were excluded. `__pycache__` directories were not descended into; `.pyc` entries were neither read nor copied. A future reviewed bootstrap must use its own newly created and fully verified source seed under `-I -B -S`; these source pins do not claim that ambient bytecode was used or validated. Gate seed pins can be constructed from exactly `path`, `bytes`, `sha256`, `mode`, plus `relative_path`; publication representation pins are separate caller evidence.

## Bounded read and timing scope

The ceilings were 128 MiB explicit regular content, 64 MiB per selected file, 2,048 regular files, 16,384 enumerated entries, 4,096 entries per directory, 1,024 held directories, depth 32, 60 post-bootstrap seconds and a 4 MiB manifest. The observed totals were 59,931,470 regular bytes, 1,246 files, 776 enumerated entries and 144 held source directories. All 1,246 one-byte EOF probes returned zero bytes.

The recorded post-import interval through final source verification was 0.17271243300638162 seconds. It includes comparison input reads, runtime and installer reads, enumeration, source copying, static parsing and final source verification. It excludes implicit CPython and standard-library bootstrap, manifest serialization/write, final CLI printing and provider elapsed time. Explicit read accounting likewise excludes implicit bootstrap and kernel/provider reads. The manifest is written exclusively and fsynced, and the caller retained the full received log.

The later `logs/installer-preread-copy-verification-01.log` checks only the stored manifest and all 479 repository copies, including strict base64 decoding and raw/stored Git-blob equality. It reads no original runtime or installed pip input, imports no package and performs no installer or bootstrap invocation. Its administrative artifact reads are separate from the original prerequisite reader's accounting.

This basis still requires complete publication readback, a reviewed separate bootstrap contract and a distinct activation before any actual installation can occur. Existing capture A/B evidence and all telescope, holdout and reservation states remain unchanged.
