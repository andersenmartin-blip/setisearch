# LS5 Kepler-160 S-band archival screen

Status: **screen-complete-followup-preregistration-required**.

The fifth distinct LS target has now received a medium-resolution spectral screen. Six public GBT scans from 14 June 2020 were processed in the frozen 1.8–2.8 GHz band, using unchanged LS1 broadband templates and the LS4B SIGPROC adapter. Total input: 3,510,634,236 bytes; designated ON integration: 898.722 seconds.

| Scan | Archival role | Retained score ≥6 events | Score ≥8 events | Retention truncated |
|---|---|---:|---:|---|
| A1 | ON | 181 | 170 | False |
| B1 | OFF | 259 | 49 | False |
| A2 | ON | 264 | 189 | False |
| C1 | OFF | 210 | 188 | False |
| A3 | ON | 290 | 248 | False |
| D1 | OFF | 270 | 251 | False |

**607 ON threshold events; 3 survive the adjacent-OFF veto.** These counts describe detector windows, not independent physical signals.

Survivors require a separately frozen HTR follow-up and pointing verification. No technosignature is claimed. No HTR samples have been opened.

## Three retained windows and post-hoc control check

All three primary survivors occur late in A1 and use the 64-second template. A labelled post-hoc audit of already screened C1/D1 data finds frequency-overlapping events above score 6 for every survivor. C1 and D1 are not A1’s frozen adjacent control. This flags interference concerns without changing the primary three-survivor result; it does not prove simultaneous emission or common physical origin. No additional spectra were read.

| A1 frequency interval (MHz) | A1 time (s) | A1 score | C1 max overlapping score | D1 max overlapping score |
|---|---:|---:|---:|---:|
| 2441.599–2444.526 | 233.0–297.4 | 20.77 | 36.56 | 6.18 |
| 2426.951–2429.878 | 234.1–298.5 | 17.98 | 23.06 | 6.48 |
| 1920.115–1923.042 | 227.6–292.1 | 11.03 | 13.67 | 90.70 |

Any follow-up should first address late-scan baseline structure and these nonadjacent control counterparts. None is presently a credible stellar technosignature candidate.

## Qualification and limits

All six SIGPROC headers call the source KEPLER-160. Roles follow the dedicated catalogue and the independently published alternating scan sequence. The original name-based rejection is preserved in results_ls5_header/preflight.json; the explicit, prespectral role amendment is LS5_POINTING_AMENDMENT.md.

The last designated ON header is 0.248 degrees from the published target coordinates; its centering is unresolved. The approximate b/c separation is 31.912 stellar radii, not a close conjunction. The 31.786–32.033 period/epoch corner range omits known transit-timing variations, stellar-radius uncertainty and unknown orbital nodes. It is not a confidence interval. No calibrated target sensitivity or occurrence limit is inferred.

The 4–64 second envelope search is a reanalysis. [Perez et al. (2020)](https://seti.berkeley.edu/kepler160/BL_Kepler160.pdf) already searched these observations for narrowband drift signals and short artificially dispersed broadband pulses. [Heller et al. (2020)](https://arxiv.org/abs/2006.02123) supplies the NASA-default b/c ephemerides and describes transit-timing variations. Their results and sensitivities are not transferred to this detector.

## Selection record

The initial five-host shortlist had no exact host-alias match. The declared expansion queried 1944 default transiting planet rows, including 733 hosts with at least two transiting rows. After excluding the four previously searched LS hosts, four systems matched the limited host/HD/HIP/TIC identifier cross-match. This is not a complete all-alias survey.

| Matched new host | Dedicated cadences | Outcome |
|---|---:|---|
| GJ 9827 | 0 | One medium product in target-only query; no dedicated sequence |
| LHS 1903 | 0 | Three medium products on separate dates; no dedicated sequence |
| HIP 41378 | 0 | Four medium products; default rows lack complete geometry |
| Kepler-160 | 3 | L and S have six scans; dedicated C listing has five |

Kepler-160 target-only metadata also exposes observations from September 2020. These were not substituted into this frozen June sequence and remain a possible later epoch.

## Reproducibility

Public freeze commit: `54c35156f83ee1fdaf8508f6e71fa07ae78598dc`, tree `30edc156a59058b94e2c340b37a1393643d6b9b4`, published and ref-verified before spectral contact.

Configuration SHA-256: `c164351ad2853fa114e110523dab91e32c057347e27a89b80ec4ca292a45af0f`. Result identity: `5f063e62178e8111608d6255dfe8fab8ca81cdc38a9b6d7b780a7429e9aa54d2`.

All 138 LS tests passed, including four checkpoint integrity tests. The broad repository suite was also attempted: its first attempts exposed missing dependencies; after installation, its log ended in an older M36 inventory test without a unittest completion summary. No full-suite pass is claimed. The completed LS test suite covers the unchanged detector, filterbank adapter and new checkpoint handling.

The report generator verifies result identity, every checkpoint against the frozen configuration, and exact reproduction of the adjacent-OFF veto. DATA_MANIFEST_LS5.sha256 records each full-file digest and public URL. Raw files are excluded from commits.

```bash
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_ls*.py' -v
PYTHONPATH=src:scripts python scripts/ls5_screen.py config/ls5_kepler160_s_light_sail.json
PYTHONPATH=src:scripts python scripts/ls5_result_report.py
```
