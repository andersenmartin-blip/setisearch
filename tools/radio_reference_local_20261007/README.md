# Local Voyager engineering reference — 7 October 2026

This is the distinct second and final infrastructure route of the new 7–20 October plan. The old CI run remains FAILED_CLOSED. No pilot, historical holdout, fresh scientific validation or ON/OFF search is executed here.

## Reproduce once in a fresh output directory

With Python 3.12, numpy 2.3.5, scipy 1.17.0 and matplotlib 3.10.8 installed:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout 1800s python run_reference.py --download --output results_reproduction
```

The command uses the normal documented public source URL only if the FIL is absent, verifies the pinned byte-count/SHA256 before reading values, refuses an existing output directory and saves a new reproducible output package. The downloaded file is 67,109,246 bytes. Downloading this public engineering reference again for reproduction would not make it a new observation or fresh validation. The current authorized execution is one local run; this README does not activate another job.

The prospective contract and SHA256 manifest preserve the chosen source, preprocessing, declared band, drift grid, threshold, full output retention, resource limits and known-carrier gate. Read the authoritative per-file header for the observation date (19 September 2016); the upstream tutorial contains an older December 2015 narrative. The upstream notebook and BSD reader-specification license are retained for provenance.

`all_threshold_channels.csv` retains every declared reference-frequency channel with maximum engineering score >=10; this can include many adjacent channels associated with the same physical feature. `representative_frequency_peaks.csv` is a separate descriptive local-maxima view. `all_search_channels.npz` retains all searched frequencies, winning drift and score, including below-threshold channels. No clustering removes entries from the full threshold list. Scores are a custom row-MAD-standardized track statistic, not turboSETI S/N or calibrated significance. No sky candidate is claimed.

The source receipt is written before header/array reading. Spectrum and carrier waterfall precede detection or carrier acceptance judgment. The resource receipt measures process CPU, peak RSS and elapsed analysis-command wall time; the initially completed source download and pre-run documentation are outside that analysis-command interval.
