# Direct eccentric factors and native arithmetic — 26 September 2026

**Engineering result: PASS. Scientific readiness remains
HOLD_POINTING_PROVENANCE_UNRESOLVED.** Eight new tests pass. This package replaces
no historical result and opens no telescope spectral values.

## What changed and why

The preceding [motion audit](RADIO_MOTION_2026-09-26_RESULT.md) demonstrated that
the legacy circular two-column basis cannot represent the retained eccentric
working orbit accurately. A new, separate `DirectFactors` type explicitly binds
source, clock, observer evidence, coordinate scenario, orbital parameters,
template order and every start/midpoint/end factor. Its immutable binary64 array
and complete input record have a content identity. Validation recomputes every
factor; changing the digest around an altered array does not make it valid.

The existing native filter/cache already accepts a full factor matrix. A typed
synthetic adapter supplies that matrix directly, with matching scan and bank
identities. The original two-column `FactorBasis`, detector, native arithmetic,
source adapter and preparation contract remain unchanged. The new adapter
accepts only synthetic sources; it provides no telescope-access factory.

## Bounded evidence

| Check | Retained result |
| --- | --- |
| Explicit coordinate scenarios | Catalogue direction plus each of the three ON header directions, kept separate |
| Bank per scenario | Zero orbital projection plus 16 phases at each projected scale 0.5 and 1: 33 templates |
| Factors checked | 4 × 33 × 96 integrations × 3 samples = 38,016 |
| Independent orbital implementation | 64-step bisection and atan2 true anomaly versus production Newton solver; maximum factor difference 0.0 in this runtime |
| Raw native fixture | One synthetic six-scan cadence, 16 × 16,384 float32 cells per scan |
| Independent normalization | All 1,572,864 cells bit-identical to independent sorted median/MAD arithmetic |
| Native filter/gather | 6 scans × 8 widths × 33 templates × 641 carriers = 1,015,344 score cells, all bit-identical to the independent per-center reference |
| New unit tests | 8 pass, including identity tampering, scan mismatch, literal time-sample selection and insufficient native support |
| Telescope requests / spectral values | 0 / 0 |

The native fixture uses only the explicitly labelled catalogue-direction
scenario, without adopting that direction as correct. The other three scenarios
are factor/model checks, not additional native realizations. Its frequency
geometry comes from the previous unfrozen validation-window proposal; no real
validation data have been opened. Widths are 1, 3, 5, 9, 17, 33, 65 and 129 native
channels, and gather chunks of 137 exercise chunk boundaries.

A fixed template-21 signal is added to ON raw arrays before normalization using
the power-conserving linear finite-exposure component, endpoint factors and
500 digital power units per row. OFF arrays receive no injection. This is one
engineering background realization, not 48 independent backgrounds. No detector
threshold, recovery gate, RFI decision, candidate trigger or false-alarm rate is
computed here. No exposed evaluation has been tuned to pass.

The complete four factor banks, input records and observer corrections are
retained. All 48 native arrays have exact score/oracle hashes and all-template
central-carrier scores. Full score matrices for epoch1_on at widths 1 and 65 are
also retained; remaining matrices are reproducible from the pinned generator.
There are no candidate/veto ledgers to omit because the candidate stage was not
run. See [result.json](results_radio_direct_factors_2026-09-26/result.json),
[score receipts](results_radio_direct_factors_2026-09-26/native_score_receipts.json)
and [qualification record](results_radio_direct_factors_2026-09-26/qualification.json).

## Scope and limitations

The model is first-order emitter motion times optical observer correction,
anchored to the first ON midpoint. Relative orbital phase is explicit. The
retained central orbital parameters and fixed sky scenarios do not establish a
physical ephemeris: time-scale, omega convention, astrometric epoch and higher
order motion questions from the prior audit remain. Agreement between two
implementations establishes arithmetic for this model, not its physical truth.
The 33 templates do not certify continuous phase/inclination coverage. Linear
endpoint exposure integration does not qualify within-exposure orbital curvature.

The complete downstream pipeline still reconstructs factors through the old
two-column basis. This package does **not** connect the new type to calibration,
retention, physical vetoes, receiver comparisons or clustering. Nor does it
qualify transfer between disjoint frequency-window calibration contexts. The
previous integrated synthetic pipeline remains its own unchanged result.

This package runs only new tests and the new fixture. Its qualification wrapper
limits each subprocess to 180 seconds. It does not consume or reset the closed
synthetic acquisition ledger, add telescope attempts, spend an M43AF holdout or
reopen M43AI. Scientific attempt and resource budgets still require a new,
integrated prospective source contract; this development design is not that
contract. The original preparation contract SHA256 remains
`c434c6f0615dfec165512195dcae888d8aa4b33a29efdb5037895ba5530d8bcb`.

No new same-scan pointing observable was acquired. The original-header/log
requirement for AGBT16A_999_189 scans 0015/0017/0019 and the
[unsent request specification](RADIO_HD1461_PROVENANCE_REQUEST_2026-09-26.md)
remain current. Closed catalogue/public-code inquiries were not repeated.

## Reproduction and next continuation

Use Python 3.12.14 and the pinned
[requirements](config/radio_motion_requirements_20260926.txt), including NumPy
2.3.5, Astropy 8.0.1, PyERFA 2.0.1.5 and IERS data 0.2026.9.21.0.56.25. The fixture
requires the retained IERS-B hash and reproduces all previous observer midpoints;
automatic IERS downloads are disabled.

```sh
PYTHONPATH=src:scripts python scripts/radio_direct_factors_qualification.py
sha256sum -c RESULTS_MANIFEST_RADIO_DIRECT_FACTORS_2026-09-26.sha256
```

The qualification log contains timing, so its hash can change on reproduction;
compare deterministic numerical outputs and refreshed qualification pins rather
than claiming a timing log must reproduce byte-for-byte. The published manifest
verifies the original retained package.

**Exact next work:** build an explicitly versioned downstream contract that
carries the direct table through calibration, retention, physical-veto,
receiver-frame and clustering interfaces while preserving the existing detector
arithmetic. Do not disguise this table as the legacy two-column basis. Qualify
that changed integration, then qualify explicitly bound disjoint cross-window
calibration and full finite-exposure signal/RFI/null controls. These steps must
precede a prospective freeze and any spectral access. The source-specific motion
bank, widths, recovery/null gates, codec evidence, independent panel identities
and cumulative resource/attempt limits must all be frozen and verified together.

`neighbor9` remains primary. Pointing provenance must be resolved separately.
M15 GJ581 and M33 HD3651 remain unresolved; the original 112+128 M43AF holdouts,
all earlier dispositions, LS8BF and the unsent CHEOPS request remain untouched.
The two-week plan is not extended.
