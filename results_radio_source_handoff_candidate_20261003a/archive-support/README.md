# Lossless SETI candidate evidence archive

This support utility preserves the exact bytes of every included regular file,
including failed acquisition and handoff attempts, synthetic H5 fixtures, sparse
mirror byte streams, native and normalized rows, logs, runtime snapshots, receiver
code/tests, and the frozen source snapshot. It makes no claim about a real
telescope acquisition or scientific qualification.

Every original relative path, length, SHA256, and ordinary permission mode is
recorded in `source-manifest.json`. Identical content is stored once under a
SHA256 blob name inside a deterministic USTAR stream compressed with zstd. Files
are restored as independent regular files. Original inodes, sparse allocation,
timestamps, and the lifetime of an original absolute path are not reconstructed.
The original root is recorded for context only.

The prospective default limits are **64 MiB compressed payload**, **1 MiB per
part**, **512 MiB address space**, and **4096 MiB restored logical file bytes**.
The source/part manifests are separate small metadata files. Compression uses one
thread, zstd level 9, a 32 MiB window, and long-distance matching. Reproducibility
is checked with the same source, Python, and zstd versions. Byte equality across
different zstd versions is not asserted.

Run only after all source work has closed and been frozen:

```sh
python archive-support/evidence_archive.py build --root /workspace/scratch/fb4056c33767 --output /workspace/scratch/fb4056c33767/evidence-archive --part-mib 1 --archive-cap-mib 64 --memory-mib 512
```

Verify all compressed parts and all archived blobs, then hash every original
file against the manifest without writing another payload copy:

```sh
python archive-support/evidence_archive.py verify --archive /workspace/scratch/fb4056c33767/evidence-archive --source-root /workspace/scratch/fb4056c33767
```

Restore into a new destination and verify every resulting file:

```sh
python archive-support/evidence_archive.py restore --archive /workspace/scratch/fb4056c33767/evidence-archive --dest /workspace/scratch/fb4056c33767/evidence-restore-check --restore-cap-mib 4096
```

Restore validates every part digest and the concatenated compressed digest before
decompression. It parses one raw USTAR header at a time, accepts ordinary regular
blob members only, rejects links/extensions/traversal/duplicates/missing blobs,
checks exact sizes and digests, and hashes every materialized file. It never
imports, runs, or reexecutes archived code. A failed build or restore removes its
private staging output and leaves its destination absent.

Only known owned top-level directories and visible root files are inventoried;
acquisition, receiver, and handoff observation prefixes are included. Hidden
entries, `__pycache__`, `publication`, `publishing`, and the chosen archive output
are excluded. A new owned directory can be explicitly named with `--include-dir`.
Filesystem links are rejected rather than dereferenced.

`test_evidence_archive.py` uses small isolated temporary fixtures to exercise
deduplication, independent restored copies, deterministic archives, streamed
verification, corruption, changed source, traversal, links, PAX extensions,
duplicate/missing blobs, and compressed cap cleanup. `test-results.json` retains
the real command outputs, including expected rejection tracebacks. The initial
test failure is retained separately: the decoder window argument was initially
given in the wrong unit and was corrected from 65536 to 67108864 bytes.

The first full evidence archive subsequently failed its independent part check:
two real part files were shorter than their intended sizes. The original writer
did not inspect the return value of each file write. Its script version is
retained as `evidence_archive_v1_incomplete_part_write.py`; the incomplete bundle
and actual failure logs are retained separately under `publication`. This is an
archive failure, independent of acquisition and receiver results. The current
writer loops until every byte is written, flushes and fsyncs each part, and
reopens every part to verify its actual length and SHA256 before accepting it.
Restoration and manifest writes use the same complete-write handling.
