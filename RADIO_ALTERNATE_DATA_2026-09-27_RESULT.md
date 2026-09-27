# Other radio data: HD 189733 selected on 27 September 2026

The owner's instruction to continue with other data, without contacting anyone,
has been executed. **HD189733 / HIP98505, cadence 85030** passes the prospectively
declared metadata and gross direction-consistency screen. Its new source contract
is preparation-only. HD1461/71139 retains its unresolved pointing hold and its
unsent request; resolving that target is no longer a prerequisite for this path.

## Selection and acquisition

The [metadata protocol](RADIO_ALTERNATE_DATA_2026-09-27_PROTOCOL.md), code,
configuration and source deny-list were published in
[`1cb49ed0d500c290ba88ff29529fc37b25756186`](https://github.com/andersenmartin-blip/setisearch/commit/1cb49ed0d500c290ba88ff29529fc37b25756186)
before any of these new remote reads. Selection followed the original host
ordering and fixed L-band criterion. Rank 41 qualified first; **reserve rank 43,
GJ724/HIP91608, cadence 73005, was not opened**. The three excluded S-band rows
remain recorded. These alternatives and HD1461 occupy the existing three-slot
shortlist; the plan still ends on 9 October.

The run lasted from **20:39:51 to 20:49:08 UTC on 27 September 2026**:

| Scope | Requests | Response-body bytes | Active seconds |
| --- | ---: | ---: | ---: |
| This alternate metadata acquisition | 80 | 55,841 | 557.320353 |
| Earlier completed source screen | 83 | 263,066 | 625.844791 |
| These two source screens combined | 163 | 318,907 | 1,183.165144 |
| Combined predeclared ceilings | 283 | 8,651,674 | 1,825.844791 |

The 80 requests comprise two JSON GETs, six HEADs and 72 conditional range GETs.
All returned the expected 200/206 response. Counts are observed response bodies,
not total network-wire bytes; other earlier metadata investigations retain their
separate budgets. There were no retries, redirects, authentication workarounds,
spectral reads, scientific trials, acquisition reservations or external messages.
The spectral ledger remains unactivated and the exhausted synthetic ledger stays
closed. This completed source screen is not to be replayed or reset.

## Six consistent headers, with a limited provenance claim

All six fine-resolution files come from the public
[AGBT16A_999_97/holding archive](https://bldata.berkeley.edu/pipeline/AGBT16A_999_97/holding/).
The exact URLs, strong ETags, sizes and raw conditional response bytes are retained
in [attempt01](results_radio_alternate_2026-09-27/attempt01).

| Scan | Role | Header UTC, rounded to second | ON separation from retained official position |
| --- | --- | --- | ---: |
| 0003 | ON | 2016-03-17 16:33:36 | 0.239880 arcsec |
| 0004 | OFF | 2016-03-17 16:39:06 | — |
| 0005 | ON | 2016-03-17 16:44:36 | 0.193534 arcsec |
| 0006 | OFF | 2016-03-17 16:50:06 | — |
| 0007 | ON | 2016-03-17 16:55:36 | 0.275637 arcsec |
| 0008 | OFF | 2016-03-17 17:01:05 | — |

The exact NASA Exoplanet Archive query resolves HD 189733 b / HD 189733 /
HIP 98505. The three ON directions satisfy the **fixed 60-arcsecond** proximity
criterion; no coordinate was corrected or propagated to another epoch.
This establishes declared source identity and gross catalogue/header consistency.
It is **not an independent audit of measured telescope pointing**, an ephemeris
uncertainty bound, or evidence for an artificial signal. The archive catalogue's
raw time strings and header MJDs are both retained; the table uses header MJDs.

Every file declares shape `[16,1,264503296]`, float32 values, chunks
`[1,1,1048576]`, integration time 17.986224128 s, and channel spacing
−2.835503418452676 Hz. Frequency endpoints are 1126.4648465855034 and
1876.46484375 MHz. The filter declaration is Bitshuffle/LZ4 (HDF5 filter 32008).
Reading that declaration did not decode a spectral chunk. The cadence contains
96 integrations on one date and spans 1,936.779586 s from first start to last end;
the ON/OFF visits are not independent observing dates.

## Reproducible preparation and verification

The six headers were independently replayed through HDF5 from the **72 retained
byte ranges**, with no network fallback or dataset indexing. All selected
attributes, geometry and filter declarations match. The new
[preparation contract](config/radio_hd189733_source_preparation_20260927.json)
has SHA-256 `98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1`.
Its source inventory matches none of the conservative 243 URLs collected from
72 earlier configurations; that deny-list includes reservations and does not
claim that every listed URL was consumed.

The normal source-contract loader accepts the six-scan inventory but correctly
returns **BLOCKED**: integrated protocol, source codec/runtime qualification and
executable extraction windows remain absent. Its empty `windows` field and
preparation stage stay immutable. Later geometric identities are a separate
artifact and do not make this contract executable.

Six new metadata boundary tests passed before acquisition. Eight further tests
cover the new widened-window binding described in the
[geometry result](RADIO_HD189733_GEOMETRY_2026-09-27_RESULT.md). The
[postflight reconciliation](results_radio_alternate_2026-09-27/postflight_verification.json)
verifies all 80 retained body hashes/counts, five inputs against the published
freeze, an independent vector-angle calculation and 15 unchanged old input pins.
No old detector/control/acquisition tests were replayed as progress.

## Exact continuation

The alternate metadata screen, source preparation, nominal geometry study and
window-identity v2 implementation are complete. Continue from the **new HD189733
window identities**, not the old HD1461 checkpoint. The next bounded task is a
source-specific motion/width design with an explicit physical/observer domain,
fresh disjoint development/calibration/evaluation identities, new numeric transfer
and recovery/RFI/null gates, and codec/runtime handoff evidence. Publish and verify
one integrated prospective execution protocol and cumulative resource/trial ledger
before any telescope spectrum is opened. Do not inherit HD1461 thresholds,
physical support or live receipts, and do not tune a failed evaluation to pass.

The existing daily continuation prompt now follows this change of source; its
end date and schedule were not extended. No new continuation task was created.
Primary neighbor9, failed/closed M43AI, the original 112+128 M43AF holdouts,
unresolved M15 GJ581 and M33 HD3651, all earlier dispositions, paused LS8BD–LS8BE,
untouched LS8BF and unsent CHEOPS remain unchanged. **No messages are to be sent.**
