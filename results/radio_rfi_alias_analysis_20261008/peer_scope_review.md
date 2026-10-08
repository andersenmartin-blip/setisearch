# Independent scope and equation review

This review reads the frozen detector and generator as text, together with the previously retained motivating-evidence report. It neither imports those modules nor generates arrays, preprocesses power, scores templates, changes thresholds, or reclassifies the experiment. Numerical tables in the final analysis require their own metered calculation and independent retained-record checks.

## Equations to verify in the new retained-data table

For an ON winner and an OFF template, let `delta_f = f_OFF - f_ON` at the common reference time, `delta_d = d_OFF - d_ON`, and `t_first`, `t_last` be the originating ON scan's first and last integration midpoint times relative to that reference. The frozen compatibility test is:

`abs(delta_f + delta_d*t_first) <= T` and `abs(delta_f + delta_d*t_last) <= T`,

where `T = ((w_ON+w_OFF)/2 + 2) * max(abs(df_ON),abs(df_OFF))`.

Both endpoints imply the necessary slope condition `abs(delta_d) <= 2*T/(t_last-t_first)`. It is necessary rather than sufficient: the allowed reference-frequency interval must also be nonempty, include an admitted discrete carrier, and have valid score support. The detector's preliminary slope restriction follows directly from these endpoint inequalities.

All fourteen previously recorded survivors have `w_ON=33`. The OFF width bank is `1,3,9,33`, so the matching tolerances in common channel-width units are respectively `19,20,23,35`. Width33 gives the largest permissible slope difference. The leaked winners have drifts around -3.17 to -3.22 Hz/s in case002 and around -3.14 Hz/s in case003, while the declared injected drift is -4 Hz/s. Checking the largest bound from retained ON endpoint times can establish that the exact injected drift is excluded for every width, independent of its reference frequency. This is a deterministic geometric conclusion; the new script must compute the exact bound and margins.

Truth localization is a different test. It uses `T_truth = (2 + max(w_ON,w_oracle)/2)*abs(df_ON)`. A width33 winner and width33 oracle therefore have a localization tolerance of18.5 channel-width units, not the35 units allowed for matching width33 against width33. A carrier can be unlocalized without its truth path necessarily being OFF-incompatible; both tests must be calculated explicitly.

Use `delta_frequency/abs(df)` for plotted signed frequency errors and label these as channel-width units. The original native frequency spacing is negative, so the sign is opposite that of a native source-channel coordinate displacement.

## What the retained evidence establishes

- Every surviving ON carrier was checked against all three OFF scans. For a survivor, `family_exhausted=true` plus a finite maximum checked score below8 establishes absence of a threshold-crossing valid compatible OFF template in the frozen family. The complete B retained-data audit is the integrity basis for that record; the new table can check the selected records without repeating the full experiment or audit.
- The injected RFI was initially localized in all three ON scans and all truth-localized ON hits were vetoed. The failure is fourteen other ON winners surviving in two interference-containing cadences, which violates the predeclared zero-survivor requirement.
- Bright global OFF winning paths can be compared geometrically with each alias to illustrate why those specific paths do not veto it. Global winning maps alone do not prove absence of all compatible OFF witnesses; the exhausted comparison records provide that evidence.
- The thirteen adjacent firstON carriers in case002 are correlated responses within one synthetic cadence. They are not thirteen independent events. Together with case003, this is two failed RFI cases, not fourteen independent trials.

## Limits on the explanation

The geometry can demonstrate exclusion of the exact injected trajectory and measured global OFF winners from the ON alias's allowed comparison region. It cannot isolate how much of an alias's ON score comes from the injected signal, noise, or preprocessing. The retained outputs do not contain a noise-only counterfactual with the injection removed. Integration smearing and broad-box off-drift responses are a plausible mechanism consistent with the frozen injection model, winning widths and path geometry; that causal attribution remains an inference.

Only the best ON template per reference carrier was classified and retained in the maximum map. The new analysis must not claim that alternative nonwinning ON templates were absent, that a different candidate-representation policy would necessarily succeed, or that the frozen implementation is defective. Proposals to preserve a candidate family or alter OFF compatibility belong to a later prospectively frozen plan with fresh validation, including signal-retention and near-frequency diagnostic controls.

The two failed qualification decisions remain failed. This selected retained-data analysis provides a mechanism constraint and an auditable description, not new qualification, sky false-alarm calibration, evidence of an extraterrestrial signal, or authorization to open telescope values.
