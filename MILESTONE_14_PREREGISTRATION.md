# Milestone 14 preregistration: GJ 687 held-out detector-v0.5 validation

Status: **frozen before spectral extraction or inspection**.

Frozen configuration SHA-256:
`8b996ffef7166056bd089b58ea317668c7692294324347118a3e39b462ed5df7`.

## Purpose and boundary

Milestone 14 is a new held-out application of detector v0.5.0 after Milestone
13 stopped fail-closed without producing a search result. The target is **GJ
687**, with GJ 687 b used only as the motion template. The data are the complete
Green Bank Telescope L-band ABACAD cadence beginning 2016-07-22 03:35:35 UTC,
archive cadence `--75045`.

Before this commit, only archive catalogue records, HTTP identity metadata,
HDF5 attributes/shape/dtype/chunking, scan timestamps, and official target/orbit
metadata were read. No selected HDF5 `data` slice was indexed, extracted,
plotted, summarized, or searched.

## Selection and non-reuse

GJ 687 is the next eligible nearby confirmed-planet host in the metadata screen
after excluding all prior or compromised targets:

- Proxima Centauri and LHS 1140 were used by earlier project milestones;
- GJ 411 was contacted by the aborted Milestone 13 extraction;
- GJ 273 and GJ 1002 were excluded after public result pages were inadvertently
  exposed during earlier archive discovery.

The selected cadence is the only inspected GJ 687 candidate that supplies six
fine HDF5 scans in a complete L-band ABACAD sequence with common geometry and
full coverage of the five bands:

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | Gj687 | 57591.149722222224 | 16 | 292.057776128 |
| 2 | OFF | Hip85098 | 57591.153622685180 | 16 | 292.057776128 |
| 3 | ON | Gj687 | 57591.157523148150 | 16 | 292.057776128 |
| 4 | OFF | Hip85417 | 57591.161458333336 | 16 | 292.057776128 |
| 5 | ON | Gj687 | 57591.165381944450 | 16 | 292.057776128 |
| 6 | OFF | Hip85612 | 57591.169293981480 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and 1023.925784044-1926.26953125 MHz
coverage. All six URLs return HTTP 200, advertise byte ranges, and match the
frozen size and ETag values in `config/gj687b_heldout_m14.json`.

The metadata/header evidence is GitHub Actions run `32391250698`, artifact
`9414921943`, digest
`sha256:16e43269b7fceed1f7a88cd28613d6124a6bb1260ae413c3b888502f54eb3adf`.

## Mandatory full-bank coverage proof

Milestone 13 demonstrated that nominal receiver coverage is insufficient: an
extracted interval must also cover the rest grid transformed by every orbital
template plus its dedoppler edge margin. Before this preregistration,
`scripts/m14_coverage_preflight.py` evaluated all:

- 21 frozen projected-scale/phase templates;
- six scan timestamps; and
- five frequency windows.

All **630** metadata-only checks passed without opening a remote file. The
smallest edge headroom is 142,496 channels, approximately 398 kHz. The proof is
run `32391826661`, artifact `9415134758`, digest
`sha256:e6f5c75da5737d1c729472be224b71bdd6e0aeec61c803ff625d48f31cda8726`.

The 600 kHz extraction guards are therefore frozen before spectral contact.
They are container/input margins only; the five searched 1 MHz rest-frame bands
remain identical to Milestones 11 and 13.

## Target and orbit template

The NASA Exoplanet Archive default GJ 687 b record supplies:

- period 38.142 days;
- semimajor axis 0.163 au;
- eccentricity 0.17;
- periastron epoch BJD 2450592.7; and
- archive `pl_orblper` 117 degrees, used as omega.

The target position, proper motion, parallax, and radial velocity come from the
same official metadata response. The unknown inclination is represented only
by the already frozen projected-scale bank. This is a coordinate-transform
template, not a claim that an emitter resides on GJ 687 b.

## Frozen detector and statistical procedure

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. The following settings are
unchanged:

- projected scales `[0, 0.25, 0.5, 0.75, 1.0]`;
- phase offsets `[-0.2, -0.1, 0, 0.1, 0.2]` cycles;
- minimum two active ON epochs and per-epoch S/N at least 3.0;
- `sqrt(N)` times the weakest active-epoch S/N recurrence statistic;
- the same moving single-epoch RFI mask;
- normalized widths `[1, 3, 5, 9]` channels;
- candidate floor 5.5, 20 Hz clustering, and unchanged family flags;
- v0.5 local-OFF and receiver-frame alias veto settings;
- 256 complete-search scrambles, with new seed `1420260820`; and
- the same completeness grid and 32 trials per level, with new seed
  `141420260820`.

## Frozen windows

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m14_1400p5` | 1399.4-1401.6 | 1400.5 | 500 |
| `m14_1406p5` | 1405.4-1407.6 | 1406.5 | 500 |
| `m14_1412p5` | 1411.4-1413.6 | 1412.5 | 500 |
| `m14_1418p5` | 1417.4-1419.6 | 1418.5 | 500 |
| `m14_1425p0` | 1423.9-1426.1 | 1425.0 | 500 |

## Decision rules

After this commit:

1. extraction must fail closed if any URL size, ETag, source, time, sampling,
   shape, dtype, or frequency geometry differs;
2. detector rules, thresholds, vetoes, templates, searched rest bands, random
   seeds, and completeness procedure may not change in response to the payload;
3. every one of the 30 configured slices and all five window searches must
   complete;
4. every automated veto and arithmetic-family flag must retain its provenance;
5. a retained candidate is only a follow-up trigger and requires a genuinely
   independent observing cadence; and
6. a null applies only to the frozen bands, template/activity bank, cadence,
   and measured completeness.
