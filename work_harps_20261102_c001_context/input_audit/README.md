# C001 input audit

PASS. The final inventory is bound by SHA-256 `e5a14bf22d63cbd568b2868ebfd153860a15605c6054958830f0778306763ef8`. Fourteen restored files reconcile to the three original input archives, historical acquisition/mapping metadata and two historical evidence archives. The audit checks opaque bytes and FITS/NPY headers; it reads no new flux or pixel values and makes no network requests. Historical extension02 files remain unchanged.

The six merged spectra are distinct HARPS exposures of HD103991, with barycentric air-Angstrom wavelengths and uncalibrated ADU flux. Their ERR header explicitly declares unavailable values. The fixed first-discovery BERV anchor is16.9196571680147 km/s; the second discovery is14.4701720470153 km/s. Both native A products have72 orders×4096 pixels. Native BUNIT is absent, so native flux must be labelled instrumental/native units rather than asserted to be calibrated or directly comparable in absolute scale to merged ADU.

Native wavelengths use the historical degree3 polynomial at zero-based pixels0…4095, with the unchanged topocentric air convention. Header coefficients reproduce the historical nearest wavelength and fixed detector trace coordinates. The joint center is3852.3925Å barycentric and3852.17509132224Å at the first-discovery topocentric anchor.

| Native order / discovery | Barycentric grid support | Topocentric grid support | Core support | Negative / positive flank support |
|---|---:|---:|---:|---:|
| Order2 /0001 | 601 | 601 | 53 | 151 /151 |
| Order2 /0016 | 601 | 601 | 53 | 151 /151 |
| Order3 /0001 | 391 | 391 | 53 | 0 /151 |
| Order3 /0016 | 394 | 391 | 53 | 0 /151 |

These counts are geometric, derived from monotone header wavelength polynomials on the frozen601-point grid. Finite flux and data gaps remain unassessed. Order3’s missing negative flank must remain missing; no extrapolation, shortened window or substituted order is justified.

Both discovery order3 panels retain their failed earlier local mapping check and later supported wider-reference check. Order2 retains passing local/global/final support. These are separate historical facts; this audit fits no new geometry and assigns no origin or classification.

`audit_inputs.py` reproduces the focused reconciliation. `INPUT_AUDIT.json` groups128 direct identity/header/geometry checks by scope and records only failures, avoiding a large per-check report. The count includes repeated identities across six merged inputs and four native order/frame contexts; it does not represent128 independent scientific tests.
