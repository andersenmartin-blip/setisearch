# Independent final static review — 8 October 2026

**PASS for prospective DEV-only execution; pilot admission remains closed.**
No control realization, RNG call, detector invocation or pilot payload was
executed by this reviewer. Python code was read/AST-parsed; JSON identities,
file hashes and metadata arithmetic were checked independently.

Science contract/config, detector, generator and summarizer now agree on:

- Same six historical time/frequency metadata templates; signed Hz spacing,
  real gaps and one whole-cadence midpoint epoch. All 4096 native ON carriers,
  5415 drifts, 1871-channel halo and 7838 loaded channels are retained.
- 501-channel running median, 5 MAD winsorized location, robust box widths
  1/3/9/33, ON>=10 and OFF>=8, with no calibrated-significance claim.
- Complete ORIGINAL-source channel rounding with rint/ties-even before
  subtracting the odd loaded-source offset. The generator's noise-free box
  oracle now uses the same rint convention. The initial mismatch was corrected
  before any DEV value was generated.
- Coupled first/last originating-ON endpoint bounds for every compatible OFF
  global hypothesis, not merely the OFF winning drift. Witness selection,
  actual checked count and early-stop/exhaustion state are explicit.
- Correctly localized final recovery in EVERY injected active ON scan;
  preliminary ON and any-active recovery also retained. Matched-RFI admission
  additionally requires all 24 cadences' primary ON trajectories to be detected
  before OFF rejection; no initial hit cannot count as successful rejection.
- All 308 case IDs and full SHA256 seed digests are unique and pairwise disjoint:
  DEV 24, VAL_A 142, VAL_B 142. Exact family counts match the prospective contract.
  The full 256-bit seed description and actual generator path are consistent.

Current main controls/pilot are all-valid. The optional mask API rejects
masked score boxes and excludes masked normalization-core estimates, but the
running median still sees those pixels. This review makes no qualified masked
filtering claim; any future masked fixture must be labelled separately or
receive its own propagation rule. No adaptive mask is authorized here.

The DEV runner verifies frozen hashes/public commit receipt/allowed DEV IDs
before RNG, refuses VAL identities and existing output directories, pins the
library versions, preserves all six maximum maps/raw ON hits/recovery outcomes
and partial failures, and records wall/CPU/RSS with watchdog reserves. First
execution should be one admitted full-family case to measure actual cost.
Subsequent jobs must select the remaining distinct identities, rather than
rerun the first case via an unfiltered `--all` invocation.

## Actual source metadata review

The prior broad index enumeration remains FAILED_CLOSED. The separately frozen
direct B-tree metadata phase completed once, without payload/value reads:

- 96 exact physical chunks, 16 time rows per each of six sources, chunk origin
  `(row,0,159383552)`; every filter mask is 0.
- Stored payload total 305,133,821 B; maximum individual chunk 3,179,660 B.
  This is distinct from 384 MiB of complete decoded chunks and the small logical
  selected arrays. It fits the 2 GiB pilot source-body allowance in metadata.
- 30 new requests / 94,080 B, each exact 206/URL/ETag/Content-Range/3136 B length,
  and all retained response-body hashes verified. Total metadata is 426 requests
  and 1,158,240 B, including the preserved failed attempt.
- Node type/size/key intervals/depth/cycle/bounds checks keep traversal on
  metadata. Leaf child pointers are recorded as payload locations and are never
  followed as metadata requests. The implementation has no dataset/codec API.

Actual source-byte feasibility is now demonstrated by metadata. Actual codec
decoding and full fresh joint validation still precede pilot spectral access.
The updated machine-readable ledger preserves historical unknowns and counts
failures; it does not certify or increase the nominal 256 MiB engineering
allowance.
