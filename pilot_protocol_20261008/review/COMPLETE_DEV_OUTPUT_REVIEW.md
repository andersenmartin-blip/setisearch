# Independent completed DEV review — 8 October 2026

**PASS for all 24 distinct DEV outputs. Fresh validation and sky admission
remain separate.** The reviewer read retained outputs and checked identities,
hashes, maps and endpoint arithmetic, without invoking RNG, the generator,
the detector or a source fetch.

All 24 frozen identities are present once. All 384 case artifact hashes and
sizes match, and all 144 six-scan maps are complete. Every ON carrier (4096
per scan) and OFF carrier (4596 per scan) has all 21,660 valid hypotheses,
equal to 5415 drifts × four widths. Every threshold ON carrier is retained
with parameters equal to its corresponding maximum map.

| DEV family | Cases | Localized pre-OFF all-active recovery | Localized final all-active recovery | Cadences with any survivor |
|---|---:|---:|---:|---:|
| Strong | 4 | 4 | 4 | 4 |
| Operating | 8 | 8 | 8 | 8 |
| Matched RFI | 8 | 8 | 0 | 0 |
| Noise | 4 | Not applicable | Not applicable | 0 |

All injected active-ON recovery counts independently match both endpoint
localization bounds. There are 3343 retained raw ON carriers and 878 surviving
carriers across the panel. All 10,029 OFF comparisons have consistent
dispositions; all 7347 recorded veto witnesses meet the threshold and both
coupled endpoint conditions. An exhausted no-veto family has no witness and
its checked maximum remains below 8. Noise cases have zero raw threshold hits.
The root's complete summary agrees with these independent family counts and
correctly retains `NOT_EVALUATED_DEVELOPMENT_ONLY`.

All job resource caps pass. Maximum whole-job wall is 94.03364288000012 s;
maximum peak RSS is 79,839,232 B. The sum of job CPU receipts is 1756.770077 s,
and the case-only sum is 1730.658752 s. The more complete conservative charge
is **1757.554301 CPU s**: first job receipt 66.326375 plus the larger of the
other 23 job receipts and coordinator child-process CPU 1691.173278, plus
coordinator CPU 0.054648. This avoids double counting while including process
termination and controller work.

The updated ledger leaves 36,635.758461981 CPU s after measured new jobs and
the conservative historical CI reservation. A prospective full VAL_A
reservation of 142 × 250 = 35,500 CPU s fits, leaving 1135.758461981 s before
additional preparation or pilot work. Historical/preparation unknowns remain
explicit; this is a feasibility bound, not a complete measured historical
total. The unused DEV reservation is released after completed actual charges.

No scientific settings changed during DEV. The separate VAL_A wrapper was
statically reviewed; root must publish and admit the complete fresh bank
before any validation realization. The declared synthetic results do not
calibrate telescope noise or establish extraterrestrial candidates.
