# C005 input and custody audit

PASS for the fixed HD106515A group0023,0029,0035,0046,0054. Seven merged spectra, five discovery nativeA files, five ancillary TARs and ten saved raw/native panels are present:27 restored files in total. All bytes match the three original input archives and batch02 evidence archive. Every declared historical source hash, original event membership, header identity, archive ancestry and selected historical review record is checked. The final inventory SHA-256 is `13154b2d280c5b9df876730184e1d86a935d3a30ea342648f89eb453e0248919`.

Only opaque file bytes, FITS headers and NPY headers are read. FITS image/table payloads are skipped while inspecting headers; pixel and flux values are not decoded. No network requests, historical edits or new mapping fits occur. The report groups267 direct reconciliation checks by scope and lists only failures; the count includes repeated file/header identities and is not a count of independent scientific tests.

The seven distinct merged exposures retain barycentric air-Angstrom wavelengths, uncalibrated ADU flux and ERR headers declaring unavailable values. Native BUNIT is absent in all five discovery products, so their flux must remain labelled instrumental/native units. Native wavelengths retain the historical topocentric air convention and degree3 polynomial evaluated at zero-based pixel0…4095. Their coefficients reproduce the historical nearest wavelengths and fixed detector trace coordinates.

The first discovery anchor is `ADP.2022-01-06T01:08:04.689`, with exact recorded BERV30.1380355615464 km/s. The common barycentric midpoint3882.0375Å corresponds to topocentric anchor3881.6472792969134Å. The fixed context is±3Å at0.01Å spacing, with51 core grid centers inside nominal±0.2525Å and151 centers in each reference flank.

| Fresh header-derived scope | Context /601 | Core /51 | Negative flank /151 | Positive flank /151 |
|---|---:|---:|---:|---:|
| Order3, all five discoveries, both frames | 601 | 51 | 151 | 151 |
| Order4, all five discoveries, both frames | 601 | 51 | 151 | 151 |

All ten original event-specific feature centers lie within their order3/4 wavelength domains. There are no structural exclusions or missing reference flanks. These are geometric support results; finite flux, data gaps and useful normalization are not established by this audit. Global, original local and later five-window mapping support are all true for each of the ten historical panels and remain recorded separately.

Exact raw identifiers and DATE-OBS strings remain distinct where required. The first three2022 raw identifiers end`.116`, `.632` and`.402`, while corresponding merged/native DATE-OBS values end`.115`, `.631` and`.401`. Each is an inherited+1ms difference; exact PROV1 identifiers and native TAR member names agree with the original archives. The four remaining merged exposures have zero recorded offset. No timestamp string normalization is used.

The original primary, secondary, adopted and review-comparison records for all five events are retained exactly, including the adopted U labels. No new raw-panel assessment or physical-origin inference is performed.

`audit_inputs.py` reproduces the audit and writes only inside this input_audit directory. `INPUT_AUDIT.json` binds the exact inventory and source hashes and records full per-order/frame coverage, timestamp offsets and mapping history. Subsequent flux analysis requires its separate public freeze and root release.
