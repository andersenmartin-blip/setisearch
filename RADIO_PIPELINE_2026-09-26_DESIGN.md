# Radio primary/control integration — preparation design

**Primary reference: unchanged `neighbor9`. Telescope protocol: NOT FROZEN.**
This continues the 26 September–9 October plan from science commit
`a3b20770773b6fd94fbf7d7a41ff3843c9ff3ac3`. It fixes the method choice before
reading any selected telescope spectra. The synthetic panel is engineering
development, not a publicly frozen scientific validation panel.

## Method choice and exact scope

Use the existing `detector_m43u` implementation with its `neighbor9` mask.
The reason is continuity with a recorded, unmodified reference endpoint and a
small auditable integration change. It is not a selection made by comparing
the new panel's detector outcomes. `centered_receiver_off_match_aggregate`
remains a recorded reference; it is not an alternate winner in this package.
The failed M43AI hybrid remains closed and is not adopted or retuned.

The preserved reference requires six alternating ON/OFF scans, three pairs,
and exactly 16 integrations per scan. The generic source reader accepts a
broader row-count range; this detector adapter deliberately does not claim it.
The conventional `epoch1_on` through `epoch3_off` labels identify roles, not
the old observing target. All source, motion, bank, grid, runtime and calibration
identities are newly supplied and bound in an outer radio context.

| Reference operation | Unchanged setting |
|---|---|
| Native normalization | Ascending extraction origin, float32 median/MAD, 4096-channel blocks |
| Native spectral widths | 1, 3, 5, 9, 17, 33, 65, 129 channels |
| Integration | Nearest-even binary64 channel mapping; ascending float32 row sum divided by float32 square root of row count |
| Activity hypotheses | All three two-of-three subsets, plus all three epochs; each active epoch at least 3; stack statistic `sum` |
| Mask | Isolation seed 10, support 3 in a radius of 9 carriers in another epoch; union over widths, then 9-carrier dilation |
| OFF-track comparison | Literal track tolerance 20 Hz; complete retained OFF ledger |
| Single paired OFF | Same hypothesis and width, floor 5.5 in any active paired OFF epoch |
| Stationary receiver check | Complete ±100 Hz native neighborhood, peak floor 5.5, at least two shared active epochs, 20 Hz comparison |
| Reporting clusters | Existing receiver-alias identity partition: connected components of ON tracks within 20 Hz; all members preserved |

Clustering changes no decision. A transitive component may span more than
20 Hz and does not establish a single physical source. A cluster representative
never replaces the retained member inventory.

## New integration and handoff requirements

`pipeline_radio.py` builds all ON/OFF epoch vectors from typed native sources,
one native filter cache at a time. Every score identity includes the source,
cache, context and payload identities. The same source inventory supplies the
stationary receiver measurements; a different cadence's score store is rejected.
Calibration is newly computed from an explicitly supplied baseline, sealed
before cases run, and unchanged throughout evaluation. A different context,
source domain, changed score payload or changed calibration fails closed.

`NativeRun.from_telescope` only rehydrates local receipts. Before opening row
files it requires a ready explicit source contract, current runtime, the exact
analysis-context hash, a code pin for the new module and a bounded array model.
Every receipt must reproduce that contract's exact scan and extraction window.
It performs no acquisition, alternate-source lookup or automatic old-receipt
reuse. Its positive telescope path has not been qualified by this synthetic run.
The public factory rejects the actual HD 1461 preparation contract before loading
any telescope rows.

The source/score ndarray model is limited to 128 MiB in this engineering panel,
with a maximum allowed interface ceiling of 512 MiB. It includes six source
matrices, one adapter's conservative work allowance and score staging. It is
not process RSS and excludes caller-held raw arrays, other runs, Python objects,
JSON ledgers and operating-system caches. Retention is capped at 10,000 members
per role; exceeding it is an error, never a truncated successful search.
Existing physical-match comparison and evidence caps remain unchanged.

Detection has no truth parameter. In the engineering harness, raw signal
additions are made before normalization. Truth is used only after the complete
detector result exists. Association requires a member's literal full ON-time
track to lie within two native channel spacings of the injected track and its
active epochs to be a subset of injected ON epochs. All widths are included.
The result reports both unassociated surviving members and unassociated
surviving clusters; it never changes vetoes to improve recovery.

## Engineering panel and interpretation

`config/radio_pipeline_engineering_20260926.json` fully specifies the panel:
8192 synthetic channels, 1 Hz spacing, a 513-carrier score interval plus 64
guard carriers on either side, two explicitly synthetic motion templates,
six 16-row scans, 127 circular-shift rows, minimum shift 32, maximum-quantile
calibration, reference floor 10, diagnostic rank ceiling 0.01, and six cases.
These frequencies, templates, amplitudes and numerical calibration choices
are **not a proposed HD 1461 frequency/motion/sensitivity scope**.

Two pseudorandom background seeds are used. The calibration background has a
synthetic raw-channel comb (spacing 8, addition 2) to supply eligible conditional
null cells. The evaluation background is separate; all six evaluation cases
reuse that one background. Signal additions have raw digital units. They do
not represent flux, EIRP, calibrated noise units or intra-integration smearing.
The 127 shift rows are resamples of one structured calibration realization,
not independent observing sequences or a physical false-alarm tail.

The initial pure-Gaussian development calibration stopped because some
scramble maxima had no eligible hypotheses and remained nonfinite. The guard
was preserved and is now a negative test. The structured calibration fixture
was added to exercise successful software execution; no detector threshold,
mask or physical rule was changed. Real sparse/empty conditional samples must
likewise be reported as insufficient rather than filled with invented maxima.

## Remaining work before selected telescope values can be opened

1. Resolve the existing HD 1461 pointing provenance with a new same-scan
   observable: original header, observing log or file-specific conversion
   evidence for `AGBT16A_999_189`, ON scans 0015/0017/0019. The closed catalogue
   query and public-code probe are not new evidence if repeated.
2. Construct and audit the source-specific time/frequency/motion context from
   the resolved metadata. Publish the exact extraction intervals, motion bank,
   controls, calibration construction, recovery/rejection gates and runtime.
   Development and evaluation native payload scopes must remain explicit and
   disjoint; no old threshold or cache is portable by assumption.
3. Freeze a new source contract and verify acquisition/codec integration against
   it. Add durable cumulative request/byte/attempt accounting before live use;
   the existing network budget applies only within one active session.
4. Only after these gates pass, run the bounded fresh radio pilot under that
   public freeze, retain every outcome and apply the two-week plan's existing
   stop/diagnosis rules. No silent target replacement or automatic LS restart.

This package completes a useful integration step during the source hold.
It grants no telescope access or scientific detector adoption. Original
M43AF 112+128 held-outs, closed M43AI evidence, all earlier radio candidate
dispositions and the paused LS branch remain preserved.
