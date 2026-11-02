# C008 independent input audit

`audit_inputs.py` produced `INPUT_AUDIT.json`: **PASS, 293 checks, zero failures**. This checkpoint verifies identity, custody and header geometry. No new spectral flux or detector pixel values were decoded or interpreted.

The exact scope is the original C008 singleton V2E2-0047 at 5182.005 Å barycentric air. Its fixed discovery is `ADP.2023-03-23T01:02:04.831`, observed on 2023-03-22. The March 2023 anchor BERV is 3.26509772194068 km/s, giving 5181.9485623946 Å topocentric air through `lambda_bary / (1 + BERV / 299792.458)`.

The audit independently verifies ten restored inputs against their exact historical archive members: seven merged spectra, one ancillary TAR, one native A product and one saved raw NPZ panel. It checks two input archive sizes and hashes, 14 inventory-bound historical sources, the assembled historical evidence ZIP, native TAR identity, exact original raw coordinates and NPZ identity, and all earlier review records. The adopted historical disposition remains U. The immutable baseline is `503e3d4bd79307aef109433b1b6ab672fce832e0`.

A fresh scan of all 72 native order header wavelength polynomials confirms that only order 43 covers the original event. There are no structurally excluded original covering orders. Its topocentric wavelength endpoints are [5156.37162001017, 5214.417647930924] Å. Header-derived support for the frozen 0.01 Å grid is:

| Native order | Frame | ±3 Å grid / 601 | Core / 51 | Negative flank / 151 | Positive flank / 151 |
|---|---|---:|---:|---:|---:|
| 43 | Barycentric | 601 | 51 | 151 | 151 |
| 43 | Topocentric | 601 | 51 | 151 | 151 |

Both full windows are geometrically covered. Finite flux, internal gaps and usable numerical normalization remain untested here. The historical global, local, baseline and later five-window mapping gates are each true and are preserved individually. No registration or wavelength solution is changed.

The native order and saved raw panel belong to one March 2023 exposure. Its two coordinate frames produce two contexts, not two independent observations. Native `BUNIT` is absent; no calibrated ADU equivalence to merged flux is asserted. Merged ERR columns are declared unavailable, and no uncertainty support is inferred. Existing millisecond differences between exact raw identifiers and observation timestamps are recorded rather than silently normalized.

The proposed C008 window [5179.005,5185.005] Å is disjoint from the seven completed C001–C007 bounded windows. The audit independently checks this geometry against all seven unchanged method plans and binds their exact hashes alongside the C002 handoff. The same seven target observations and the original epoch/native/raw evidence are reused. Different wavelength coverage does not establish untouched data, blind analysis or independent observing evidence.

FITS data areas are skipped by byte offsets; NPZ arrays are inspected only through NPY shape/type headers. Complete archive members are hashed as opaque bytes for custody checks. No full raw detector products are restored and no network requests are made.

Frozen bindings:

- Input inventory SHA-256: `80cce49d1000211f735449d65efc27b447de85bdd9e5ba9fbbbfac924e21f890`.
- Restore helper SHA-256: `0809ba178ae5b316c96b541b5381d2813ea65f26e99a7a959d410db9f2270b6a`.
- Audit helper SHA-256: `2077e8c74b8d47f5ed61de511e9941adffb151e9da18479fd30f0ce7b1500ba9`.
- PASS receipt SHA-256: `206f3b7e42821b7b7eebcb5b1e89e408313b2a4c329121f61009c59e4a5c9dbf`.

Run from the repository root with `python work_harps_20261102_c008_context/input_audit/audit_inputs.py`. Rerunning creates a new timestamped receipt; preserve this checkpoint's exact receipt bytes after method freeze.
