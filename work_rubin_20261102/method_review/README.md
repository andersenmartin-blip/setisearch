# Frozen Rubin archival-dimming method and development controls

**The adopted detector uses a 180-day prior archival baseline, direct science-image flux, a 0.3-mag depth cut and a conservative deficit score of at least 5.** It is ready for a separately selected main sample. The earlier 30-day proposal is historical and was not adopted: the twenty development objects have only two October observing dates and much older June/July history. The longer context was fixed from those development data before any main-sample flux was opened. It does not establish local quiescence across the long gap.

`MAIN_METHOD_FREEZE.json` is the final release guard. It binds the executable detector, configuration, all thirty-six fixed injection cases and results, development summary, technical corrections and six passing boundary checks. The original proposal and first failed control attempt are preserved in `attempts/initial_before_technical_fixes/`. No threshold or injection position was changed in response to control recovery, and no main-sample flux was read for this method work.

## Actual development results

| Separate stream | Returned objects / measurements | October objects / measurements | Numerically evaluable objects / visits | Original hits |
|---|---:|---:|---:|---:|
| DiaSource-centroid science flux, primary | 20 / 259 | 20 / 119 | 8 / 40 | 0 |
| DiaObject-centroid forced science flux, quality-limited context | 14 / 326 | 14 / 114 | 9 / 50 | 0 |

The source quality rules admitted 237 of 259 historical measurements: 21 had the dipole flag and one had the bad-pixel flag. Of 119 October source rows, nine fail quality, seventy lack the required baseline, and forty are numerically evaluable. All forty use a baseline with a gap exceeding thirty days. Missing withdrawal metadata affects every returned measurement despite explicit requests. Consequently **zero development objects are certified fully quality-vetted** by these tabular checks. The forced stream additionally lacks measurement-quality flags. Numerical counts are conditional screening denominators, not confirmed physical dimmings or a qualified null result.

## Adopted detector

The authoritative details are in `CONFIG.json` and `detector.py`:

- Run source and forced photometry separately; do not combine them as additional observations. Use signed `scienceFlux` and positive finite `scienceFluxErr` in nJy. Preserve exclusions, missing fields and exact integer/string identifiers.
- For sources, reject explicit critical centroid, science-fit, pixel, dipole, glint and injection flags. Unknown mandatory flags are excluded with an explicit reason. A missing withdrawal field is retained as `WITHDRAWAL_STATUS_UNKNOWN`, never inferred non-withdrawn. The separate forced stream remains quality-limited.
- Deduplicate exact repeated measurement IDs. Conflicting versions and multiple measurements of one object/visit/band, including alternate detectors, are excluded as ambiguous. Count distinct **visit IDs**, not visit-detector pairs.
- For every October measurement, use admitted same-band measurements from the preceding 180 days, excluding its entire UTC date. Require at least five distinct visits across three earlier UTC dates. No faint-point clipping, trend fitting or filter mixing is performed.
- Let B be the median baseline flux and S=max(1.4826 MAD, median quoted baseline error). Require B>0 and B/S>=10. S is not divided by sqrt(N); it is a conservative empirical reference scale, not a calibrated standard error of the median.
- Retain a hit when F/B<=0.7585775750291838 and (B-F)/sqrt(sigma_F²+S²)>=5. The flux ratio is the exact 0.3-mag point-estimate cut. The score is **not** a Gaussian significance, a global false-alarm probability or a five-sigma lower bound on the depth. Every singleton and threshold crossing is retained.
- For positive F, delta_mag=-2.5 log10(F/B). Nonpositive fitted science flux stays in the linear-flux calculation but receives a null magnitude and an explicit review flag. Never use log(abs(F)) or turn missing flux into zero.

Every tested row records its baseline IDs, distinct visits/dates, span and gap. Image/association/variability review remains necessary. In particular, a source's state during the approximately hundred-day unsampled gap is unknown.

## Thirty-six controls, with sampling losses retained

The frozen grid contains three depths (0.3, 0.6, 1.0 mag), three durations (60 seconds, one hour, one day), and four distinct placements per combination: **36**, not 108. Development exposures are about 15–30 seconds and short within-band spacing is about 20–40 seconds. Eighteen positions are observation-centered; eighteen are deliberate gap challenges. Seven objects and nine object-band pairs are reused, so these are not independent trials or random-phase survey sampling.

| Control outcome | Count |
|---|---:|
| Sampled and numerically evaluable | 18 |
| Recovered among those sampled cases | 18 |
| No exposure overlaps the injected event | 18 |
| Total | 36 |

Every depth-duration cell has two recoveries and two unsampled misses: 2/4 unconditional and 2/2 conditional on sampling in this designed set. These fractions do not estimate the survey duty cycle or upstream alert completeness. All unchanged development control curves retain zero hits.

The injection subtracts alpha B(1-10^(-0.4d)) from the measured signed science flux, preserving original residuals, quoted errors, flags, identities and times. Alpha is the exposure fraction overlapping the top-hat. Missing exposure durations use explicitly marked midpoint sampling; **no affected row in these completed controls required that approximation**. The complete frozen detector, including its baseline rules, is rerun. Fixed quoted errors make this a digital post-processing test, not a new photon-noise experiment. Full target-band score records are retained in `RECOVERY_RESULTS.json`; the compact grid and hashes are in `RECOVERY_SUMMARY.json`.

The first attempt stopped on an overly broad assertion about missing exposure times in historical rows, before any result file. The corrected implementation also counts unique visit IDs and rejects ambiguous alternate-detector measurements. The thirty-six positions, numerical thresholds and development counts remain identical. `TECHNICAL_CORRECTIONS.json` records both changes. Six boundary checks explicitly test four visits represented by five detector rows, duplicate ambiguity, depth/time/filter boundaries, negative flux and missing flags.

## Physical quantities, time and missing history

Official Fink documentation distinguishes direct science flux, template flux and signed difference `psfFlux`; their fitted measurements do not obey exact science=template+difference algebra. Do not construct total flux by blindly adding the latter two, or interpret a negative difference flux alone as a 0.3-mag stellar dimming. For positive total F in nJy, m_AB=31.4-2.5 log10(F); the usual small-error magnitude formula applies only at sufficient signal-to-noise. [Fink photometry](https://doc.lsst.fink-broker.org/data/photometry/).

The actual endpoint schemas expose direct flux/error/time/band/identity in both streams. Forced rows have no measurement-quality flags. Source science fits use DiaSource positions; forced science fits use DiaObject positions. Some field definitions evolve or remain unpopulated, so the saved schema and actual response govern each record. [APDB schema](https://sdm-schemas.lsst.io/apdb.html) · [Fink API definitions](https://doc.lsst.fink-broker.org/services/api/definitions/).

`midpointMjdTai` is effective visit-midpoint MJD in TAI, not JD or UTC. Convert explicitly with Astropy and retain the original value. October's UTC interval corresponds to **[61314.00042824074, 61345.00042824074) MJD(TAI)** using Astropy 8.0.2 and its installed leap-second table. Do not call these times barycentric. [Astropy time](https://docs.astropy.org/en/stable/time/index.html).

Fink warns about missing fields, object mis-association and early reliability scores. No additional reliability threshold is used here. Rubin's alert product contains at most twelve months of associated history; repeated packets are not new visits. Upstream masks, association and filtering already censor the stream, and absent rows are not constant-flux observations. [Fink quality](https://doc.lsst.fink-broker.org/data/quality/) · [Known issues](https://doc.lsst.fink-broker.org/data/issues/) · [Rubin alert packets](https://prompt-products.lsst.io/products/alerts/index.html) · [Upstream filtering](https://prompt-products.lsst.io/processing/filtering/index.html).

## Main-sample interpretation and reproduction

The required fifty-object minimum is **not established by these twenty development objects or by an API/metadata count**. Apply the frozen method to the disjoint metadata-selected main sample and report returned, admitted, numerically evaluable and fully reviewed objects separately. The primary and forced denominators must not be added. Fewer than fifty usable main objects is a forstudie; insufficient image/quality/association controls make the result limited or partial even if fifty objects are numerically evaluable. Do not loosen the detector to reach the minimum.

In a separate working copy with the saved development input files restored:

```bash
python3 work_rubin_20261102/method_review/run_development.py
python3 work_rubin_20261102/method_review/validate_boundaries.py
```

For recovery reproduction, preserve the published output and run `recovery_control.py run` in that separate copy without an existing `RECOVERY_RESULTS.json`; the script verifies its frozen inputs before execution. `prepare` is not part of resuming or reproducing the already frozen controls. No network access is needed for these calculations.

Primary-source documentation was retrieved on **2 November 2026**. `SOURCES.json` preserves URLs, retrieval dates, local schema hashes and the approved-plan hash. The original approved plan itself was not edited by this review.
