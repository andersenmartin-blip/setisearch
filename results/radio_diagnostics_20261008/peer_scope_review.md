# Manual review of retained transient and near-OFF diagnostic scope

Review date: 2026-10-08. This review reads the frozen generator, detector and control contract as text. It does not import or run them, draw values, search templates, or change the experimental rules. Numerical results below must be supplied by the separately metered retained-output analysis.

## Frozen sources read

- `pilot_controls_20261008/generator.py`: `full_panel`, `_profile`, `_ideal_projection`, `generate_case`.
- `pilot_controls_20261008/control_contract.json`: geometry, amplitude definition, recovery definition and qualification gates.
- `pilot_engine_20261008/detector.py`: `_score_tile`, `_restricted_off_witness`, `classify_hits`, `recovery_matches`.

The relevant diagnostic families are `single_row_transient` and `near_off_contamination`. The latter is the exact case-bank name; “near-OFF signal” is a prose description. Neither family has `eligibility_case=true`, and neither supplies an additional qualification gate. Their results cannot reverse B's failure.

## Single-row transient: what was actually injected

The 12 cases cross the three ON indices (0, 2, 4), transient row (0, 15), and intrinsic width (1, 3). There is exactly one active ON per case. The main injected layer is zero in the other 15 rows of that ON and in every other scan. The background remains present in all rows.

The frequency profile is the frozen intrinsic top-hat convolved with the uniform frequency sweep during one integration, using a declared drift of -4 or +4 Hz/s and the native descending frequency axis. This is a frequency-localized pulse after integration smearing, not a broadband row disturbance. The declared linear truth trajectory is defined throughout the scan even though injected power occurs at one integration only.

The amplitude is chosen before noise from the ideal projection over the complete 16-row scan, with only the selected row contributing. Its nominal ideal box score is 24. Consequently the one-row layer has a substantially higher per-active-row amplitude than a comparably projected signal distributed over all rows. Nominal score is not the measured robust score, a calibrated S/N, a flux calibration, or evidence that a faint real single-row event would survive.

The statistic sums a hypothesized track over all 16 rows and divides by `sqrt(Nrow * width)`. It does not require two populated rows or a minimum number of active rows. A sufficiently bright contribution confined to one row can therefore exceed the ON threshold. OFF absence alone is insufficient to reject such an event. A line fit to a single populated time is intrinsically underconstrained; differences between a retained winning drift and the injected drift do not independently establish an erroneous temporal trend in the pulse.

The localized-recovery rule nevertheless tests the winning linear track against the declared truth at both first and last integration-centre times of the active ON. It uses tolerance `(2 + max(winning_width, injection_oracle_width)/2) * abs(df)`. Thus a surviving carrier need not count as a truth-localized recovery, and a localized recovery does not prove multirow emission. Report both outcomes separately.

Meaningful retained-only measurements are the case-level localized pre/post-OFF recovery, raw/surviving carrier counts, source-row placement, declared and retained winning widths/drifts, retained ON score range, and the presence/absence of OFF witnesses. If normalization summaries are retained they may be described; they do not provide the per-row matched-track contributions needed to demonstrate measured temporal concentration. The original power and standardized residual arrays are not implicitly available merely because maximum maps were saved.

Do not infer a real-sky transient false-alarm probability or universal rejection rate from these 12 designed, strong, Gamma-background controls. Many neighboring carriers produced by one event are correlated responses, not independent transient events. No morphology filter is currently present; a future temporal-support rule is a proposal for a later separately qualified plan.

## Near-OFF contamination: what was actually injected

The 12 cases cross one active ON index (0, 2, 4), intrinsic width (1, 3), and diagnostic OFF offset (2 or 8 native channels). The main line has drift 0 Hz/s and nominal ideal box score 12 in the selected ON only. A separate line with the same intrinsic width and nominal ideal box score 24 is injected only in the immediately following OFF (`scan_index - 1` belongs to the active ON indices). The other two OFF scans contain background only, rather than an injected counterpart.

The diagnostic OFF reference source channel equals the main reference source channel plus the declared positive channel offset. Because `df_hz` is negative, a positive offset corresponds to a lower physical reference frequency. Both layers have zero drift. A match between them therefore measures rejection of an intentionally neighboring frequency line, not a temporally continued copy of the exact main injected line.

`truth.json` records `flux_by_scan` only for the main active layer, and records active ON identifiers for the main signal. It does not record the near-OFF diagnostic layer's separate flux/trajectory. Its definition must be traced to the immutable case-bank fields and the generator text; an absence of that layer in `flux_by_scan` must not be interpreted as absence in the generated values.

The OFF matching tolerance uses `(ON_width + OFF_width)/2 + 2` native-channel equivalents, rather than the recovery tolerance above. It checks endpoint differences at the first and last times of the ON scan being tested, while scoring the compatible template on the selected OFF scan's own rows. All three OFF scans are examined for every ON threshold carrier, and any qualifying OFF witness vetoes that carrier. Thus the immediately following contaminated OFF is an intended likely source of witnesses, but a retained witness in another OFF can also veto; classify actual witness locations rather than assume them.

Every ON carrier retains only its maximizing drift/width for classification. The OFF comparison searches the compatible frozen frequency/drift/width family until the first score at least 8 is found. For a vetoed family `family_exhausted=false`, `maximum_checked_score` is a traversal-dependent checked maximum, and `checked_valid_compatible_templates` is a partial count. Neither can be described as the global OFF maximum or complete family size. The retained `witness` provides the actual sufficient veto, including score, drift, width, reference frequency and ON endpoint errors. For a nonvetoed exhausted family, the checked maximum and count do cover the valid compatible family.

Meaningful retained-only measurements are (i) whether the injected ON had a localized threshold hit before OFF, (ii) which of those localized hits were vetoed, (iii) any remaining localized and nonlocalized survivors, (iv) the OFF scan supplying each sufficient witness, and (v) the witness offsets and endpoint errors relative to the main and declared diagnostic lines. A witness's closeness to the declared OFF line can be shown geometrically; it does not by itself measure the fraction of its score caused by that line because row-level score contributions were not retained.

A case with no pre-OFF localized ON recovery is a detection/localization loss before OFF; it is not an OFF-caused loss. A case with pre-OFF recovery and no final recovery is an observed loss at the OFF stage under the frozen rules. These are different denominators. Since there is only one active ON per case, all-active and any-active localized recovery coincide here. The 12 controls do not measure the frequency of such neighboring contamination in real observations or establish the specificity of this filter on sky data.

## Suggested review boundaries

The analysis should use all 24 committed B cases from these two families, immutable case definitions, retained six-scan maximum maps, retained raw carrier classifications/OFF witness records, and retained localized-recovery summaries. Record input hashes and check the report against those saved records. No new synthetic data, rescoring, widened families, changed thresholds, or retroactive gates are needed.

The two conclusions can coexist: bright short pulses may survive the current detector, while nearby OFF emission can remove a main ON line. Tightening a spatial/trajectory rule or adding a temporal-support rule involves sensitivity tradeoffs and requires a future independent design and qualification. The current analysis documents those tradeoffs without selecting or implementing a new rule.
