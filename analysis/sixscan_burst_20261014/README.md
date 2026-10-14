# Complete declared-band six-scan burst method

This is a separately frozen method study, designed after the completed raw648 and matched216 studies. It uses 205 fresh prescribed synthetic identities: 63 calibration references followed by a 142-case joint signal/RFI/null/diagnostic panel. It does not reopen original validation A/B or admit the original sky pilot.

All six actual header epochs from the exposed 28 April 2017 cadence are preserved, including scan gaps. Each ON scan searches all 4,096 native reference carriers at the one common cadence midpoint, 5,723 drifts over ±4 Hz/s, seven four-row windows and widths 1/3/9/33. One combined top five is retained **per carrier**. Native4 aliases are compressed for scoring but every attainable global parameter alias survives into the OFF test. The OFF reference family has 6,652 carriers, including a 1,278-channel halo on each side.

The OFF test uses the retained four-row ON window's two midpoint endpoints. It queries an exhaustive inventory of every OFF native4 identity with score ≥8, across all seven windows and all widths, with every discrete drift alias. It never uses only the OFF top five to prove absence of a veto. Any compatible ON-alias/OFF-alias pair provides a witness. The separately declared binary64 predicate is computed in native-channel units. Width/window/minimum donor-index ordering resolves exact score ties.

Raw ON threshold10 and OFF threshold8 remain empirical robust-score cutoffs. Final survivors additionally require `(1 + count63(reference global ON maximum >= candidate score))/64 <= 1/64`. The references use the complete pre-OFF ON maximum. This rank calibration concerns only the declared independent Gamma16 law. It does not calibrate telescope RFI or sky significance. Empty final lists remain valid measured outcomes; failed or unsubmitted jobs are not empty lists.

The new operating/strong levels16/32 are nominal noiseless projection levels, not measured SNR or the original operating level12. The signal is an intrinsic one- or three-channel uniform line convolved with its exposure-duration drift sweep, in float64 before one float32 raw-power cast. Its oracle and amplitude are calculated before RNG. Placements, widths, drift signs and nuisance offsets have declared blocking/confounding, and burst-window counts are unequal. This panel cannot estimate independent causal factor effects or a physical sensitivity curve.

All programming and numerical inputs are pinned in `SCOPE.json`. `GO.json` is written only after exact immutable GitHub readback. Each primary identity has one exclusive claim and one draw. Independent QA may reconstruct that same recipe for verification; it is not another trial or a replacement draw. No retry or outcome tuning is permitted.

Execution order, from this directory after a valid GO:

```bash
python coordinator.py --phase primary_calibration --workers 4
python summarize.py --root . --calibration-only
python coordinator.py --phase primary_validation --workers 4
python coordinator.py --phase qa --workers 4
python summarize.py --root .
```

The coordinator records complete `wait4` CPU/wall/RSS evidence and all failed or unsubmitted indices. Four concurrent workers each have a 1GiB address-space cap; every child has 600 CPU-s and 1,800 wall-s limits. A separate 90,000 CPU-s stage envelope includes an unreleased 1,000-s preparation/delivery allowance. Historical period debits and reservations remain preserved; the earlier assistant-defined 12-hour ceiling was explicitly superseded by the user's continuing full-power instruction. No paid resources or new telescope requests are authorized here.

After all 205 cases and independent QA close with an integrity PASS, nine already exposed, postselected authentic six-scan bands may be described:

```bash
python coordinator.py --phase exposed --workers 4
python coordinator.py --phase qa_exposed --workers 4
python summarize.py --root . --exposed
```

These nine bands are a re-search of retained data from the same historical visit. They are not fresh observations, independent confirmation or new telescope frequency coverage. Any Gamma16 p on these real backgrounds is only a model diagnostic. A scientific control failure cannot be hidden by rank rejection or changed to a missing-data zero.

The retained artifact recipes, seeds, float32 inputs, maps, aliases, exhaustive OFF inventories, raw hits, witnesses, QA and logs support reproduction of these fixed draws. Fresh execution must use a separate copy and admission; existing once-only claims are intentionally retained and block accidental repetition. Reproduction is not another validation trial. Original A/B remains **FAIL_CLOSED**, 2016 remains protected, 2019 remains closed, and the formal checkpoint remains 20 October 2026.
