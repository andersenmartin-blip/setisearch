# HD1461 motion, exposure response and prospective radio design

**The metadata audit is complete. Twelve new engineering tests pass.**
The old circular-orbit construction is not valid for HD1461's retained eccentric
working parameters. A finite-exposure injection component and a concrete
three-window resource proposal are now available. **No selected telescope
spectrum has been read, no coordinate has been adopted, and no source-specific
search or calibration has been qualified.**

This continues the active radio plan from science commit
`a841e1912ac5243a467ef43e900f0d462245bfbb`. The immutable HD1461 preparation
contract remains SHA-256
`c434c6f0615dfec165512195dcae888d8aa4b33a29efdb5037895ba5530d8bcb`.
The existing `neighbor9` primary, detector, source reader and durable acquisition
code are unchanged. This is preparation evidence, not a new radio observation.

## Timing and coordinate comparison

The six scans contain **96 integrations of 17.986224128 seconds**, covering
**1969.779586 seconds** from first start to last end. The earlier approximately
1682-second figure describes first-to-last scan starts, not the full elapsed
observation. Scan gaps are about 49.220414 seconds, except the final gap at
46.220413 seconds. Split-JD timing differs from the earlier single-MJD arithmetic
by at most **0.308 microseconds**; this is not a material motion error here.
All evaluated timestamps have final IERS-B UT1 and polar-motion coverage.

The comparison uses four fixed ICRS directions: the catalogue and each of the
three ON headers. Every direction is evaluated over the same complete time
inventory, including OFF times for a common celestial hypothesis. No unprovided
astrometric epoch, distance or proper-motion propagation is inserted. The GBT
site coordinates are the retained project geodetic values; they are not new
measurements of the telescope position.

At an illustrative **1500 MHz**:

| Metadata-only quantity | Result |
|---|---:|
| Native channel spacing | 2.835503418 Hz |
| Catalogue-direction observer frequency sweep across midpoints | 159.845102 Hz |
| Largest observer-only start-to-end sweep within one integration | 1.581162 Hz |
| Largest header/catalogue absolute frequency correction difference | 185.337852 Hz |
| Largest difference after matching the first carrier frequency | 0.046347 Hz |
| Header/catalogue angular separation | 34.23243–34.23316 arcmin |

Thus these two coordinate scenarios have almost the same short-term drift once
their constant carrier offset is removed. That numerical resemblance **does not
establish where the telescope pointed**. The pointing hold remains necessary.
The retained proper motion amounts to only about 11 arcseconds over an
illustrative 25 years; that scale comparison is not an epoch correction.

The [Astropy velocity documentation](https://docs.astropy.org/en/stable/coordinates/velocities.html)
specifies the optical convention and multiplicative correction. The audit uses
the observer frequency multiplier `1 + vcorr/c`, with Astropy's builtin ephemeris
and a hash-pinned packaged IERS-B file; automatic downloads are disabled.

## Why the old motion construction cannot simply transfer

The previous source used an explicitly circular working orbit. Its two sampled
phases can generate all circular phases by sine/cosine coefficients. HD1461's
retained composite row has **P = 5.77152 days, a = 0.0634 AU, e = 0.172**.
Applying the circular construction at this nonzero eccentricity loses the
higher harmonics of the Keplerian velocity.

Using 2048 equally spaced mean-anomaly offsets at the first ON midpoint and
the retained omega of −10 degrees, the new direct Kepler solver compares exact
and two-phase velocities. A free constant carrier offset is removed by matching
the first frequency; it therefore cannot explain away the measured errors.

| Comparison at 1500 MHz, unit projected scale | Result |
|---|---:|
| Circular analytic/quadrature check, maximum velocity residual | 1.75 × 10⁻¹⁰ m/s |
| Eccentric approximation error over all six scans | **8178.353204 Hz** |
| Eccentric approximation error over ON scans only | **6810.913706 Hz** |
| Sampled phase cases exceeding one native channel | **2046 / 2048** |
| Largest sampled orbital sweep during one integration | **159.971582 Hz**, or 56.4173 channels |
| All-phase acceleration bound for the stated P/a/e | 2.196372 m/s² |
| Corresponding orbital integration-sweep bound | 197.658910 Hz, or 69.7086 channels |
| Largest sampled midpoint departure from a linear exposure track | 0.008017 Hz |

The acceleration bound is `n² a / (1−e)²`, the periastron acceleration norm.
It bounds the line-of-sight component for this idealized Keplerian model; it
does not cover uncertainties in P/a/e, transmitter rotation or other planets.
The 2048 sampled comparisons are not a continuous phase-bank coverage proof.

An additional radial-only relativistic comparison differs from the first-order
emitter model by up to **5.097073 Hz** after carrier anchoring. That comparison
omits transverse motion and is not an adopted orbital correction. It identifies
another accuracy term that cannot be silently assumed negligible relative to
the 2.84 Hz channels.

The [NASA archive documentation](https://exoplanetarchive.ipac.caltech.edu/docs/pscp_calc.html)
explains why a composite row need not be one consistent solution. Its
[column definitions](https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html)
also preserve differing stellar/planetary periastron-angle conventions.
The retained small snapshot does not resolve the orbital reference, uncertainty,
absolute time system or astrometric epoch. The audit therefore uses relative
phase comparisons, not the snapshot's Tper as an asserted BJD-TDB ephemeris.
No old circular-source result has been changed or relabelled.

## Finite-exposure injection component

`exposure_radio.py` adds time-averaged digital power to raw float32 rows **before
normalization**. For a linearly moving top-hat line and rectangular native channel
cells, it integrates the overlap exactly between its piecewise-linear breakpoints.
Zero-width lines, reverse drift and static boundary cases have explicit rules.
Missing support and failed power conservation raise errors rather than truncating
or renormalizing away a loss.

Twenty-four unit-power development profiles cover four intrinsic widths and six
sweep sizes. Total float64 digital power is preserved. For a one-channel intrinsic
line swept across 56.4173 channels, its maximum single-channel share drops to
**0.0177250**, compared with 1 for the unswept centered case. Wider filters collect
more of that power with their corresponding noise penalty. This demonstrates why
the previous point-per-integration injections cannot certify this source's response.

The component assumes ideal channel cells, uniform emission and locally linear
drift. It does not model the GBT polyphase/FFT response, bandpass, calibrated flux
or EIRP. It has not yet been integrated with an adopted eccentric bank and a new
end-to-end scientific evaluation panel. The 0.008017 Hz sampled curvature result
is useful preparation, not a general sub-integration error certificate.

## Concrete prospective extraction proposal

Three adjacent full HDF5 frequency chunks around the middle of the recorded band
are assigned roles before looking at amplitudes. The proposed extraction is the
central **16384 channels** of each chunk, with four 4096-channel normalization
blocks. Half-open archive channel intervals are exact:

| Role | HDF5 frequency chunk | Archive interval | Proposed first-ON carrier center, MHz |
|---|---:|---|---:|
| Calibration | 150 | [157802496, 157818880) | 1478.796787375 |
| Validation | 151 | [158851072, 158867456) | 1475.823546543 |
| Pilot | 152 | [159899648, 159916032) | 1472.850305710 |

The proposal separates **decoded spectral chunks**, not merely selected columns;
two column ranges within one compressed chunk would expose shared native payload.
These remain three frequency regions of **one cadence**, not independent observing
visits. The proposed score grid has 513 carriers at the native spacing and 64
guard carriers on each side. Actual template/filter/receiver support still needs
certification against a frozen bank. Carrier anchoring here refers to observed
frequency at the first ON midpoint, not a known emitted frequency.

The resource proposal allows one fully charged session per role, each at most
500 requests, 512 MiB and 1200 seconds: total ceilings 1500 requests, 1.5 GiB and
3600 seconds. The illustrative 128-template ceiling gives a **67,715,072-byte**
search-array model, under a proposed 128 MiB limit. Acquisition's separate buffer
model is **96,993,280 bytes**. These are not total process RSS limits or a promise
that three downloads fit: compressed chunk sizes, actual metadata overhead and
live codec behavior remain unqualified. The extracted raw+normalized matrices
would total 36 MiB, while all decoded chunks would total 1152 MiB across stages.

`prospective_design.json` is deliberately **NOT_FROZEN_NOT_EXECUTABLE** and has no
adopted motion bank, scientific panel, recovery/control gate or calibration
transfer contract. Its artifact type cannot be used as a ready source contract.
The original preparation contract has not been edited.

One concrete integration gap is now explicit: `pipeline_radio.Calibration`
is bound to one exact `Context`. Separate real frequency windows change that
context. The earlier synthetic test used distinct realizations at the same
geometry; it did not qualify calibration transfer between real windows. A new
explicitly bound cross-window design is needed, without falsifying context hashes
or treating an empty conditional null as a usable tail. The resource template
ceiling is not a claim that it covers HD1461's orbital domain.

## Verification and next work

The **12 new tests** cover independent Kepler-equation bisection, the circular
analytic limit, rejection of eccentric input by the circular constructor,
integration clocks and overlap rejection, the acceleration bound, finite-exposure
analytic cases and independent time quadrature, raw-power placement and complete
support, and compressed-payload separation. The initial acceleration test used an
incorrect LOS saturation expectation; the retained qualification record explains
its correction. The physical bound and detector rules were unchanged.

Reproduce in the pinned isolated runtime using
`config/radio_motion_requirements_20260926.txt`:

```sh
PYTHONPATH=src:scripts python scripts/radio_motion_qualification.py
```

`results_radio_motion_2026-09-26/` retains all 96 clock rows, four coordinate
scenarios, 2048 phase cases, worst-case tracks, 24 exposure profiles, exact proposed
payload identities, source references and the full test log. The immutable package
inventory is `RESULTS_MANIFEST_RADIO_MOTION_2026-09-26.sha256`.

The newly checked official operator-log route redirects to NRAO sign-on. It did
not supply a same-scan observable. The [unsent retrieval specification](RADIO_HD1461_PROVENANCE_REQUEST_2026-09-26.md)
now identifies exactly which original records would resolve the hold.

**Next autonomous preparation:** implement and qualify an explicitly identified
direct eccentric factor-table interface, preserving the frozen downstream detector
arithmetic, followed by disjoint calibration-context transfer and finite-exposure
end-to-end controls. Any model remains a declared working model until its parameter
provenance and numerical error budget are resolved. Combine these with positive
codec/receipt qualification into the eventual integrated freeze. Continue only
genuinely new same-scan provenance routes; do not repeat closed probes or invent
access. No source spectra may open merely because engineering checks pass.

M43AI remains closed; the original M43AF 112+128 holdouts, all prior candidate
dispositions and the paused LS inputs remain preserved. No external message,
observation booking or paid service was used. Three additional hourly evening
continuations are enabled for 26 September, alongside the existing daily plan;
future execution is not claimed as completed work.
