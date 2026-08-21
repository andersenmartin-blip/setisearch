# Milestone 15 preregistration: GJ 581 held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`117b689c9a2d12726133e3f53fd6560b80d8d354540310c94ab9b4032c3a8c99`.

## Purpose and boundary

Milestone 15 is a new held-out application of detector v0.5.0.  The target is
**GJ 581**, with GJ 581 b used only as the motion template.  The data are the
complete Green Bank Telescope L-band ABACAD cadence beginning
2016-03-30 09:53:27 UTC, archive cadence `--87092`.

Before this commit, only catalogue records, HTTP object identities, HDF5
attributes/shape/dtype/chunking, scan timestamps, official target/orbit
metadata, and locally calculated extraction geometry were read.  No selected
HDF5 `data` value was indexed, extracted, plotted, summarized, or searched.

## Fixed target selection

The selection rule was committed as
`61007e59a81f094ff08b5da47ae8ce371bc81f6c` before the Milestone 15 metadata
jobs ran.  It screened Tau Ceti, GJ 581, and GJ 667 C and required a complete
fine-resolution L-band ABACAD cadence plus a sufficiently specified official
planet/host record.

- Tau Ceti supplied no qualifying HDF5 cadence and its official records lack a
  periastron epoch.
- GJ 667 C supplied no qualifying HDF5 cadence and its composite record lacks
  a periastron epoch.
- GJ 581 supplied one qualifying cadence and a complete composite GJ 581 b
  orbit/host record.

Ross 128 was excluded after a target-specific public result page was exposed.
All prior project targets and the earlier exposed GJ 273/GJ 1002 targets retain
their recorded exclusions.  The complete screen is GitHub Actions run
`32502205358`; artifact identities and result hashes are preserved in
`metadata/m15_gj581_selection.json`.

## Frozen cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP74995 | 57477.412118055550 | 16 | 287.779586048 |
| 2 | OFF | HIP74995_OFF | 57477.415902777780 | 16 | 287.779586048 |
| 3 | ON | HIP74995 | 57477.419675925930 | 16 | 287.779586048 |
| 4 | OFF | HIP74995_OFF | 57477.423449074070 | 16 | 287.779586048 |
| 5 | ON | HIP74995 | 57477.427222222220 | 16 | 287.779586048 |
| 6 | OFF | HIP74995_OFF | 57477.430995370370 | 16 | 287.779586048 |

Every scan has shape `[16, 1, 264503296]`, float32 samples,
17.986224128 s integrations, 2.835503418 Hz channels, and coverage from
1126.464846586 to 1876.464843750 MHz.  All six URLs return HTTP 200, advertise
byte ranges, and match the frozen sizes, ETags, sources, times, and geometry in
`config/gj581b_heldout_m15.json`.

The GJ 581 metadata result is artifact `9453942416`, digest
`sha256:357c0a074e596bbdc714d512b12ecf7725547f0aeca77a4ec3f55b45468c2b91`.

## Mandatory extraction-coverage proof

Before this preregistration, `scripts/m14_coverage_preflight.py` evaluated all
21 frozen projected-scale/phase templates at all six scan times in all five
windows.  All **630** checks passed without opening a remote file.  The
smallest edge headroom is 115,925 channels, approximately 328.706 kHz.

The proof is GitHub Actions run `32502808044`, artifact `9454156957`, digest
`sha256:af82ef35901c099b1fc49708cce6148d9f07a8f0fde03be367c05777a16856f8`.
The result file has SHA-256
`73f3ca677f97f326f377b51e4983c1e589d669d49d756aee77cc1ea478a643d3`.

The 800 kHz extraction guards are now frozen.  They are input-container
margins only; the five searched rest-frame bands remain the same 1 MHz bands
used in Milestones 11, 13, and 14.

## Target and orbital template

The NASA Exoplanet Archive `pscomppars` composite GJ 581 b record supplies:

- period 5.3686 days;
- semimajor axis 0.0399 au;
- eccentricity 0.0342;
- periastron epoch BJD 2454751.76; and
- longitude of periastron 54 degrees, used as omega.

The same official record supplies the target position, proper motion,
parallax, and radial velocity.  The unknown inclination is represented only by
the already frozen projected-scale bank.  The orbit is a coordinate-transform
template; it does not establish that an emitter resides on GJ 581 b.

## Frozen detector and statistical procedure

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`.  The following settings are
unchanged:

- projected scales `[0, 0.25, 0.5, 0.75, 1.0]`;
- phase offsets `[-0.2, -0.1, 0, 0.1, 0.2]` cycles;
- minimum two active ON epochs and per-epoch S/N at least 3.0;
- `sqrt(N)` times the weakest active-epoch S/N recurrence statistic;
- the same moving single-epoch RFI mask;
- normalized widths `[1, 3, 5, 9]` channels;
- candidate floor 5.5, 20 Hz clustering, and unchanged family flags;
- v0.5 local-OFF and receiver-frame alias vetoes;
- 256 complete-search scrambles, with seed `1520260821`; and
- the same completeness grid and 32 trials per level, with seed
  `151520260821`.

## Frozen windows

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m15_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m15_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m15_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m15_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m15_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision and interpretation rules

After this commit:

1. extraction must fail closed if any URL size, ETag, source, time, sampling,
   shape, dtype, or frequency geometry differs;
2. detector rules, thresholds, vetoes, templates, searched rest bands, random
   seeds, and completeness procedure may not change in response to the data;
3. all 30 configured slices and all five window searches must complete;
4. every automated veto and arithmetic-family flag retains its provenance;
5. a retained candidate is only a follow-up trigger and requires a genuinely
   independent observing cadence; and
6. a null applies only to the frozen bands, template/activity bank, cadence,
   and measured completeness.
