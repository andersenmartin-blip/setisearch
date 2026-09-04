# LS1 Stage 1 medium-resolution result

Status: **COMPLETE — TWO EDGE-ALIGNED EVENTS SURVIVE THE FROZEN ADJACENT-OFF
VETO; HIGH-TIME-RESOLUTION FOLLOW-UP REQUIRED; NO TECHNOSIGNATURE CLAIM**.

GitHub Actions run
[`33872124679`](https://github.com/andersenmartin-blip/setisearch/actions/runs/33872124679)
reproduced the metadata-only selection of cadence `--63424`, recovered the
frozen synthetic injection, downloaded and hashed all six public `.0002`
products, and completed the preregistered 1100--1900 MHz ABACAD screen without
retention truncation.

The three ON scans produced 265 events at the frozen score threshold of 8.0.
The frequency-coincidence test against their adjacent OFF scans vetoed 263.
Two events remain, both in the first ON scan A1:

| Frequency (MHz) | Relative time (s) | Width | Duration | Score | Stage 1 disposition |
|---:|---:|---:|---:|---:|---|
| 1557.0288--1568.7447 | 228.707--293.132 | 4 base bins | 64 s | 25.9876 | HTR follow-up |
| 1149.8022--1152.7290 | 0--64.425 | 1 base bin | 64 s | 8.1989 | HTR follow-up |

Both events touch a scan boundary: the stronger one reaches the end of A1 and
the weaker one begins at its start. That is suspicious for acquisition or
bandpass settling, but boundary rejection was not part of the frozen Stage 1
veto and is therefore not applied after seeing the data.

Stage 1 authorizes only a separately frozen `.8.0001` follow-up of A1 and its
adjacent OFF scan B1. The follow-up will ask whether the medium-resolution
envelope is reproduced and whether it contains the predicted subsecond
diffraction-like modulation. Even a positive follow-up remains an uncalibrated
candidate requiring independent observation.

## Reproducible identities

| Item | SHA-256 |
|---|---|
| Stage 1 result identity | `212db71cbe8890715cdb74942ecc8651ab1a5c74dd7e62ebd0e4967a74fbc81b` |
| `results_ls1/screen.json` | `5a62b75eda4e5c33c83f35a451258d6d7cd19c9cabd564bf01af44c7d2e1f646` |
| Frozen LS1 configuration | `a429a9cb1bad4484b7a2fd0cb47834184bb6a939e7f0dc53790d08d5f20e1cdd` |
| Raw-source hash manifest | `2a9f9a19ec276021f463b64f7b1879d6204cf2806361c9a9aac56031e88cd793` |
| Derived-results manifest | `ef69657345906a4813e3e6c5cb80ecf34fca9ab84d60c3c3502ca2e0c473a1f8` |

Only source hashes and derived records are published. The raw spectra are not.
