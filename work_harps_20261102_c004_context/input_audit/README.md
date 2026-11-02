# C004 exact-input and header audit

**PASS: 614 checks**, with no new spectral-flux or detector-pixel values interpreted. This independent audit checks saved bytes, provenance, FITS/NPY headers and header-derived wavelength geometry; it does not evaluate the future profile measurements.

[INPUT_AUDIT.json](INPUT_AUDIT.json) records every scope and result. [audit_inputs.py](audit_inputs.py) reconstructs the checks without importing the restoration or comparison implementation. The [input inventory](../inputs/INPUT_INVENTORY.json) is bound by SHA-256 `1be83dc6e3be2ca639de5a90f16bcff28081e591243c5d2f46160ecc2222607e`.

The 16 exact files comprise seven original-cohort merged spectra, three ancillary TARs, three native-A products and three event-specific historical NPZ panels. They match their original members in three existing archives: extension02 input part 1 and raw batch02 input parts 2 and 3. Complete input archives, ancillary members and restored files were hashed as opaque bytes. NPY headers were read for shape/type custody; no array payload was decoded.

The fixed first-discovery reference is **V2E2-0028 / ADP.2022-03-08T01:01:37.342**, observed on 2022-03-07. Its header BERV is **10.77158288517 km/s**, giving the topocentric-air anchor **3872.1058747209718 Å** from the common barycentric-air center 3872.245 Å. This is the March discovery anchor, not the January anchor from preceding groups. Original identifiers and small raw-identifier/header timestamp differences remain separate and recorded.

All **216 native order headers** were checked independently from the three products. The wavelength polynomials are monotonic over their complete orders, and only **order 3** covers the original feature center in each product. Every one of the six distinct product/order/frame contexts geometrically covers all 601 grid centers, the 51 core centers and 151 centers in each normalization flank. This is geometric support only: finite flux, sample gaps, positive references and uncertainty support remain unassessed here.

All three historical global, local, baseline and later five-window mapping flags are **true**, exactly as stored in the original batch02 records. They remain separate historical diagnostics; no new detector registration or mapping calibration was performed. All primary, secondary, comparison and adopted reviews are preserved, and all three adopted labels remain U.

Merged products retain their verified barycentric air-Angstrom coordinates and uncalibrated ADU flux. Native BUNIT is absent, so native flux units remain unspecified. The merged ERR columns are declared unavailable; no positive uncertainty values are inferred from headers.

C004's original core [3871.995, 3872.495] Å lies entirely inside the completed C003 positive reference flank [3871.25125, 3872.75125] Å. Its central flux was already visible there, and the same seven observations are reused. This audit adds neither blind validation nor independent observing time. No acquisition was performed and no earlier tracked extension02 files changed.
