# HD189733 metadata-only window and width compatibility study

Declared after the completed alternate-source metadata screen and before the
calculations below. No telescope values, new HTTP requests, calibration or
evaluation are authorized. Use only the retained new headers, official planet
record and preparation contract. The HD1461 contracts remain unchanged.

The selected nominal catalogue model has eccentricity zero. For this bounded
compatibility calculation only, treat its semimajor axis as the emitter's
circular orbital radius, use a stationary observer and first-order velocity
Doppler factors normalized at the first ON integration midpoint. Vary orbital
phase through the whole circle. This is a declared mathematical scenario,
not measured emitter support, an adopted planet ephemeris, a complete physical
error budget or a proof of detectability.

At a fixed upper reference of 1425.85 MHz, derive continuous-phase bounds using
V=2*pi*a/P and denominator c-V. Bound displacement from the first ON midpoint
at all retained integration start/mid/end times by
2*nu*V*abs(sin(pi*delta_t/P))/(c-V). Bound the frequency span within one
integration by the same expression with delta_t=tsamp. These are analytical
upper bounds over phase, not a finite-phase coverage claim.

Compare only widths 129 and 257 native channels, allowing one native-channel
intrinsic support in addition to the frequency sweep. Compare only extraction
lengths 16384, 32768 and 65536 channels. A geometric guard must include the
phase displacement bound, a 99-carrier adjacent-bin grid (49 bins each side),
half the smallest sufficient tested odd width and one interpolation bin.
Choose the smallest tested extraction length satisfying that geometric bound.
No extra length, width or phase tuning after the calculation is permitted.
If none fits, record that outcome without extracting data.

For a successful nominal geometry, declare three disjoint prospective roles:
calibration, validation and pilot, in that order. Use anchor frequencies
1400.5, 1412.5 and 1425.0 MHz, respectively. Choose the closest complete native
HDF5 chunk centre whose proposed extraction interval lies wholly within
1399.65–1425.85 MHz; break ties by the smaller chunk index. Record exact
channel intervals and endpoint frequencies, all six source identities and all
16 time-chunk coordinates per source. Reject any cross-role native-chunk
overlap. Normalization remains ascending-order 4096-channel blocks from each
new extraction origin.

Calculate sample/decoded-chunk/modelled-buffer sizes explicitly. These are
geometry bounds, not observed compression ratios, HTTP costs or benchmarks.
Keep actual source acquisition and every scientific panel unexecuted.
Check the old cross-window identity API against the new length and report any
incompatibility without changing that old API or presenting a draft as ready.

The result may guide a new integrated protocol. It cannot establish physical
bank coverage, numerical threshold transfer, end-to-end recovery/RFI/null
performance or decoder qualification on telescope payloads. No old calibration
certificate, exhausted ledger, holdout or failed evaluation is reopened.
