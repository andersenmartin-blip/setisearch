# Completed full ON burst search

All source, independent global-ranking and original-HDF5 context QA stages passed. No qualified SETI detection or calibrated false-alarm probability is established.

The three HIP98505 / HD189733 ON scans belong to one already exposed 2017-04-28 visit. The completed search contains 2,010 new maps plus 288 unchanged pilot maps, 9,412,608 carrier references and 20,952,465,408 correlated hypothesis occurrences. Both unrestricted and best per-hypothesis DC-clean winners were preserved.

| ON scan | Rank | Reference MHz | Drift Hz/s | Start row | Width | Ranking score | Own DC rows selected4/full16 |
|---|---:|---:|---:|---:|---:|---:|---:|
| epoch1_on | 1 | 2301.220240630 | -3.89873417722 | 12 | 1 | 6.812761874 | 0/0 |
| epoch1_on | 2 | 2296.995887160 | -1.9746835443 | 0 | 1 | 6.744084984 | 0/0 |
| epoch1_on | 3 | 2299.208432995 | -0.506329113924 | 0 | 1 | 6.638491350 | 0/0 |
| epoch2_on | 1 | 2298.367074318 | -2.83544303797 | 4 | 1 | 6.996867084 | 0/0 |
| epoch2_on | 2 | 2303.274832293 | 3.69620253165 | 12 | 1 | 6.961946174 | 0/0 |
| epoch2_on | 3 | 2301.897235774 | -0.962025316456 | 8 | 1 | 6.916444045 | 0/0 |
| epoch3_on | 1 | 2297.995686159 | 1.9746835443 | 0 | 1 | 7.450294835 | 0/0 |
| epoch3_on | 2 | 2297.842375562 | 1.67088607595 | 8 | 1 | 7.031163159 | 0/0 |
| epoch3_on | 3 | 2298.779955693 | -0.658227848101 | 12 | 1 | 6.749950807 | 0/0 |

2 of the nine selections exactly match an authenticated previous pilot TOP3 scientific tuple. The 54 fixed profiles comprise 9 origin ON, 18 other ON and 27 OFF contexts. Selected4/full16 DC diagnostics preserve all scores and are not a qualified OFF veto.

A faulty synthetic v1 boundary fixture was corrected before observational QA execution. V2 isolated the spike in row0 and passed all ten cases; production scoring code was unchanged.

The fixed159 drift grid, widths1/3, overlapping4-row windows, bounded frequency support and time gaps limit coverage. Ranking after maximization is subject to selection bias. Reference-frequency spacing does not establish independent physical sources. Protected2016 and closed2019 states remain unchanged; original A/B remains FAIL_CLOSED. No new telescope request or additional cost occurred.

Full-precision tuples, quantitative context diagnostics, provenance pins and actual QA bindings are in FINAL_SCIENCE_REVIEW.json and SELECTED_CLEAN_TOP9.csv. A final PDF is created separately only after the completed archive and fresh saved-data replay pass.
