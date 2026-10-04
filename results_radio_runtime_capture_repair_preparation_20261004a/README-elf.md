# Inert ELF mapping and selected-file failure-context repair — 4 October 2026

This new preparation namespace changes prospective source only. It does not
modify, replay, reinterpret or rearm the closed capture identity, original
0700 output root, original sources, marker or evidence. The engineering subtotal
remains970seconds/48MiB. All eleven authentic scientific fields remain pending;
no scientific dataset, native package import, RNG, acquisition, trial or new
live allocation occurred here.

## Supported mapping change and its evidence

The original parser demanded that an entire dynamic string table fit in one
PT_LOAD segment. A separate root-controlled read-only preread of the exact
externally pinned Python binary found a current table at virtual4191704,
length42266. Its file-backed intersections are:

| Program-header index | Virtual interval | File interval |
|---|---|---|
| 2 | 4191704..4194304 | 1496..4096 |
| 4 | 4194304..4233970 | 4096..43762 |

These two disjoint adjacent segments have the same virtual-to-file translation.
No single segment contains the entire range. See the separately retained
`python-elf-diagnostic.json` and its script/log for scope, hashes, original table
regions and limitations. That diagnostic identifies current geometry; it does
not identify the original unnamed failing ELF input or certify runtime custody.
This agent read the retained diagnostic, not the target binary.

The official generic ELF ABI describes p_offset/p_vaddr as the segment starts
and p_filesz as initialized file bytes; bytes after p_filesz up to p_memsz are
zero-filled. DT_STRTAB gives a table address and DT_STRSZ its byte size.
Sources read4October2026:

- https://gabi.xinuos.com/elf/07-pheader.html, sections7.1–7.2.
- https://gabi.xinuos.com/elf/08-dynamic.html, section8.3.

**Our bounded parser inference** is that several adjacent file-backed load
segments may jointly supply a uniquely mapped requested range when their file
translation is identical. The repair accepts precisely that case, without
page-map, relocation, loader, search-order or dependency-resolution emulation.
The parser still rejects disjoint virtual gaps, BSS coverage, changed file
translations, overlapping/unordered loads, unsigned overflow, file truncation,
unsupported headers/loader tags and all pre-existing hard limits. PT_DYNAMIC
also uses the same complete-coverage law and still must match its file offset.
The success field `dynamic_string_table_mapping` reports the contributing
PT_LOAD-list indices (not original program-header indices), file/virtual range
and continuous translation; it grants no execution or scientific authority.

## Bounded error receipts

A parser rejection now carries a structured error context with input length,
SHA256 for bytes within the fixed64MiB input ceiling, parser subset, stage and
requested table address/size/end when known. Overflow has a null end rather
than a wrapped address. At most16 load-candidate records are retained; total
candidate counts, reason counts and the truncation flag remain explicit.
Header-level failures have unknown table fields and empty candidate records.
The parser never opens a file or dispatches a program.

The prospective collector catches a selected ELF rejection and binds it to the
already hash-checked selected path, bytes and SHA256, actual selected ELF helper
source SHA256/length, collector source SHA256, parser exception/reason and
bounded helper context. An injected fixture parser is explicitly marked
synthetic and has no adopted parser source pin. Malformed, deep, overlong or
oversized helper context is dropped as unavailable. Structural validation is
bounded to512 nodes, depth5,16-element arrays and24576 encoded context bytes;
the complete error record is bounded to65536 encoded bytes. Unknown fields in
an exception object are not dumped.

The CLI exits1, writes one normal CLOSED_FAILED line followed by one
ELF_ERROR_CONTEXT JSON line to stderr, and produces no stdout observation.
The error receipt says observation_adopted:false and retains all sixteen
original authority flags false. It never turns partial metadata or a rejected
input into a certificate. Selected application reads are unchanged: error
hashing and parsing use already retained bytes, and perform no additional file
read.

## Verification and preserved failures

Final isolated primary-Python runs passed **26 ELF plus26 collector tests**:
`final-elf-primary-tests-04.log` and `final-collector-tests-03.log`.
All original17 ELF and23 collector checks remain. Added regressions exercise
adjacent same-translation ranges, the separately observed numeric table geometry
as synthetic bytes, virtual/file gaps, BSS, contextual overflow/truncation,
40-candidate truncation, selected source/file binding, stderr-only CLI failure
and malicious fixture exception bounds. Fixtures inspect no host runtime.

The before-fix regression failed as expected:25 ELF tests with five errors and
26 collector tests with three errors. `failed-elf-regression-01/` retains the
exact source/test cohort, and both `*-regression-before-fix-01.log` files retain
full output. Baseline original four sources are separately copied unchanged in
`baseline-elf-source/`. Development logs after the first implementation and the
final system-Python ELF run are also retained; no failure is overwritten.

A future genuine capture still needs a distinct fully published frozen contract,
full immutable readback, authenticated procfs law, marker and fresh irreversible
allocation. This repair preparation creates none of those and does not waive
HDF5/plugin/filter, genuine CAS, full127/24 or original scientific inputs.
Consolidation remains9October2026.
