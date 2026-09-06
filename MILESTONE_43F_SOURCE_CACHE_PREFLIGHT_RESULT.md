# M43F: native coverage and channel-mapping transfer result

**Preflight complete: the fixed M43E bank is incompatible with the existing M37 source/cache contract.**

The M43E 1,701-template bank retains its passed geometric result. M43F identifies the concrete engineering changes required to score that bank on telescope data. No production detector, source contract or threshold was changed.

## Gate results

| Check | Result |
|---|---|
| Original 93-template extraction headrooms | All 30 scan/window geometries reproduce exactly |
| Current extraction covers the 1,701-template bank with width 129 | 0/30 scan/window pairs |
| Current cache factor precondition holds for entire bank | 0/30 scan/window pairs |
| Unique template/integration factors below 1 | 62,800 / 163,296 |
| Literal duplicate-channel witnesses | 30 / 30 selected minimum-factor mappings |
| Proposed wider intervals cover the fixed bank | 30/30, including the 129-channel filter and fixed reserve |

The same factor table is used across frequency windows, so the 62,800 factor violations are counted once, not multiplied by five. The 30 collision examples are scan/window checks, not independent astronomical events. The unchanged original bank still passes its original extraction checks.

## Example at 1412.5 MHz

In epoch1_on, 761/1,701 templates extend beyond the old extraction at one or more integrations/carriers for width 129. The worst required extensions are 78,841 channels below and 136,478 above the old filtered range. Even width 1 is not fully covered.

The selected minimum factor is 0.9996718307359274. Its full proxy-support mapping contains 245 adjacent pairs mapped to the same native channel. The first pair uses proxy carriers 1411444248.5056973 and 1411444251.3412006 Hz. Their indices in the old extraction are [-77214, -77214]; the corresponding indices in the proposed wider extraction are [1629, 1629].

The verifier checks every frozen collision pair in the proposed geometry as well: 30/30 remain duplicated while lying inside valid 129-channel filter coverage. Widening the extraction therefore does not by itself solve the mapping incompatibility. The old strict-injectivity requirement must be addressed explicitly before using a new adapter.

## Exact extraction and resource requirements

Archive channel intervals below are descending-frequency, start-inclusive and stop-exclusive. They preserve the old interval and include a fixed two-channel rounding reserve beyond the widest filter. Their endpoints lie inside the frozen remote dataset dimensions. This is metadata verification, not a new remote-file availability check.

| Window | Proposed archive interval | Native channels | Increase | Raw MiB/scan | Raw+normalized+frequency MiB/scan |
|---|---|---:|---:|---:|---:|
| m37_1400p5 | [167265950, 168394955) | 1,129,005 | 23.13% | 68.91 | 146.43 |
| m37_1406p5 | [165148986, 166279623) | 1,130,637 | 23.30% | 69.01 | 146.64 |
| m37_1412p5 | [163032021, 164164291) | 1,132,270 | 23.48% | 69.11 | 146.86 |
| m37_1418p5 | [160915057, 162048959) | 1,133,902 | 23.66% | 69.21 | 147.07 |
| m37_1425p0 | [158621679, 159757349) | 1,135,670 | 23.85% | 69.32 | 147.30 |

All five proposed intervals exceed each of the current per-source limits: 916,947 native channels, 64 MiB raw, 8 MiB frequency coordinates and 140 MiB combined raw/normalized/frequency arrays. These are limits of the frozen software contract, not evidence that the machine lacks enough RAM. Any larger or streaming source factory needs its own verified memory accounting; no cap was raised here.

Estimated width-specific cache payloads total approximately 3.47–3.49 GB per window across six scans and eight widths. Disk payload totals are not simultaneous resident RAM requirements. The estimate excludes file headers, transport buffers, decompression, filter scratch, masks, operating-system caches and other live arrays. Cache-bank and source identities must be rebuilt; matching dimensions do not authorize reuse of old contents.

Every proposed extraction shifts the normalization origin by a nonzero amount modulo 4096. The original normalization is anchored to the extracted ascending channel zero, so changing the extraction changes block alignment and can change normalized values. Define the new normalization scope before reading/scoring the new products; never claim old normalized or threshold receipts still apply.

## Next transfer contract

1. Freeze a separately named source/normalization adapter for the proposed intervals, with verified payload ancestry and bounded streaming memory.
2. Specify and qualify native-channel gathering when neighboring proxy carriers repeat a raw channel. Preserve the full carrier lattice, native-filter order, OFF controls and explicit repeat correlations; do not silently deduplicate or drop carriers.
3. Give the fixed bank and every source/cache product new identities. Test local and exhaustive score agreement, then execute predetermined real-data anchors and renew null/threshold calibration.

The immediate next milestone is that transfer adapter and its synthetic qualification. The M43F gate blocks using the old adapter for the new bank; it does not reverse M43E or indicate a sky-signal failure. The existing authorization to continue analysis and publication remains in effect.

## Verification and limits

Public freeze `99dfaa5e7c6ce0956ed82eccf99d8473e2bbd17a`, tree `54bc19800e238c9c498a5e3be6d9bd6b7d25baee`, was verified before execution. All 33 M43-family tests pass. This report regenerates the frozen result byte-for-byte, checks all 240 scan/window/width inventories and directly recomputes the 30 full minimum-factor mappings and collision pairs. The endpoint method is checked against exhaustive toy lattices; positive factors make endpoint coverage bound every interior carrier. No broader repository test run is claimed.

Result identity: `4c26515e18ec7ef429a1cd7c883fd938f4eaa063ba563dc8a0e19a54c8ae4537`. The source is M43E confirmation `41d0a61648d877710aef1549b63e30f66e1220fdd91bd31bd1e8061ca8c27198` and fixed bank `84524f7e129c0b414bde5004fe64bfb3ff94877357a7bb4dce399562d945d873`.

No telescope requests, spectral reads, injection trials, cache payloads or scores were evaluated. Proposed geometries are not attested source products. No sensitivity, recovery rate, occurrence rate or technosignature claim follows. All M37/M41/LS results and M43E denominators remain unchanged.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43f_source_cache_preflight.py
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43f_result_report.py
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_m43*.py' -q
```
