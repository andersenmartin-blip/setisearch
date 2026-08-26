# Milestone 33 report: HD 3651 b higher-smearing held-out search

Status: **FOLLOW-UP REQUIRED — 17 OF 18 ABOVE-THRESHOLD CLUSTERS ARE
PHYSICALLY VETOED; ONE CASE REMAINS UNRESOLVED; NO DETECTION CLAIM**.

Milestone 33 searched the sole complete compatible HD 3651 L-band cadence
with frozen detector v0.5.0 and retained all 951 frequency clusters. Eighteen
clusters exceeded the empirical global threshold. Two have strong local
control recurrence, 15 map to recurring receiver-frame features, and one weak
1424.934238382 MHz arithmetic-family case remains unresolved after the
separately frozen morphology review.

HD 3651 b supplies only the motion template. This search neither assumes nor
tests that a transmitter is located on the planet. The unresolved case is a
request for independent data, not a technosignature or detection claim.

## Frozen target and data

Milestone 33 advanced the already frozen higher-smearing target order. HD
192263 at rank 31 and HD 99492 at rank 33 were consumed by Milestones 31 and
32; rank 32 had no qualifying cadence. HD 3651 / HIP 3093 at rank 34 was the
next eligible untouched host. Rank 35 had no compatible L-band cadence, so
this also completes the eligible targets in the frozen ranks 31--35 extension.

HD 3651 b's conservative full-projection periastron proxy is 2.27163433 Hz/s
at 1425 MHz. The `[1, 3, 5, 9, 17, 33]`-channel higher-smearing bank,
non-truncating 1600-cluster report cap, 21 motion templates, four activity
subsets, control-field vetoes, 256 scrambles, and completeness procedure were
fixed before any spectral value was read.

The primary archive cadence is `--73274`, beginning MJD
57557.577152777776 (2016-06-18 13:51:06 UTC), with the sequence:

`HIP3093 -- HIP2023 -- HIP3093 -- HIP2206 -- HIP3093 -- HIP2360`.

All six scans have 16 integrations of 18.253611008 s and 2.793967724 Hz
channels. The metadata-only motion-plus-width proof passed all 630 checks.
It included the 16-channel half-width of the widest filter; the smallest
extraction-edge headroom after motion and width margins was 163,266 channels,
approximately 456.130 kHz.

## Blind search result

Detector v0.5.0 searched five disjoint 1 MHz planet-frame bands with 21 motion
templates, four activity subsets, and six spectral widths: approximately
**901,940,760 nominal trials**. The 256 complete scrambles gave:

- observed global maximum: S/N **3873.2958205244836**;
- empirical global p-value: **1/257 = 0.0038910505836575876**;
- null median: S/N **8.828831672668457**;
- operational global threshold: S/N **10.329352378845215**.

The minimum empirical p-value shows that the cadence contains extremely
strong structured features. It does not override physical control evidence
and does not establish an astrophysical or artificial origin.

| Window | Retained clusters | Above threshold | Maximum S/N | Maximum frequency (MHz) | Above-threshold disposition |
|---|---:|---:|---:|---:|---|
| `m33_1400p5` | 49 | 1 | 3394.304518 | 1400.229275703 | local-control veto |
| `m33_1406p5` | 23 | 1 | 3873.295821 | 1406.087976374 | local-control veto |
| `m33_1412p5` | 64 | 0 | 9.358722 | 1412.296750024 | below threshold |
| `m33_1418p5` | 275 | 0 | 9.927665 | 1418.975396402 | below threshold |
| `m33_1425p0` | 540 | 16 | 10.960506 | 1425.127376989 | 15 receiver aliases; 1 unresolved |

Complete frozen accounting is therefore:

- 933 below the global threshold;
- 2 `rfi_veto_local_off_source`;
- 15 `rfi_veto_receiver_frame_alias`;
- 1 `rfi_family_veto_pending_manual_review`, subsequently classified
  `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE` by the fixed post-hoc protocol.

## Strongest events and physical vetoes

The global maximum at 1406.087976373732 MHz uses the 33-channel boxcar and
template 5 and is active in ON epochs 1 and 3. A control feature under the
same motion template reaches S/N **14989.147348565468** only
**2.793967724 Hz** away. The 1400.229275703430 MHz maximum is similarly
reproduced in control data at S/N **10508.485818170819**, also one native
channel away. Both receive the frozen local-control veto.

All 15 automatically vetoed 1425 MHz clusters map to recurring
receiver-frame features in at least two claimed active epochs within the
frozen 20 Hz tolerance. Their low excesses above threshold do not survive the
physical alias check.

## Unresolved 1424.934238 MHz case

The remaining case has frozen recurrence S/N 10.728838, uses template 15,
projected scale 0.75, phase +0.2 cycles, the 33-channel width, and all three ON
epochs. Its ON track values are S/N 7.6967, 6.4577, and 6.1943.

The separately frozen post-hoc review reproduced the track in every ON scan.
The three adjacent-control track values are only S/N 4.2468, 4.7200, and
3.2022. The nearest qualifying stationary OFF peaks are 173.226 and 203.960
Hz from their paired ON features; the middle OFF scan has no stationary peak
at or above S/N 5.5. None lies within the fixed 20 Hz tolerance, and no
cross-candidate receiver alias exists. The case therefore remains formally
unresolved. Full measurements are recorded in
`MILESTONE_33_CANDIDATE_INVESTIGATION.md`.

The public header screen contains no second qualifying HD 3651 cadence. A new
independent observation is required to test recurrence. Milestone 33 cannot
close as an unqualified null result while this case remains open.

## Measured completeness

Completeness injections used real `m33_1412p5` background, 32 trials per
level, active epochs 1 and 3, four exact truth templates spanning the
higher-smearing bank, and frozen seed `332120260826`.

| Ideal single-epoch S/N | Multichannel recovered | One-channel recovered |
|---:|---:|---:|
| 8 | 0/32 | 0/32 |
| 12 | 11/32 | 8/32 |
| 16 | 22/32 | 13/32 |
| 20 | 30/32 | 17/32 |
| 24 | 32/32 | 19/32 |
| 32 | 32/32 | 28/32 |
| 40 | 32/32 | 30/32 |

Linear interpolation between tested levels gives approximate multichannel
50% and 90% recovery at ideal single-epoch S/N **13.82** and **19.40**. The
corresponding one-channel estimates are **19.00** and **35.20**. These are
grid interpolations for exact bank templates active in epochs 1 and 3, not
confidence bounds or guarantees for other activity patterns and orbital-model
errors.

## Scope and interpretation

- The search covers five disjoint bands totaling 5 MHz, not the full receiver
  band.
- All three ON scans belong to one approximately 29-minute cadence, not
  independent observing nights.
- The empirical p-value measures departure from the circular-shift null;
  structured RFI can produce the same departure.
- Arithmetic-frequency family membership and the selected 33-channel width
  are cautionary context, not physical vetoes.
- The unresolved case has no independent recurrence evidence, and no
  technosignature claim is made.
- Any null constraint applies only to the other frozen hypotheses, searched
  bands, cadence, signal model, and measured completeness.

## Reproducibility

The preregistration commit is
`e8f23e58e00cc57d26db03c06869ea3a2b06f5fa`; the primary execution commit is
`5579899a1d86bfb302ec225073826e91f5f66c26`; and the primary result publication
commit is `fd5a11afdba3774554a3d55fcad2f82ee7be6569`. Workflow run `32939248755`
published artifact `9596493002` with digest
`sha256:ef34b8150f37410b0c9d3ad51d3add7474d671ca3cd7cce0c167d0ff61713f0a`.

The candidate-investigation protocol is commit
`8b1481d6fbeed1bf3bf857b2954af80ef519014c`; its execution commit is
`b911d172d417848cfc4354ef5f9382252538e772`, and its result publication commit
is `724e03aa26073c94c40f343ac86cc675c5c30828`. Workflow run `32941363711`
published artifact `9596661263` with digest
`sha256:076f469c0d4b3fe3d6f89f244316149093f10b782d21243a4792345d44be11c1`.

The frozen configuration SHA-256 is
`aaf4e2d53a4b95bb4428195d2567b9d3a8f8f60b62de104d8879c018b320971a`.
The primary search-summary SHA-256 is
`8bcc1b7fc2177d93b7a7ef47e7ec9bbe47e8ccc53d38fe7529ae49e389d8ab2b`;
the candidate-investigation SHA-256 is
`6430df53e2dbba2757db0b629926ceb71967b2734a7f43e097ffbe83aefc48ef`.
Primary and investigation data manifests identify 30 and six reproducible
extracts; their result manifests identify nine and four published outputs.
Extracted telescope slices are not committed.

Publication verification is appended after an independent workflow has
revalidated both result sets, complete primary and post-hoc accounting,
execution provenance, and this report.
