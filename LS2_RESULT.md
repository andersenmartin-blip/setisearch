# LS2 final result

Status: **COMPLETE — NO SURVIVING MEDIUM-RESOLUTION EVENT; HTR NOT
AUTHORIZED; NO TECHNOSIGNATURE CLAIM**.

LS2 extended the experimental light-sail leakage track beyond HD 219134. A
prospectively frozen sequence of metadata milestones screened five nearby
multi-transiting systems, recovered public cadence relationships, verified
HDF5 headers and selected one independent-system observation before spectral
values were read.

## Selection chain

1. **LS2 inventory:** LTT 1445 A, L 98-59, HD 260655, GJ 9827 and TRAPPIST-1
   were checked against current NASA ephemerides and the Breakthrough Listen
   public catalogue. HD 260655 and GJ 9827 had exact archive aliases and public
   GBT medium-resolution products.
2. **LS2B cadence discovery:** the dedicated archive cadence view found two
   six-scan HD 260655 ABACAD listings. GJ 9827 had no cadence listing.
3. **LS2C header preflight:** both HD 260655 cadences passed the
   medium-resolution header gate. L-band cadence `--64524` had all six HTR
   products and a nominal projected b--c separation of 32.5777 stellar radii;
   S-band cadence `--78205` had five HTR products and a separation of 36.2446.
   The L-band cadence was selected by the frozen rule.
4. **LS2D screen:** the six exact `--64524` medium-resolution files were
   fetched, hash-verified and searched over 1100--1900 MHz with the unchanged
   LS1 broadband detector.

## Stage-1 outcome

| Scan | Role | Retained events | Truncated |
|---|---|---:|---|
| A1 | ON | 278 | no |
| B1 | OFF | 225 | no |
| A2 | ON | 309 | no |
| C1 | OFF | 284 | no |
| A3 | ON | 242 | no |
| D1 | OFF | 244 | no |

The three ON scans produced 805 events at score >= 8.0. Every event had the
predeclared adjacent-OFF frequency-coincidence evidence, so zero events survived
the veto. No scan reached the 2048-event retention cap. The frozen rule
therefore does not authorize opening HTR spectral values, and LS2 closes without
an HTR follow-up.

## Interpretation boundary

This is a null result for one 2016 GBT L-band cadence, the exact LS1-derived
template bank and its adjacent-OFF rule. It is not a general light-sail
exclusion. The nominal geometry is about 5.21 times less favourable than the
LS1 selected cadence, and the 31.9474--33.1723 stellar-radius ±1σ-input corner
envelope does not make it a close-conjunction observation. The 1.1--1.9 GHz
band is also below the motivating paper's illustrative optimum near tens of
GHz.

Scores are robust screening statistics rather than calibrated significances.
No calibrated false-alarm, sensitivity, occurrence-rate or technosignature
claim is made. Raw radio spectra were not published.

## Reproducible identities

| Item | SHA-256 |
|---|---|
| LS2 inventory result identity | `5ab49d0e71ef3a9fddddbfecd45532ddbe7f48378f33a953b62820771fa142fe` |
| LS2B cadence result identity | `91f39e7d2772f4397137445a3091e58301d4f39af5acf475ca01aa0dda03cf26` |
| LS2C header result identity | `8dabc55d068e0d5d8dec0f43f85b44044aff8d1a52343af192daa0d5cb9f7aea` |
| LS2D screen result identity | `b122bb587be05412946f4009bb025445fda8ddb32b07ccd9eeb372816a5bef17` |
| `results_ls2d/screen.json` | `ddda7dc25a02ff6363a4b0e332698e858028c3273165ed5f08ea7bbf5cc7cda3` |
| LS2D source-data manifest | `0933aa146d5a067263e814d5002b5b301b9d438fb12eea8833f39a957395fc95` |
| LS2D derived-results manifest | `94938b3fbbbefb5627d24c1e733c8d6dd82c587ac8c25cba4f58ab7a4321dc81` |

The canonical LS2D archive execution is GitHub Actions run
[`33883544682`](https://github.com/andersenmartin-blip/setisearch/actions/runs/33883544682).
