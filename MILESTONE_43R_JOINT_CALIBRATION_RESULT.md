# M43R joint calibration and native-injection pilot

The frozen bounded pilot is complete. It uses 37 selected templates, all eight
widths and four activity subsets over 4,097 central score carriers, approximately
11.6 kHz around 1412.5 MHz. All scans are from one observing sequence. This is
the first measured native-injection recovery exercise of the connected M43 path.
It does not authorize an astronomical candidate or establish a full-search limit.

## Fixed threshold and held-out noise shifts

The frozen rule gives a threshold of
**10**. The predeclared floor of
10 dominates the calibration maximum of 8.33997726; thus the
threshold did not need to rise above that floor. The held-out maximum is
8.38696384. The fixed certificate was saved before held-out
evaluation or signal insertion. Of the separate 128 rows,
**0/128** were at or above that threshold and
**0/128** strictly above it. These are correlated
within-sequence, pre-veto resampling exceedances, not independent observations
or a measured physical false-alarm probability. The smallest possible calibration
rank p is 1/129, approximately 0.007752; ties use the inherited inclusive rank.

The unmodified background retained 0 ON and 0
OFF members, with 0 ON members passing the
evaluated physical vetoes. Any background member remains diagnostic only.

## Signal recovery

Eight fixed truths cross parent templates 0 and 1700 with all four activity
subsets at the central carrier. Each has nominal active-epoch SNR 0, 8, 32 and 64.
The zero level reuses one background execution eight times; it is not eight
independent trials. There are 24 nonzero injections and 25 detector executions.

| Nominal active-epoch SNR | Endpoints | Retained | Pass physical vetoes | Recovered incl. rank |
|---:|---:|---:|---:|---:|
| 0 | 8 | 0 | 0 | 0 |
| 8 | 8 | 8 | 8 | 8 |
| 32 | 8 | 8 | 8 | 8 |
| 64 | 8 | 8 | 8 | 8 |

Recovery requires the exact injected template, activity subset and carrier,
at any width, passing all evaluated physical vetoes and the fixed rank cut.
Retention and physical passage are shown separately so losses stay visible.

| Parent template | Active epochs (1-based) | SNR 8 | SNR 32 | SNR 64 |
|---:|---|---|---|---|
| 0 | 1, 2 | recovered | recovered | recovered |
| 0 | 1, 3 | recovered | recovered | recovered |
| 0 | 2, 3 | recovered | recovered | recovered |
| 0 | 1, 2, 3 | recovered | recovered | recovered |
| 1700 | 1, 2 | recovered | recovered | recovered |
| 1700 | 1, 3 | recovered | recovered | recovered |
| 1700 | 2, 3 | recovered | recovered | recovered |
| 1700 | 1, 2, 3 | recovered | recovered | recovered |

Signal samples were added to normalized native channels before filtering and
gathering. Complete affected windows and proxy columns were recomputed; receiver
signatures used the same additions. The original telescope receipts remain
unaltered and each overlay has its own provenance. These idealized, on-template,
single-channel injections do not include fractional leakage, intra-integration
smearing, varied carrier positions or a source population. The table is a small
engineering sensitivity pilot, not an astrophysical completeness curve.

All 24 nonzero injections were recovered, including all eight at nominal SNR 8;
none of the eight reused zero-level endpoints was recovered. The selected
strengths therefore do not locate the transition from missed to recovered
signals. The useful next experiment is a newly frozen extension below SNR 8,
with fractional-channel profiles, integration smearing, off-template truths and
additional carrier positions. The present 24/24 result must not be generalized
to that harder population or compared directly with the older M41 denominator.

## Evidence and reproducibility

- Public pre-evaluation freeze: `a21197fb0b0169b1b7e576b7d9aea2190ef08a5a`.
- Result seal: `8cf756a77830979e7cf86ee25862c6247b8e40fb1dc1ed5b744b60efc5209b51`.
- Threshold certificate: `9c8fe4dccaa4c38e564dd251158e044cbcbae72896dcb9ba6379c8080e9f2065`.
- Config SHA-256: `bdb495d46549705304af266cfea6bec412035831bf5224c541377dc9219de5bc`; 219 pinned dependencies.
- Twelve focused tests pass: five new overlay/fixed-calibration tests plus the
  seven unchanged M43Q integration tests. Earlier 165-test evidence is reused
  for unchanged code rather than repeating the full suite.
- All 3,751,800 cropped ON score cells match
  receipt-bound ancestor scores exactly across 24 native caches. The 96 M43P
  arrays were verified before reuse. Zero new telescope data requests.
- Calibration evaluated 620,908,544 scrambled
  score cells; the held-out pass evaluated the same number. Cell counts are
  arithmetic coverage, not independent statistical samples.
- Successful execution took 206.254 seconds. A first launcher
  reached no evaluation because the public freeze fetch was still pending;
  its `bootstrap_wait.log` is retained. No scientific plan amendment was needed.

All 32 endpoints, all 24 injected compact member inventories, source-overlay
receipts, stage certificates, null maxima and run logs are in
[`results_m43r_joint_calibration/`](results_m43r_joint_calibration/).
Each compact trial includes the hash of the complete in-memory pipeline result;
compact audits are not represented as the full pipeline serialization.
The SHA-256 manifest covers the published report, code, plan and artifacts.

Run from the repository with the same pinned Python/NumPy environment and
verified M43H sources/M43P anchor arrays:

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python scripts/m43r_joint_calibration.py \
  --freeze-commit a21197fb0b0169b1b7e576b7d9aea2190ef08a5a \
  --anchor-root /path/to/m43p_work --source-root /path/to/m43h_work/live
```

Earlier full-band numerical qualifications and their denominators remain intact.
Fresh independent observing coverage, a broader bank/frequency calibration and
more realistic injections remain necessary before scientific search claims.
