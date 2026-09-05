# LS6 TRAPPIST-1 9.92 GHz subband pilot

Status: **screen-complete-followup-preregistration-required**.

A sixth distinct stellar system has received a project LS spectrum screen, here as a limited four-scan pilot. The selected archive-labelled TRAPPIST-1 observations from 23 February 2017 cover 9.826466–10.013963 GHz. Two ON and two OFF scans provide 120.259 seconds of designated ON integration. Total input: 58,721,848 bytes.

| Scan | Role | Retained score ≥6 windows | Score ≥8 windows | Truncated |
|---|---|---:|---:|---|
| A1 | ON | 46 | 46 | False |
| B1 | OFF | 0 | 0 | False |
| A2 | ON | 21 | 1 | False |
| B2 | OFF | 0 | 0 | False |

**47 ON threshold windows; 47 survive the frozen adjacent-OFF veto.** Window counts are not independent signals. No score is a calibrated significance.

Survivors require separately frozen follow-up, pointing checks and independent data. No HTR values were read and no technosignature is claimed.

A descriptive grouping of the retained windows reveals only two shared time intervals: all end at their scan boundary. This raises a scan-end/baseline concern and does not establish astrophysical pulses. It does not alter the primary veto disposition.

| ON | Shared time interval (s) | Requested duration (s) | Retained ON windows |
|---|---:|---:|---:|
| A1 | 44.023–60.130 | 16 | 46 |
| A2 | 52.613–60.130 | 8 | 1 |

The complete frequency windows and scores are retained in results_ls6_screen/screen.json. Both OFF scans have all 64 valid base-frequency bins, so their zero-event counts are not caused by an empty or entirely invalid frequency grid. Inspect scan-end common-mode behavior before promoting any candidate.

## Scope

This is an explicitly amended ABAB pilot, not a six-scan ABACAD search or a full-band survey. A1 is checked against B1; A2 against B1 and B2. The LS1 detector thresholds, clipping, native channel aggregation and spectral widths are unchanged. The initial attempt failed because the inherited 64-second template does not fit these 60.13-second scans. A public technical amendment fixed the duration bank at 4,8,16,32 seconds based only on header length. A1 samples had been accessed before this amendment; fitting-window scores were computed internally but not returned, saved or inspected. This is not an independent held-out rerun. The failed freeze and runner are preserved, and no threshold was retuned.

The 187.5 MHz subband was chosen by metadata proximity to the inherited 10 GHz operational anchor. The other 220 medium subband files remain unopened. All seven NASA default transit epochs were absent; the pilot makes no conjunction-ranking claim. A later geometric analysis must adopt and validate published dynamical ephemerides, such as [Agol et al. (2021)](https://arxiv.org/abs/2010.01074).

Designated ON header coordinates differ from the current stellar catalogue by tens of arcseconds. They do not establish full tracking or beam-centering histories. No calibrated sensitivity, target-origin claim, or general constraint on light sails follows from this limited screen.

## Other targets checked

Kepler-446 has two individual medium-resolution products but no dedicated cadence in the scoped lookup. Kepler-732 has a complete six-scan listing, yet its three ON HDF5 positions agree with that listing and differ from NASA by 9.6821–9.6824 arcminutes. Kepler-732 spectra remain unopened. HDF5 coordinates were decoded as decimal RA hours / Dec degrees, separately from SIGPROC packed coordinates.

The initial generic HDF5 preflight attempt failed on a missing HTTP dependency; those error receipts are preserved. The later successful, proxy-aware pointing-only audit is results_ls6_header/pointing_audit.json. Missing dependencies were not interpreted as missing archive data.

TRAPPIST-1 was found under DIAG_TRAPPIST1. The archive target query also returns OFF records; exact labels and unique URLs were used for grouping. Its 224 medium products span 16 scan times and four receiver blocks. The selected pilot uses only four products near 9.92 GHz.

## Verification and reproduction

All 144 LS tests passed, including explicit four-scan veto mapping, HDF5 coordinate-unit checks, and reproduction of the oversized-template failure plus the repaired duration-bank success. The older full repository suite was attempted during LS5 but did not produce a complete passing summary; only the completed LS suite is claimed here.

Public prespectral freeze: `5aba35e7aaec5de881f71a05edabff8bed56bfed`; tree `1174bc7eb3a77cbbcffc70451744ca88beced78e`. Initial branch ref verified before starting downloads. Technical amendment `208fa0992f66120e7c0e75e89d82ac022f9f4598` (tree `a1a44bb4754e7019c90c256d87b95646427e705f`) was separately ref-verified before the successful rerun.

Configuration SHA-256: `886feddc6daf44f321bb885e6487d3d08b1bca33934068ec3212ffa08386087a`. Result identity: `fdbae28dff1f07b8be0f787de96bfcf66b7459bfb67ef9e91bc09fe993c5f55f`.

This report generator verifies the sealed result, all checkpoint identities and exact veto reproduction. DATA_MANIFEST_LS6.sha256 retains the complete input-file digests and public URLs. Raw radio files are excluded from commits and deleted after use.

```bash
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_ls*.py' -v
PYTHONPATH=src:scripts python scripts/ls6_repaired_screen.py config/ls6_trappist1_x_subband_repaired.json
PYTHONPATH=src:scripts python scripts/ls6_result_report.py
```
