# LS4G: frozen conditional synthetic recovery study

LS4F rejected all seven previously selected features under LS4E, while LS4E
had only qualified strong 12 ms trains. LS4G maps a limited engineering
operating range of that unchanged diagnostic. It reads no telescope data,
does not revisit the seven dispositions, and does not fit a diffraction model.

## Frozen design

The configuration, executable, tests and detector dependencies are hashed and
committed locally before the first grid run. This is a local pre-execution
freeze, not public preregistration. No thresholds or grid cells may be changed
after results are inspected. All outcomes, including failures, are retained.

Each 120 s synthetic scan has 1 ms samples, a fixed 30–70 s candidate interval
and six irregular, separated rectangular pulses. Each pulse center receives
independent uniform jitter within ±0.15 s, fixed by the seed and shared across
all cells with that seed. Sample-center membership uses a half-open pulse
interval. The ledger records the actual discrete pulse centers and widths.

There are 12 predeclared seeds and three backgrounds: independent unit-normal
noise; stationary Gaussian AR(1) noise with rho 0.8 and unit marginal variance;
and independent noise with ON candidate-interval standard deviation doubled
(variance quadrupled), retaining unit noise in ON reference and OFF. ON and
OFF use separate random draws. Noise has mean 100. Amplitude is the added
per-sample level in units of the baseline marginal standard deviation; it is
not matched-filter S/N, flux, or integrated pulse energy. AR(1) and white
realizations reuse innovations, so background comparisons are paired.

The recovery grid crosses six pulse widths (1, 3, 12, 30, 100, 300 ms), six
amplitudes (0.5, 1, 2, 4, 8, 16), three backgrounds and 12 seeds: 1,296 trials.
There are also 36 no-injection trials, one per background and seed; null cells
are not duplicated across widths. A separate white-noise control grid fixes
the ON train at 12 ms and amplitude 10 and adds one rectangular pulse to OFF
at 50.25 s or ON reference at 15.25 s. It crosses three widths (1, 12, 100 ms),
five amplitudes (0, 2, 4, 8, 16) and 12 seeds: 360 trials. Total: **1,692**.
Zero-amplitude control cases deliberately repeat the same paired baseline;
they must not be counted as independent noise realizations.

## Endpoints

Retain the unchanged LS4E pass flag, existence of cross-scale support before
vetoes, each veto flag, and inside/reference/OFF cluster counts at all scales.
Also retain a truth-associated recovery flag. For each scale, chronologically
match detected peaks one-to-one to the injected discrete pulse centers within
half the sum of the effective detector width and discrete injected width,
plus one sample. Recovery requires an LS4E pass and at least three of the
same injected pulses matched at both scales of an LS4E supporting pair.
Injected times never influence the detector, its normalization or its vetoes.
No-injection cases have no truth-associated recovery by definition.

Report every cell as recovered/trials, alongside support and veto counts.
There is no scientific pass/fail gate, interpolation, fitted sensitivity
threshold or post-result optimization. Implementation checks must pass before
execution. An incomplete run cannot produce a completed-grid conclusion.

## Reproduction and resource boundary

Run `PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_ls4*.py'`,
then `PYTHONPATH=src:scripts python scripts/ls4g_synthetic_recovery.py`.
The runtime verifies both LS4E and LS4G manifests, refuses to overwrite any
existing result directory, writes a per-trial ledger as it runs, and records
an abort receipt on error. Arrays remain in memory and are never published.
One scan pair is evaluated at a time; no network or raw-data access is used.
The summary binds the ledger SHA256, freeze identity and runtime versions.

## Interpretation boundary

Fractions describe only the chosen synthetic family, fixed envelope, 1 ms
geometry and 12 seeds per cell. Seeds and pulse/noise realizations are reused
across cells; these are paired engineering comparisons, not independent
survey trials. In particular, 1 ms is not the native LS4F 0.349525 ms geometry.
No Stage-1 selection, frequency-channel extraction, quantization, clipping,
instrument response, genuine diffraction waveform or real noise distribution
is simulated. This cannot establish astronomical completeness, a calibrated
false-alarm rate, flux sensitivity, signal origin or a light-sail exclusion.
The control grid explicitly tests how an unrelated pulse can veto an injected
ON signal. Recovery in synthetic noise cannot reinstate an LS4F candidate.
