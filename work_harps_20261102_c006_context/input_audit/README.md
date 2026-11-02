# Independent C006 input identity and header audit

[INPUT_AUDIT.json](INPUT_AUDIT.json) passes **465 checks** without interpreting spectral flux or detector pixel values. The audit separately reopens the two original archived input packages, validates their historical hashes, verifies ZIP/TAR member bytes, and reads FITS headers and NPY shape headers only. It does not import the input-restoration or analysis implementation.

The restored scope is seven merged spectra, two distinct native A spectra, their two ancillary TARs and three event-specific saved raw panels: **14 unique files**. V2E2-0042 and V2E2-0043 share a discovery/native product; their distinct historical panels and review records remain separate, without counting shared data twice.

All 144 native order header solutions are independently checked for endpoint geometry, monotonicity and coverage of the original event centers. Only order 19 covers those centers. Its four unique product/order/frame contexts geometrically cover all 601 grid positions, 81 core positions and 151 positions on each normalization flank. This establishes header geometry, not finite flux, actual gap-free support or usable normalization.

Historical mapping gates are preserved separately:

| Event | Global gate | Original local gate | Original baseline gate | Later five-window support |
|---|---|---|---|---|
| V2E2-0025 | true | false | false | true |
| V2E2-0042 | true | true | true | true |
| V2E2-0043 | true | true | true | true |

No registration is changed. The V2E2-0025 local/baseline limitation remains visible despite its later reference support. All primary, secondary, comparison and adopted review records match the historical source exactly; all three adopted labels remain U.

Native `BUNIT` is absent and is not assumed to equal merged uncalibrated ADU. The merged ERR column is declared unavailable; no positive uncertainty support is established by this header audit. Original raw identifiers and DATE-OBS differences, including the inherited millisecond offsets, remain exact.

Run [audit_inputs.py](audit_inputs.py) only in a separate reproduction copy after restoring its exact inputs. The published audit binds the inventory and restoration script hashes; the prospective phase freeze binds this audit and its source. No network acquisition occurred.
