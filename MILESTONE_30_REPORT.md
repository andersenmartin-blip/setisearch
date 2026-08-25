# Milestone 30 report: bet UMi b held-out search

## Outcome

Milestone 30 is a **primary-cadence null result**. The frozen detector searched
the sole qualifying bet UMi L-band cadence and retained every one of its 309
frequency clusters. Twenty-five clusters exceeded the empirical global
threshold. All 25 received a physical OFF-source veto defined before spectral
contact: 18 matched the control data on the candidate track, and seven had a
recurrent control feature within the frozen 20 Hz local tolerance. **No
candidate survives.**

bet UMi b is used only as a motion template. This result neither assumes nor
tests that a transmitter is on the planet, and no independent second L-band
cadence exists for this target.

## Frozen target and data

The target is bet UMi / HIP 72607 at 38.77472 pc. The official composite orbit
used period 522.3 days, semimajor axis 1.4 au, eccentricity 0.19, periastron
epoch BJD 2453175.3, and longitude of periastron 307.4 degrees. The primary
archive cadence is `--74586`, beginning MJD 57584.09893518518
(2016-07-15 02:22:28 UTC), with the sequence:

`Hip72607 -- Hip72307 -- Hip72607 -- Hip73047 -- Hip72607 -- Hip73715`.

All six scans have 16 integrations of 18.253611008 s and 2.793967724 Hz
channels. The metadata-only proof passed all 630 template/scan/window checks;
its smallest extraction-edge headroom was 238,473 channels, approximately
666.286 kHz.

## Blind search result

Detector v0.5.0 searched five disjoint 1 MHz planet-frame bands with 21 motion
templates, four activity subsets, and boxcar widths of 1, 3, 5, and 9
channels: approximately **601,293,840 nominal trials**. The 256 complete
scrambles gave:

- observed global maximum: S/N **26.063907832950388**;
- empirical global p-value: **1/257 = 0.0038910505836575876**;
- null median: S/N **6.521295070648193**;
- operational global threshold: S/N **11.218682289123535**.

The small empirical p-value says that the data contain unusually strong
structure; it does not override the preregistered control-field vetoes.

| Window | Retained clusters | Above threshold | Maximum S/N | Maximum frequency (MHz) | Above-threshold disposition |
|---|---:|---:|---:|---:|---|
| `m30_1400p5` | 56 | 4 | 17.588181 | 1400.043401413 | 4 local-control vetoes |
| `m30_1406p5` | 2 | 0 | 5.572947 | 1406.853557058 | below threshold |
| `m30_1412p5` | 1 | 0 | 5.527776 | 1412.561696395 | below threshold |
| `m30_1418p5` | 8 | 0 | 5.823330 | 1418.264460139 | below threshold |
| `m30_1425p0` | 242 | 21 | 26.063908 | 1425.047656707 | 18 matched-control and 3 local-control vetoes |

Complete disposition accounting is therefore:

- 284 below the global threshold;
- 18 `rfi_veto_off_source`;
- 7 `rfi_veto_local_off_source`;
- 0 unresolved or surviving candidates.

## Strongest event

The global maximum is centered at 1425.047656707466 MHz, uses the nine-channel
boxcar and template 18, and is active in epochs 2 and 3. The same frozen motion
hypothesis finds a recurrent control-field feature with S/N
19.550247939856526 only **5.587935447693871 Hz** away. It also maps into a
receiver-frame feature shared by the active epochs and aliases with 20 other
planet-frame clusters. Its preregistered disposition is
`rfi_veto_off_source`.

The strongest 1400 MHz event likewise has a local control recurrence at S/N
705.7036161676306, 16.763806343078613 Hz away. Thus neither high-S/N region
requires a post-hoc rule or an interpretive manual veto.

## Measured completeness

Completeness injections used real `m30_1412p5` background, 32 trials per
level, active epochs 1 and 3, four exact truth templates, and the frozen seed
`302120260825`.

| Ideal single-epoch S/N | Multichannel recovered | One-channel recovered |
|---:|---:|---:|
| 8 | 0/32 | 0/32 |
| 12 | 10/32 | 10/32 |
| 16 | 29/32 | 24/32 |
| 20 | 31/32 | 29/32 |
| 24 | 32/32 | 30/32 |
| 32 | 32/32 | 30/32 |
| 40 | 32/32 | 30/32 |

Linear interpolation between tested levels gives approximate multichannel
50% and 90% recovery at ideal single-epoch S/N **13.26** and **15.96**. The
corresponding one-channel estimates are **13.71** and **19.84**. These values
describe exact bank templates active in epochs 1 and 3, not every possible
duty cycle or orbital-model error.

## Scope and interpretation

This is a search of five disjoint bands totaling 5 MHz, not the full receiver
band. A null result constrains only emission present in at least two of the
three ON epochs and represented by the frozen motion and width bank. The
result cannot establish independent recurrence because the only other bet UMi
cadence is S-band.

## Reproducibility

The preregistration commit is
`f0da6dff82dffe37e254534e30cd47ffbf74b067`; the execution commit is
`5e6195aa2c20c31a5efd23085e084758f888103e`; and the checked result commit is
`29fa64d720ac79ed0876970559b9b0fae10a29bd`. Workflow run `32805474906`
published artifact `9548317287` with digest
`sha256:01b831e7d7c24538c843a64cfd5c5e3065c0fbfc7dd05ae6744f7dd3650924bc`.

The frozen configuration SHA-256 is
`b08e820bb55cc0d1b946890f93cb7a15742825df97274392cb44d97058b989d3`.
The machine-readable search summary SHA-256 is
`54bc04f4cd2bc399709f9233e12cdc4ca1996c10bdd82fb262e0ef0e8d141ed9`.
The data and result manifests identify 30 reproducible extracted slices and
nine published result files. Extracted telescope slices are not committed.

Publication verification workflow run `32806857727` independently revalidated all nine result-file hashes, complete accounting for 309 clusters, every one of the 25 above-threshold physical vetoes, known-answer tests, execution provenance, and the pre-verification report hash. Its machine-readable receipt is `MILESTONE_30_PUBLICATION_VERIFICATION.json`.
