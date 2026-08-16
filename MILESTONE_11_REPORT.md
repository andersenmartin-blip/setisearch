# Milestone 11 report: frozen-detector transfer to LHS 1140

## Result in one sentence

The preregistered five-band Green Bank Telescope search produced spectral
structure far outside the circular-shift null, but the present evidence does
not support a technosignature claim: several strong features have direct or
nearby OFF-source counterparts or automated interference flags, while five
reported clusters remain formally **FOLLOW-UP REQUIRED**.

## Frozen scope

Milestone 11 transferred the unchanged `seti-repeater` v0.4.0 detector from
the Proxima Centauri work to a new target, telescope, date, cadence, and source
payload. The search used the complete public 2017-01-21 Green Bank Telescope
L-band ABACAD cadence for LHS 1140 (archive cadence `--114914`): three LHS 1140
pointings interleaved with HIP 2579, HIP 2586, and HIP 3249 controls.

The five planet-frame search intervals were deliberately held equal to the
Milestone 10 intervals:

- 1400.0–1401.0 MHz;
- 1406.0–1407.0 MHz;
- 1412.0–1413.0 MHz;
- 1418.0–1419.0 MHz;
- 1424.5–1425.5 MHz.

The configuration was frozen at 2026-08-16T10:10:22Z with SHA-256
`bff867ce097051dbb4a2a426ba774c18347705d4bb692d1a544be8eeb8375e3a`.
The frozen detector source digest was
`80201e8c2061122dedf5b166c648c7c31c9f223873c231fc9403030ed1f9641e`.
No selected spectral payload was inspected before preregistration.

## Execution and integrity

- GitHub Actions run: `31946147664`, starting from commit
  `828e1883b1444292972a44df52ae0835e4bdf8d0`.
- Pipeline: `seti-repeater` 0.4.0, Python 3.12.13, NumPy 2.5.2.
- Eight unit tests and both one-channel and multi-channel known-answer tests
  passed before the search.
- Thirty extracted products were recorded in `DATA_MANIFEST_M11.sha256` and
  verified before analysis.
- Every ON and OFF scan contains 16 × 18.253611008 s integrations at
  2.7939677238464355 Hz channel spacing, so the controls have equal exposure.
- A second complete search gave byte-identical `search_summary.json`,
  `completeness.json`, `scramble_nulls.npz`, and `window_summary.csv`.

## Search result

The complete search covered approximately **601,293,840** nominal
frequency/orbit/activity/width trials. Its global statistics were:

- observed maximum: **S/N 105.8952**;
- scrambled-null median: **S/N 7.5012**;
- scrambled-null 99th percentile and operational threshold: **S/N 10.3893**;
- empirical global p-value: **1/257 = 0.003891**;
- preregistered assessment: **FOLLOW-UP REQUIRED**.

The empirical p-value means that none of the 256 coherence-destroying
scrambles reached the observed maximum. It measures incompatibility with this
particular shifted-noise null; it is not the probability that the feature is
artificial or extraterrestrial. Recurrent interference can also defeat that
null.

| Planet-frame band | ON maximum S/N | Width | Frequency (MHz) | Active scans | Matched OFF S/N | Window p | Frozen disposition |
|---|---:|---:|---:|---|---:|---:|---|
| 1400.0–1401.0 | 105.895 | 9 ch | 1400.926242128 | 2+3 | 4.742 | 0.003891 | arithmetic-family flag; manual review pending |
| 1406.0–1407.0 | 12.177 | 9 ch | 1406.707600184 | 1+2+3 | 17.059 | 0.003891 | OFF-source veto |
| 1412.0–1413.0 | 8.293 | 5 ch | 1412.562288716 | 2+3 | fails recurrence floor | 0.003891 | below global threshold |
| 1418.0–1419.0 | 5.762 | 9 ch | 1418.242790125 | 2+3 | fails recurrence floor | 0.618677 | below global threshold |
| 1424.5–1425.5 | 45.312 | 1 ch | 1425.063540414 | 1+2 | fails recurrence floor | 0.003891 | survives automated exact-hypothesis veto |

The 1425.063540 MHz ON maximum requires particular caution. Although the
frozen exact-hypothesis OFF statistic fails its per-epoch recurrence floor, the
OFF-bank global maximum is S/N 26.43 at 1425.063546 MHz—only about 5.6 Hz away.
This post-hoc frequency proximity is strong interference evidence, but it is
reported separately rather than silently changing the frozen disposition.
Likewise, the 1412.562289 MHz sub-threshold ON maximum is about one channel
from the OFF global maximum at 1412.562292 MHz.

## Candidate reduction

The frozen reducer retained 1,099 hypothesis peaks, merged them into 320
frequency clusters, and reported 109 clusters after the per-band report limit.
Their dispositions were:

- 80 below the global threshold;
- 8 vetoed by an OFF-source coincidence at the same tested hypothesis;
- 16 assigned arithmetic-frequency-family flags pending manual review;
- 5 formally surviving for follow-up.

The five formal survivors occur only in the heavily structured 1400 and 1425
MHz bands. Four prefer the widest 9-channel template; the fifth is the
1425.063540 MHz one-channel feature with the nearby strong OFF maximum noted
above. Arithmetic-family labels are triage flags, not proof of interference,
so the S/N 105.90 maximum cannot be dismissed solely from that label.

## Real-noise completeness

Signals were injected into independently shifted real 1412.0–1413.0 MHz
planet-frame noise, using the preregistered four exact orbital templates and
activity in scans 1 and 3.

| Ideal single-scan S/N | Multi-channel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 0/32 (0.0%) | 0/32 (0.0%) |
| 12 | 14/32 (43.8%) | 14/32 (43.8%) |
| 16 | 26/32 (81.2%) | 20/32 (62.5%) |
| 20 | 32/32 (100%) | 22/32 (68.8%) |
| 24 | 32/32 (100%) | 30/32 (93.8%) |
| 32 | 32/32 (100%) | 30/32 (93.8%) |
| 40 | 32/32 (100%) | 30/32 (93.8%) |

Coarse piecewise-linear point estimates put the multi-channel 50% and 90%
recovery levels near ideal single-scan S/N 12.67 and 17.87. The corresponding
one-channel estimates are 13.33 and 23.40. These are not confidence bounds;
32/32 has a Wilson 95% lower bound of 89.3%.

## Interpretation limits

- The search covers five disjoint bands totaling 5 MHz, not the full receiver.
- All three ON scans lie within one 28-minute cadence; this is not independent
  long-baseline recurrence.
- The planet supplies a motion law, not a proven source location.
- The 256-scramble p-value cannot resolve values below 1/257.
- Strong structured RFI is present in both ON and OFF products. A low
  circular-shift p-value is therefore insufficient for a discovery claim.
- Exact-hypothesis OFF vetoes can miss a nearby line whose width, activity
  subset, or best template differs slightly.
- The arithmetic-family algorithm is an auditable triage heuristic, not a
  physical classification.
- Completeness covers exact bank members active in scans 1 and 3, not every
  orbital-model error or duty cycle.

## Conclusion and next action

Milestone 11 successfully demonstrates that the frozen pipeline transfers to
a new target and exposes a much more structured interference environment. It
does **not** establish a technosignature. The scientifically appropriate next
step is a labelled post-hoc candidate investigation: inspect the surviving
features in topocentric and barycentric coordinates, compare every ON and OFF
scan locally around each frequency, search other LHS 1140 cadences, and check
known instrumental or transmitter families. Detector thresholds should remain
frozen during that investigation.
