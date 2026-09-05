# LS4I: measured-background digital intervention study

LS4H found that a common pre-quantization physical injection cannot yet be
identified across the available products. LS4I takes the explicitly narrower
route: independent, specified digital perturbations in each archived product,
with a shared analytic time/frequency shape and **separate amplitude axes**.
Its endpoint is a conditional response of the software on these backgrounds.
It is not physical signal completeness, flux sensitivity or an origin test.

## Exact data and preservation

Only development scans A1 and its complete adjacent OFF B1 are read. The
four medium/HTR files total 22,007,514,360 bytes. All source URLs, sizes and
SHA256 values are known and bound in the configuration. Validate full digests
before numerical use and verify frozen headers. Reserve A3/C1/D1 unchanged;
none of their spectra is opened here. A1/B1 are reused observations from the
same 2017 session, not independent confirmation.

One raw file at a time is stored in a unique `/tmp` directory outside the
synchronized workspace. Require expected file size plus 4 GB free disk.
Permit at most two whole-file attempts per source, charging the full expected
size per attempt against a 44,015,028,720-byte budget. Preserve attempt errors.
Delete files and partial downloads on both success and failure. An incomplete
run has an abort receipt and cannot support a completed-grid conclusion.
The result directory cannot be overwritten. Medium outputs and source receipts
are checkpointed as each source completes. No raw spectrum, collapsed series
or normalized spectrum is published; publish only code, receipts and derived
decision evidence. Lossless compression preserves the full medium event lists.

## Frozen digital interventions

Use the LS4H-selected 12 MHz bands centered at 8.5 and 10.5 GHz and 32 s
envelopes at 48–80 and 176–208 s. Six pulse offsets are fixed at 2.13, 6.67,
11.12, 16.84, 23.37 and 29.42 s. Cross pulse widths 3, 12 and 100 ms. The
analytic profile has envelope height 0.1 and added pulse height 1; compute
bin averages by exact fractional interval overlap in each native time grid.
No clean-background selection, noise replacement, random seeds or post-result
retuning is used. Every predeclared cell is retained.

In medium-resolution data, inject inside the selected native frequency
centers **before normalization and clipping**. Add the profile times amplitude
1, 4 or 16 times each channel's pre-injection full-scan robust MAD scale.
Invalid or degenerate channels are not made valid by injection. Recompute
all affected native coarse bins; unchanged bins can be cached because their
native per-channel normalization is independent. Reuse the original search
function's bytecode with a private preprocessing callback. Compare this path
exactly with full native recomputation on qualified synthetic fixtures before
the freeze; replay each unmodified real scan against its historical full
search result with rtol 1e-10 and atol 1e-8 before processing injections.
All global templates, normalization, clipping, competition, retention and
adjacent-OFF veto settings stay unchanged. An event-retention cap hit aborts.

There are **36 injected medium searches**. A Stage-1 event associates with
the injected region only if intersection covers at least half of **both**
intervals in time and in frequency. Keep every qualifying retained event,
including those rejected by B1; cap at 64 matches per trial, aborting rather
than truncating. Retain the complete searched event lists, not only matches.

For HTR, extract the actual Stage-1 event frequency bands padded by 0.5 MHz
using corrected channel-center selection, plus both exact injection bands.
At most 64 unique bands may be extracted. Promote archived byte values to
floating-point for additive digital perturbations; do not re-quantize, clip,
or claim that this represents adding power before the original conversion.
The amplitude unit is the uninjected collapsed **injection band's** robust
MAD scale outside its truth envelope and 2 s guards. Apply levels 0, 4, 8 and
16 uniformly in digital counts to native channels within the injection band.
For a selected extraction band, linear averaging reduces the added level by
the exact fraction of its channels inside the injection band. This does not
identify the medium per-channel scale with the HTR collapsed-band scale.

HTR envelope and reference windows come from the **detected Stage-1 event**,
never substituted with injected truth. Apply unchanged LS4E metrics/vetoes.
Truth association additionally requires at least three of the same injected
pulses to match at both scales of a supporting pair, using the unchanged LS4G
one-to-one time association. Retain pre-veto support and both control flags.
There are **144 paired digital configurations**: 36 medium trials crossed
with four independently specified HTR levels. A paired pass needs at least
one same event to survive both Stage-1 OFF and HTR truth-associated tests.
Do not multiply marginal rates, treat cells as independent observations, or
equate equal amplitude numbers across products.

Replay the unmodified medium background's associated events through HTR at
zero added amplitude. Compare paired passes with these uninjected baselines;
report a baseline-present feature separately from a newly passing digital
configuration. Even a pass absent at baseline is not a new sky candidate.

Also retain **48 fixed-truth-window HTR diagnostics** (two bands, two windows,
three widths, four HTR levels). These bypass Stage 1 and are explicitly
diagnostic; they cannot rescue a missed Stage-1 candidate or count as full
pipeline passes. Zero-amplitude cases repeat the same measured background
under different truth-matching widths and are not independent null trials.

## Interpretation and execution

Commit plan, implementation, tests and dependency hashes locally before any
LS4I spectral access. This is not public preregistration. Unit tests and both
historical real-data replay gates must pass. Keep defaults and all outcomes;
no scientific success threshold is required. Record runtime versions, source
receipts, freeze digest and canonical result identity. The two known historical
scans provide a small, deliberately retrospective engineering diagnostic.
Prior LS4F dispositions are unchanged; no independent epoch, general light-sail
exclusion or calibrated false-alarm probability follows from this experiment.

```bash
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_ls4*.py'
PYTHONPATH=src:scripts python scripts/ls4i_measured_digital_injections.py
```
