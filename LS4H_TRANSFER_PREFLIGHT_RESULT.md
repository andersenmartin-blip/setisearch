# LS4H: transfer preflight result

**Preflight completed; measured-background injections have not been executed.**

The time/frequency geometry can be grouped consistently and the development
and reserved validation scans have disjoint files with complete OFF adjacency.
However, the available receipts do not identify a file-specific amplitude
transfer through the 8-bit HTR conversion. A joint physical injection recovery
fraction is therefore not ready to measure. This is a calibration limitation,
not a new rejection of a radio candidate or a measured recovery failure.

## Verified geometry

| Quantity | Result |
|---|---:|
| HTR samples per medium integration | 3,072 |
| Medium channels per HTR channel | 128 |
| Maximum grouped channel-center discrepancy | 0 MHz |
| Common time support | 292.057776128 s |
| Common medium / HTR sample counts | 272 / 835,584 |
| HTR tail without a complete medium counterpart | 2,048 samples; 0.715827883 s |

The analytic envelope-plus-pulses example conserves integrated area 32.72 in
both grids. Direct medium integration and grouped HTR integration differ by
at most 1.36 × 10⁻¹⁴ in bin-average amplitude. Fractional boundary coverage is
included, so short pulses are diluted within long integrations rather than
incorrectly expanded to their full peak amplitude. This validates the toy
integration adapter; it does not establish the instrument's response or its
FFT power normalization. No missing tail integration is padded into the data.

## The unresolved amplitude transfer

The Breakthrough Listen data-format paper describes conversion of float
filterbanks to 8-bit data with `sum_fil`.
[Source: Lebofsky et al., section II.3](https://arxiv.org/html/1906.07391v3).

The reviewed converter clips values at estimated limits and maps the retained
range to unsigned bytes. Its 32-to-8 path estimates limits from a histogram
of a configurable initial region; the output header is written before those
limits are computed. The project's saved headers contain neither these limits
nor the exact conversion command. The pinned source is evidence about the
documented tool, not proof of the revision or settings used for these files.
[Source: pinned sum_fil.c](https://github.com/UCBerkeleySETI/bl_sigproc/blob/b98d00e9ec1a683695758eb3544896a92f649a69/src/sum_fil.c).

Two analytic examples demonstrate the missing information. With different
quantizer gains, identical stored bytes `[100, 100]` become `[101, 100]` after
the same input increment. Even with the gain fixed, distinct unresolved
within-bin inputs produce `[100, 101]` after another common increment. Thus
adding the same number to stored bytes is not uniquely equivalent to adding
one physical signal before conversion. Quantizer assumptions can be modeled,
but their uncertainty must be declared and validated.

## Archive check

The frozen execution queried the cadence API on 2026-09-05 at 03:41 UTC.
All 12 configured medium/8-bit-HTR products matched URL, size, target and epoch
in the 18-entry response. No unquantized `.gpuspec.0001.fil` was listed.
HEAD-only checks of the two inferred A1/B1 float-HTR sibling paths returned
HTTP 404. This establishes the result for those paths and that response, not
that unquantized data are unavailable everywhere. No file-specific conversion
sidecar was identified in the reviewed project inputs or catalog.

The exact catalog response and request outcomes are retained. No telescope
payload was downloaded or decoded. Header geometry came from the earlier
hash-bound LS4A receipt; these were not fresh header reads.

## Protected data split

| Role | ON | Required OFF | Approximate medium + HTR volume |
|---|---|---|---:|
| Development | A1 | B1 | 22.01 GB |
| Reserved validation | A3 | C1 and D1 | 33.01 GB |

A2 is excluded because its two OFF controls span the groups. The reserved
files share the observing session with development and are not independent
epochs. Their medium-resolution products were previously searched; the HTR
products were not opened by LS4C/F. Reservation protects against future LS4H
tuning and does not erase that prior exposure.

The configuration fixes prospective signal placements without searching for
clean noise: 12 MHz bands centered on 8.5 and 10.5 GHz; development windows
48–80 and 176–208 s; reserved windows 80–112 and 208–240 s. No bad-looking
window may be silently replaced. Development source digests are known;
reserved HTR SHA256 values remain explicitly unknown until first acquisition.

## Concrete next boundary

For a common physical injection, obtain unquantized inputs or a documented,
validated transfer model with the conversion limits, scaling and uncertainty.
The two unsuccessful path checks do not justify a large speculative download.

An immediately useful alternative is a separately frozen measured-background
study of **post-quantization digital perturbations**, retaining separate
medium and HTR amplitude axes. It can diagnose stage-specific losses, but it
must not multiply marginal recovery fractions or label independent amplitudes
as one physical injected signal. This narrower study has not yet been run.

In either route, preserve original Stage-1 global selection, normalization,
clipping, event retention and OFF adjacency. Follow-up windows must come from
detected events, with injected truth used only for evaluation. Compare with
uninjected backgrounds to distinguish pre-existing events from injection
effects. LS4F's 0/7 dispositions and LS4G's synthetic results are unchanged.

## Verification and reproduction

All **48 relevant unit tests passed** before the combined preflight execution.
The plan, configuration, tests and executable were committed locally in
`01a594c` before that run. Metadata exploration preceded the freeze as stated
in the plan; no public preregistration or blind metadata discovery is claimed.

```bash
sha256sum -c LS4H_FREEZE.sha256
sha256sum -c RESULTS_MANIFEST_LS4H.sha256
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_ls4*.py'
```

The original runtime refuses to overwrite its result directory. A repeat
must preserve and move aside that directory before running
`PYTHONPATH=src:scripts python scripts/ls4h_transfer_preflight.py`.
Live metadata and timestamps can change; the original receipts remain the
evidence for this execution.

Result identity: `5ac4dbfbd786cdeaf29a5de9a55835d3dfb2e51703f9f9664ee1c04e7aeef903`.
