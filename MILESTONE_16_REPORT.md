# Milestone 16 report: HD 219134 held-out detector-v0.5 search

Status: **FOLLOW-UP REQUIRED — one automated survivor and one manual RFI-family case; no detection claim**.

Milestone 16 applied frozen detector v0.5.0 to a previously unused public HD
219134 cadence after the preregistered target discovery, corrected HDF5-header
screen, official selected-target metadata query, and a successful 630-case
extraction-coverage proof. HD 219134 h supplies only the motion template; the
search does not assume that an emitter is located on the planet.

GitHub Actions run `32558092616` completed all detector tests, 30 HDF5
extractions, five searches, 256 global scrambles, and the preregistered
completeness study. The result artifact is `9472228098`, digest
`sha256:6f561293a71238c23e2497f788d4a6b6cd068f4486754d6a88464b545c88f0ff`.

## Global result

Across approximately **601,293,840** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 9.1455** at 1412.485745177 MHz;
- scrambled-null median: **S/N 6.4460**;
- scrambled-null 99th percentile and operational threshold: **S/N 7.4288**;
- empirical global p-value: **1/257 = 0.003891**; and
- pipeline assessment: **FOLLOW-UP REQUIRED**.

The p-value is the smallest rank resolvable by 256 scrambles. It means that the
observed maximum exceeded every scrambled maximum under this particular null;
it is not a Gaussian-sigma conversion and does not establish an astrophysical
or artificial origin. Structured RFI or an instrumental feature can also
produce a low empirical rank.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 7.923 | 1400.300845981 | 9 | 8.481 | 0.003891 | local-OFF veto |
| 1406.0-1407.0 | 5.696 | 1406.920369208 | 9 | 5.713 | 0.529183 | below threshold |
| 1412.0-1413.0 | 9.145 | 1412.485745177 | 9 | 5.306 | 0.003891 | survives for follow-up |
| 1418.0-1419.0 | 5.500 | 1418.469238415 | 3 | 5.490 | 0.887160 | below threshold |
| 1424.5-1425.5 | 7.478 | 1425.136278570 | 9 | 7.174 | 0.007782 | arithmetic-family review |

The 1400 MHz maximum is independently rejected by a nearby OFF-bank
recurrence. The 1406 and 1418 MHz maxima remain below the global operational
threshold. The 1412 MHz maximum is the sole automated survivor. The 1425 MHz
maximum is handled separately as an unresolved RFI-family morphology case.

## Automated follow-up survivor

The surviving cluster has the following frozen measurements:

| Quantity | Value |
|---|---|
| Planet-frame frequency | 1412.485745177 MHz |
| Recurrence S/N | 9.1455 |
| Selected boxcar | 9 channels (approximately 25.146 Hz) |
| Projected scale / phase | 0.75 / +0.1 cycles |
| Active ON epochs | 1 and 2 |
| ON epoch values at the selected frequency | 14.577, 6.467, 1.308 |
| OFF values on the same candidate track | 0.989, -0.410, 0.362 |
| Best nearby OFF recurrence within 20 Hz | none |
| Receiver-frame alias flag | none |
| Arithmetic-family flag | none |

This cluster passes the frozen v0.5 OFF-source, adjacent-OFF, receiver-alias,
and arithmetic-family vetoes. It is nevertheless a weak follow-up trigger,
not a detection. It consists of one reported hypothesis, appears in only the
first two of the three ON scans, and selects the widest permitted boxcar even
though the predicted active-epoch acceleration smearing is less than half a
channel per integration. Those features make a separately declared
topocentric morphology investigation and an independent cadence essential.

## Manual RFI-family case

The 1425.136278570 MHz cluster reaches S/N 7.4783, selects the nine-channel
boxcar, and uses all three ON epochs. It has no direct automated OFF recurrence,
but it belongs to eight detected arithmetic frequency families. The family
flag is triage evidence rather than a physical veto, so this record remains
labelled `rfi_family_veto_pending_manual_review` until a fixed post-hoc
morphology analysis resolves it. It is not promoted to a follow-up survivor.

## Candidate reduction

The frozen reporting procedure retained 910 hypothesis peaks, formed 362
frequency clusters before per-window report limits, and reported 115 clusters:

| Disposition | Clusters |
|---|---:|
| Below operational threshold | 78 |
| Local OFF-source veto | 24 |
| Single adjacent-OFF-track veto | 6 |
| Receiver-frame alias veto | 5 |
| Arithmetic-family flag pending manual review | 1 |
| Survives for follow-up | 1 |

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 15/32 (46.9%) | 15/32 (46.9%) |
| 12 | 32/32 (100%) | 31/32 (96.9%) |
| 16 | 32/32 (100%) | 32/32 (100%) |
| 20 | 32/32 (100%) | 32/32 (100%) |
| 24 | 32/32 (100%) | 32/32 (100%) |
| 32 | 32/32 (100%) | 32/32 (100%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **8.24** and **11.25**. The corresponding one-channel
estimates are **8.25** and **11.45**. These are grid interpolations, not
confidence bounds; a 32/32 level has a Wilson 95% lower bound of 89.3%.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full
  receiver band.
- All three ON scans belong to one approximately 28-minute ABACAD cadence on
  2016-08-22, not independent observing nights.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on HD 219134 h.
- The empirical p-value measures departure from the circular-shift null.
  Structured RFI can produce the same departure.
- The nine-channel survivor requires morphology review because broad or
  structured interference can be favored by the widest boxcar.
- A retained candidate is only a request for independent follow-up. No
  technosignature or detection claim is made.

## Reproducibility

The preregistration commit is
`287defd3aaabbb54278d74fcfc086abaf83ca48a`; its frozen configuration SHA-256
is
`8f2da40aaa1b80fbbc4d34087dde5ef2cd565d7d7da7319fa52264e94d38919f`.
The execution commit is
`4aff378b7c54de6969c5f9efbf08dc9fa2fa0d11`. The workflow repeated all
detector tests and the 630-case coverage proof before extraction.
`DATA_MANIFEST_M16.sha256` identifies the 30 extracted slices;
`RESULTS_MANIFEST_M16.sha256` identifies the primary published outputs. The
extracted telescope slices are not committed.
