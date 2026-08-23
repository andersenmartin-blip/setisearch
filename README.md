# SETI Repeater Pipeline

This package implements a transparent multi-epoch search for intermittent
narrowband signals that become coherent under the predicted motion of a
selected exoplanet. The planet supplies a motion hypothesis, not a proven
source location: a detected feature could instead arise from terrestrial or
spaceborne interference, an instrumental effect, or any source within the
telescope response. The working technosignature hypothesis is a transmitter
whose frequency is stable in the selected planet frame and whose beam is not
necessarily aimed at Earth.

**Current scientific status:** no surviving candidate and no technosignature
claim. The repository preserves frozen configurations, checksummed results,
technical aborts, post-hoc labels, and non-redetections so that positive and
negative outcomes remain independently auditable.

Version 0.5.0 is the frozen detector used for new held-out validation. It
retains the Milestone 7 recurrence statistic, spectral filters, per-epoch
interference mask, candidate clustering, and RFI-family flags, and adds the
Milestone 12 local-OFF and receiver-frame alias vetoes.

## Milestone 23 result

Milestone 23 applied detector v0.5.0 to the earliest complete compatible GBT
L-band cadence for HD 33564, using HD 33564 b only as the motion template.
Across approximately 592,487,280 nominal trials, the global maximum reached
S/N 184.2732 at 1400.135544237 MHz, with empirical global p-value 1/257 and an
operational threshold of S/N 7.9455. The maximum is strongly reproduced in
OFF-source data and receives the frozen interference veto.

Because the primary 1400 MHz output reached its 50-cluster report cap, a
separately frozen complete audit reproduced the primary result and preserved
all 124 clusters in that window. Across all five windows, 77 clusters exceeded
the global threshold; all receive matched-OFF, local-OFF, single-adjacent-OFF,
or receiver-frame-alias vetoes. There is no surviving candidate. A complete
independent HD 33564 cadence six days later remains spectrally untouched
because the preregistered recurrence trigger did not fire.

## Milestone 22 result

Milestone 22 applied detector v0.5.0 to the sole complete compatible GBT
L-band cadence for HD 87883, using HD 87883 b only as the motion template.
Across approximately 592,487,280 nominal trials, the global maximum reached
S/N 16.1118 at 1400.114068134 MHz, with empirical global p-value 1/257 and an
operational threshold of S/N 8.3645.

Twenty clusters exceeded the threshold. Nineteen, including the global
maximum, map to the same recorded receiver feature in both active epochs and
receive the frozen receiver-frame-alias veto. The remaining case is reproduced
within 19.849 Hz in OFF-source data and receives the fixed local-OFF veto.
There is no surviving candidate and no technosignature claim.

## Milestone 21 result

Milestone 21 applied detector v0.5.0 to the sole complete compatible GBT
L-band cadence for HD 154345, using HD 154345 b only as the motion template.
Across approximately 592,487,280 nominal trials, the global maximum reached
S/N 328.3539 at 1400.000778429 MHz, with empirical global p-value 1/257 and
an operational threshold of S/N 9.5556. The maximum is stronger in matched
OFF-source data and receives the frozen interference veto.

Two separate 1425 MHz arithmetic-family cases entered a separately frozen
morphology review. Despite different planet-frame frequencies and orbital
templates, both map to exactly the same recorded receiver feature in both
claimed active epochs; one also exceeds the fixed adjacent-OFF track
threshold. Both are classified `RFI_OR_INSTRUMENTAL`. There is no surviving
candidate and no technosignature claim.

## Milestone 20 result

Milestone 20 applied detector v0.5.0 to the sole complete compatible GBT
L-band cadence for rho CrB, using rho CrB c only as the motion template.
Across approximately 592,487,280 nominal trials, the global maximum reached
S/N 69,174.5910 at 1400.459812410 MHz, with empirical global p-value 1/257 and
an operational threshold of S/N 8.0913.

The very strong maxima are matched or locally reproduced in OFF-source data
and receive the frozen interference vetoes. One separate 1400.196827972 MHz
arithmetic-family case entered a separately frozen morphology review. Its
strongest local ON feature in active epoch 1 occurs at exactly the same
receiver frequency as a stronger adjacent-OFF feature, satisfying the fixed
20 Hz coincidence veto. There is no surviving candidate and no
technosignature claim.

## Milestone 19 result

Milestone 19 extended the frozen low-smearing target ranking to positions
6-10. Header-only screening selected 47 UMa / HIP 53721 at rank 8: the two
nearer hosts lacked a complete compatible L-band cadence. The held-out search
used 47 UMa d only as the motion template and read cadence `--73992` after a
successful 630-case extraction-coverage proof.

Across approximately 601,293,840 nominal trials, the global maximum reached
S/N 7.4147 at 1425.240493566 MHz. The frozen operational threshold was S/N
7.6987 and the empirical global p-value was 9/257. All 89 reported clusters
were below threshold, so no candidate or post-hoc follow-up was triggered.
There is no surviving candidate and no technosignature claim.

## Milestone 18 result

Milestone 18 applied detector v0.5.0 to the sole complete compatible GBT
L-band cadence for GJ 649, using GJ 649 b only as the motion template. Across
approximately 592,487,280 nominal trials, the global maximum reached S/N
7.8935 at 1425.213204339 MHz, with empirical global p-value 1/257 and an
operational threshold of S/N 7.2884.

Four 1425 MHz arithmetic-family cases exceeded the threshold without an
automatic OFF veto. A separately frozen morphology review showed that all four
different planet-frame solutions select the same receiver-frame feature in
both shared active epochs. Every case therefore receives the fixed
cross-template alias disposition `RFI_OR_INSTRUMENTAL`. There is no surviving
candidate and no technosignature claim.

## Milestone 17 result

Milestone 17 applied detector v0.5.0 to a previously unused complete GBT
L-band cadence for GJ 849, using GJ 849 b only as the motion template. Across
approximately 601,293,840 nominal trials, the global maximum reached S/N
140.9364 at 1400.254871242 MHz, with empirical global p-value 1/257 and an
operational threshold of S/N 8.9124.

The maximum is decisively rejected by the frozen OFF-source veto: the matched
OFF statistic is S/N 77.5420 and a nearby OFF recurrence reaches S/N 113.8490
within 11.176 Hz. All 50 reported above-threshold clusters receive the same
physical OFF-source disposition, while the remaining 53 are below threshold.
There is no surviving candidate and no technosignature claim. The complete
cadence reserved six days later was therefore not opened spectrally.

## Milestone 16 result

Milestone 16 applied detector v0.5.0 to a previously unused complete GBT
L-band cadence for HD 219134, using the predicted motion of HD 219134 h. Across
approximately 601,293,840 nominal trials, the held-out maximum was S/N 9.1455
at 1412.485745177 MHz, with empirical global p-value 1/257 and an operational
threshold of S/N 7.4288.

Post-hoc morphology left that automated survivor and a separate
1425.136278570 MHz arithmetic-family case unresolved pending an independent
cadence. Both exact hypotheses were then tested under frozen rules in the
earliest later complete qualifying HD 219134 cadence, observed approximately
40 days later. Neither reached the S/N 3 persistence floor in any of the three
independent ON scans. Both are formally not redetected, leaving no surviving
Milestone 16 candidate and no technosignature claim.

## Milestone 14 result

Milestone 14 applies detector v0.5.0 to a previously unused public GJ 687
cadence after a successful 630-case full-bank extraction-coverage proof.

Across approximately 601,293,840 nominal trials, the observed maximum is S/N
61,308.5941 and the empirical global p-value is 1/257. The maximum is rejected
by the frozen local-OFF veto; every other window maximum is also automatically
vetoed. Of 85 reported clusters, 34 are below threshold, 46 receive a specific
v0.5/OFF veto, and 5 weak 1425 MHz arithmetic-family cases were referred to
the fixed post-hoc review. That review classifies two as RFI or instrumental
from adjacent-OFF evidence. The other three were then tested in the only
additional public L-band GJ 687 data set, an incomplete A-B-A-D sequence from
2016-07-15, seven days earlier. None reached the fixed S/N 3 recurrence floor
in either independent ON scan. There is no surviving candidate and no
technosignature claim.

## Milestone 13 status

Milestone 13 preregistered the first independent detector-v0.5.0 application
to a public GJ 411 cadence. All detector tests passed and all 30 configured
HDF5 slices were extracted and hashed, but the search stopped fail-closed
before any window completed: the frozen 350 kHz extraction guard did not cover
the full rest grid for the extreme `scale=1.0`, `phase=-0.2` template.

No candidate statistic, empirical p-value, or completeness result was
produced. The milestone is recorded as a technical abort, not a null search;
the frozen extraction range will not be widened after spectral contact.

## Milestone 11 result

Milestone 11 transfers the unchanged v0.4.0 detector to the complete public
2017-01-21 Green Bank Telescope L-band ABACAD cadence for LHS 1140. It changes
the target, telescope, date, cadence, and spectral payload while deliberately
reusing the five Milestone 10 planet-frame bands.

Across approximately 601,293,840 nominal frequency/orbit/activity/width trials:

- observed global maximum: **S/N 105.8952** at 1400.926242128 MHz;
- scrambled-null median: **S/N 7.5012**;
- scrambled-null 99th percentile and operational threshold: **S/N 10.3893**;
- empirical global p-value: **1/257 = 0.003891**;
- assessment: **FOLLOW-UP REQUIRED**.

The result is not a technosignature claim. The 1406.707600 MHz maximum is
stronger in its matched OFF hypothesis. The 1425.063540 MHz ON maximum survives
the frozen exact-hypothesis veto, but a strong OFF-bank maximum lies only about
5.6 Hz away. The strongest 1400.926242 MHz feature has arithmetic-family flags,
which are triage evidence rather than a sufficient physical veto.

Candidate reduction reported 109 clusters: 80 below threshold, 8 exact matched
OFF vetoes, 16 arithmetic-family flags pending manual review, and 5 formal
follow-up survivors. A complete repeat produced byte-identical primary outputs.
The next step is a labelled post-hoc topocentric/ON-OFF/cross-cadence
investigation with the detector settings left frozen.

## Milestone 10 result

Milestone 10 applies the frozen detector to five fresh 1 MHz planet-frame bands
using previously unextracted public Parkes observations from 30 April, 2 May,
and 3 May 2021. The searched intervals total 5 MHz and do not overlap any
Milestone 6–9 interval.

Across approximately 840,001,680 nominal frequency/orbit/activity/width trials:

- observed global maximum: **S/N 9.3115** at 1424.937812000 MHz;
- scrambled-null median: **S/N 9.2781**;
- scrambled-null 99th percentile and operational threshold: **S/N 12.6079**;
- empirical global p-value from 256 complete-search scrambles: **0.4942**;
- assessment: **no candidate**.

All five band maxima are below the global threshold and their matched OFF
hypotheses fail the recurrence floor. The real-noise completeness experiment
places coarse multichannel 50% and 90% recovery points near ideal single-epoch
S/N 20.44 and 28.8. A one-channel-only search does not reach 50% recovery by
S/N 40. A complete repeat run produced byte-identical primary outputs.

## Milestone 9 result

Milestone 9 applies the frozen detector to independent Parkes observations from
29 April, 30 April, and 1 May 2021. It retests the 1405.25–1405.75 MHz
Milestone 8 band at 2 Hz resolution, using three 30-minute Proxima scans and
their immediately following 5-minute 1421−490 blank-sky controls.

Across approximately 84,000,336 nominal frequency/orbit/activity/width trials:

- observed global maximum: **S/N 8.1271** at 1405.516462000 MHz;
- scrambled-null median: **S/N 8.1083**;
- scrambled-null 99th percentile and operational threshold: **S/N 9.0548**;
- empirical global p-value from 256 full-search scrambles: **0.4708**;
- assessment: **no candidate**.

The strongest fluctuation appears in all three ON epochs but is typical of the
complete-search null distribution. Its matched OFF hypothesis fails the
per-epoch recurrence floor. A post-hoc cross-check also finds that neither the
2019 nor the 2021 maximum recurs in the other campaign.

## Milestone 8 result

The confirmation search covers 1405.25–1405.75 and 1423.25–1423.75 MHz in the
planet frame at 3.814697 Hz resolution. The 1 MHz total bandwidth is independent
of Milestone 7 in frequency, but it reuses the same three observing epochs.

| Band | Best S/N | Width | Frequency (MHz) | Window p | OFF result |
|---|---:|---:|---:|---:|---|
| 1405.25–1405.75 | 6.154 | 9 ch | 1405.472141266 | 0.735 | fails recurrence floor |
| 1423.25–1423.75 | 6.335 | 9 ch | 1423.628288269 | 0.350 | fails recurrence floor |

Across approximately 88,081,056 nominal frequency/orbit/activity/width trials:

- observed global maximum: **S/N 6.3347**;
- empirical global p-value from 256 complete-search scrambles: **0.6031**;
- scrambled-null median: **S/N 6.4046**;
- scrambled-null 99th percentile and operational threshold: **S/N 7.2519**;
- assessment: **no candidate**.

Candidate reduction retained 75 hypothesis peaks above S/N 5.5 and merged them
into 69 frequency clusters. All 69 are below the global threshold. The frozen
single-epoch interference rule masked zero cells in either ON or OFF band, so
the confirmation null does not depend on RFI excision.

## Frozen confirmation record

The configuration was frozen at 2026-08-15T18:34:04Z with SHA-256
`2e9df9f13f5cf2a3c438f1ffbd20784e76355e66e3fcb90e70f2ff19658a3d6d`.
The eight detector tests passed before extraction. The configuration retained:

- S/N at least 3 in every claimed active epoch;
- `sqrt(N)` times the weakest active-epoch S/N as the recurrence statistic;
- a moving per-epoch mask for isolated S/N ≥ 10 features with a 9-channel guard;
- normalized 1-, 3-, 5-, and 9-channel filters;
- the same candidate clustering and arithmetic-family rules as Milestone 7.

The two bands, new random seeds, and extended completeness grid were the only
planned Milestone 8 changes.

## Real-noise completeness

Signals are injected into independently shifted real 1405.5 MHz planet-frame
noise. They use continuous fractional-channel frequencies and a time-averaged
sinc-squared response while sweeping during each 16.777216 s integration. Four
exact orbital templates span 0.34–5.02 swept channels per integration.

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 4/32 (12.5%) | 4/32 (12.5%) |
| 12 | 25/32 (78.1%) | 9/32 (28.1%) |
| 16 | 32/32 (100%) | 17/32 (53.1%) |
| 20 | 32/32 (100%) | 21/32 (65.6%) |
| 24 | 32/32 (100%) | 28/32 (87.5%) |
| 32 | 32/32 (100%) | 32/32 (100%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

Coarse piecewise-linear estimates put multichannel 50% and 90% recovery near
ideal S/N 10.29 and 14.17. The corresponding one-channel estimates are 15.5
and 25.6. These are point estimates rather than confidence bounds; 32/32 has a
Wilson 95% lower bound of 89.3%.

## Citation and reuse

Citation metadata is provided in `CITATION.cff`. The software is released
under the MIT License; public telescope data remain subject to their source
archive terms. Contributions should follow `CONTRIBUTING.md`, especially the
rule that held-out configurations and disposition rules are fixed before
spectral contact. Security reports should follow `SECURITY.md`.

## Install and reproduce

Requirements are Python 3.10+, NumPy, Astropy, Matplotlib, GCC, and OpenMP.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
seti-repeater validate --tsamp 18.253611008 \
  --channel-width 2.7939677238464355 \
  --output results_m11/validation.json
seti-repeater extract \
  --config config/lhs1140b_new_target_m11.json \
  --data-dir data_m11 --workers 12
sha256sum -c DATA_MANIFEST_M11.sha256
seti-repeater search \
  --config config/lhs1140b_new_target_m11.json \
  --data-dir data_m11 --output-dir results_m11
python -m unittest discover -s tests -v
```

`extract` uses HTTP byte-range requests and downloads only selected channels,
not the multi-gigabyte filterbanks in full. Existing slices are cached. Source
URLs and filterbank header metadata are preserved in every extract.

## Statistical calibration

Each null realization circularly shifts epoch spectra independently before
repeating the complete width/orbit/activity search. The per-epoch RFI mask is
shifted by the same amount. This preserves each epoch's noise and interference
while destroying the inter-epoch coherence being tested. The empirical p-value
is `(1 + exceedances) / (N + 1)` and is not converted to Gaussian sigma.

## Limits

- Milestone 23 searched five 1 MHz windows in one primary HD 33564 cadence,
  not the full GBT L-band receiver range or independent observing nights.
- Its 77 over-threshold clusters are all rejected by frozen physical OFF or
  receiver-frame vetoes after a complete report-cap audit.
- The complete compatible HD 33564 cadence six days later remains spectrally
  untouched because no primary case survived the automatic vetoes.
- Milestone 22 searched five 1 MHz windows in one HD 87883 cadence, not the
  full GBT L-band receiver range or independent observing nights.
- Its 20 over-threshold planet-frame clusters are all rejected by frozen
  receiver-frame-alias or local-OFF vetoes; no manual review was triggered.
- The other frozen HD 87883 cadence is S-band and does not cover the search
  windows.
- Milestone 21 searched five 1 MHz windows in one HD 154345 cadence, not the
  full GBT L-band receiver range or independent observing nights.
- Its two morphology-review cases map to the same receiver features under
  different planet templates and are rejected as RFI or instrumental.
- No second complete compatible HD 154345 cadence was present in the frozen
  public header screen.
- Milestone 20 searched five 1 MHz windows in one rho CrB cadence, not the full
  GBT L-band receiver range or independent observing nights.
- Its strong window maxima recur in OFF-source data; the sole manual-review
  case is independently rejected by an exact adjacent-OFF frequency match.
- No second complete compatible rho CrB cadence was present in the frozen
  public header screen.
- Milestone 19 searched five 1 MHz windows in one 47 UMa cadence, not the full
  GBT L-band receiver range or independent observing nights.
- Every Milestone 19 reported cluster was below the globally calibrated
  threshold; no candidate-local review was triggered.
- No second complete compatible 47 UMa cadence was present in the frozen
  public header screen.
- Milestone 18 searched five 1 MHz windows in one GJ 649 cadence, not the full
  GBT L-band receiver range or an independent observing epoch.
- Its four over-threshold planet-frame cases all map to the same receiver-frame
  feature in two ON epochs and are vetoed as RFI or instrumental under the
  separately frozen morphology rule.
- No second complete compatible GJ 649 cadence was present in the frozen public
  header screen.
- Milestone 17 searched five 1 MHz windows in one primary GJ 849 cadence, not
  the full GBT L-band receiver range.
- Its very low empirical rank is driven by strong structured features that
  recur in OFF-source data and are rejected as RFI or instrumental.
- The second complete GJ 849 cadence was deliberately left spectrally
  untouched because no primary case survived the frozen vetoes.
- Milestone 16 searched five 1 MHz windows in one primary cadence, not the full
  GBT L-band receiver range.
- Its 40-day recurrence test targeted two post-hoc hypotheses in a complete
  independent cadence; it was not a second blind search and cannot increase
  the frozen global significance.
- Milestone 16 non-redetection does not exclude an intermittent transmitter
  that was inactive during the independent 2016-10-01 cadence.
- Milestone 14 covers one cadence and five 1 MHz windows, not the full receiver
  band or an independent observing epoch.
- The partial independent Milestone 14 cadence contains only two target scans
  and is not a complete ABACAD observation. Non-redetection does not exclude an
  intermittent signal that was inactive on 2016-07-15.
- Arithmetic-frequency-family and widest-boxcar flags are triage evidence, not
  physical vetoes.
- Milestone 11 covers one 28-minute ABACAD cadence, not independent
  observing nights.
- Milestone 11 contains strong structured ON and OFF features. Its minimum
  empirical p-value shows departure from the circular-shift null, not evidence
  of an extraterrestrial origin.
- Exact-hypothesis OFF vetoes can miss nearby interference with a different
  best width, activity subset, or template.
- Five Milestone 11 reported clusters remain formally follow-up-required; no
  technosignature claim is made.

- Milestone 10 covers five disjoint bands totaling 5 MHz, not the full receiver
  band.
- The three Milestone 10 epochs all belong to the April–May 2021 follow-up
  campaign. November 2020 and January 2021 filterbanks were not returned by the
  public API when preregistered, so this is not an independent long-baseline
  confirmation.
- The Milestone 10 global null has a heavy tail dominated empirically by the
  1400.0–1401.0 MHz band; no physical cause is assigned without a separate
  full-band diagnostic.
- Milestone 9 is independent in observing epoch, not frequency; it directly
  retests the lower Milestone 8 band.
- Milestone 9 covers 0.5 MHz total, not the full receiver band.
- The 2021 OFF scans are only 5 minutes, versus 30 minutes ON, so the OFF veto
  is less sensitive.
- Completeness assumes an exact orbital-bank member and activity in epochs 1
  and 3.
- In Milestone 9, the frozen RFI rule masked 45 ON and 44 OFF
  template/epoch/frequency cells; these are only about 2.9 parts per million of
  the corresponding banks.
- Boxcars are approximations, not exact matched filters for every swept profile.
- Arithmetic-frequency families are triage flags, not proof of interference.
- A null result constrains only the signal class, epochs, frequencies, and
  sensitivity actually tested.

## Key files

- `MILESTONE_23_TARGET_SELECTION.md` — fixed HD 33564 target and cadence split.
- `MILESTONE_23_SELECTED_METADATA_RESULT.md` — official orbit and astrometry.
- `MILESTONE_23_PREREGISTRATION.md` — frozen held-out search design.
- `MILESTONE_23_PRIMARY_RESULT.md` — primary result and report-cap boundary.
- `MILESTONE_23_COMPLETE_AUDIT_PLAN.md` — fixed complete-disposition audit.
- `MILESTONE_23_REPORT.md` — final no-survivor result and limits.
- `config/hd33564b_heldout_m23.json` — frozen primary search configuration.
- `config/hd33564b_m23_complete_audit.json` — one-field report-cap expansion.
- `DATA_MANIFEST_M23.sha256` — checksums for all 30 primary extracts.
- `RESULTS_MANIFEST_M23.sha256` — primary output checksums.
- `results_m23_complete_audit/audit_summary.json` — complete veto accounting.
- `MILESTONE_22_TARGET_SELECTION.md` — fixed HD 87883 target and cadence.
- `MILESTONE_22_SELECTED_METADATA_RESULT.md` — official orbit and astrometry.
- `MILESTONE_22_PREREGISTRATION.md` — frozen held-out search design.
- `MILESTONE_22_REPORT.md` — final no-survivor result and limits.
- `config/hd87883b_heldout_m22.json` — frozen target, cadence, orbit, and bands.
- `DATA_MANIFEST_M22.sha256` — checksums for all 30 reproducible extracts.
- `RESULTS_MANIFEST_M22.sha256` — primary output checksums.
- `results_m22/search_summary.json` — machine-readable complete search record.
- `MILESTONE_19_HEADER_SCREEN_PLAN.md` — frozen ranks 6-10 target extension.
- `MILESTONE_19_HEADER_SCREEN_RESULT.md` — header-only cadence outcome.
- `MILESTONE_19_TARGET_SELECTION.md` — fixed 47 UMa target and cadence.
- `MILESTONE_19_SELECTED_METADATA_RESULT.md` — official orbit and astrometry.
- `MILESTONE_19_PREREGISTRATION.md` — frozen held-out search design.
- `MILESTONE_19_REPORT.md` — final no-candidate result and limits.
- `config/47umad_heldout_m19.json` — frozen target, cadence, orbit, and bands.
- `DATA_MANIFEST_M19.sha256` — checksums for all 30 reproducible extracts.
- `RESULTS_MANIFEST_M19.sha256` — primary output checksums.
- `results_m19/search_summary.json` — machine-readable complete search record.
- `MILESTONE_17_TARGET_SELECTION.md` — frozen GJ 849 target and cadence split.
- `MILESTONE_17_SELECTED_METADATA_RESULT.md` — official orbit and astrometry.
- `MILESTONE_17_PREREGISTRATION.md` — frozen held-out search design.
- `MILESTONE_17_REPORT.md` — primary result and final no-survivor disposition.
- `config/gj849b_heldout_m17.json` — frozen target, cadence, orbit, and bands.
- `DATA_MANIFEST_M17.sha256` — checksums for all 30 reproducible extracts.
- `RESULTS_MANIFEST_M17.sha256` — primary output checksums.
- `results_m17/search_summary.json` — machine-readable complete search record.
- `MILESTONE_16_PREREGISTRATION.md` — frozen HD 219134 h held-out design.
- `MILESTONE_16_REPORT.md` — primary held-out result and survivor record.
- `MILESTONE_16_CANDIDATE_INVESTIGATION_PLAN.md` — frozen morphology protocol.
- `MILESTONE_16_CANDIDATE_INVESTIGATION.md` — morphology and ON/OFF evidence.
- `MILESTONE_16_INDEPENDENT_CADENCE_PLAN.md` — frozen 40-day recurrence test.
- `MILESTONE_16_INDEPENDENT_CADENCE_RESULT.md` — final two-case non-redetection.
- `config/hd219134h_m16_independent_followup.json` — independent scan
  identities and geometry.
- `results_m16_independent_followup/independent_followup.json` —
  machine-readable dispositions.
- `DATA_MANIFEST_M16_INDEPENDENT_FOLLOWUP.sha256` — independent extract checksums.
- `RESULTS_MANIFEST_M16_INDEPENDENT_FOLLOWUP.sha256` — independent result checksums.
- `MILESTONE_14_PREREGISTRATION.md` — frozen GJ 687 held-out design.
- `MILESTONE_14_REPORT.md` — held-out result and scientific interpretation.
- `MILESTONE_14_CANDIDATE_INVESTIGATION_PLAN.md` — fixed post-hoc protocol.
- `MILESTONE_14_CANDIDATE_INVESTIGATION.md` — five-case disposition record.
- `MILESTONE_14_INDEPENDENT_CADENCE_METADATA.md` — complete GJ 687 cadence inventory.
- `MILESTONE_14_INDEPENDENT_CADENCE_PLAN.md` — frozen partial-cadence follow-up rules.
- `MILESTONE_14_INDEPENDENT_CADENCE_RESULT.md` — three-candidate non-redetection record.
- `config/gj687b_m14_partial_independent_followup.json` — four-scan identities and geometry.
- `results_m14_independent_followup/independent_followup.json` — machine-readable follow-up evidence.
- `results_m14_candidate_investigation/candidate_investigation.json` —
  machine-readable morphology and ON/OFF evidence.
- `RESULTS_MANIFEST_M14_CANDIDATE_INVESTIGATION.sha256` — investigation
  output checksums.
- `MILESTONE_11_PREREGISTRATION.md` — frozen LHS 1140 transfer design.
- `config/lhs1140b_new_target_m11.json` — target, cadence, orbit, and bands.
- `DATA_MANIFEST_M11.sha256` — checksums for all 30 reproducible extracts.
- `results_m11/search_summary.json` — complete search and candidate evidence.
- `results_m11/completeness.json` — aggregate and per-injection recovery data.
- `results_m11/completeness_thresholds.json` — coarse recovery thresholds.
- `results_m11/reproducibility_audit.json` — byte-identical repeat evidence.
- `results_m11/scramble_nulls.npz` — empirical global and per-band null maxima.
- `MILESTONE_11_REPORT.md` — scientific handoff and follow-up boundary.
- `MILESTONE_10_PREREGISTRATION.md` — frozen five-band survey design.
- `config/proxima_small_survey_m10.json` — Milestone 10 scan and search config.
- `DATA_MANIFEST_M10.sha256` — checksums for all 30 reproducible extracts.
- `results_m10/search_summary.json` — complete five-band search evidence.
- `results_m10/completeness.json` — aggregate and per-injection recovery data.
- `results_m10/completeness_thresholds.json` — coarse recovery thresholds.
- `results_m10/reproducibility_audit.json` — deterministic rerun evidence.
- `results_m10/scramble_nulls.npz` — empirical global and per-band null maxima.
- `MILESTONE_10_REPORT.md` — scientific handoff.
- `MILESTONE_9_PREREGISTRATION.md` — frozen design and config hash.
- `config/proxima_temporal_confirmation_m9.json` — temporal confirmation config.
- `DATA_MANIFEST_M9.sha256` — checksums for all six reproducible extracts.
- `results_m9/search_summary.json` — complete search evidence.
- `results_m9/completeness.json` — aggregate and per-injection recovery data.
- `results_m9/completeness_thresholds.json` — coarse recovery thresholds.
- `results_m9/temporal_crosscheck.json` — labelled post-hoc campaign comparison.
- `results_m9/reproducibility_audit.json` — deterministic rerun evidence.
- `results_m9/scramble_nulls.npz` — empirical null maxima.
- `MILESTONE_9_REPORT.md` — scientific handoff.

The extracted telescope slices are not included in the distributable archive;
the extractor and checksum manifest reproduce and verify them from public URLs.
