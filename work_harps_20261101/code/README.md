# HARPS first stage emission detector

This is an independent, bounded implementation inspired by the running-continuum
and consecutive-pixel criterion in Fields and Goodman (2025),
https://arxiv.org/html/2508.08628v1. No upstream source code is copied. It is a
first-stage screening algorithm, not a reproduction of their complete survey or
a classifier of extraterrestrial lasers.

The frozen configuration searches 3800–6900 Angstrom in the supplied wavelength
frame, using an odd 101-pixel centered median and population standard deviation.
The statistic includes absorption lines and candidate emission in the window.
Four through sixty consecutive samples at or above median plus 3.5 local standard
deviations constitute a preliminary emission hit. Every threshold run is saved,
including shorter and wider runs. A local contrast of 3.5 is not a calibrated
Gaussian significance or false alarm probability.

Nonfinite flux and exactly zero flux are masked. Exact-zero samples are treated
as filled or missing samples in this pilot. A 50-pixel margin on either side of
each valid segment is excluded, preventing padded windows from contributing.
Wavelength gaps larger than 1.5 times the median wavelength step split segments.
No airglow line mask, repeated-epoch requirement, cosmic ray veto, or Gaussian
profile acceptance gate is applied at this stage.

Input Phase-3 spectra have air wavelength (TUCD1 `em.wl;obs.atmos`) in Angstrom,
with `SPECSYS=BARYCENT` in the inspected development files. Flux is uncalibrated
ADU. Their ERR vectors contain only NaNs, so those vectors are not used as
uncertainties. The reader records these metadata rather than silently changing
wavelength frame or units. Follow-up comparisons must handle air/vacuum and
barycentric/topocentric transformations explicitly.

## Usage

With the required NumPy, SciPy and Astropy versions installed:

```bash
python code/test_harps_detector.py
python code/harps_detector.py INPUT.fits --config code/DETECTOR_CONFIG.json --output OUTPUT --save-arrays
python code/plot_development.py OUTPUT
```

The Python interface is `read_spectrum(path)` and
`analyze_arrays(wave, flux, config=None)`. The latter returns a JSON-serializable
result and numerical arrays. Main-protocol callers must separately preserve
input identity, code and configuration hashes and output provenance.

`DETECTOR_FREEZE.json` pins the code and configuration after the first development
spectrum. Two later, explicitly assigned development spectra were analyzed with
the unchanged detector; their receipt is `../development/DEVELOPMENT_SUMMARY.json`.
No validation or main-science FITS was inspected by this implementation task.

## Checks performed

The hand-constructed test checks four-pixel inclusion, short and wide run
classification, flushing a terminal run, zero and NaN gaps, and excluded edge
windows. It also independently calculates several scalar medians and standard
deviations. On the first real development spectrum, 308 scalar window checks
gave exact medians and a maximum population-standard-deviation disagreement of
3.13e-10 ADU. These are arithmetic and boundary checks, not sensitivity validation.

The displayed FWHM is an interpolated half-height width in the continuum-subtracted
data at the highest-contrast sample. It is neither a deconvolved physical width
nor an instrumental-profile fit.
