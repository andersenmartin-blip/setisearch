The closed 20261005c operation installed and verified the three original packages, then stopped during the collector's initial ELF metadata snapshot. This directory preserves that failure and proposes a parser correction. It does not reopen or repeat the operation.

The first reproducible offending file is the pinned interpreter:

- Path: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12`
- Bytes: 30,894,944
- SHA-256: `fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7`
- DT_STRTAB virtual address: 4,191,704 (`0x3ff5d8`)
- DT_STRSZ: 42,266
- PT_LOAD 0: virtual 4,190,208; file offset 0; file-backed size 4,096.
- PT_LOAD 1: virtual 4,194,304; file offset 4,096; file-backed size 134,512.

The dynamic string table crosses these adjacent segments. Both translate virtual addresses to the same consecutive file offsets. The original collector required the entire table to lie inside exactly one PT_LOAD, so it rejected this file despite complete, unique file-byte coverage.

`elf_string_mapping.py` partitions the requested virtual interval at every file-backed segment boundary. Each partition must have one unique file-offset translation. Adjacent mappings and overlapping headers with identical translations are accepted; gaps, zero-filled tails without file backing, conflicting offsets (even when bytes coincide), oversized intervals and out-of-file spans are refused. The prospective collector also rejects file sizes greater than memory sizes and virtual extents exceeding the ELF address width.

`collect_runtime_identity_repaired.py` is a separate copy with this small correction embedded. `parser-repair.diff` gives the exact change. Original source, tests, freeze, result and closed stderr/custody are preserved with hashes in `original-copy-pins.json`. No frozen preparation source was changed.

Eight pure synthetic ELF tests passed, covering ELF32/ELF64 and both byte orders, contiguous and noncontiguous file spans, equivalent and conflicting overlaps, gaps/zero fill, invalid load extents, bounds and unterminated strings/tables. An independent read-only review found no substantive defect.

A separate read-only check of the whole pinned interpreter bytes succeeded with the repaired parser: six DT_NEEDED entries and RPATH `$ORIGIN/../lib` were recovered. Diagnosis and validation selected calls each had a 60-second wall alarm and 512 MiB address-space cap. Their recorded explicit native/source evidence reads total 62,802,037 bytes, below the separate 512 MiB read ceiling. `diagnosis.json` and `repaired-static-validation.json` retain the observations and limits. These checks read ELF bytes only; they did not launch the installed interpreter or import scientific packages.

Any future metadata capture needs a distinct identity, fresh output, complete frozen/read-back source and input pins, one separately reserved guarded child, and new one-shot activation. It may reuse the byte-verified installed files after rechecking their complete inventory. Installation need not be repeated. The old operation remains closed, and no new activation or native metadata capture is authorized by these artifacts. The repair grants no native, loader, transport, source or scientific qualification.

The original 13 injected collector tests also passed against the repaired collector (0.009 seconds), separately from the eight new mapping tests. `test_original_collector_regression.py` is the retained original test source with only its collector filename changed; `original-collector-regression.log` preserves the full result. These fake-interface regressions performed no scientific imports.
