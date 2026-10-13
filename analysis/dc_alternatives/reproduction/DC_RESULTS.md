# Original-family DC alternatives: completed result

All nine previously selected signal templates are unchanged. Recovering the best admissible original hypothesis at every previously excluded carrier did not change any per-ON TOP3 selection. The previous 54 fixed context profiles can therefore be reused; this DC stage performs zero new context queries.

The target is HIP98505 / HD189733 during the already exposed 28 April 2017 visit. The family remains the original 785 drifts from −4 to +4 Hz/s, widths 1 and 3, and sixteen own-reference rows. A hypothesis is admissible when each sampled width box avoids all three fixed DC center bins. Original power and normalization remain unchanged.

| Completed item | Count |
|---|---:|
| Previously excluded reference carriers | 7,083 |
| Original hypotheses exhaustively replayed | 11,120,310 |
| Admissible hypothesis occurrences | 10,688,400 |
| Recovered nonempty carrier maxima | 7,074 |
| Explicit EMPTY carriers | 9 |
| Complete admissible carrier family | 9,412,599 |
| Preserved original raw scoring frames | 18 |
| Independent QA checks | 446,669 |
| Independent QA mismatches | 0 |

All 7,083 unrestricted original score/drift/width tuples were reconciled exactly. Each of the nine EMPTY carriers lies at a fixed DC center in row zero, so neither original width admits any drift. Complete original 16×12,096 float32 scoring crops, immutable normalization terms, whole-frame nearest501 filtering, original float64 prefix origin and sequential sixteen-row addition order were preserved.

The independent audit authenticated nine original HDF5 sources and 144 decoded rows, verified all eighteen saved crops against their original parent data, audited the full normalization cores, reproduced all alternative maxima and the merged TOP700/separatedTOP100/TOP3 lists. It passed in the relocated root `dc_alt_qa_work/analysis`; the original failed path-containment preflight log remains preserved. The frozen scientific code and scope were unchanged during relocation.

The nine retained templates are:

| ON scan | Rank | Reference frequency, MHz | Drift, Hz/s | Width, channels | Ranking score |
|---|---:|---:|---:|---:|---:|
| epoch1_on | 1 | 2303.864789754 | 1.48979591837 | 1 | 6.953941938 |
| epoch1_on | 2 | 2303.142451309 | -3.17346938776 | 3 | 6.899802267 |
| epoch1_on | 3 | 2296.187030710 | -2.75510204082 | 1 | 6.662058873 |
| epoch2_on | 1 | 2300.000000373 | -4.4408920985e-16 | 1 | 9.107593201 |
| epoch2_on | 2 | 2297.034745663 | -1.80612244898 | 3 | 6.714253862 |
| epoch2_on | 3 | 2296.405982785 | 0.826530612245 | 1 | 6.561431419 |
| epoch3_on | 1 | 2303.250876814 | -2.10204081633 | 1 | 6.693843670 |
| epoch3_on | 2 | 2298.732592352 | -3.04081632653 | 3 | 6.589656056 |
| epoch3_on | 3 | 2299.954408407 | -0.785714285714 | 1 | 6.541930287 |

The context reuse audit verifies all 31 existing fields of each selected template, all 864 transported centers and all 54 physical 4096-channel/full16 normalization domains. It authenticates 187 prior saved-output pins. Added score-authority fields identify the existing clean cached map maxima; none of the recovered alternatives enters the final nine.

The portable NumPy replay preserves the eighteen raw scoring crops, original row normalization files, relevant original maps, previously authenticated clean prefixes and new recovered arrays. It needs no whole HDF5 files, SciPy or h5py. Its source authentication is inherited from the pinned completed source QA; the portable replay itself cannot reauthenticate omitted whole HDF5 sources. The portable replay passed after exact public code/scope readback at commit `3ca79f78f9cd9dea0c6a0904b0a80b02cd0d818a`: 156,083 checks, zero mismatches, 34.66 CPU seconds, and zero HDF5 opens. Its scope, code, GO and all input hashes remained unchanged through completion.

These exposed ranking scores do not provide a calibrated SNR/FAP, independent observing visit, physical-source independence or a SETI detection. Avoiding the three DC centers does not exclude adjacent leakage or other interference. Original A/B FAIL_CLOSED, protected2016 and closed2019 decisions remain unchanged. No telescope request or additional payment was made.
