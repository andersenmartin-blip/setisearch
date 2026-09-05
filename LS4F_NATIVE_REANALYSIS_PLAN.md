# LS4F: frozen retrospective native-data reanalysis

LS4F applies the unmodified LS4E residual diagnostic to the seven already-seen
LS4C events. Its purpose is to determine whether the 9.38 GHz event, and the
other six contextual events, pass that diagnostic and whether the two extra
channels affected the historical result. This is retrospective analysis of
existing recordings, not an independent observation or a blind confirmation.

The executable/configuration is committed locally before re-reading spectral
values. It is not a claim of public preregistration before execution. The
original LS4C and LS4E freezes remain unchanged.

## Exact inputs and resource boundary

The configuration copies both full source receipts from the published LS4C
result: A1 (LHS1140) and B1 (HIP2579), 9,435,087,189 bytes each. Their exact
SHA256 digests, URLs and dimensions are bound by the configuration and its
manifest. Total source data are 18,870,174,378 bytes. One full download attempt
per source is allowed in this execution, with no automatic retries. Data are
streamed with SHA256 calculation and processed only after digest verification.
An HTTP response error, incomplete download, identity or metric mismatch
stops the run and preserves an abort receipt. No complete conclusion is then
permitted. Existing result directories cannot be overwritten.

Only one raw file is retained at a time, with at least 4 GB of free disk
headroom after the planned download. Read chunks contain 4096 time rows.
Raw files and incomplete downloads are deleted in cleanup even on failure.
No raw spectra or full collapsed time series are published. Derived A1
metrics are checkpointed before the B1 download.

## Frozen calculations

For each of the exact seven historical candidate windows in each source:

1. Verify the SIGPROC header with the frozen LS4C decoder and geometry.
2. Reproduce the 13-channel historical mean series and select the 11 channels
   whose centers lie within the historical padded frequency interval. Both
   selections are computed from the same samples, not separate observations.
3. Recompute all historical metrics in the original band. Require identical
   structure, integers and dispositions, with relative tolerance 1e-10 and
   absolute tolerance 1e-8 for floats to accommodate NumPy-version arithmetic.
   Failure stops the run; no historical code is silently altered.
4. Apply both the old HTR rule and the unchanged LS4E residual diagnostic to
   both original and corrected bands. Retain the individual pulse clusters,
   times, scores, reference events and final ON/OFF comparisons. These are
   screening statistics, not calibrated significance values.
5. For every residual cluster, compute positive per-channel excess relative
   to the original band's outside-envelope mean (excluding its 2 s guard),
   using the effective-width window centered on the cluster's peak. Retain
   the largest channel's fractional excess and the fraction in the two extra
   channels. This is a descriptive concentration metric, not a new veto.
6. Count byte values 0 and 255 per channel across the original band. Endpoint
   occupancy does not by itself establish hardware saturation.
7. For corrected-band pulse lists, count one-to-one time matches across all
   21 pairs of candidate bands at each scale within that scale's effective
   width. Only pulses within the same source scan are compared. No ON/OFF
   simultaneous coincidence is claimed. Guard-excluded intervals can differ
   slightly across candidates; matches remain descriptive, without a new veto.

The maximum number of retained pulse records per source is 250,000; exceeding
it aborts rather than truncating output. All seven windows are retained even
if the revised rule rejects them. Degenerate normalization aborts the run.

## Decision and interpretation

The endpoint is each candidate's original/corrected LS4E comparison. Rejecting
a feature under this diagnostic does not prove its terrestrial origin or
exclude other transient morphologies. Passing does not identify diffraction,
sol-sail leakage or artificial origin. Multiple scales remain correlated.
The short synthetic qualification is not end-to-end calibration. Any future
promotion still requires independent data and stronger source attribution.

The report will distinguish data reanalysis from independent confirmation,
record the runtime and exact source/result digests, and preserve the old
result unchanged. Any publication request covers derived evidence only.
