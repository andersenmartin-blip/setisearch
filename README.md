# SETI Repeater Pipeline

This package implements a transparent multi-epoch search for intermittent
narrowband signals that become coherent under the predicted motion of a
selected exoplanet. The planet supplies a motion hypothesis, not a proven
source location: a detected feature could instead arise from terrestrial or
spaceborne interference, an instrumental effect, or any source within the
telescope response. The working technosignature hypothesis is a transmitter
whose frequency is stable in the selected planet frame and whose beam is not
necessarily aimed at Earth.

**Current scientific status:** no technosignature claim. The unresolved
Milestone 33 follow-up case remains open. Milestone 36 completed the HIP 48714
primary search and complete-retention audit; no M36 candidate survives.
Milestone 37 authorized and read the six HD 156668 cadence files, built all
240 native caches, completed calibration and sealed an operational threshold
of S/N 126.20158386230469. The original Run 004 remains permanently
`M37_INVALID_NO_CONCLUSION` after its 10,000-record capacity overflow. A
separately documented post-contact, capacity-only v0.6.1 amendment preserved
that invalid result and completed a new Run 006 with 43,883 ON and 2,160 OFF
records. Full physical disposition, independent rank-p evidence and the exact
five-window outcome join are now complete. All 43,883 ON records are
physically vetoed—41,863 by single-adjacent-OFF evidence, 1,318 by exact OFF
and 702 by local OFF—and zero unresolved candidates remain. Run 006 therefore
reports `closed_no_unresolved_scientific_candidates` for this one primary
cadence and frozen search model. Detector completeness remains pending, so M37
does not yet provide a quantitative sensitivity or occurrence-rate bound.

Milestone 35 provides the latest survey-level synthesis. At exact ideal S/N 40
its finite-injection pointwise 95% upper bound on `f(40)` is 33.16%, where
`f(40)` is the common archive-cohort system-occurrence probability for the
frozen injected class. Under the common independent-occurrence and
independent-injection-trial models, it is additionally conditional on the
randomized-background model and on score recoveries surviving every downstream
candidate stage. If either sensitivity-transport condition is not imposed,
the only supported end-to-end upper bound is the trivial 100%. The repository
preserves frozen configurations, checksummed results, technical aborts,
post-hoc labels, and non-redetections so that positive and negative outcomes
remain independently auditable.

Version 0.5.0 is the frozen detector used through the Milestone 36 search. It
retains the Milestone 7 recurrence statistic, spectral filters, per-epoch
interference mask, candidate clustering, and RFI-family flags, and adds the
Milestone 12 local-OFF and receiver-frame alias vetoes. Detector v0.6 is the
separate Milestone 37 implementation used by the authorized run. Its frozen
capacity rule, rather than a candidate disposition, determined the invalid
outcome.

## Milestone 37 invalid run, amendment and closed Run 006 outcome

Milestone 37 selected HD 156668 / HIP 84607 at extension rank 37. HD 156668 b
supplies only the motion template. The metadata-only coverage proof and the
prospective detector-v0.6 discrete-bank preflight are published. The new bank
uses 93 motion templates and eight spectral widths to preserve coverage for
the higher-smearing target without inspecting telescope spectral values.

The v0.6 production path includes resumable identity-bound range transport,
native-channel filtering, exhaustive retention, OFF and adjacent-OFF evidence,
receiver-frame alias handling, global rank-p significance, immutable
persistence artifacts and a hash-chained run journal. Before production, the
synthetic checkpoints exercised the full downstream contracts and resource
envelopes.

The current complete local suite runs 306 tests with one expected benchmark
skip and no failures. Run 004 independently reopened every sparse-mirror
segment, published 30 normalized window/scan products and verified
11,545,072,128 cache-payload bytes. Its five calibration windows evaluated
14,880 hypotheses and 2,848,065,331,200 null score cells. The exact 256-member
global null yielded inclusive rank-p 0.01556420233463035 at the operational
threshold.

Retention was parallelized by independent frequency window without changing
the artifact schema or hypothesis order. Four window artifacts completed with
1,800, 218, 225 and zero ON records. An exact replay located the first capacity
overflow in the remaining window at template 4, width 129, epochs `[0, 1]`:
8,925 prior records plus 1,101 in that hypothesis gave a lower bound of 10,026.
The journal was permanently advanced to `invalid` with reason
`retention-capacity-overflow`.

The frozen protocol forbids truncation and threshold adaptation. The partial
window artifacts cannot support candidate, null, sensitivity or population
claims. Any new attempt requires a separately documented run and must preserve
the Run 004 invalid result.

The subsequent diagnostic-only census evaluated all 22,250,510,400 ON/OFF
score cells and sealed ten restartable child ledgers. The complete counts are
ON/OFF 1,800/1,720, 218/232, 225/208, 41,640/0 and 0/0. The overflow is one
dense score-space feature: every record uses width 129, all lie in
1,419,340,000--1,419,360,000 Hz census buckets, and none reaches 1.25 times the
frozen threshold. No candidate records or veto dispositions were produced.

The explicitly post-contact, capacity-only v0.6.1 amendment raised the
per-window record limit to 50,000 and proportionally raised evidence and
downstream work envelopes. Threshold, grid, template bank, widths, activity
subsets, vetoes and the immutable Run 004 journal remained unchanged. Run 006
completed all ten normative retention ledgers and exactly reproduced the
census counts.

Complete physical disposition then classified all 43,883 retained ON records.
The dense 1418.5 MHz feature's 41,640 members all have qualifying frozen
single-adjacent-OFF evidence. Independent global rank-p evaluation found
43,741 statistically eligible records, but statistical eligibility cannot
override a physical veto. The receipt-bound outcome join therefore contains
zero `scientific_candidate_unresolved` records and closes the M37 primary
cadence as `closed_no_unresolved_scientific_candidates`. See
`MILESTONE_37_V0P6P1_OUTCOME_RESULT.md`.

## Milestone 36 result

Milestone 36 searched the sole complete compatible HIP 48714 cadence using
HIP 48714 b only as a motion template. The detector-v0.5 primary search
reported 1,676 clusters; 239 exceeded the frozen operational threshold and
all received a physical control disposition.

A later review found that the upstream v0.5 collector was not an exhaustive
above-threshold recorder. A separately frozen retrospective audit therefore
replayed the same 30 checksummed extracts without changing the primary
threshold, significance, or completeness result. It visited all
1,202,587,680 frozen score cells and accounted for all 7,571 cells at or above
threshold. The complete audit contains 1,081 member records in 637 clusters,
with zero unaccounted cells, zero unresolved members, and zero unresolved
clusters. The published outcome is
`PRIMARY_CADENCE_NULL_AFTER_COMPLETE_RETENTION_AUDIT`.

This is a null result for one archive cadence under the frozen search model,
not evidence that no transmitter exists. No second qualifying HIP 48714
cadence was identified, and the unresolved Milestone 33 case is unchanged.

## Milestone 35 result

Milestone 35 retrospectively combined the complete M14--M33 detector-v0.5
cohort in the only frequency interval with a matched injection background,
1412.0--1413.0 MHz. Across 20 systems, all 267 matched-band clusters are fully
retained. Forty-nine exceed their target thresholds, 48 have frozen physical
vetoes, and M16 is conservatively counted as one candidate-positive system
despite its later independent-cadence non-redetection.

Using exact target-specific Poisson-binomial tails, the nominal plug-in upper
limit at exact ideal single-epoch S/N 40 is 23.06%. A split-alpha construction
that also accounts for the 32 finite injection trials per target gives a
pointwise 95% upper bound of 33.16%. Those 32 trials are per target at that
exact S/N level; each target has 224 trials over all seven levels. No
non-trivial bound exists at S/N 8.

These are conditional score-recovery results, not unconditional transmitter
occurrence limits. Completeness averages the frozen truth-frequency and
randomly shifted empirical-background generator and does not execute the
downstream clustering, retention, veto, or adjudication stages. If either
relationship is not assumed, the documented efficiency lower bound is zero
and the occurrence upper bound is 100%. No candidate status changes; the
unresolved Milestone 33 case remains outside the matched 1412 MHz outcome.

## Milestone 34 result

Milestone 34 reran the legacy Milestone 17 GJ 849 and Milestone 21 HD 154345
primary cadences with the sole configuration change
`max_report_clusters: 50 -> 500`. All 30 extracted-slice hashes per target and
all cap-independent search results reproduced. The complete lists contain 776
clusters, of which 177 exceed their unchanged primary thresholds.

The audit exposed 17 previously omitted above-threshold clusters: 14 in the
capped GJ 849 1400 MHz list and three in the corresponding HD 154345 list.
Every one has the frozen matched-OFF physical veto. The audit creates zero new
open cases and changes zero published dispositions. Seven already published
M17 clusters gain only the non-physical arithmetic-family annotation. No
reserved or independent cadence was opened, and the unresolved Milestone 33
case is unchanged.

## Milestone 33 result

Milestone 33 completed the eligible targets in the frozen higher-smearing
ranks 31--35 extension by searching HD 3651 / HIP 3093 at rank 34. HD 3651 b
supplied only the motion template. A width-aware metadata proof passed all 630
checks before spectral contact, and the blind search used the sole complete
compatible L-band cadence `--73274` with the unchanged six-width bank.

Across approximately 901,940,760 nominal trials, the global maximum reached
S/N 3873.2958 at 1406.087976374 MHz, with empirical global p-value 1/257 and
an operational threshold of S/N 10.3294. All 951 retained clusters are
reported. Eighteen exceeded threshold: two have strong local-control
recurrence and 15 map to recurring receiver-frame features. The remaining
weak 1424.934238382 MHz arithmetic-family case passed a separately frozen
six-scan morphology review and remains unresolved because no independent HD
3651 cadence exists. It is not a detection or technosignature claim. Estimated
multichannel 50% and 90% recovery occur near ideal single-epoch S/N 13.82 and
19.40; the corresponding one-channel estimates are 19.00 and 35.20.

## Milestone 32 result

Milestone 32 advanced the frozen higher-smearing ranking to HD 99492 /
HIP 55848 at extension rank 33 after rank 32 proved ineligible. HD 99492 b
supplied only the motion template. A width-aware metadata proof passed all 630
checks before spectral contact, and the blind search used the sole complete
compatible L-band cadence `--70969` with the unchanged six-width bank.

Across approximately 888,730,920 nominal trials, the global maximum reached
S/N 3388.1311 at 1400.167769733 MHz, with empirical global p-value 1/257 and
an operational threshold of S/N 10.9827. All 691 retained clusters are
reported. Fourteen exceeded threshold: five matched control data on the
candidate track, seven had a frozen local-control recurrence, and two mapped
to the same receiver-frame feature. All 14 are physically vetoed and no
candidate survives. Estimated multichannel 50% and 90% recovery occur near
ideal single-epoch S/N 15.50 and 20.80; one-channel recovery reaches 81.25%
at the highest tested S/N 40 and does not measure a 90% point.

## Milestone 31 result

Milestone 31 prospectively extended the frozen survey beyond the original 1
Hz/s conservative smearing group. The header-only screen selected HD 192263 /
HIP 99711 at extension rank 31; HD 192263 b supplied only the motion template.
A width-aware metadata proof passed all 630 checks before spectral contact,
and the blind search used the sole complete compatible L-band cadence
`--66435` with the frozen six-width bank `[1, 3, 5, 9, 17, 33]`.

Across approximately 901,940,760 nominal trials, the global maximum reached
S/N 33.1947 at 1400.335505150 MHz, with empirical global p-value 2/257 and an
operational threshold of S/N 13.2003. All 583 retained clusters are reported.
Eleven exceeded threshold; six matched the control data on the candidate track
and five had a recurrent control feature within the frozen 20 Hz tolerance.
All 11 are physically vetoed and no candidate survives. Estimated
multichannel 50% and 90% recovery occur near ideal single-epoch S/N 22.25 and
29.16; one-channel recovery reaches only 15/32 at the highest tested S/N 40.

## Milestone 30 result

Milestone 30 searched bet UMi / HIP 72607 using bet UMi b only as the
motion template and the sole complete compatible L-band cadence \`--74586\`.
The metadata-only coverage proof passed all 630 checks before any spectral
value was read.

Across approximately 601,293,840 nominal trials, the global maximum reached
S/N 26.0639 at 1425.047656707 MHz, with empirical global p-value 1/257 and an
operational threshold of S/N 11.2187. All 309 retained clusters are reported.
Twenty-five exceeded threshold; 18 matched the control data on the candidate
track and seven had a recurrent control feature within the frozen 20 Hz local
tolerance. The strongest event had control S/N 19.5502 only 5.588 Hz away.
All 25 are physically vetoed and no candidate survives. Estimated
multichannel 50% and 90% recovery occur near ideal single-epoch S/N 13.26 and
15.96.

## Milestone 29 result

Milestone 29 completed the frozen rank 26-30 header screen and selected HD
11964 at rank 28 after ranks 26 and 27 proved to be S-band. The held-out search
used HD 11964 b only as the motion template and the sole complete compatible
L-band cadence `--66653`. Rank 29 bet UMi retains one untouched compatible
L-band cadence for a later milestone.

Across approximately 601,293,840 nominal trials, the global maximum reached
S/N 13.7849 at 1400.038687989 MHz, with empirical global p-value 1/257 and an
operational threshold of S/N 7.5677. Twenty-one of 23 above-threshold clusters
received the frozen single-adjacent-control veto. Two weak 1425 MHz
arithmetic-family cases entered a separately frozen morphology review; both
mapped to the identical receiver feature in all three ON scans and had an
adjacent-control peak within 16.764 Hz. All 344 clusters were retained, all 23
above-threshold cases are physically vetoed, and there is no surviving
candidate. Multichannel completeness reaches estimated 50% and 90% recovery
near ideal single-epoch S/N 9.78 and 11.67.

## Milestone 28 result

Milestone 28 advanced the frozen rank 21-25 screen to psi1 Dra B at rank 24.
The held-out search used psi1 Dra B b only as the motion template and the sole
complete compatible L-band cadence `--84027` after a successful 630-case
coverage proof.

Across approximately 592,487,280 nominal trials, the global maximum reached
S/N 184.8547 at 1400.052203120 MHz, with empirical global p-value 1/257 and an
operational threshold of S/N 10.5659. All 196 clusters above threshold are
reproduced by exact matched-OFF, local-OFF, or single-adjacent-OFF evidence;
all 296 clusters were retained, and there is no surviving candidate.
Multichannel completeness reaches estimated 50% and 90% recovery near ideal
single-epoch S/N 12.94 and 15.95. The frozen screen contains no second
compatible L-band cadence for independent recurrence.

## Milestone 27 result

Milestone 27 advanced the frozen rank 21-25 screen to HD 127506 at rank 23.
The held-out search used the selected planet hypothesis only as the motion
template and cadence `--83509` after the metadata-only coverage proof.

Across approximately 601,293,840 nominal trials, the global maximum reached
S/N 102,410.8607 at 1406.485088594 MHz, with empirical global p-value 1/257
and an operational threshold of S/N 8.7488. All 18 clusters above threshold
are reproduced by exact matched-OFF or local-OFF evidence; all 299 clusters
were retained, and there is no surviving candidate. Multichannel
completeness reaches estimated 50% and 90% recovery near ideal single-epoch
S/N 11.11 and 14.93; the corresponding one-channel estimates are 13.71 and
23.20.

## Milestone 26 result

Milestone 26 advanced the frozen rank 21-25 screen to HD 19994 at rank 22.
The held-out search used HD 19994 b only as the motion template and the sole
complete compatible L-band cadence `--84358` after a successful 630-case
coverage proof.

Across approximately 592,487,280 nominal trials, the global maximum reached
S/N 644.9192 at 1406.437003620 MHz, with empirical global p-value 1/257 and an
operational threshold of S/N 12.7328. All 52 clusters above threshold are
reproduced by exact matched-OFF or local-OFF evidence; all 353 clusters were
retained, and there is no surviving candidate. Multichannel completeness
reaches estimated 50% and 90% recovery near ideal single-epoch S/N 15.75 and
19.37. One-channel recovery reaches 87.5% at S/N 40 and does not cross 90% on
the frozen grid.

## Milestone 25 result

Milestone 25 extended the frozen target ranking to positions 21-25. The
header-only screen selected HD 164922 at rank 21 and preserved compatible
L-band cadences for ranks 22-24 without spectral contact. The held-out search
used HD 164922 b only as the motion template and cadence `--84744` after a
successful 630-case coverage proof.

Across approximately 592,487,280 nominal trials, the global maximum reached
S/N 78.6024 at 1406.207696457 MHz, with empirical global p-value 1/257 and an
operational threshold of S/N 8.0080. All 83 clusters above threshold receive
frozen matched-OFF, local-OFF, receiver-frame-alias, or single-adjacent-OFF
vetoes. All 216 clusters were retained, and there is no surviving candidate.
The multichannel completeness grid places 50% and 90% recovery near ideal
single-epoch S/N 9.86 and 11.69.

## Milestone 24 result

Milestone 24 applied detector v0.5.0 to the sole complete compatible GBT
L-band cadence for 16 Cyg B, using 16 Cyg B b only as the motion template.
Across approximately 601,293,840 nominal trials, the global maximum reached
S/N 54.2691 at 1400.117483467 MHz, with empirical global p-value 1/257 and an
operational threshold of S/N 40.3396.

All nine clusters above that threshold are reproduced by exact matched-OFF,
local-OFF, or single-adjacent-OFF evidence and receive the frozen physical
interference vetoes. All 388 clusters were retained without a report-cap
audit. There is no surviving candidate. The heavy-tailed 1400 MHz interference
also limits sensitivity: the preregistered injection grid reaches only 5/32
recoveries at ideal single-epoch S/N 40 and does not measure a 50% recovery
point. No second qualifying 16 Cyg B cadence exists in the frozen screen.

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

The Milestone 34 complete report-cap audit retained all 372 clusters. Of 113
above-threshold clusters, 95 receive matched-OFF vetoes, 16 receive
single-adjacent-OFF vetoes, and the two exact previously reviewed cases retain
their `RFI_OR_INSTRUMENTAL` resolutions. No M21 case remains open.

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
within 11.176 Hz. The Milestone 34 complete report-cap audit retained all 404
clusters: 64 exceed threshold, including 14 previously omitted by the
50-cluster cap, and all 64 receive the same physical OFF-source disposition.
The remaining 340 are below threshold. There is no surviving candidate and no
technosignature claim. The complete cadence reserved six days later was
therefore not opened spectrally.

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

- Milestone 26 searched five 1 MHz windows in one HD 19994 cadence, not the
  full GBT L-band receiver range or independent observing nights.
- Its 52 over-threshold clusters are all rejected by frozen matched-OFF or
  local-OFF vetoes.
- No second complete compatible HD 19994 L-band cadence was present; its other
  frozen cadence is S-band.
- Milestone 25 searched five 1 MHz windows in one HD 164922 cadence, not the
  full GBT L-band receiver range or independent observing nights.
- Its 83 over-threshold clusters are all rejected by frozen physical OFF or
  receiver-frame vetoes.
- No second complete compatible HD 164922 L-band cadence was present; its
  other frozen cadence is S-band.
- Milestone 24 searched five 1 MHz windows in one 16 Cyg B cadence, not the
  full GBT L-band receiver range or independent observing nights.
- Its nine over-threshold clusters are all rejected by frozen physical OFF
  vetoes, but 1400 MHz interference raises the global threshold to S/N 40.34.
- The Milestone 24 completeness grid does not reach 50% recovery through ideal
  single-epoch S/N 40, so the null result has limited sensitivity.
- No second complete compatible 16 Cyg B cadence was present in the frozen
  public header screen.
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
- Its complete Milestone 34 audit retained 372 clusters and closed all 113
  above-threshold cases, including three previously omitted by the old cap.
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
- Its complete Milestone 34 audit retained 404 clusters and physically vetoed
  all 64 above-threshold cases, including 14 previously omitted by the old cap.
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

- `MILESTONE_37_V0P6P1_OUTCOME_RESULT.md` — Run 006 physical, rank-p and closed primary-cadence outcome.
- `MILESTONE_37_V0P6P1_SIGNIFICANCE_OUTCOME_PLAN.md` — frozen post-physical adjudication plan.
- `results_m37_v0p6p1_primary_006/outcome-summary.json` — machine-readable Run 006 adjudication summary.
- `results_m37_v0p6p1_primary_006/outcome.json.gz` — complete canonical five-window outcome.
- `results_m37_v0p6p1_primary_006/significance-manifest.json` — complete rank-p child inventory and counts.
- `results_m37_v0p6p1_primary_006/physical-disposition-manifest.json` — complete physical child inventory and counts.
- `scripts/m37_v0p6p1_significance_outcome.py` — restartable significance/outcome continuation.
- `MILESTONE_37_PRIMARY_CAPACITY_RESULT.md` — authorized spectral execution and fail-closed capacity result.
- `results_m37_v0p6_primary_004/result.json` — machine-readable Run 004 summary.
- `results_m37_v0p6_primary_004/retention-capacity-failure.json` — exact immutable overflow evidence.
- `results_m37_v0p6_primary_004/final-journal-event.json` — terminal invalidation event.
- `RESULTS_MANIFEST_M37_PRIMARY_004.sha256` — report and result identities.
- `scripts/m37_v0p6_parallel_retention.py` — restartable parallel window retention.
- `scripts/m37_v0p6_capacity_diagnostic.py` — deterministic capacity-failure replay and invalidation.
- `MILESTONE_37_TARGET_SELECTION.md` — fixed HD 156668 target and untouched cadence.
- `MILESTONE_37_COVERAGE_PREFLIGHT_PLAN.md` — continuous motion-plus-width proof.
- `MILESTONE_37_DETECTOR_V0P6_BANK_PREFLIGHT_PLAN.md` — prospective v0.6 bank.
- `MILESTONE_37_DETECTOR_V0P6_IMPLEMENTATION_READINESS.md` — non-frozen implementation audit.
- `MILESTONE_37_DETECTOR_V0P6_RUNNER_PROGRESS.md` — metadata-only bootstrap progress.
- `results_m37_v0p6_runner_progress/progress.json` — machine-readable M37 status.
- `MILESTONE_37_DETECTOR_V0P6_STREAMING_EVIDENCE_CHECKPOINT.md` — width-streaming evidence checkpoint.
- `results_m37_v0p6_streaming_evidence/progress.json` — machine-readable streaming status.
- `MILESTONE_37_DETECTOR_V0P6_SPARSE_RETENTION_CHECKPOINT.md` — bounded phase-2 retention/OFF/rank reference.
- `results_m37_v0p6_sparse_retention/progress.json` — machine-readable phase-2 status.
- `MILESTONE_37_DETECTOR_V0P6_PHYSICAL_REFERENCE_CHECKPOINT.md` — bounded phase-3 adjacent-OFF/receiver-alias reference.
- `results_m37_v0p6_physical_reference/progress.json` — machine-readable phase-3 status.
- `MILESTONE_37_DETECTOR_V0P6_RESOURCE_ENVELOPE_CHECKPOINT.md` — bounded aggregate physical-evidence resource checkpoint.
- `results_m37_v0p6_resource_envelope/progress.json` — machine-readable resource-envelope status.
- `MILESTONE_37_DETECTOR_V0P6_RESOURCE_PERSISTENCE_CHECKPOINT.md` — restartable synthetic resource-artifact checkpoint.
- `results_m37_v0p6_resource_persistence/progress.json` — machine-readable resource-artifact persistence status.
- `MILESTONE_37_DETECTOR_V0P6_RESOURCE_RUN_MANIFEST_CHECKPOINT.md` — ordered restartable resource run-inventory checkpoint.
- `results_m37_v0p6_resource_run_manifest/progress.json` — machine-readable resource run-manifest status.
- `MILESTONE_36_REPORT.md` — primary result and exhaustive audit interpretation.
- `MILESTONE_36_PREREGISTRATION.md` — frozen HIP 48714 search design.
- `MILESTONE_36_EXHAUSTIVE_RETENTION_AUDIT_PLAN.md` — complete-retention protocol.
- `results_m36/search_summary.json` — primary machine-readable search record.
- `results_m36_exhaustive_retention_audit/audit_summary.json` — complete audit result.
- `MILESTONE_35_SURVEY_SYNTHESIS_PLAN.md` — frozen retrospective analysis plan.
- `config/m35_survey_synthesis.json` — input hashes, cohorts, and assumptions.
- `scripts/m35_survey_synthesis.py` — fail-closed accounting and statistics.
- `results_m35_survey_synthesis/analysis_summary.json` — machine-readable result.
- `results_m35_survey_synthesis/occurrence_bounds.csv` — exact bound table.
- `results_m35_survey_synthesis/score_recovery_bounds.png` — primary comparison.
- `RESULTS_MANIFEST_M35_SURVEY_SYNTHESIS.sha256` — all seven result hashes.
- `MILESTONE_35_REPORT.md` — scope, results, and interpretation limits.
- `MILESTONE_33_TARGET_SELECTION.md` — fixed HD 3651 target and cadence.
- `MILESTONE_33_SELECTED_METADATA_RESULT.md` — official orbit and astrometry.
- `MILESTONE_33_PREREGISTRATION.md` — frozen higher-smearing search design.
- `MILESTONE_33_CANDIDATE_INVESTIGATION_PLAN.md` — fixed post-hoc protocol.
- `MILESTONE_33_CANDIDATE_INVESTIGATION.md` — unresolved six-scan review.
- `MILESTONE_33_REPORT.md` — final result, open case, and sensitivity limits.
- `config/hd3651b_heldout_m33.json` — frozen target, cadence, bands, and widths.
- `DATA_MANIFEST_M33.sha256` — checksums for all 30 primary extracts.
- `RESULTS_MANIFEST_M33.sha256` — checksums for all nine primary outputs.
- `results_m33/search_summary.json` — complete machine-readable search record.
- `MILESTONE_32_TARGET_SELECTION.md` — fixed HD 99492 target and cadence.
- `MILESTONE_32_SELECTED_METADATA_RESULT.md` — official orbit and astrometry.
- `MILESTONE_32_PREREGISTRATION.md` — frozen higher-smearing search design.
- `MILESTONE_32_REPORT.md` — final no-survivor result and sensitivity limits.
- `config/hd99492b_heldout_m32.json` — frozen target, cadence, bands, and widths.
- `DATA_MANIFEST_M32.sha256` — checksums for all 30 reproducible extracts.
- `RESULTS_MANIFEST_M32.sha256` — checksums for all nine primary outputs.
- `results_m32/search_summary.json` — complete machine-readable search record.
- `MILESTONE_31_HEADER_SCREEN_PLAN.md` — frozen ranks 31-35 extension.
- `MILESTONE_31_TARGET_SELECTION.md` — fixed HD 192263 target and cadence.
- `MILESTONE_31_SELECTED_METADATA_RESULT.md` — official orbit and astrometry.
- `MILESTONE_31_PREREGISTRATION.md` — frozen higher-smearing search design.
- `MILESTONE_31_REPORT.md` — final no-survivor result and sensitivity limits.
- `config/hd192263b_heldout_m31.json` — frozen target, cadence, bands, and widths.
- `DATA_MANIFEST_M31.sha256` — checksums for all 30 reproducible extracts.
- `RESULTS_MANIFEST_M31.sha256` — checksums for all nine primary outputs.
- `results_m31/search_summary.json` — complete machine-readable search record.
- `MILESTONE_26_TARGET_SELECTION.md` — fixed HD 19994 target and cadence.
- `MILESTONE_26_SELECTED_METADATA_RESULT.md` — official orbit and astrometry.
- `MILESTONE_26_PREREGISTRATION.md` — frozen held-out search design.
- `MILESTONE_26_REPORT.md` — final no-survivor result and limits.
- `config/hd19994b_heldout_m26.json` — frozen target, cadence, orbit, and bands.
- `DATA_MANIFEST_M26.sha256` — checksums for all 30 reproducible extracts.
- `RESULTS_MANIFEST_M26.sha256` — checksums for all nine primary outputs.
- `results_m26/search_summary.json` — complete machine-readable search record.
- `MILESTONE_25_HEADER_SCREEN_PLAN.md` — frozen ranks 21-25 extension.
- `MILESTONE_25_TARGET_SELECTION.md` — fixed HD 164922 target and cadence.
- `MILESTONE_25_SELECTED_METADATA_RESULT.md` — official orbit and astrometry.
- `MILESTONE_25_PREREGISTRATION.md` — frozen held-out search design.
- `MILESTONE_25_REPORT.md` — final no-survivor result and limits.
- `config/hd164922b_heldout_m25.json` — frozen target, cadence, orbit, and bands.
- `DATA_MANIFEST_M25.sha256` — checksums for all 30 reproducible extracts.
- `RESULTS_MANIFEST_M25.sha256` — checksums for all nine primary outputs.
- `results_m25/search_summary.json` — complete machine-readable search record.
- `MILESTONE_24_TARGET_SELECTION.md` — fixed 16 Cyg B target and cadence.
- `MILESTONE_24_SELECTED_METADATA_RESULT.md` — official orbit and astrometry.
- `MILESTONE_24_PREREGISTRATION.md` — frozen held-out search design.
- `MILESTONE_24_REPORT.md` — final no-survivor result and sensitivity limits.
- `config/16cygbb_heldout_m24.json` — frozen target, cadence, orbit, and bands.
- `DATA_MANIFEST_M24.sha256` — checksums for all 30 reproducible extracts.
- `RESULTS_MANIFEST_M24.sha256` — checksums for all nine primary outputs.
- `results_m24/search_summary.json` — complete machine-readable search record.
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
