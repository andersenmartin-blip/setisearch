# Milestone 11 post-hoc candidate investigation

## Result in one sentence

All five formal Milestone 11 follow-up survivors are classified **RFI OR
INSTRUMENTAL** by labelled post-hoc evidence; there is no remaining
technosignature candidate in this cadence.

This conclusion does not rewrite the preregistered result. The frozen v0.4.0
search remains `FOLLOW-UP REQUIRED` at its original boundary. The present work
performs the promised follow-up using local topocentric morphology, every ON
and OFF scan, cross-template receiver-frame comparisons, and a public-archive
cadence check.

## Scope and execution

- source cadence: the complete public 2017-01-21 GBT L-band LHS 1140 ABACAD
  sequence used in Milestone 11;
- data inspected: the two extracted windows containing the five formal
  survivors, for all three ON and all three OFF scans;
- diagnostic window: ±100 Hz around each predicted topocentric midpoint;
- receiver-frame coincidence tolerance: the already frozen 20 Hz candidate
  clustering tolerance;
- local evidence floor: S/N 5.5, equal to the frozen candidate reporting
  floor;
- code path: `scripts/m11_candidate_investigation.py`;
- GitHub Actions evidence run: `32330549163`;
- uploaded artifact SHA-256:
  `21ac7c0878f7001a98ffc0eebe2c64ffa172f0aec9f63a03122bb425a004e9c4`;
- all eight detector unit tests passed after the diagnostic run.

No detector threshold, orbital template, activity subset, spectral width, or
search statistic was retuned. The script reads the frozen survivors from
`results_m11/search_summary.json` and applies separately labelled diagnostics.

## Candidate dispositions

| # | Frozen rest frequency (MHz) | Frozen S/N | Width | Post-hoc evidence | Classification |
|---:|---:|---:|---:|---|---|
| 1 | 1425.063540414 | 45.312 | 1 ch | Receiver-frame OFF peaks in both active epochs, each one channel (2.794 Hz) below the ON peak; matched-track OFF S/N 12.22 and 23.08 | RFI or instrumental |
| 2 | 1400.000458129 | 21.718 | 9 ch | Receiver-frame OFF offsets −11.18 and +2.79 Hz in the two active epochs; matched-track OFF S/N 11.18 and 7.34 | RFI or instrumental |
| 3 | 1400.787219882 | 12.503 | 9 ch | Maps to exactly the same strongest topocentric bins as candidate 4 in both active ON epochs | RFI or instrumental |
| 4 | 1400.826385722 | 11.945 | 9 ch | Different planet template/rest coordinate, but the same 1400.825994 and 1400.825731 MHz receiver features as candidate 3 | RFI or instrumental |
| 5 | 1424.527517706 | 10.582 | 9 ch | Same candidate track is present in the adjacent epoch-1 OFF scan at S/N 9.11 versus S/N 9.45 in ON | RFI or instrumental |

### Candidate 1: 1425.063540414 MHz

The active ON scans peak at topocentric frequencies 1424.983278383 and
1424.983275589 MHz. Their paired OFF scans peak 2.793968 Hz lower in both
epochs, exactly one native channel. The feature is visually stationary and is
also prominent in the third ON and OFF scans even though those scans are not
part of the frozen activity subset. This resolves the known weakness of the
exact-hypothesis OFF veto: the OFF feature selected a nearby bin/hypothesis,
but it is the same receiver-frame line.

### Candidate 2: 1400.000458129 MHz

The two active ON peaks lie at 1399.979343172 and 1399.979256559 MHz. The
nearest stationary OFF peaks differ by −11.175871 and +2.793968 Hz,
respectively, both inside the frozen 20 Hz clustering tolerance. The identical
candidate track also scores above the reporting floor in both adjacent OFF
scans. The broad nine-channel preference and the ON/OFF recurrence make an
astrophysical source at LHS 1140 unnecessary.

### Candidates 3 and 4: cross-template alias

These initially appeared to be two distinct rest-frame clusters separated by
about 39.166 kHz. Their orbital scales are different, so the coordinate
conversion maps them onto the same receiver data. In both shared active
epochs, their strongest stationary frequencies are exactly identical at the
native-bin precision:

- epoch 1: 1400.825993624 MHz;
- epoch 2: 1400.825730991 MHz.

The two waterfall panels therefore show the same structured line under two
different predicted tracks. A physical narrowband emitter cannot be two
different LHS 1140 rest frequencies at once; this is a template-bank alias of
one local/topocentric feature.

### Candidate 5: 1424.527517706 MHz

This feature did not have a stationary OFF peak within 20 Hz, because it is
visibly drifting. The correct comparison is the already selected candidate
track. Epoch-1 ON scores S/N 9.45 on that track and the immediately following
OFF scan scores S/N 9.11 on the same track, width, and template. Its appearance
away from LHS 1140 is sufficient RFI/instrumental evidence even though the
frozen two-OFF recurrence floor was not met.

## Topocentric and regulatory context

All five features lie within or immediately adjacent to the 1400–1427 MHz
passive band. NTIA's current frequency-management manual reproduces Radio
Regulation 5.340, under which emissions are prohibited in 1400–1427 MHz:
<https://redbook.ntia.gov/view/4-17>. That fact prevents a responsible
identification with a normal licensed service from frequency alone; it does
not make a narrow line extraterrestrial.

Historical GBT L-band measurements explicitly recorded narrow RFI features in
the protected region, including entries around 1417, 1424, and 1426 MHz, and
also documented approximately 25 MHz gain structure:
<https://www.gb.nrao.edu/~glangsto/rfi/lband/>. NRAO likewise cautions that a
protected allocation does not exclude internal electronics or unintended
emissions. The present data support the generic `RFI OR INSTRUMENTAL`
classification, not a claim about a particular transmitter or hardware unit.

## Independent-cadence search

The public `blpd0` LHS 1140 directory index was enumerated on 2026-08-20. It
exposes three LHS 1140 observation IDs—the same three ON pointings already used
in Milestone 11. Files ending in `.0002.fil` and `.8.0001.fil` are alternate
products of those same observation IDs, not new pointings or observing nights.

No independent LHS 1140 cadence was found in that index. This is an
archive-availability result, not a non-recurrence measurement. No further
observation is required to resolve the five present survivors because each has
already acquired direct RFI/instrumental evidence, but a genuinely independent
future LHS 1140 cadence would still be scientifically valuable as a new frozen
search.

## Evidence files

- `results_m11_candidate_investigation/candidate_investigation.json` — full
  machine-readable per-scan measurements and dispositions;
- `results_m11_candidate_investigation/scan_metrics.csv` — flat scan-level
  metrics;
- `results_m11_candidate_investigation/archive_cross_cadence_search.json` —
  archive URLs, response hashes, exposed filenames, and observation-ID grouping;
- `results_m11_candidate_investigation/candidate_*.png` — six-scan waterfall
  and stationary-spectrum panels for every survivor;
- `scripts/m11_candidate_investigation.py` — reproducible post-hoc analysis.

## Final assessment

Milestone 11 remains a successful frozen-detector transfer and an instructive
failure mode for exact-hypothesis OFF vetoes. The candidate investigation
closes all five formal survivors as RFI/instrumental. There is **no surviving
technosignature candidate and no detection claim** from the 2017-01-21 LHS
1140 cadence.
