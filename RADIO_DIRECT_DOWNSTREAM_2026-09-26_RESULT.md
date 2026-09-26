# Direct-factor downstream integration — 26 September 2026

**Connector result: PASS. Engineering control gate: FAIL. Scientific readiness
remains HOLD_POINTING_PROVENANCE_UNRESOLVED.** The literal eccentric factor table
now reaches calibration, exhaustive retention, matched-OFF, adjacent-OFF,
receiver-frame, rank and clustering stages without constructing or accepting a
legacy two-column `FactorBasis`. No telescope values were opened.

## Versioned contract and changed risk

The new `radio-direct-downstream-factor-contract-v1` binds the complete
`DirectFactors` identity, the 33-template catalogue, six scan labels, midpoint
factor table, ON/OFF row selections and native grid. Historical v0.6 certificate
fields named `factor_basis_sha256` and `factor_basis_labels_sha256` are still
required by the unchanged numerical ledgers. The new result explicitly maps
those slots to the direct-bank and direct-midpoint-label identities; it does not
create a numerical basis or present the factors as Cartesian coefficients.

The old `pipeline_radio`, `detector_m43u` and factor-table validation path are
unchanged. The shared adjacent-OFF finalizer gained one explicit selection-hash
argument so the direct path need not supply a false basis. Eight targeted legacy
pipeline regressions pass after that change.

The direct pipeline is synthetic-only and exposes no telescope constructor. It
requires every normalized source scope to contain the exact scan and direct-bank
identity before scoring. Calibration, score inventories, receiver queries and
the final report each bind the new context identity. A calibration from another
context is refused.

## Fresh bounded fixture

The fixture uses all 33 templates from the separately qualified catalogue-
direction bank, all eight widths (1–129 channels), 641 support carriers and a
127-row conditional scramble calibration. Calibration and each of four cases
have fresh, mutually disjoint synthetic source identities. Signals are added to
raw powers with the start/end finite-exposure model before normalization.

| Case | Retained ON / OFF | Final members | Final clusters | Intended-track result |
| --- | ---: | ---: | ---: | --- |
| Noise | 0 / 0 | 0 | 0 | No injected truth |
| Finite-exposure ON signal | 2,246 / 0 | 2,246 | 2 | Recovered; this large survivor set is not completeness evidence |
| Matched ON/OFF signal | 2,261 / 2,250 | **13** | **2** | Intended matched track vetoed; control nevertheless fails |
| Signal with one paired OFF epoch | 559 / 0 | 0 | 1 | Intended track rejected by adjacent-OFF stage |

All members, scores, masks, matched-OFF evidence, adjacent-OFF measurements,
receiver signatures, rank evidence, decisions and complete clusters are retained
in `reports.json.gz`; no trigger was truncated. The case backgrounds are distinct
synthetic realizations, but they are only four engineering cases, not a
false-alarm distribution. The 500-unit digital injections are not flux or EIRP
calibration.

Eight new tests pass. They cover identity tampering, scan reordering, wrong-bank
sources, exact-context calibration, complete cluster partitioning, all physical
stages, explicit compatibility-slot identities and absence of telescope or
candidate authority. Eight legacy regression tests also pass. Closed M43 panels
and the previous synthetic acquisition ledger were not rerun or reset.

## Bounded diagnosis of the failed control

The 13 final matched-control members form two clusters. All use width 129 and
activity subset epochs 1+2; six use template 30 and seven template 31. For every
one, the alternate track intersects the strong injected line within the
64-channel half-width during epoch 1. During epoch 2 it is more than 9 kHz from
the injected truth, but its noise score lies just above the fixed per-epoch floor
of 3. The combined score therefore passes. The intended injected ON/OFF track
itself is correctly vetoed.

This demonstrates a control-design limitation: a strong matched interferer can
seed a broad-width alternate hypothesis in one epoch and combine with marginal
noise support in another. It does not demonstrate an implementation error, and
it is not repaired or retuned here. The exact 13 records and separations are in
[control_diagnosis.json](results_radio_direct_downstream_2026-09-26/control_diagnosis.json).

## Claim boundary and continuation

The connector is qualified for further engineering because every versioned
handoff completes and the unchanged legacy path still passes. The integrated
recovery/RFI/null gate is **not** qualified: the matched-control requirement
fails, the ON signal produces extensive alternate-track retention, and receiver/
cluster behavior has only four synthetic realizations. `neighbor9` remains the
primary; the exposed cases cannot be tuned into a pass.

Cross-window calibration remains unqualified. The present calibration is bound
to one exact synthetic validation-window context and must not be relabelled for
the proposed calibration or pilot windows. Physical ephemeris, continuous bank
coverage, within-exposure curvature and pointing provenance also remain open.

**Exact next work:** implement an explicit disjoint-window calibration contract
that binds the three proposed frequency/payload identities and rejects reuse of
an exact-context certificate. Then publish a prospective, fresh finite-exposure
control panel that includes strong matched-interferer broad-width leakage and
counts every unassociated final member/cluster. Keep the fixed failed case as
development evidence; do not alter it or choose settings from its outcomes.
Only a new, disjoint evaluation may test a frozen remedy and gate.

The same-scan original header/log requirement for AGBT16A_999_189 scans
0015/0017/0019 is unchanged. The original preparation contract remains blocked.
M43AI, 112+128 M43AF holdouts, M15 GJ581, M33 HD3651, LS8BF and CHEOPS remain
untouched. The two-week plan is not extended.

## Reproduction

```sh
PYTHONPATH=src:scripts python scripts/radio_direct_downstream_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_DIRECT_DOWNSTREAM_2026-09-26.sha256
```

See [result.json](results_radio_direct_downstream_2026-09-26/result.json),
[qualification.json](results_radio_direct_downstream_2026-09-26/qualification.json)
and the complete compressed reports. The qualification log records the two test
panels and deterministic fixture/diagnosis commands.
