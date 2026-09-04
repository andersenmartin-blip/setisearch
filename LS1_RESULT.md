# LS1 final result

Status: **COMPLETE — NO HIGH-TIME-RESOLUTION-SUPPORTED CANDIDATE; NO
TECHNOSIGNATURE CLAIM**.

LS1 searched one public GBT L-band ABACAD cadence of HD 219134 for the short,
broadband leakage morphology motivated by Guillochon & Loeb (2015). The target,
cadence, medium-resolution templates and vetoes were frozen before Stage 1
spectral access. The two Stage 1 survivors then received a separately frozen,
candidate-conditioned high-time-resolution test.

## Outcome

Stage 1 evaluated all six `.0002` scans over 1100--1900 MHz. Of 265 ON events
above the screening threshold, 263 were rejected by the frozen adjacent-OFF
frequency-coincidence veto. Both survivors occurred in A1 and touched a scan
boundary.

GitHub Actions run
[`33873522360`](https://github.com/andersenmartin-blip/setisearch/actions/runs/33873522360)
then verified the HTR freeze, fetched and hashed only A1 and adjacent-OFF B1,
and evaluated the two exact candidate bands at 0.349525 ms sampling.

| Candidate | HTR ON envelope score | HTR OFF envelope score | Subsecond scales supported | Disposition |
|---|---:|---:|---:|---|
| `LS1-A1-1557` | -123.583 | 525.919 | 0 | Rejected by adjacent-OFF HTR envelope |
| `LS1-A1-1150` | -25.222 | -57.518 | 0 | Not confirmed as a positive HTR envelope |

Neither candidate reproduces the required ON-only positive envelope, and
neither supports the frozen diffraction-like subsecond criterion. LS1 therefore
closes with zero HTR-supported candidates. The `.0002` boundary events are
consistent with instrumental/RFI structure rather than the searched signal
class under the frozen decision rule.

## Interpretation boundary

This is a null result for one 2016 cadence, one 1.1--1.9 GHz band and the exact
frozen template bank. It is not a general exclusion of light sails: the
motivating paper's illustrative optimum lies at tens of GHz, event timing is
unknown, and LS1 has no calibrated end-to-end sensitivity or occurrence-rate
model. Screening scores are not Gaussian significances.

No independent observation was performed because no candidate passed HTR.
No technosignature is claimed. Only hashes, environment records and derived
summaries are published; raw telescope spectra are not.

## Reproducible identities

| Item | SHA-256 |
|---|---|
| HTR result identity | `03561ee7d3cf99d49eadd3848a7bf9f4ebf61c95fe63dd1763592c4def29ec56` |
| `results_ls1_htr/followup.json` | `49674d51acc0d1bb11c2e562b7905b4c5d1bd1c2b7192a4fea894a94fdd62f92` |
| Frozen HTR configuration | `c2cef002c7e214495995254e977d553d988e54d7e6b23a85e8ebd80cd1266ab1` |
| HTR source-hash manifest | `64115a969372b1e18ea55115520d74155732b71f0dd3828be7eb842b141e1808` |
| HTR derived-results manifest | `b40d8775439b3ff8dd4e9c4124c80bd9902796c93182ceeac9dcb12702e4994e` |

The Stage 1 workflow was incidentally retriggered when the HTR scripts were
published. Run `33873522161` stopped immediately at its immutable
already-published-result guard, before data access. The canonical Stage 1 run
remains successful run `33872124679`.
