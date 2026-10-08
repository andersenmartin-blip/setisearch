# Prospective bounded ON/OFF detector - 8 October 2026

This code has been authored and checked by static parsing only. No DEV, fresh
validation, historical holdout or actual sky-pilot values have been generated
or searched by this package. Root must freeze the reviewed code, exact current
source geometry, new DEV identities and execution command before running it.
`config_proposed.json` is a proposal, not an execution authorization or result.

Use the working Python environment with numpy 2.3.5 and scipy 1.17.0. No new
native runtime, loader tracing, account, service or telescope reservation is
required. This detector does not download data or write output at import.

## Input API

Construct six chronologically ordered `Scan` objects, alternating ON/OFF.
`power` is the complete requested `[time, frequency]` float32/float64 array in
the original native channel order. `fch1_hz` is the frequency of ORIGINAL
SOURCE channel zero, not the frequency of the first extracted channel.
`source_channel0` is the absolute source index of that first extracted channel.
`normalization_source_channels` is the frozen static 4096-channel source core;
for the proposed primary it is `159905792:159909888`. `expected_nrows` is the
metadata-declared full row count (16 for the primary), never the number of
rows the downloader happened to return. Default masks are all-valid; this
prospective run declares no adaptive data-derived mask.

Call `search_cadence(scans, reference_frequencies_hz, Config())`. The 4096 ON
frequencies are the consecutive native centers of the frozen source core at
the common reference epoch. Missing rows, non-finite or negative power,
invalid median/MAD, overlapping/out-of-order scan integrations, or missing
drift/filter/box context are errors. None are represented as scientific EMPTY.

## Fixed statistic and geometry

The global reference epoch is halfway between the first and last integration
midpoints of the six original files. Each row's actual file start MJD and
integration midpoint define its time coordinate; gaps remain gaps. Drift is
positive toward higher frequency, independently of native channel order.
The grid is ascending `linspace(-4,4,2*n+1)`, with `n=ceil(4*Tspan/min(abs(df)))`;
its center is explicitly exact zero. Half-step mismatch over the FULL midpoint
baseline is at most half a channel. Do not substitute a coarser grid or a
smaller carrier count for a reported scientific pass.

For each row, divide power by its median on the fixed normalization core;
subtract a 501-channel frequency running median; then estimate `m0=median(core_residual)` and `scale=1.4826*MAD` on that core.
Subtract `location=m0+mean(clip(core_residual-m0,-5*scale,+5*scale))` and divide
by that scale. The median, winsorized location and scale are all retained. Score a
nearest-channel drifting odd box of width 1, 3, 9 or 33 as the sum across all
rows and box channels divided by `sqrt(Nrow*width)`. `np.rint` rounds the
complete ABSOLUTE SOURCE channel coordinate with ties to even, then subtract
the integer loaded-channel offset. Local-index parity is never used for
half-channel ties. This custom robust statistic
is neither turboSETI S/N nor calibrated sky significance. It is evaluated with
cached row box sums and bounded drift/carrier tiles. Winning ties prefer the
first width, then the first ascending drift.

## Outputs and OFF veto

All six scan maps retain every searched reference carrier's maximum over the
full drift/width family, winning drift/width and valid-hypothesis count.
Every ON threshold carrier with score at least 10 is retained, including a
single-ON occurrence and adjacent threshold channels. No clustering removes
entries from the complete list. OFF maps include a metadata-derived reference
halo beyond both ON-band edges. At maximum width the conservative halo uses
`Cmax=35`, an uncertainty slope bound and the largest scan-midpoint distance
from the global reference time. Decode additional drift, 250-channel running
median, 16-channel half-box and rounding context outside that OFF bank.

The OFF veto does NOT inspect only each OFF carrier's winning drift. For each
ON hit and each trial OFF width, search every OFF `(frequency,drift,width)`
template satisfying BOTH ON-endpoint compatibility bounds:

`abs((fOFF-fON)+(dOFF-dON)*tON_endpoint) <= ((wON+wOFF)/2+2)*abs(df)`.

The same global trial track is scored across all rows of each OFF scan. Any
score at least 8 supplies an existential veto witness. A stopped family has
`family_exhausted=false`; its witness and actual evaluated compatible-template
count/maximum-checked-score are recorded without claiming a complete family
maximum or complete match count. Traversal is width, ascending drift tile,
ascending carrier tile, then drift/carrier within the tile. All three OFF
scans receive comparisons. Survivors are exploratory outputs only.

## Recovery gate and resources

`recovery_matches(result, truth)` uses the generator's frozen active ON scan
IDs, true global frequency/drift and noise-free oracle width per active scan.
Localization must hold at both ON integration midpoint endpoints within
`(2+max(w_hit,w_oracle)/2)*abs(df)`. The final gate requires a localized survivor
in EVERY active ON scan; any-active recovery is reported separately. Raw ON
and final recovery are distinct. Noise/RFI acceptance and subgroup decisions
belong to the frozen external control runner, not this kernel.

`metadata_cost_estimate.json` is a metadata-only estimate: 5415 drifts, 4096
ON carriers, 4596 OFF carriers, 7838 conservatively decoded channels per scan,
and approximately 9.04 billion scalar row score gathers for one six-scan
search, plus data-dependent restricted OFF rescans. Cached OFF box arrays are
approximately 13.5 MB, decoded float32 arrays approximately 3.0 MB and one
score tile 64 KiB; preprocessing scratch, interpreter and dependencies add
to peak RSS. Large archive chunks can enlarge transfer without enlarging the
logical array. These figures are NOT a measured performance pass. First DEV
execution must measure RSS, wall time and cumulative CPU under the plan's
4 GiB / 30 minute per job / 12 CPU-hour overall limits. If necessary, run
separate full-family DEV cases as separate bounded jobs; do not label a partial
family as a completed control.

## Admitted DEV command

After the immutable public freeze, root writes a separate
`pilot_engine_20261008/DEV_ADMISSION.json` receipt with
`status="ADMITTED_DEV_ONLY"`, a 40-character `public_commit_sha`, explicit
`allowed_case_ids`, SHA256 entries for `detector`, `runner`, `generator`,
`contract`, `cases` and `summarizer`, and a `budget` containing
`remaining_cpu_seconds`, `max_wall_seconds_per_job` and `max_rss_bytes`.
The receipt is not included in its own hash binding. It admits this concrete
invocation; merely preparing this code does not generate controls.

Run the first complete frozen DEV case with:

```bash
python3 pilot_engine_20261008/run_dev.py \
  --contract pilot_controls_20261008/control_contract.json \
  --cases pilot_controls_20261008/development_cases.json \
  --generator pilot_controls_20261008/generator.py \
  --summarizer pilot_controls_20261008/summarize.py \
  --freeze-receipt pilot_engine_20261008/DEV_ADMISSION.json \
  --case 'SETI_RADIO_PILOT_20261008_DEV:strong:000' \
  --output pilot_engine_20261008/dev_runs/first_strong_000
```

Use another exact `--case` identity and a fresh output directory for each
subsequent admitted case. Alternatively, `--all` selects the complete frozen
DEV list in its fixed order, subject to the same whole-job watchdog. An
existing output directory is refused. Failures do not trigger retries or
redraws. VAL manifests and sky data are rejected by this runner.

Each case saves the frozen definition, truth, exact C-order array byte hashes,
six compressed full carrier maps, all ON threshold carriers with OFF witnesses,
endpoint-localized raw/final recovery, resource measurements and artifact
checksums. Root job outputs also retain all outcomes, an explicitly development
only summary, admission bindings and whole-process CPU/RSS/wall accounting.
Missing panel cases remain missing; a one-case run cannot masquerade as a
complete 24-case DEV panel or an independently validated scientific result.
Wall/CPU signals reserve time for failure logs before the admitted caps.
