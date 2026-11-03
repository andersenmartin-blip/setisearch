# C009 independent input audit

[audit_inputs.py](audit_inputs.py) produced [INPUT_AUDIT.json](INPUT_AUDIT.json): **PASS, 298 checks, zero failures**. This checkpoint verifies identity, custody, historical decisions and header geometry. No new spectral flux or detector pixel values were decoded or interpreted.

The exact scope is the original C009 singleton V2E2-0050 at 6802.02 Å barycentric air, original queue row 18 / R010 on route INDIVIDUAL_PROFILE_CONTEXT. Its fixed discovery is `ADP.2023-03-23T01:02:04.831`, observed on 2023-03-22. The March 2023 anchor BERV is 3.26509772194068 km/s, giving **6801.945918689643 Å** topocentric air through `lambda_bary / (1 + BERV / 299792.458)`. The wavelength-specific anchor is independently recalculated; the C008 numeric anchor is not reused.

The audit independently verifies ten restored inputs against their exact historical archive members: seven merged spectra, one ancillary TAR, one native A product and one saved raw NPZ panel. It checks two complete input archive sizes and hashes, 14 inventory-bound historical sources, the assembled historical evidence ZIP, native TAR identity, original raw coordinates and NPZ identity, and the exact prior review records. The immutable baseline is `e3b4a2be111e60c48012159354f63de355a61e3b`.

A fresh scan of all 72 native order header wavelength polynomials confirms that only **order 70** covers the original event. No original covering order is structurally excluded. Its topocentric wavelength endpoints are **[6759.84721690394, 6836.063260095031] Å**. Header-derived support for the frozen 0.01 Å grid is:

| Native order | Frame | ±3 Å grid / 601 | Core / 51 | Negative flank / 151 | Positive flank / 151 |
|---|---|---:|---:|---:|---:|
| 70 | Barycentric | 601 | 51 | 151 | 151 |
| 70 | Topocentric | 601 | 51 | 151 | 151 |

Both complete windows are geometrically covered. Finite flux, actual gaps and usable numerical normalization remain untested here. The historical global, local, baseline and later five-window mapping gates are each true and preserved individually. No registration or wavelength solution is changed.

**The historical review distinction is retained exactly: primary A, secondary A, root-adopted U.** Both reviewers provisionally described a compact slanted concentration in order 70. The secondary evidence also retained broad continuum residuals and explicitly could not exclude an underlying spectral contribution. Root conservatively adopted U because the possible artifact/spectral blend remained unresolved. The audit checks the exact original review records, conservative-override note and unconfirmed-origin field; it also verifies the current disposition and original queue still carry U. It performs no new classification and does not substitute the two earlier A votes for the adopted result.

The native order and saved raw panel belong to one March 2023 exposure. Its two coordinate frames produce two contexts, not two independent observations. Native `BUNIT` is absent, so no calibrated ADU equivalence to merged flux is asserted. Merged ERR columns are declared unavailable; no positive uncertainty support is inferred. Exact raw identifiers retain their existing millisecond differences from observation timestamps.

The C009 window [6799.02, 6805.02] Å is disjoint from all eight completed C001–C008 bounded windows. The audit checks their unchanged exact method plans and the C008 metadata handoff, and binds those hashes alongside the original queue and current disposition. The same seven observations and original epoch/native/raw evidence are reused. Distinct wavelength coverage does not establish untouched data, blind analysis or independent observing evidence.

FITS data areas are skipped by byte offsets; NPZ arrays are inspected only through NPY shape/type headers. Complete archive members are hashed as opaque bytes for custody checks. No full raw detector product is restored and no network request is made. Old files are unchanged.

Frozen bindings:

- Input inventory SHA-256: `961a3b767b16441bac13c260b5ff44254282788caea34f69ceb8f1ffd3ddd9e3`.
- Restore helper SHA-256: `33b4074cad530f1e5fc0d3c22fe0f490926f27d3d48db3db386e5bc5a33d696c`.
- Audit helper SHA-256: `a829d253abe652bf5e29629b21183dfeac2ea8d30e52288b2963c1d5c5ea647b`.
- PASS receipt SHA-256: `f30b11b18e6a3bb4dc7dec83db8345a2c454782d8b8464d501356ce0e2b42982`.

Run from the repository root with `python work_harps_20261103_c009_context/input_audit/audit_inputs.py`. Rerunning creates a new timestamped receipt; preserve this checkpoint's exact bytes after method freeze.
