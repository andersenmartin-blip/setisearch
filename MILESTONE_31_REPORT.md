# Milestone 31 report: HD 192263 b higher-smearing held-out search

## Outcome

Milestone 31 is a **primary-cadence null result**. The frozen detector searched
the sole complete compatible HD 192263 L-band cadence and retained every one
of its 583 frequency clusters. Eleven clusters exceeded the empirical global
threshold. All 11 received a physical OFF-source veto defined before spectral
contact: six matched the control data on the candidate track, and five had a
recurrent control feature within the frozen 20 Hz local tolerance. **No
candidate survives.**

HD 192263 b is used only as a motion template. This result neither assumes nor
tests that a transmitter is on the planet, and no independent second L-band
cadence exists for this target.

## Higher-smearing extension and frozen data

Milestones 16--30 exhausted the 30 unique hosts inside the original
conservative 1 Hz/s acceleration-smearing group. Milestone 31 froze ranks
31--35 from the already preserved Milestone 16 order before reading any of
their spectral data. HD 192263 / HIP 99711 at rank 31 was the first host with a
complete compatible GBT L-band cadence. HD 99492 and HD 3651 at ranks 33 and
34 each retain one spectrally untouched qualifying cadence for later work.

HD 192263 b's conservative full-projection periastron proxy is 1.05365446 Hz/s
at 1425 MHz. The wider `[1, 3, 5, 9, 17, 33]`-channel boxcar bank and a
non-truncating 1600-cluster report cap were prospectively frozen before any
rank 31--35 telescope product was opened. Detector software v0.5.0, the
21-template motion bank, four activity subsets, control-field vetoes, 256
scrambles, and completeness procedure otherwise remained unchanged.

The primary archive cadence is `--66435`, beginning MJD
57683.92162037037 (2016-10-22 22:07:08 UTC), with the sequence:

`HIP99711 -- HIP100159 -- HIP99711 -- HIP100786 -- HIP99711 -- HIP98698`.

All six scans have 16 integrations of 18.253611008 s and 2.793967724 Hz
channels. The metadata-only motion-plus-width proof passed all 630
template/scan/window checks. It included the 16-channel half-width of the
widest filter; the smallest extraction-edge headroom after motion and width
margins was 129,682 channels, approximately 362.327 kHz.

## Blind search result

Detector v0.5.0 searched five disjoint 1 MHz planet-frame bands with 21 motion
templates, four activity subsets, and six spectral widths: approximately
**901,940,760 nominal trials**. The 256 complete scrambles gave:

- observed global maximum: S/N **33.19471222767169**;
- empirical global p-value: **2/257 = 0.007782101167315175**;
- null median: S/N **8.701365947723389**;
- operational global threshold: S/N **13.200340270996094**.

The small empirical p-value says that the data contain unusually strong
structure; it does not override the preregistered control-field vetoes.

| Window | Retained clusters | Above threshold | Maximum S/N | Maximum frequency (MHz) | Above-threshold disposition |
|---|---:|---:|---:|---:|---|
| `m31_1400p5` | 34 | 11 | 33.194712 | 1400.335505150 | 6 matched-control and 5 local-control vetoes |
| `m31_1406p5` | 26 | 0 | 7.487875 | 1406.910445035 | below threshold |
| `m31_1412p5` | 14 | 0 | 6.436981 | 1412.835396267 | below threshold |
| `m31_1418p5` | 24 | 0 | 6.847700 | 1418.408218160 | below threshold |
| `m31_1425p0` | 485 | 0 | 10.439278 | 1425.351942144 | below threshold |

Complete disposition accounting is therefore:

- 572 below the global threshold;
- 6 `rfi_veto_off_source`;
- 5 `rfi_veto_local_off_source`;
- 0 unresolved or surviving candidates.

## Strongest event

The global maximum is centered at 1400.335505150259 MHz, uses the new
33-channel boxcar and template 11, and is active in epochs 2 and 3. A control
feature under the same motion template reaches S/N 36.28698806499014 only
**8.381903171539307 Hz** away. The event also has single-adjacent-control
track evidence and aliases with three other planet-frame clusters through the
same receiver-frame feature. Its preregistered disposition is
`rfi_veto_local_off_source`; no post-hoc rule is needed.

## Measured completeness

Completeness injections used real `m31_1412p5` background, 32 trials per
level, active epochs 1 and 3, four exact truth templates spanning the
higher-smearing bank, and frozen seed `312120260825`.

| Ideal single-epoch S/N | Multichannel recovered | One-channel recovered |
|---:|---:|---:|
| 8 | 0/32 | 0/32 |
| 12 | 0/32 | 0/32 |
| 16 | 3/32 | 2/32 |
| 20 | 7/32 | 4/32 |
| 24 | 23/32 | 5/32 |
| 32 | 32/32 | 7/32 |
| 40 | 32/32 | 15/32 |

Linear interpolation between tested levels gives approximate multichannel
50% and 90% recovery at ideal single-epoch S/N **22.25** and **29.16**. The
one-channel detector reaches only 15/32 = 46.875% at the highest frozen level,
so neither a one-channel 50% nor 90% point is measured on this grid. These
values describe exact bank templates active in epochs 1 and 3, not every
possible duty cycle or orbital-model error.

## Scope and interpretation

This is a search of five disjoint bands totaling 5 MHz, not the full receiver
band. A null result constrains only emission present in at least two of the
three ON epochs and represented by the frozen motion and width bank. The
result cannot establish independent recurrence because no second qualifying
HD 192263 cadence exists. The higher-smearing extension improves sensitivity
to broader within-integration power, but its measured completeness is poorer
than the preceding low-smearing case and must be carried with the null result.

## Reproducibility

The preregistration commit is
`e1d53fafef00b89c9c55b6b8e8c2b53d639b0eb7`; the execution commit is
`b879ae4569d904e9e9edd61caba98ef03e95f65a`; and the checked result commit is
`e48eb1902ada7569fb22c1ca347539d745aeab43`. Workflow run `32868632596`
published artifact `9571977799` with digest
`sha256:971e468c49023f89f24052dae683390fcdaf57d5b5bf6ade13a87687560e85b7`.

The frozen configuration SHA-256 is
`4037921bc5fabd38e606455f1d515b97da8ffcf1aab2a993553ab114929ee986`.
The machine-readable search summary SHA-256 is
`d85c977d58ca1e85d8918fe905e3b16be40c09e28ce7eae040dc283fadc2501d`.
The data and result manifests identify 30 reproducible extracted slices and
nine published result files. Extracted telescope slices are not committed.

Publication verification workflow run `32871654840` independently revalidated all nine result-file hashes, complete accounting for 583 clusters, every one of the 11 above-threshold physical vetoes, the six-width bank and known-answer tests, execution provenance, and the pre-verification report hash. Its machine-readable receipt is `MILESTONE_31_PUBLICATION_VERIFICATION.json`.
