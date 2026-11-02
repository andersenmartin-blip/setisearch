# Independent C007 input identity and header audit

[INPUT_AUDIT.json](INPUT_AUDIT.json) passes **280 checks** without interpreting spectral flux or detector pixel values. The audit separately reopens the two original input archives, verifies their historical hashes and ZIP/TAR member bytes, and reads only FITS headers and NPY shape headers. It imports neither the restoration implementation nor the production analysis.

The restored scope is seven merged spectra, one discovery native A spectrum, its ancillary TAR and the singleton V2E2-0026 historical raw panel: **10 exact files**. All seven target observations are shared with earlier phases. The original C007 core [4312.450, 4312.950] Å lies inside the completed C006 positive reference flank [4311.955, 4313.455] Å. The new context is therefore not an untouched sample or independent validation.

All **72 native order header solutions** were independently checked for endpoint geometry, monotonicity and coverage of the original center. Only order 19 covers it. Both unique product/order/frame contexts geometrically cover all **601 grid positions, 51 core positions and 151 positions in each normalization flank**. This establishes coordinate support, not finite flux, actual gaps, positive references or usable normalization.

Historical mapping gates remain separate:

| Event | Global gate | Original local gate | Original baseline gate | Later five-window support |
|---|---|---|---|---|
| V2E2-0026 | true | false | false | true |

No registration was changed. The original local/baseline limitations remain despite later reference support. Primary, secondary, comparison and adopted reviews match their historical source records exactly; the adopted label remains U. Fresh order coverage does not promote the historical detector mapping.

Native `BUNIT` is absent, so native extracted flux is not asserted to be calibrated ADU or physically equivalent to merged flux. Merged FLUX is explicitly uncalibrated ADU. Its ERR column is declared unavailable; positive uncertainty support is not established by this header audit. Original raw identifiers and DATE-OBS differences, including inherited millisecond offsets, remain exact.

[audit_inputs.py](audit_inputs.py) binds the exact inventory and restoration-script identities. Reproduce only in a separate copy after restoring the exact inputs, preserving this published receipt. The prospective phase freeze also binds the audit source. No network acquisition or new flux/pixel interpretation occurred.
