# Fresh six-scan replication after runtime rollback — 15 October 2026

This is **SETI_SIXSCAN_BURST_20261015_RECOVERY_V1**, a separately frozen replication with 205 fresh prescribed identities. The original `SETI_SIXSCAN_BURST_20261014` study has status **UNKNOWN_UNRECOVERED** after runtime rollback. Its 205 synthetic and nine descriptive identities are retired. They are not rerun, counted as measured nulls, included in this reference panel, or represented as completed validation.

The complete scientific design, normalizer, thresholds, amplitudes, geometry and gates are unchanged. Only the metadata builder namespace and generator namespace guard change in code; detector, worker, coordinator, independent QA and summarizer are byte-identical to the exact restored public freeze. Every seed is SHA256 of the entire new ASCII case identity and all 205 seed hashes are disjoint from the original bank. No prior partial noise fragment or unavailable outcome was used to tune the new design.

The prior full 90,000 CPU-s envelope remains an irreconcilable historical reservation/debit, in addition to earlier ledgers. It is neither refunded nor treated as available capacity. A separately declared new 260,000 CPU-s envelope, including its own 1,000-s preparation/delivery reservation, follows the standing full-power free-compute authority. Together these two envelopes total 350,000 CPU-s in limits/reservations, which is not measured consumption; cost remains 0 DKK and new telescope bytes/requests/visits remain zero. `RECOVERY_DECLARATION.json` preserves all 20 exact recovered-file pins and the public freeze/admission references.

Inherited deterministic component-test receipts are historical evidence for the byte-identical detector and QA, not newly executed tests. The new input review is a metadata and source-diff audit; independent execution QA remains required for every fresh case. At this preparation stage no GO exists and no new random draw or search has been made.

Before public freeze, the engineering concurrency limit was revised from four to eight workers following the observed eight-CPU cgroup allocation. Each child retains its 1GiB address-space, 600 CPU-s and 1,800 wall-s caps; the sum of eight address-space ceilings is 8GiB, which is not an RSS estimate. At that concurrency revision the aggregate envelope was 90,000 CPU-s; the final budget revision below supersedes it. All scientific definitions remain unchanged. The coordinator source remains byte-identical with default four workers; execution explicitly supplies `--workers 8`. The unpublished preparation SCOPE SHA256 `430d41107220c149d0440bf0457b407b2d115982ef53fc84189deff00fe0b3c0` is superseded by this metadata revision. No GO, public freeze or scientific execution preceded the revision.

The final engineering budget is **260,000 CPU-s**. The unchanged fixed plan has 428 children: 205 primary, 205 independent QA, nine exposed and nine exposed QA. Their 600 CPU-s caps sum to 256,800 CPU-s; adding the 1,000-s preparation/delivery reservation gives 257,800 CPU-s, leaving 2,200 CPU-s headroom. The earlier unpublished 90,000-s recovery envelope could stop this panel solely through reservation accounting. The unpublished SCOPE SHA256 `758c8220fe638470673f623931882a2049943aad910ee8f178a808fbbf6a2b6f` is therefore superseded before public freeze, GO, random draws or outcomes. This changes an engineering limit only; the original 90,000-s historical debit remains preserved and no measured CPU consumption is inferred from either envelope. Per-child caps, eight-worker concurrency, code, identities, signal strengths, thresholds and gates are unchanged.

The specification below is carried forward from the original study. Its references to fresh identities and new resources apply to this separately admitted replication; historical result claims do not carry forward.

# Carried-forward complete declared-band six-scan method

This is a separately frozen method study, designed after the completed raw648 and matched216 studies. It uses 205 fresh prescribed synthetic identities: 63 calibration references followed by a 142-case joint signal/RFI/null/diagnostic panel. It does not reopen original validation A/B or admit the original sky pilot.

All six actual header epochs from the exposed 28 April 2017 cadence are preserved, including scan gaps. Each ON scan searches all 4,096 native reference carriers at the one common cadence midpoint, 5,723 drifts over ±4 Hz/s, seven four-row windows and widths 1/3/9/33. One combined top five is retained **per carrier**. Native4 aliases are compressed for scoring but every attainable global parameter alias survives into the OFF test. The OFF reference family has 6,652 carriers, including a 1,278-channel halo on each side.

The OFF test uses the retained four-row ON window's two midpoint endpoints. It queries an exhaustive inventory of every OFF native4 identity with score ≥8, across all seven windows and all widths, with every discrete drift alias. It never uses only the OFF top five to prove absence of a veto. Any compatible ON-alias/OFF-alias pair provides a witness. The separately declared binary64 predicate is computed in native-channel units. Width/window/minimum donor-index ordering resolves exact score ties.

Raw ON threshold10 and OFF threshold8 remain empirical robust-score cutoffs. Final survivors additionally require `(1 + count63(reference global ON maximum >= candidate score))/64 <= 1/64`. The references use the complete pre-OFF ON maximum. This rank calibration concerns only the declared independent Gamma16 law. It does not calibrate telescope RFI or sky significance. Empty final lists remain valid measured outcomes; failed or unsubmitted jobs are not empty lists.

The new operating/strong levels16/32 are nominal noiseless projection levels, not measured SNR or the original operating level12. The signal is an intrinsic one- or three-channel uniform line convolved with its exposure-duration drift sweep, in float64 before one float32 raw-power cast. Its oracle and amplitude are calculated before RNG. Placements, widths, drift signs and nuisance offsets have declared blocking/confounding, and burst-window counts are unequal. This panel cannot estimate independent causal factor effects or a physical sensitivity curve.

All programming and numerical inputs are pinned in `SCOPE.json`. `GO.json` is written only after exact immutable GitHub readback. Each primary identity has one exclusive claim and one draw. Independent QA may reconstruct that same recipe for verification; it is not another trial or a replacement draw. No retry or outcome tuning is permitted.

Execution order, from this directory after a valid GO:

```bash
python coordinator.py --phase primary_calibration --workers 8
python summarize.py --root . --calibration-only
python coordinator.py --phase primary_validation --workers 8
python coordinator.py --phase qa --workers 8
python summarize.py --root .
```

The coordinator records complete `wait4` CPU/wall/RSS evidence and all failed or unsubmitted indices. Up to eight concurrent workers each have a 1GiB address-space cap; every child has 600 CPU-s and 1,800 wall-s limits. A separate 260,000 CPU-s stage envelope includes an unreleased 1,000-s preparation/delivery allowance. Historical period debits and reservations remain preserved; the earlier assistant-defined 12-hour ceiling was explicitly superseded by the user's continuing full-power instruction. No paid resources or new telescope requests are authorized here.

After all 205 cases and independent QA close with an integrity PASS, nine already exposed, postselected authentic six-scan bands may be described:

```bash
python coordinator.py --phase exposed --workers 8
python coordinator.py --phase qa_exposed --workers 8
python summarize.py --root . --exposed
```

These nine bands are a re-search of retained data from the same historical visit. They are not fresh observations, independent confirmation or new telescope frequency coverage. Any Gamma16 p on these real backgrounds is only a model diagnostic. A scientific control failure cannot be hidden by rank rejection or changed to a missing-data zero.

The retained artifact recipes, seeds, float32 inputs, maps, aliases, exhaustive OFF inventories, raw hits, witnesses, QA and logs support reproduction of these fixed draws. Fresh execution must use a separate copy and admission; existing once-only claims are intentionally retained and block accidental repetition. Reproduction is not another validation trial. Original A/B remains **FAIL_CLOSED**, 2016 remains protected, 2019 remains closed, and the formal checkpoint remains 20 October 2026.
