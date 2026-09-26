# Radio continuation — independent source interface

**The radio plan continues during the HD 1461 pointing hold.** Public-code
provenance research is extended, and a new explicit-source acquisition entry
point is implemented and locally checked. Seven engineering tests pass. No new
telescope product, spectral value, calibration, or detector result is evaluated.

The owner challenged the previous stop. The earlier status treated a specific
source-provenance obstruction as a stop for the entire task. That was too broad:
code preparation and public provenance research can proceed autonomously while
the selected spectra remain closed. This package corrects that work boundary;
it is not a new numbered detector milestone or a request for publication approval.

## Coordinate investigation

The earlier 34.23-arcminute discrepancy remains unresolved. The selected source
is still HD 1461 / HIP1499, cadence 71139. This investigation reads public source
code and commit history; it does not repeat the completed archive-catalogue
probe, read a new telescope header, or decode a spectral sample.

The pinned source register is
`results_radio_source_2026-09-26/coordinate_provenance.json`. It identifies eleven
inspected files by repository, commit, path and Git blob, plus relevant changes.

| Layer inspected | Finding and limitation |
|---|---|
| Blimpy 2017 and March 2018 readers | Packed SIGPROC angles are decoded using absolute magnitude and the original sign. HDF5 declination is already decimal degrees. These versions do not justify decoding the retained HDF5 value again. |
| September 2017 SIGPROC writer fix | Handles angle strings without fractional seconds. It does not establish a correction for this cadence. |
| `gbt_seti` conversion, including code before the May 2016 scans | `guppi2spectra.c` constructs the packed angle from the original `DEC_STR` components, with seconds padding. The selected scans' original `DEC_STR` values and deployed executable version are still missing. |
| Original GUPPI telescope-status code | Uses the SLALIB sign and sexagesimal components. No demonstrated transform from HD 1461 to the retained declination was found. |
| Later Berkeley Ruby telescope-status code | Separates the sign before formatting. It was added in July 2016, after these observations; that history does not identify the software deployed for the May scans. |

The absence of a demonstrated conversion is a bounded result, not proof that
the discrepancy originated at the telescope or that no public record exists.
The exact missing evidence remains a same-scan original header or observing log
for `AGBT16A_999_189`, scans 0015/0017/0019, or documented file-specific conversion
provenance. No coordinate is overwritten and no substitute target is selected.

## Acquisition implementation

`src/seti_repeater/source_radio.py` provides an explicit-contract entry point.
Unlike the old M43 entry point, it does not load the HD 156668 preflight or old
qualification receipts. The original code and configurations are unchanged.
It reuses the unchanged M43H native row extraction, float32 median/MAD arithmetic,
atomic persistence, content hashes and receipt rehydration.

The caller supplies an independently retained contract-file SHA256. That file
binds six unique, alternating ON/OFF scans; exact URLs, sizes, ETags, raw header
coordinates and chunk shapes; extraction intervals; source-bound gate evidence;
runtime; implementation pins; and the shared session budget. Source names,
timing, common geometry and nonoverlapping extraction windows are checked.

`src/seti_repeater/transport_radio.py` adds aggregate request, byte and elapsed-time
checks to the retained range-checkpoint interface. It refuses redirects and
changed identity, status, range, encoding or length before reading a response
body. There are no retries or alternate objects. Failed requests consume their
byte reservation. The extra byte used to detect an oversized body is reserved
as well. On-demand metadata reads no longer inherit the old 64 MiB prefix or
large read-ahead. Allocated chunks are planned and recorded before extraction.

The budget is shared by the caller throughout one active acquisition session.
It is not a durable multi-session quota or a background scheduler. A later live
orchestrator must retain cumulative attempt accounting and the run log under
its prospective protocol. A network timeout bounds an individual operation;
elapsed time is checked at boundaries and does not forcibly interrupt a native
library in the middle of decoding. These limits are stated rather than hidden.

The new preparation contract is
`config/radio_hd1461_source_preparation_20260926.json`, SHA256
`c434c6f0615dfec165512195dcae888d8aa4b33a29efdb5037895ba5530d8bcb`.
Its source inventory SHA256 is
`92f877c4041e3a6150273cf108fd3b13ab8394c80c1b817e37d1f6b02a5a66b8`.
All six definitions come from the already published metadata snapshot. The
contract is deliberately **preparation-only**, with no extraction windows or
approved runtime, and unresolved pointing/protocol/integration gates. Even an
explicit `spectral_access_authorized=True` call is rejected before networking.
Its 500-request/512 MiB/1200 s software ceilings are not a scientific data freeze.

## Verification and claim boundary

`scripts/radio_source_qualification.py` runs the focused checks and retains their
actual log, implementation hashes, runtime and outcome. All HTTP replies in the
codec tests are in-process synthetic fixtures, marked `local-fixture`; none is
reported as telescope provenance. Both gzip and bitshuffle/LZ4 are decoded by
the actual HDF5 libraries.

| Check | Observed result |
|---|---|
| Native values and mapping | Exact synthetic native hyperslabs; ascending frequency origin checked; normalized values exactly match the independently sorted reference |
| Interrupted extraction | No complete source after the intentional first-row interruption; that row is reused on restart |
| Completed restart | All three fixture rows reused; no additional GET requests; HEAD identity checked again |
| Receipt integrity | Changed row payload rejected; fixture receipt rejected when telescope provenance is required |
| Contract isolation | Changed contract hash, code pin, inventory identity, gate source and overlapping windows rejected |
| Actual HD 1461 preparation contract | All six pins parse; unresolved gates block before any network request |
| Transport faults | Changed ETag, range, encoding and length rejected before body read; budgets and redirect refusal checked |
| Source fidelity | Changed live size/ETag binding, header or chunk shape stops completion |

Runtime: NumPy 2.3.5, h5py 3.16.0, HDF5 2.0.0, hdf5plugin 7.1.0.
The first development run exposed a one-channel geometry probe, while the
inherited geometry requires at least two channels. The probe was corrected to
two channels before the retained passing run; no telescope data were involved.

**Seven tests passed; zero telescope requests.** This establishes local software
behavior in the tested cases. It does not qualify HD 1461 pointing, compressed
telescope payloads, the motion model, detector, false-alarm rate or sensitivity.
The original M43AF reserved panels and all LS inputs remain unopened.

Reproduce the local checks:

```bash
PYTHONPATH=src:scripts python scripts/radio_source_qualification.py
PYTHONPATH=src:scripts python scripts/radio_source_prepare.py \
  --contract config/radio_hd1461_source_preparation_20260926.json \
  --sha256 c434c6f0615dfec165512195dcae888d8aa4b33a29efdb5037895ba5530d8bcb
```

Evidence and checksums are in `results_radio_source_2026-09-26/` and
`RESULTS_MANIFEST_RADIO_SOURCE_2026-09-26.sha256`.

## Continuation

Ordinary radio SETI remains active and LS remains paused. Do not stop all useful
work merely because HD 1461 spectra are on hold. Continue target-independent
primary/control orchestration and design from the pinned interface inventory;
make its remaining scientific choices explicit before any evaluation. Further
pointing work should seek a genuinely new same-scan observable or authoritative
processing record, not repeat the closed catalogue query or fit a coordinate
correction to the desired target.

Before live extraction, resolve the file-specific pointing provenance and
publish one integrated primary/control protocol with exact band, windows,
motion/width bank, new calibration and control identities, numerical gates,
codec/runtime evidence, and cumulative resource/attempt accounting. Then publish
a new source-bound contract; do not toggle this preparation artifact in place
and present its old hash as a freeze. Existing user authorization covers that
work and its publication. No external message or unattended job has been sent
or scheduled by this package.
