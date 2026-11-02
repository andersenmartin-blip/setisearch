# C002 independent input audit

`audit_inputs.py` produced `INPUT_AUDIT.json`: **PASS, 305 checks, zero failures**. This is an input identity and header geometry checkpoint. No new spectral flux or detector pixel values were decoded or interpreted.

The exact scope is the original C002 singleton V2E2-0033 at 3868.6025 Å barycentric air. Its fixed discovery is `ADP.2022-05-08T01:01:37.876`, observed on 2022-05-07. The anchor BERV is −18.8907517532076 km/s, giving 3868.846286702511 Å topocentric air through `lambda_bary / (1 + BERV / 299792.458)`. The January and March products are not the anchor.

The audit independently verifies all 11 restored inputs against their exact historical archive members: seven merged spectra, one ancillary TAR, one native A product and two saved raw NPZ panels. It checks two input archive sizes and hashes, 14 inventory-bound historical sources, the assembled historical evidence ZIP, native TAR identity, exact original raw coordinates, and all earlier review records. The adopted historical disposition remains U. The immutable baseline is `bf0a49edf503af62fd7cd0e5aa0ae09204cb44cd`.

A fresh scan of all 72 native order header wavelength polynomials confirms that only orders 2 and 3 cover the original event. Both remain present; neither is structurally excluded. Header-derived support for the frozen 0.01 Å grid is:

| Native order | Frame | ±3 Å grid / 601 | Core / 51 | Negative flank / 151 | Positive flank / 151 |
|---|---|---:|---:|---:|---:|
| 2 | Barycentric | 417 | 51 | 151 | 0 |
| 2 | Topocentric | 417 | 51 | 151 | 0 |
| 3 | Barycentric | 601 | 51 | 151 | 151 |
| 3 | Topocentric | 601 | 51 | 151 | 151 |

Order 2 ends at offset +1.160941197456 Å in the barycentric frame and +1.161014356181 Å in the topocentric frame. Its entire positive reference flank [+1.5,+3] Å is outside the wavelength domain. Full core coverage therefore does not establish usable two-flank normalization. Order 3 geometrically covers both full windows; finite flux, internal gaps and numerical normalization remain untested here.

The historical mapping gates remain separate and unchanged:

| Order | Global | Local | Baseline | Later five-window |
|---|---|---|---|---|
| 2 | true | false | false | true |
| 3 | true | true | true | true |

The two extracted orders and two saved raw panels belong to one May exposure. Their two coordinate frames produce four contexts, not four independent observations. The native `BUNIT` header is absent; no calibrated ADU equivalence to merged flux is asserted. Merged ERR columns are declared unavailable, and no uncertainty support is inferred. Existing millisecond differences between exact raw identifiers and observation timestamps are recorded rather than silently normalized.

C002's full core [3868.3525,3868.8525] Å was already inside C003's displayed surrounding window, between C003's negative reference flank and core. The exact C003 plan is independently hash-bound in the receipt. The seven epoch observations are also reused. Any later interpretation must retain this prior exposure; it cannot be described as blind or independent evidence. The wider proposed C002 context also overlaps the completed C004 context, as recorded by the phase baseline and handoff.

All FITS data areas are skipped by byte offsets; NPZ arrays are inspected only through NPY shape/type headers. Complete members are hashed as opaque bytes for custody checks. No full raw detector products are restored, no network requests are made, and no registration or wavelength solution is changed.

Frozen bindings:

- Input inventory SHA-256: `703b3dabc53c7133b8c3c9c4a581fad381c54fb4a0dca501b9c846dd976e8c23`.
- Restore helper SHA-256: `08bba29ba2b8f33cc5943824dc93587dd100b9246436bab0dcf9a7ef1a96dbce`.
- Audit helper SHA-256: `80797af4ed90ed3d28edc0b1b0465273f2fc9074e4f626c6c5cf1ecac2943f47`.
- PASS receipt SHA-256: `191567ef7ba7dd3438bd56076a995311d1d69fd3995daf0c10370cdce3e00046`.

Run from the repository root with `python work_harps_20261102_c002_context/input_audit/audit_inputs.py`. Rerunning creates a new timestamped receipt; preserve this checkpoint's exact receipt bytes after method freeze.
