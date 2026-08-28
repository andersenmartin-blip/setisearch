# Milestone 37 detector-v0.6 streaming-evidence checkpoint

Status: **NON-FROZEN SYNTHETIC CHECKPOINT — WIDTH-STREAMING GATE PASSED —
NO SPECTRAL ACCESS**.

This checkpoint closes the bounded physical-evidence streaming blocker from
the metadata-only runner checkpoint. It was implemented and tested without
opening, requesting or inspecting an HD 156668 / HIP 84607 telescope spectral
payload. It is not a detector release, preregistration, search, null result or
signal claim.

## Closed gate

- `CacheWidthStream` revalidates a trusted run-level cache manifest against
  independently supplied file, inventory and factor-bundle receipts.
- It opens exactly one certified spectral width and the three required ON or
  OFF scans at a time, in frozen width order. Repeated, skipped, overlapping,
  incomplete or over-cap batches permanently invalidate the stream.
- Every mapped payload byte and open handle is owned by a
  `NativeFilterCacheArena`. All three handles must be closed and the mapped
  byte count must return to zero before the next width can open.
- The M37 wrapper fixes the live mapped-payload cap at 536,870,912 bytes and
  requires all eight widths from the exact 240-entry run manifest.
- Receiver-frame and single-adjacent-OFF evidence now have generic and frozen
  M37 width-streaming entry points. They produce the same evidence and
  certificate objects as the existing full-inventory reference functions.
- A canonical, independently revalidatable resource certificate records every
  width batch, peak bytes, peak handle count and closure assertion, and binds
  that accounting to the resulting evidence SHA-256.

## Synthetic verification

The tests publish real read-only native-cache files, reopen them through
memory maps and exercise the fail-closed contracts. They do not use M37
telescope data.

| Check | Result |
|---|---|
| Targeted cache-stream, receiver and adjacent-OFF tests | 23 passed, 0 skipped, 0 failed |
| Full repository suite | 252 run, 251 passed, 1 expected benchmark skip, 0 failed |
| Receiver streaming versus full inventory | Bit-identical result object |
| Adjacent-OFF streaming versus full inventory | Bit-identical result object |
| Width order, skip and byte-cap violations | Permanently fail closed |
| Resource-receipt mutation after resealing | Rejected by semantic accounting checks |
| HD 156668 spectral files contacted | No |
| Spectral dataset values read | No |

The exact-grid benchmark remains the one expected opt-in skip in the full
suite; this checkpoint does not replace its earlier independent passing run.

## Remaining blockers

1. Extend the sparse/local completeness reference through exhaustive
   retention, OFF and adjacent-OFF disposition, receiver-alias dependencies,
   rank-p, production receipts and the complete resource envelope.
2. Integrate the now-closed streaming interfaces and evidence-bound resource
   receipts into the restartable end-to-end production runner and journal.
3. Pin Python, extractor dependencies, OS, compiler, OpenMP runtime, CPU policy
   and the eight-thread execution host.
4. Only after those gates pass may a final preregistration be frozen. Spectral
   access would still require a separate exact-scope authorization receipt.

The machine-readable checkpoint is
`results_m37_v0p6_streaming_evidence/progress.json`.
