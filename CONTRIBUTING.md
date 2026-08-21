# Contributing

Contributions that improve reproducibility, tests, documentation, performance,
data adapters, interference rejection, or statistical calibration are welcome.

## Scientific record

Published milestone configurations, manifests, primary results, and labelled
post-hoc reports are immutable research records. Do not rewrite a completed
result in place. Corrections must preserve the original evidence and add a
clearly dated erratum or superseding analysis.

Any new held-out search or candidate-disposition rule must be committed before
spectral contact. Post-hoc diagnostics must be labelled as such and may not be
used to increase the frozen search significance.

## Proposing a change

1. Open an issue describing the scientific or technical motivation.
2. Keep the change focused and add or update tests where applicable.
3. Run `python -m unittest discover -s tests -v`.
4. Submit a pull request with the assumptions, validation performed, and any
   effect on reproducibility or prior results.

Do not commit telescope payloads, credentials, private data, generated caches,
or environment-specific secrets. Public archive URLs, metadata, checksums, and
small diagnostic products are appropriate when they are needed to reproduce a
published result.
