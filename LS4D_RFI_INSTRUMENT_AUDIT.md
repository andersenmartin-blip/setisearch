# LS4D: LHS 1140 RFI and instrument audit

Status: **AUDIT COMPLETE — MORPHOLOGY EVIDENCE INSUFFICIENT; ORIGIN UNRESOLVED**.

This retrospective audit follows the published LS4C result at commit
`3ba9a2ec0de5c0869793e659920b1af50b3659d3`. The 9.38 GHz event remains an
unresolved archival feature. Passing LS4C is insufficient evidence for
diffraction structure or artificial origin. We preserve all seven historical
dispositions and the original code; this document changes the interpretation,
not the recorded outcome of the frozen test.

## What was checked

The audit verifies the LS4C input hashes, recomputes its result identity and
replays all seven decisions from the published metrics. All agree. No new
radio spectra were downloaded or examined. Separate synthetic tests exercise
the historical detector. All 20 LS4A–LS4D unit tests pass, and the complete
LS4C freeze and result manifests still verify.

## Findings

### 1. Pulses also occur in the controls

The surviving event is `LS4B-A1-9380`, selected at 9379.881–9382.807 MHz.
The published metrics already contain the following information:

| Requested scale | ON maximum inside | ON maximum outside | OFF maximum inside | OFF blocks at threshold |
|---|---:|---:|---:|---:|
| 1 ms | 53.007 | 47.095 | 18.169 | 16 |
| 3 ms | 29.068 | 38.446 | 9.623 | 6 |
| 10 ms | 16.210 | 20.134 | 12.301 | 2 |
| 30 ms | 15.940 | 16.177 | 12.146 | 2 |

These are the four scales that passed LS4C. At three of them the ON-reference
maximum exceeds the candidate-window maximum. The OFF scan contains
above-threshold blocks at all four scales. The frozen rule compares ON and
OFF maxima with a margin; it neither requires a pulse-free OFF scan nor uses
the ON-reference maximum as a veto.

These comparisons are descriptive, not a new significance calculation. The
reference interval contains about 3.48 times as many blocks as the candidate
window, and the OFF scan occurs later rather than simultaneously. Pulse
timestamps and correlations were not retained, so common pulse timing cannot
be established from these receipts.

### 2. A constant plateau passes the claimed structure test

Using the real LS4C sample count, cadence, envelope interval and unchanged
thresholds, the audit generates two independent white-noise series with
standard deviation 1, then adds a constant +1 plateau to the ON envelope.
It injects no subsecond pulses. With the documented seed `114004`, this
passes the historical `diffraction_structure_supported` rule at four scales:
10, 30, 100 and 300 ms. ON/OFF envelope scores are approximately 428.972 and
−1.728.

The block scores are measured against the outside-envelope baseline, so a
level increase can look significant at several averaging widths without
demonstrating internal modulation. This is a constructive counterexample to
the rule's specificity. It is not a fit to the real event, does not reproduce
its four-scale pattern, and provides no false-alarm rate. The original
positive injection test remains valid as a recovery test but is insufficient
as a specificity test. The shared LS1–LS4C HTR method needs this qualification
wherever its positive result is interpreted as diffraction evidence.

### 3. Descending-frequency extraction included two extra channels

For all seven candidates, the actual extraction used 13 HTR channel centers;
only 11 centers lie in the configured candidate interval plus 0.5 MHz padding.
For `LS4B-A1-9380`, the requested padded interval was
9379.380619–9383.307446 MHz, while the recorded center extent was
9379.138184–9383.532715 MHz. Historical indices were `[7353, 7366)`; the
independent center-in-interval predicate selects `[7354, 7365)`.

The descending-axis rounding rounds outward in both directions. ON and OFF
used the same actual bands, and the receipts correctly disclose their extent,
so this does not erase the historical calculation. The extra channels could
affect the measured pulses; their influence cannot be determined from the
collapsed metrics. A new analysis must explicitly choose center inclusion or
channel-overlap semantics and validate both ascending and descending axes.

### 4. RFI context is substantial but does not identify the source

The seven Stage-1 survivors share 61.203284 seconds of overlapping envelopes
despite occupying separated frequency intervals. This is consistent with a
common disturbance, but correlation cannot be measured from event summaries.

The candidate lies inside the 9300–9500 MHz weather-radar range documented
by the [ITU/WMO radar material](https://www.itu.int/en/ITU-R/seminars/Global-ITU-WMO/Documents/Training-Workshop-singapore/Presentations/Day-2/Eric%20Allaix_Weather%20Radar.pdf).
[NRAO's VLA X-band RFI inventory](https://science.nrao.edu/facilities/vla/observing/RFI/X-Band)
also lists intermittent airborne weather radars at 9300–9500 MHz and SAR
satellites at 9300–9900 MHz. The VLA inventory describes another observatory;
neither source proves which transmitter, if any, affected GBT in January 2017.
Radar/RFI is a plausible explanation, not an established attribution.

### 5. No independent X-band cadence in the refreshed scoped inventory

At 2026-09-04T21:11:23Z, a new successful public archive query for exact target
alias `LHS1140`, telescope `GBT`, `cadence=True`, `primaryTarget=True`, limit
3000, returned four records. They are the existing C/L/S/X cadences
`--114891`, `--114914`, `--114947` and `--114966`, all on 2017-01-21. Only
`--114966` is X-band, and it is already used by LS4. The response and source
checksum are preserved in `results_ls4d_audit/archive_refresh.json`.

This scoped query did not discover an independent X-band cadence. It does not
exclude other aliases, ungrouped scans or other archives. A2/A3 in the same
cadence can provide additional controls, but are not an independent epoch.
Reprocessing A1 at higher time resolution also is not an independent
astronomical confirmation.

## Next analysis boundary

Before promoting this feature, a separately versioned LS4E procedure should:

1. Specify frequency selection precisely and test it with independent channel
   oracles. Retain the original LS4C result as historical evidence.
2. Separate the slowly varying envelope from residual pulse structure;
   validate against noise, constant/smooth plateaus, isolated impulses,
   gain steps and common ON/OFF interference as well as injected modulation.
3. Freeze the residual method and thresholds before re-reading spectra.
   Label any reanalysis of LS4C's already-seen candidate as retrospective.
4. Compare original versus corrected bands; retain derived pulse times,
   cross-band coincidence, channel concentration and clipping diagnostics
   across A1/B1 and additional controls, without publishing raw spectra.
5. Calibrate the complete selection path and seek a genuinely independent
   epoch before any scientific candidate promotion. Passing several correlated
   averaging scales is not multiple independent confirmations.

LS4D does not change LS1–LS3's recorded null outcomes, demonstrate their
completeness, or establish that this particular event is terrestrial. It
establishes that the existing positive morphology claim is too strong.

## Reproduction

From the repository root:

```bash
PYTHONPATH=src:scripts python scripts/ls4d_rfi_instrument_audit.py
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_ls4*.py'
sha256sum -c LS4C_FREEZE.sha256
sha256sum -c RESULTS_MANIFEST_LS4C_HTR.sha256
```

The machine-readable result is `results_ls4d_audit/audit.json`. It binds the
historical inputs and the refreshed archive receipt, records the synthetic
seed and NumPy version, and includes its own canonical result hash.
