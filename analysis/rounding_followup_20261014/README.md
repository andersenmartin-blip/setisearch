# Exact local native-bin path family — 14 October 2026

The completed four-row geometry now contains **all 19 test patterns missed by the previous 405-point drift/phase grid**. Strong conditional injections achieve full native-bin capture in **1,512/1,512** cases, previously **1,493/1,512**. Weak maximum-based capture falls from **1,067 to 1,036 of 1,512**, showing that geometric completeness does not make the noisy maximum a reliable sole retention rule. **No qualified SETI detection is established.**

## Completed scope

Nine previously selected HIP98505/HD189733 ON paths are followed through six original scans from **28 April 2017**, giving 54 profiles and **378** overlapping four-row window families. All scans belong to one exposed historical visit; the OFF scans point to other stars.

Each family retains the original selected-window midpoint anchor and integer reference channel. Its box is delta drift **±0.0253164556962 Hz/s**, reference phase **±0.5 native channel**, width one native bin, with the actual scan gaps. Native frequency spacing is 2.7939677238464355 Hz. Exact rational rounding-cell enumeration includes interiors, edges and vertices with nearest-integer ties-to-even. Completeness is restricted to this declared four-row linear quantizer model.

The completed census is **22,235 native paths counted within their zero-offset window families**, **200,115 saved scores** across nine offsets, and **800,460 saved row terms**. The eight controls use fixed offsets ±256/512/768/1024 channels and the original normalization cores. These paths, windows and controls are correlated; they are not independent trials or physical sources. Every previous 405-grid path remains present.

## Conditional injection result

The 3,024 trials add a one-native-bin delta to four active rows at amplitudes 2 or 8 in standardized residual units. They reuse exposed backgrounds and fixed normalization, bypassing raw preprocessing. They do not measure physical sensitivity, an instrumental line response or a fresh recovery probability.

| Outcome | Previous grid | Exact family |
|---|---:|---:|
| Signal-only truth geometry represented, each amplitude | 1,493/1,512 | 1,512/1,512 |
| Amplitude 8 noisy maximum captures all four active bins | 1,493/1,512 | 1,512/1,512 |
| Amplitude 2 noisy maximum captures all four active bins | 1,067/1,512 | 1,036/1,512 |

The weak transition consists of **43 losses and 12 gains**, net −31. In the losses, a new partially matching path has a higher noisy score; the smallest measured score advantage is **0.0101296**. The complete truth path remains available. All scored paths are retained rather than treating the selected maximum as evidence that the full path is absent.

## Observations and verification

The nine selected ON-origin maxima remain unchanged at **6.638491–7.450295**. Other-ON maxima range **2.444902–4.543590** and OFF maxima **2.010474–3.828783**. The expanded family increases one of 18 other-ON maxima and four of 27 OFF maxima. These are postselection descriptive scores, without calibrated SNR/FAP, qualified OFF rejection or independent observing-visit replication.

All nine selected ON-origin winners have genuine two-dimensional feasible regions. Among 54 zero-offset maxima, one OFF winner (`epoch3_on_rank1_epoch2_off`) is feasible only at a parameter point; the other 53 have two-dimensional regions.

Independent QA passes using native-channel candidate enumeration and separate exact phase feasibility rather than importing the producer. It checks **110,136 candidate tuples**, all 54 full normalization cores, all 200,115 scores and all 3,024 injection outcomes. Maximum checked numerical error is **5.33×10⁻¹⁵**. Geometry, producer and QA used **8.58 / 26.12 / 44.99 measured process-CPU seconds** respectively; those components are not a complete session total.

The final four-page Danish PDF and **14 waterfalls** were visually reviewed. Final waterfall assets are in `waterfalls_v2/`; the preserved first version needed legend/caption spacing correction. Scientific arrays and scoring were unchanged by that presentation correction.

## Continue from preserved scores

Next, diagnose weak full-truth-path ranks, score gaps and the partial winners that displace them. Specify any multi-candidate retention rule before fresh validation. The current exposed outcomes may diagnose a loss mechanism but cannot qualify a newly tuned policy. Morphology review must preserve existing scores and detection claims.

Original **A/B remains FAIL_CLOSED**. Protected 2016 and closed 2019 states are unchanged. **0 DKK, no new telescope requests or observations; formal checkpoint 20 October 2026.**

## Evidence and reproduction

- [Scientific summary](SUMMARY.json) and [Danish repository report](RADIO_EXACT_ROUNDING_2026-10-14.md).
- [19 missing-cell diagnosis](geometry_results/DIAGNOSIS19.json) and [exact geometry receipt](exact_geometry_results/GEOMETRY_RECEIPT.json).
- [Producer receipt](results/EXECUTION_RECEIPT.json), [independent QA summary](qa_results/QA_RECEIPT_SUMMARY.json), [486 compact score summaries](results/SCORES_COMPACT.csv), [3,024 compact injection records](results/INJECTIONS_COMPACT.csv), [full source hashes](PUBLIC_EVIDENCE.json).
- [Final waterfall manifest](waterfalls_v2/PLOT_MANIFEST.json), `SETI_native_spor_2026-10-14.pdf` in the complete ZIP, [layout-only correction receipt](LAYOUT_CORRECTION_RECEIPT.json).
- [Reproduction instructions](REPRODUCE.txt). The supplied `replay.py` wrapper is syntax-checked but has not itself been run across all 54 profiles for this delivery. Actual completed producer and independent QA runs are documented by their receipts and logs. Replay requires the complete archive's pinned source crops and prior-grid evidence, Python 3.12 and NumPy; this repository stage alone is not a standalone array package.

The complete ZIP contains the full QA receipt, full JSON results, all score arrays, source raw crops and original normalizations. Compact public tables and the QA summary retain source hashes and key outcomes; they do not replace those complete reproduction inputs.
