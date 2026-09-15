# LS7T evidence and reproduction

This directory contains instrument telemetry and diagnostic gain arithmetic,
not image pixels or photometry. See [findings](../LS7T_CALIBRATION_CONTRACT.md)
and [pre-acquisition scope](../LS7T_SCOPE.md).

The exact product is SCI_RAW_HkExtended for visit
CH_PR300024_TG000301_V0300, OBSID 1015522. Seven range objects total 165,480
bytes: six FITS header blocks and a 148,200-byte binary table. The reconstructed
metadata FITS packages the original table header/data with a synthetic primary
HDU and padding for convenient reading; it is not an additional acquisition
or a byte-for-byte copy of the full remote file. The original object's trailing
1,560 padding bytes were not acquired. Range manifests preserve UTC acquisition times, ETag,
Content-Range, exact product name and SHA-256. Derived CSV gzip uses mtime=0.

Requires Python 3, NumPy and Astropy. Verified versions appear in summary.json.
Run from the repository root:

```bash
python3 scripts/ls7t_acquire_hk.py --offline
python3 scripts/ls7t_assess_contract.py
```

For an intentional fresh acquisition, omit --offline. The script fixes the
single visit/product and a five-megabyte limit, requires consistent verified
HTTP 206 responses and rejects unexpected FITS structures before table reading.
It does not retry a rejected range as a full download.

The assessor reuses the verified LS7S gain FITS and GPL PIPE reader, and only
the LS7R raw header cards for onboard correction flags. It extracts and executes
the unchanged reviewed gain function, without importing PIPE or running a
photometry pipeline. Native input remains float32 for that path; explicit
alternative formulas are float64. All are labelled diagnostics.

Offline input-range reconstruction and a separate output-directory audit
reproduce summary.json and hk_gain_diagnostics.csv.gz byte-for-byte.
See clean_reproduction.json and verification.log. This is reproducibility and
independent arithmetic within this project, not external review.

source_identities.json pins fourteen inspected CHEOPSim/common_sw sources.
Follow its permanent URLs to obtain those source bodies; they are not vendored
because no redistribution license was established. Each record includes the
Git blob identity, SHA-256 and size checked during this work. Existing LS7S
records identify the already preserved GPL PIPE code.

calibration_contract.json states the remaining input decisions. No gain choice,
native detector, recovery result or observing-coverage claim is adopted here.
