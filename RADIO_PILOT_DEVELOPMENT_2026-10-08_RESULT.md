# New radio study: complete development and source qualification, 8 October 2026

The approved 7–20 October study has completed its new 24-case development bank
using the unchanged, prospectively frozen full-cadence detector. No telescope
pilot or independent validation values were opened to obtain these results.

| Development family | Cases | Result |
| --- | ---: | --- |
| Strong injected tracks | 4 | 4/4 localized after OFF in every active ON |
| Operating-level tracks | 8 | 8/8 localized after OFF in every active ON |
| Matched ON+OFF interference | 8 | All initially detected; all rejected, zero survivors |
| Noise, four declared laws | 4 | Zero ON hits and zero survivors |

The detector searched all 4,096 ON reference carriers, 5,415 drifts spanning ±4 Hz/s and
widths 1/3/9/33 in each complete six-scan case. All 144 maps retain 21,660 valid
hypotheses per carrier; 384 case artifact hashes were independently verified.
Single-ON activity is retained. Multiple neighboring threshold carriers around
one injection are not independent signals or discoveries.

Whole-process/parent accounting charges 1,757.554301 CPU-s for DEV. Maximum job
wall time 94.033643 s and RSS 79,839,232 B passed the unchanged limits. The prior
failed CI reference remains closed and conservatively charged; its nominal
engineering-byte compliance remains unverified.

Source metadata qualifies six historical HD189733/HIP98505 ON/OFF scans from
one visit, 17 March 2016. Exact 96 compressed payload ranges total 305,133,821 B,
with 384 MiB physical decoded chunks. Current metadata acquisition spent
1,158,240 B in 426 requests, including the preserved failed enumeration. No
payload was fetched. The source report records pointing, times, exact grids,
codec, misleading dimension labels, ETags and whole-file checksum limitations.

The 24 complete job archives and per-member hashes are in
`pilot_protocol_20261008/dev_archives/` and `dev_archives_manifest.json`.
Scientific freeze: `cbc27ebfb10fc09f58a8ab4a1f00adad47ab1960`;
source metadata freeze: `a35b5436934b6709151c8ada3ba7da5b74919907`.
Independent scientific and output reviews are in `pilot_protocol_20261008/`.

Next is the separately admitted 142-case fresh VAL_A bank. DEV is descriptive;
the full joint validation gates must pass before the telescope pilot opens.
Old holdouts, closed failures and reserved VAL_B remain untouched.
