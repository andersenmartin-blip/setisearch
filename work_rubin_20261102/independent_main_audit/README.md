# Independent Rubin numerical audit

This directory uses a separate scalar implementation (`independent_science.py`) with Python statistics, `math.hypot`, and ERFA TAI-to-UTC conversion. It imports no production detector functions and performs no network requests. All source, forced-source, object and visit identifiers remain exact strings.

The final corrected development method passed **19,096 comparisons** (maximum numeric difference 9.09e-13). All 259 source and 326 forced records were reproduced, including 40 source and 50 forced numerically evaluable October measurements. Neither unchanged stream triggered.

All **36 fixed recovery cases** were independently rebuilt from raw development direct-science flux. **528,411 comparisons passed**, including 104,190 numerical comparisons; maximum numeric difference was 3.64e-12. Every original case placement was preserved across the technical correction. All quoted errors and nonflux metadata remained unchanged. The result was 18 recovered observation-centered cases and 18 unsampled longest-gap cases, with no affected measurement missing exposure duration.

The exposure-overlap calculation also agrees with an alternative closed form to 3.85e-8 in fractional exposure, consistent with subtraction of nearby MJD values. This did not change any recovery classification. These controls validate a deliberately selected detector-response challenge, not survey duty cycle, random-phase sensitivity, upstream alert completeness or independent physical trials. They reuse seven objects and nine object-band pairs, and some observed injection intervals overlap.

The completed **main audit passed 33,609 comparisons** (4,587 numerical comparisons; maximum difference 9.09e-13). It independently verified every normalized/scored/trigger row, duplicate handling, raw-file lineage, all **188×2 eligibility rows**, both summaries, exact cutout associations and output hashes. All 807 selected source IDs in the earlier metadata snapshot also occur in the main acquisition, with no added or missing identities.

| Separate main stream | Returned objects | Measurements | Numerically evaluable objects | Evaluable October measurements | Triggers |
|---|---:|---:|---:|---:|---:|
| Source-position science photometry |188|807|2|7|0|
| Object-position forced photometry |10|77|3|14|0|

The two streams cannot be added as independent stars or observations. All 21 evaluable measurements have long reference gaps and unknown withdrawal status; forced measurements also lack measurement-quality flags. The original minimum of 50 evaluable main objects is **not met**. No qualified null result or survey sensitivity follows.

For source photometry, 130 objects have all October measurements rejected by the frozen quality/numeric guards, 56 lack usable historical baseline, and two remain numerically evaluable. Forced photometry is absent for 178 selected objects; seven of the ten returned objects lack usable baseline. These are preserved outcomes, not grounds to loosen the frozen method.

The initial main audit stopped in its final metadata-only comparison because a broad filename glob also selected receipt JSONs. The data-file pattern was corrected to exact two-digit source-data filenames; the complete rerun then passed. No production science file or method was changed by this audit fix.

Run the relevant audit in a separate copy because each command rewrites its report:

```bash
python3 audit_development.py
python3 audit_recovery.py
python3 audit_main.py
```

Numeric agreement is not an origin determination. Missing withdrawal status, absent forced measurement flags and long reference gaps remain explicit scientific limitations.
