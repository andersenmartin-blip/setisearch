# LS4H: measured-background injection transfer preflight

The objective is to test signal recovery through LS4B selection and LS4E
residual follow-up using measured backgrounds. This first executable phase
qualifies the cross-product adapter and identifies missing source calibration.
It does not substitute synthetic noise for the requested measured-noise study.

## Why this boundary is necessary

LS4B searches 32-bit medium-resolution spectra; LS4E consumes series extracted
from 8-bit high-time-resolution (HTR) spectra. Their sample durations and
frequency widths differ. A common time/frequency grid is necessary but does
not establish equal amplitude units or invert a quantizer. Independent
"sigma" injections into each product would describe different interventions.
Multiplying their recovery fractions would not measure a common physical
injection through the complete pipeline.

The existing headers and source receipts were inspected before this freeze.
An exploratory metadata request and HEAD checks of two inferred float-HTR
paths were also made. The executable repeats those bounded metadata checks
and records the evidence. The synthetic adapter examples are predeclared
below; their results have not been used to change detector thresholds.
The reviewed external source is identified in `LS4H_SOURCE_REVIEW.json`.

## Data partition and identities

Use the existing X-band cadence `--114966`, preserving scan adjacency:

| Role in LS4H | ON | Required OFF | Prior exposure |
|---|---|---|---|
| Development/calibration | A1 | B1 | Medium spectra and seven HTR bands previously analyzed |
| Reserved validation | A3 | C1 and D1 | Medium spectra previously screened; HTR not opened by LS4C/F |
| Unused bridge | A2 | B1 and C1 | Shares controls across the two groups; excluded |

The groups have disjoint scan files. They share an observing session and are
not independent epochs. "Reserved" means protected from LS4H tuning from now
on; the medium-resolution products are not historically blind data.
The configuration binds exact URLs, sizes, source names, start epochs and
available source SHA256 values. The three reserved HTR digests are not yet
known and are explicitly null. A future first acquisition must record them
and verify the frozen header/size identities before numerical evaluation.

Preselected signal bands are 12 MHz wide, centered at 8.5 and 10.5 GHz.
Development envelopes are 48–80 and 176–208 s; reserved envelopes are 80–112
and 208–240 s. These are fixed by design without selecting clean measured
noise. Interference-rich windows must not be silently replaced. They are
prospective placements, not an executed injection grid or tuned candidates.

## Executable preflight

1. Verify local source receipts and both stage geometry configurations by hash.
2. Check scan roles, full OFF adjacency and disjoint partitions.
3. Calculate the integer time/frequency grouping ratios, channel-center
   alignment, common time support and unmatched tail. Do not pad a missing
   medium-resolution integration with invented samples.
4. Integrate a rectangular 48–80 s envelope at amplitude 1 with six 12 ms
   pulses of added amplitude 10 at the configured times. Compute bin averages
   analytically in each geometry and compare the direct medium integration
   with grouped HTR integrations. Check total area conservation. This is a
   time-integration toy, not a model of the telescope FFT response.
5. Evaluate two predeclared quantization ambiguity examples: different
   unknown gains can yield the same stored byte but respond differently to
   one common physical increment; different sub-bin inputs can do so even
   with the gain fixed. The toy uses clipped truncation to unsigned integers,
   motivated by the pinned converter source, not identified as the exact
   conversion of these particular observations.
6. Fetch the cadence JSON once (at most 2 MB) and compare the 12 known medium
   and 8-bit HTR URLs/sizes/epochs/targets. Retain the exact response. Record
   whether any unquantized `.gpuspec.0001.fil` is listed. Perform HEAD-only
   requests for the two inferred A1/B1 float-HTR siblings; retain errors as
   availability observations, not as global proof of absence.

The output directory cannot be overwritten. Network failures are retained
and prevent a positive availability conclusion. No telescope payload is
downloaded or decoded. Header metadata come from the hash-bound LS4A receipt,
not a fresh header read. Preserve HTTP dates and any observed status codes.
All implementation tests must pass and code/config must be committed locally
before executing the combined preflight. This is not public preregistration.

## Decision and next execution boundary

Geometry qualification alone cannot authorize a claim of joint physical
injection recovery. The full numerical study needs an identified common
pre-quantization input and response model, or a validated transfer model with
declared uncertainty and file-specific calibration provenance. No such
calibration artifact has been identified in the current project inputs.

If that information is unavailable, a separately specified experiment may
measure **post-quantization digital perturbations** in each product. It must
retain separate amplitude axes and report a conditional engineering endpoint;
it cannot be relabeled as common physical or end-to-end recovery. Choosing
that model requires a new scientific specification, not silently equating
independent per-product noise units.

The eventual full search must retain global frequency competition, original
clipping, normalization, retention limits and all required OFF scans. HTR
windows must come from detected Stage-1 events; injected truth is used only
to assess associations, never to replace missed or shifted detections.
Record matched uninjected backgrounds and losses at each stage. Do not count
pre-existing background events as unambiguous injection-caused recoveries.

The development medium+HTR inventory is about 22.01 GB; reserved validation
adds about 33.01 GB. A future acquisition must freeze its actual transfer cap,
one-file-at-a-time cleanup and at least 4 GB spare disk after a file download,
using disposable storage outside the synchronized workspace. No spectral
download is part of this preflight. Unknown gains must not be filled with
guessed values to make this gate pass. No LS4F disposition is changed.
