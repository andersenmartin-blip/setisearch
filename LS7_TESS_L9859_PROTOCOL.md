# LS7: L 98-59 TESS sector 28 qualification pilot

Status at freeze: prospective engineering experiment, 12 September 2026.
Publication and execution are authorized by the owner's ongoing project direction
and request to continue with TESS. This is one integrated optical pilot. It does
not reopen or change the LS1 radio result or the closed M43AI evaluation.

## Data and selection

Use only the two public SPOC 20-second products pinned by full filename and byte
count in `config/ls7_tess_l9859.json`: TIC 307210830, sector 28, approximately
31 July–25 August 2020. Selection used archive metadata and FITS headers, not
measured light-curve or pixel values. Freeze this protocol, configuration, code,
tests and dependency pins on the public science branch before opening the arrays.
Record retrieved SHA-256 hashes, observation headers and software versions.
Other sectors and targets remain unopened for subsequent evaluation.

TESS measures approximately 600–1000 nm with 21-arcsecond pixels. It cannot
establish laser coherence or the spectrum of a transient; a narrow 1.06-micron
beam is outside its nominal band. The proposed optical light-sail signatures
motivate timescales, not an assertion that a detectable signal exists here.

## Fixed processing and screening

1. Verify TIC, sector, TDB time reference, 20-second sampling, matching LC/TPF
   cadence IDs/times and flux units. Reconstruct calibrated target pixels before
   ground cosmic-ray subtraction using the `TARGET COSMIC RAY` extension, its
   detector coordinates and cadence IDs. Preserve the corrected aperture sum and
   compare it to SPOC SAP. This does not reconstruct uncalibrated CCD data.
2. Sum the SPOC optimal aperture (mask bit 2). Use the intersection of TPF and LC
   `QUALITY == 0`, finite times and finite aperture pixels. Split at missing IDs,
   excluded samples or time gaps greater than 30 seconds. Do not fill gaps.
3. In each run of at least 126 samples, subtract a 121-sample running median.
   Estimate one fixed noise scale per run from 1.4826022185 times the MAD of
   first differences divided by sqrt(2). Exclude 60 samples at each run edge.
   Screen positive and negative 2-, 3-, and 5-sample box sums divided by the
   noise scale and sqrt(window length). Threshold: 8. These scores are not
   Gaussian significance, a false-alarm probability or a SETI detection statistic.
4. Keep the strongest overlapping window, with two samples of separation; sort
   deterministically. Cap each sign at 2,000 events and fail qualification if
   truncated. Archive the retained ledger, not just interesting events.
5. For each event, compare its mean excess image to a local median image using
   sidebands up to 60 samples away, excluding the five adjacent samples. The
   positive aperture reference image is the empirical spatial profile. Require
   cosine similarity >=0.90, centroid displacement <=0.5 pixel, brightest-pixel
   positive-excess fraction <= profile peak fraction +0.20, and absolute median
   outside-aperture excess / mean aperture excess <=0.5. Require at least three
   usable outside pixels. These are provisional instrumental screens. On-target
   stellar flares and unresolved contaminants can pass them.

## Fixed digital recovery and nuisance controls

Choose 10 evenly spaced indices in the list of eligible times having 200 valid
samples on both sides. Select using time/quality only, without checking flux.
Use 401-sample local contexts, the same baseline and the frozen full-run noise.

Inject an aperture-confined empirical stellar profile with fractional amplitudes
0.1%, 0.3%, and 1% relative to its local median aperture flux. Shapes: 30-, 60-,
100-second top hats and two 30-second pulses separated by 87 seconds. Test phases
0 and 10 seconds. Integrate each shape over continuous 20-second exposure bins;
the individual 2-second readout gaps are approximated as uniform live time.
This gives **240 stellar-profile injections**. The doublet is a duration model,
not a test that the light-sail mechanism predicts this system's flux.

At the same anchors/phases add **40 nuisance trials**: a 1% equivalent aperture
signal in the brightest single pixel, or distributed uniformly across the stamp,
both with a 30-second shape. Add **20 unchanged null trials**. No random anchor
selection, data-dependent amplitude changes or threshold tuning is allowed.

Recovery requires a screening window centered within 20.1 seconds of an injected
peak, score >=8 and passing pixel morphology. If any matching unmodified window
already scores >=8, mark the trial baseline-confounded and do not count recovery.
Keep confounded trials in the conservative headline denominator and separately
report their fraction. Select the highest-scoring matching window, even if
another window would pass morphology. Preserve all 300 trial records.
For nuisance acceptance, count every above-threshold, morphology-passing trial,
including baseline-confounded trials, to avoid understating false acceptance.

The provisional engineering gate requires >=90% recovery of the **60 single-pulse
1% trials**, <=5% acceptance of the **40 nuisance controls**, <=20% confounded
stellar trials, intact products and no event-cap overflow. Failure is a useful
result and does not permit refitting on this sector. Passing qualifies only
this restricted experiment, not an adopted survey detector.

These injections occur after mission processing and quality selection. They
measure digital sensitivity on accepted backgrounds; they do not measure
hardware response, SPOC flagging losses, full transient completeness or a
population upper limit. The empirical injection profile is also the reference
used by the morphology test. This deliberately favorable spatial model needs
independent off-profile and real-flare validation before scientific use.

## Geometry, outputs and interpretation

Annotate all native triggers and summarize accepted exposure within a projected
pair separation of one stellar radius using the frozen LS3 b/c/d ephemerides.
Use BJD_TDB = BTJD + the FITS reference, never UTC/MJD interchangeably. The model
is circular, edge-on, one dimensional, and assumes a common node. It omits
inclination, node and ephemeris uncertainties; it is **not** a planet occultation,
beam interception probability or precise conjunction forecast. Do not gate the
search or rank evidence by this geometry. No targeted conjunction significance
test is planned.

Publish a source manifest, coverage/quality counts, both-sign event ledger,
per-trial recovery/control ledger, summary, scientific figure and readable report.
Do not publish raw FITS files. Native events remain instrumental/astrophysical
screening outputs; no event is promoted as an LS candidate by this pilot.
No event count alone establishes a discovery or an astrophysical null result.
The optical band, timescale, target and calibrated time series complement LS1's
radio analysis but have different sensitivity and denominators.

## Reproduction and next decision

```sh
python -m pip install -r requirements_ls7.txt
PYTHONPATH=src python -m unittest discover -s tests -p test_ls7_tess.py -v
sha256sum -c LS7_FREEZE.sha256
PYTHONPATH=src python scripts/ls7_tess_pilot.py
```

The runner refuses an existing result directory or a mismatching freeze. A
reproduction can specify another empty `--output` directory. The default raw
cache is ignored by git. A subsequent method change must be named, justified and
frozen separately. First inspect any qualification failure; then use another
unopened sector for a new independent evaluation. Do not expand automatically
to every available sector or spend new analysis credits on an unqualified rule.

## Sources

- [MAST exact target-pixel product](https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:TESS/product/tess2020212050318-s0028-0000000307210830-0190-a_fast-tp.fits)
- [NASA TESS data products](https://heasarc.gsfc.nasa.gov/docs/tess/data-products.html)
- [NASA TESS cosmic-ray processing and reversible 20-second corrections](https://heasarc.gsfc.nasa.gov/docs/tess/TESS-CosmicRayPrimer.html)
- [Guillochon and Loeb optical light-sail model, submitted 7 September 2026](https://arxiv.org/abs/2609.07574)
- [Existing LS3 target/ephemeris inventory](results_ls3_inventory/inventory.json)

Primary product and processing documentation checked 12 September 2026.
