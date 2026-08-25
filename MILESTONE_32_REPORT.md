# Milestone 32 report: HD 99492 b higher-smearing held-out search

## Outcome

Milestone 32 is a **primary-cadence null result**. The frozen detector searched
the sole complete compatible HD 99492 L-band cadence and retained every one of
its 691 frequency clusters. Fourteen clusters exceeded the empirical global
threshold. All 14 received a physical veto defined before spectral contact:
five matched the control data on the candidate track, seven had a recurrent
control feature under the frozen local rule, and two mapped to the same
receiver-frame feature. **No candidate survives.**

HD 99492 b is used only as a motion template. This result neither assumes nor
tests that a transmitter is on the planet, and no independent second L-band
cadence exists for this target.

## Frozen target and data

Milestone 32 advanced the already frozen higher-smearing target order. HD
192263 at rank 31 was consumed by Milestone 31, rank 32 had no qualifying
cadence, and HD 99492 / HIP 55848 at rank 33 was therefore the next eligible
untouched host. HD 3651 at rank 34 remains spectrally untouched for later
work.

HD 99492 b's conservative full-projection periastron proxy is 1.66346922 Hz/s
at 1425 MHz. The `[1, 3, 5, 9, 17, 33]`-channel higher-smearing bank,
non-truncating 1600-cluster report cap, detector v0.5.0, 21 motion templates,
four activity subsets, control-field vetoes, 256 scrambles, and completeness
procedure were frozen before any spectral value was read.

The primary archive cadence is `--70969`, beginning MJD
57521.07474537037 (2016-05-13 01:47:38 UTC), with the sequence:

`HIP55848 -- HIP54998 -- HIP55848 -- HIP55211 -- HIP55848 -- HIP55321`.

All six scans have 16 integrations of 17.986224128 s and 2.835503418 Hz
channels. The metadata-only motion-plus-width proof passed all 630 checks.
It included the 16-channel half-width of the widest filter; the smallest
extraction-edge headroom after motion and width margins was 202,076 channels,
approximately 572.987 kHz.

## Blind search result

Detector v0.5.0 searched five disjoint 1 MHz planet-frame bands with 21 motion
templates, four activity subsets, and six spectral widths: approximately
**888,730,920 nominal trials**. The 256 complete scrambles gave:

- observed global maximum: S/N **3388.131144481915**;
- empirical global p-value: **1/257 = 0.0038910505836575876**;
- null median: S/N **8.965343952178955**;
- operational global threshold: S/N **10.982738494873047**.

The minimum empirical p-value says that the data contain extremely strong
structured features. It does not override stronger control-field evidence.

| Window | Retained clusters | Above threshold | Maximum S/N | Maximum frequency (MHz) | Above-threshold disposition |
|---|---:|---:|---:|---:|---|
| `m32_1400p5` | 64 | 4 | 3388.131144 | 1400.167769733 | 1 matched-control and 3 local-control vetoes |
| `m32_1406p5` | 25 | 3 | 1961.301181 | 1406.112295944 | 1 matched-control and 2 local-control vetoes |
| `m32_1412p5` | 30 | 0 | 8.034788 | 1412.556939740 | below threshold |
| `m32_1418p5` | 51 | 4 | 505.350322 | 1418.003639452 | 3 matched-control and 1 local-control veto |
| `m32_1425p0` | 521 | 3 | 31.680565 | 1424.988099392 | 2 receiver-alias and 1 local-control veto |

Complete disposition accounting is therefore:

- 677 below the global threshold;
- 5 `rfi_veto_off_source`;
- 7 `rfi_veto_local_off_source`;
- 2 `rfi_veto_receiver_frame_alias`;
- 0 unresolved or surviving candidates.

The configured 20 Hz local rule is implemented by v0.5.0 as an integer native
channel tolerance. For this cadence it becomes eight channels, or at most
22.684027 Hz. This discretization is part of the frozen detector and was not
changed after the data were read.

## Strongest event and receiver aliases

The global maximum is centered at 1400.167769733249 MHz, uses the 33-channel
boxcar and template 19, and is active in epochs 1 and 3. A control feature
under the same motion template reaches S/N **8289.641362592643** only
**2.835503437 Hz** away. It also has single-adjacent-control track evidence.
Its preregistered disposition is `rfi_veto_local_off_source`; no post-hoc rule
is needed.

The strongest otherwise unmatched 1425 MHz case is S/N 31.680565 at
1424.988099392 MHz. It and the second 1424.988116405 MHz cluster map to the
same receiver-frame feature in both claimed active epochs, within the frozen
receiver-alias tolerance. Both receive
`rfi_veto_receiver_frame_alias` automatically.

## Measured completeness

Completeness injections used real `m32_1412p5` background, 32 trials per
level, active epochs 1 and 3, four exact truth templates spanning the
higher-smearing bank, and frozen seed `322120260825`.

| Ideal single-epoch S/N | Multichannel recovered | One-channel recovered |
|---:|---:|---:|
| 8 | 0/32 | 0/32 |
| 12 | 2/32 | 2/32 |
| 16 | 18/32 | 8/32 |
| 20 | 28/32 | 10/32 |
| 24 | 32/32 | 13/32 |
| 32 | 32/32 | 20/32 |
| 40 | 32/32 | 26/32 |

Linear interpolation between tested levels gives approximate multichannel
50% and 90% recovery at ideal single-epoch S/N **15.50** and **20.80**. The
one-channel 50% point is approximately **27.43**; one-channel recovery reaches
only 26/32 = 81.25% at S/N 40, so a 90% point is not measured on the frozen
grid. These values describe exact bank templates active in epochs 1 and 3,
not every possible duty cycle or orbital-model error.

## Scope and interpretation

This is a search of five disjoint bands totaling 5 MHz, not the full receiver
band. A null result constrains only emission present in at least two of the
three ON epochs and represented by the frozen motion and width bank. The
result cannot establish independent recurrence because no second qualifying
HD 99492 cadence exists. The measured completeness must be carried with the
null result.

## Reproducibility

The preregistration commit is
`1007a4de4e40834b8665489922f2add3f45940d0`; the execution commit is
`d35d908de39801a5e75d22e966658ce255db1170`; and the checked result commit is
`e96b2004799b557a2bee2c182193340825d1b957`. Workflow run `32873831269`
published artifact `9573919417` with digest
`sha256:4c71d568c228a634c6deb3456ec3461266f3e5e4a483ccc075e4d80bace2411e`.

The frozen configuration SHA-256 is
`7f0f20f6e76f4182c9c9b94bb7ccca34c2d5345a459085362e480ef546732cf7`.
The machine-readable search summary SHA-256 is
`e7c0bef19a969589cbf5bec66a4342b845c174eb2be82d34d29f86a5cf649be3`.
The data and result manifests identify 30 reproducible extracted slices and
nine published result files. Extracted telescope slices are not committed.

Publication verification workflow run `32876651071` independently revalidated all nine result-file hashes, complete accounting for 691 clusters, all 14 above-threshold physical vetoes, the six-width bank and known-answer tests, discrete local-tolerance handling, execution provenance, and the pre-verification report hash. Its machine-readable receipt is `MILESTONE_32_PUBLICATION_VERIFICATION.json`.
