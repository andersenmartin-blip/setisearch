# Radio continuation — integrated native search and controls

**Eight local integration tests pass. All six engineering cases complete.**
The new explicit-source reader can now feed a common, receipt-bound radio
search/control interface. The unchanged `neighbor9` reference is selected for
the planned pilot, subject to a source-specific scientific protocol and gate.
No new telescope spectrum has been opened. HD 1461 remains on its existing
pointing-provenance hold.

This package continues the [two-week radio plan](RADIO_TWO_WEEK_PLAN_2026-09-26.md)
and the [source-interface work](RADIO_SOURCE_2026-09-26_RESULT.md).
The [preparation design](RADIO_PIPELINE_2026-09-26_DESIGN.md) states the exact
reference settings, new integration boundaries and outstanding live-data gates.

## What now works

`src/seti_repeater/pipeline_radio.py` builds full-support ON/OFF scores from six
explicit native sources and runs fresh baseline calibration, complete retention,
OFF-track matching, paired OFF checks, stationary receiver checks, rank accounting
and a complete cluster ledger. It supplies new source/bank/grid/context identities
to the unchanged reference algorithms. It loads no old target configuration or
old calibration. Only one native filter cache is retained at a time.

The synthetic path uses raw powers, adds signals before normalization and then
executes the same native normalization/filter/gather chain. Telescope and
synthetic provenance retain separate types. A gated local telescope factory
requires the new context/code/runtime/source contract; the actual HD 1461
preparation contract is rejected before any telescope row is opened.

Every ON and OFF member is retained in the compressed full detector ledgers.
Every ON member appears in exactly one existing track-identity cluster, with
its original physical and rank decisions. There is no top-N truncation and no
truth-informed veto. Capacity overflow prevents a successful result.

## Observed engineering outcomes

| Synthetic case | Retained ON / OFF members | Diagnostic final members | Final clusters | Result |
|---|---:|---:|---:|---|
| Unmodified evaluation noise | 0 / 0 | 0 | 0 | No retained event |
| Narrow signal, all three ON epochs | 54 / 0 | 54 | 1 | Injected track recovered |
| Five-channel signal, two ON epochs | 131 / 0 | 131 | 1 | Injected track recovered |
| Matched signal in ON and OFF | 54 / 51 | 0 | 0 | Rejected by fixed OFF tests |
| One strong ON epoch | 0 / 0 | 0 | 0 | No eligible retained event |
| Two ON epochs, one matching paired OFF | 9 / 0 | 0 | 0 | Rejected by single paired-OFF evidence |

Both signal cases contain one final cluster. Under the fixed narrow truth-track
association rule, 31/54 and 18/131 final members match truth directly; the other
23 and 113 remain explicitly recorded. They belong to the same corresponding
associated cluster. There are zero unassociated final clusters in this panel.
Multiple widths, carriers and activity subsets are not counted as independent
signal discoveries.

The six evaluation cases reuse **one synthetic noise cadence**. A second seed
supplies a separate, deliberately structured calibration fixture. There are
127 distinct calibration shift rows; the operational threshold is the fixed
engineering floor 10. Neither the six labelled cases nor the shifts are six
or 127 independent telescope/null observations. The initially empty conditional
calibration correctly failed; it was not treated as a measured zero tail.

## Verification and limits

The eight tests check complete execution and member partitioning; independently
sorted normalization; direct per-native-window scores; stationary receiver
measurements; truth isolation; source/score/calibration mismatch rejection;
capacity failure; the HD 1461 hold; and insufficient conditional calibration.
Individual test methods include multiple subcases.

- **786,432** normalized native cells agree bit-for-bit with the independent
  sort-based reference.
- **61,536** full-support score cells across all six scans, eight widths and
  two templates agree bit-for-bit with independent direct native-window sums.
- **24** receiver queries, including score-grid edges, agree with direct
  unshifted native-window measurements.
- The per-run modeled ndarray bound is **10,519,808 bytes**, below the specified
  128 MiB array limit. This is not a process-memory or ledger-memory measurement.

The retained runtime is Python 3.12.14 and NumPy 2.3.5. HDF5 decoding is not part
of this run; h5py/hdf5plugin are absent in this execution environment. The earlier
seven codec/source checks remain separate evidence under their recorded runtime.
No claim of a new telescope-codec qualification is made.

These are deterministic local engineering checks on two synthetic background
seeds, two toy motion templates and two signal designs. They do not establish
HD 1461 recovery, false-alarm probability, broad completeness, physical
sensitivity or general qualification. The passed checks do not reverse M43AI's
failed scientific gate. The live telescope factory's positive path and the
source-specific motion model remain unqualified.

## Evidence, reproduction and continuation

`results_radio_pipeline_2026-09-26/` contains the actual test log, runtime/code
pins, full synthetic context, raw/normalized input-hash inventory, fixed
calibration, complete gzip JSON detector ledgers for all six cases, complete
truth/member accounting and the machine-readable qualification summary.
Gzip is lossless; every written JSON artifact is decoded and checked after
writing. `RESULTS_MANIFEST_RADIO_PIPELINE_2026-09-26.sha256` pins the package.

```bash
PYTHONPATH=src:scripts python scripts/radio_pipeline_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_PIPELINE_2026-09-26.sha256
```

Re-running rewrites the measured test-duration log and its hashes; compare the
deterministic context, source hashes and detector reports separately from timing.

**Scientific readiness remains HOLD_POINTING_PROVENANCE_UNRESOLVED.** The next
information requirement is unchanged: original same-scan pointing/processing
evidence for HD 1461. The next engineering work is durable acquisition-attempt
accounting and the source-specific prospective context/protocol, while keeping
all selected spectra closed. The existing daily continuation through 9 October
will read this updated project state; no duplicate task is created.

M43AF's original 112 injection/control and 128 native-null held-outs remain
unopened. LS stays paused; LS8BF and all 16 unresolved LS events remain preserved.
No message, observation booking or CHEOPS request has been sent.
