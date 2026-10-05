Independent source and retained-evidence review of E preparation, 5 October 2026.

No material blocker was found in the reviewed raw RECORD collector repair and metadata-only preflight. This is a read-only preparation review, not a successful native capture or an activation. The reviewer read source, inputs and retained results; did not run additional tests, execute a collector, import scientific packages, launch the installed interpreter, or change frozen C/D artifacts.

The reviewed collector is `runtime-metadata-repair-E/collect_runtime_identity.py`, 39,445 bytes, SHA-256 **`f4eabe78bd7e609572eeb64fee82770824dc61e462360d06860ca00978e03596`**. The final retained metadata-only preflight JSON SHA-256 is **`d919ef5d0d4bf669fef0ba591e68170828a2ccf5406f4076f7a0f91e0ce66bb0`**. Both hashes were independently checked against current retained files. Any execution copy must preserve the collector's exact bytes and be independently pinned/read back in the new E freeze.

The repair obtains the complete raw RECORD body for each of exactly three cohort distributions. It binds the exact `.dist-info/RECORD` path, concrete `PathDistribution._path` owner, version, body size, whole-file SHA-256 and mode. Inventory no longer obtains its authoritative rows from the presence-filtered `Distribution.files` property. Every raw row is retained, including the two declared NumPy script paths that caused D to refuse.

Parsing is finite and strict: each RECORD body is capped at 1 MiB, rows at 12,000, path bytes at 4,096 and declared member size at 128 MiB, inside the collector's 512 MiB explicit-read ceiling. Strict UTF-8/CSV parsing rejects malformed three-field rows, duplicate or noncanonical paths, unsafe traversal, noncanonical URL-safe SHA-256, noncanonical decimal sizes, and missing/invalid self rows. Ordinary missing files fail closed. Only the two exact frozen NumPy 2.3.5 script relocations are permitted; both must be used and their actual bytes/modes and RECORD expectations must match. There is no generic path fallback.

The separately reported stdlib presence projection retains raw CSV row order and explicitly remains incomplete inventory. A reversed-row inert regression checks that ordering against a real `PathDistribution.files`. Raw RECORD source witnesses are included in before/after comparison.

| Cohort | Complete raw rows | Stdlib presence-filtered rows | Verified script relocations |
| --- | ---: | ---: | ---: |
| NumPy 2.3.5 | 904 | 902 | 2 |
| h5py 3.16.0 | 106 | 106 | 0 |
| hdf5plugin 7.1.0 | 26 | 26 | 0 |

The final retained offline log reports **37 tests passed**: eight ELF mapping tests, thirteen injected collector regressions and sixteen raw RECORD/layout tests. Relevant checks cover realistic stdlib omission, raw ordering, a `.files` property that must never be consulted, missing ordinary rows, duplicate/alias paths, malformed CSV/hash/size, changed RECORD bodies, wrong owner/body/mode, finite bounds and exact relocation refusals. The reviewer did not rerun them.

The final preflight receipt is `METADATA_LAYOUT_PREFLIGHT_PASSED_ONLY` and matches the reviewed collector hash. It enforces current base Python with `-I -B -S`, a base prefix distinct from any installed venv, and the exact 30,894,944-byte interpreter SHA-256 `fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7`. The locator input is bounded before JSON parsing. Its explicit accounting is:

| Explicit preflight reads | Bytes |
| --- | ---: |
| Interpreter and collector source | 30,934,389 |
| RECORD/control inputs and relocated scripts | 100,835 |
| Total | **31,035,224** |
| Explicit-read ceiling | **67,108,864 (64 MiB)** |

The selected call elapsed **0.1743317510045017 seconds** (approximately 0.1743 seconds), under its 60-second wall bound and 512 MiB address-space ceiling. The receipt candidly excludes implicit stdlib projection/version metadata reads from explicit reader accounting; it does not claim complete process IO.

The preflight imports the collector under an inert module name, never invokes its CLI/main or `collect()` path, constructs stdlib metadata distributions, and injects a native reader that only stats package files. No scientific package native bytes, ELF interpretation or HDF5 filter observation is supplied by that override. Source flow contains no installed-interpreter launch or scientific-package import, and the retained receipt records final absence of all three cohort modules. Reading the base interpreter bytes for its hash is explicitly charged separately; it is not a scientific package import. The real collector's default native reader and guarded capture remain separate future work.

The current E gate includes **both `record_inputs_path` and `record_relocations_path` in mandatory source-pin requirements**, and supplies **both `--record-inputs` and `--record-relocations`** to the collector. Freeze/publication must bind those exact sidecars, the execution copy of the reviewed collector, all reused drivers and selected runtime inputs. E must use its own identity, empty output root, immutable publication/readback, finite reservation and irrevocable one-shot activation. C and D remain closed.

This review grants no runtime, loader, native custody, CAS, transport, source-session or scientific qualification, no spectral access, no certificate and no scientific execution permission. All eleven scientific admission fields remain pending. A layout preflight cannot predict successful native imports or supply complete native IO/loader custody.
