# BW: prospective q254 completion

BW searches exactly one carrier core, q254, in the five already complete HIP44295 cadence scans (archive IDs 65133, 65135, 65137, 65139, 65141). The missing sixth OFF scan remains unavailable. No new observation or archive transfer is claimed.

## Why this core

The original BN validator explicitly admitted q254. Its count of 253 cores excluded q128, not q254. BV froze q33–253 and preserved that scope, including q128. The earlier description of BV as covering every safe core was overbroad. The metadata-only boundary review found that q254 has complete 4096-channel halos: carrier interval [1040384, 1044480), support [1036288, 1048576). The conservative projected-track bound is 2218 channels. q0 and q255 do not have complete halos and remain excluded.

This extension was selected from geometry before q254 detector scoring. Full-native normalization had already touched these powers in BU/BV; q254 is not a holdout. Historical plans, scores and failures remain unchanged.

## Fixed analysis

One serial batch, q254, five scans, sixteen time rows per scan; the exact BN numerical functions, AC normalization, 839 drift values from −4 to +4 Hz/s, widths 1/3/9/33 and strides 1/1/2/8 are retained. Local median/MAD ESS threshold is 10, available-OFF flag threshold 5. Association uses the same q-local calibration, including projected positions in the halo. Missing OFF5 is NaN/invalid, never zero.

The scope contains 45,104,640 correlated track combinations (27,062,784 ON), spanning 0.011444091796875 MHz of carrier bins. Those are neither independent trials nor calibrated astronomical sensitivity. If completed, BU+BV+BW covers q1–254, or 2.90679931640625 MHz, in these five scans.

## Execution and acceptance

Publish and read back the frozen plan/source/review before scoring. Use exclusive tmpfs output, validate every member of the closed result ZIP before and after export, require unchanged source/input identities, actual child exit zero and natural stdout EOF. Production has a 180-second wall/CPU cap, independent audit 120 seconds, overall bound 300 seconds. There is one attempt; any failure stops and is retained.

The independent audit checks saved classifications, selected scalar tracks/calibration vectors and normalization. A separate closure review validates archive membership and all stored maxima/catalog rows. These checks do not constitute a second complete detector run. Source and scope regression checks must pass before execution.

## Interpretation and next data

Full-cadence assessment remains `NOT_EVALUABLE_MISSING_OFF5`. No original BA coverage credit, queue advancement, calibrated false-alarm probability or sensitivity follows from BW. The original authority remains 486 unique archive IDs and 268.50128173828125 technical MHz-visits, with zero qualified astronomical sensitivity.

`recovery/RESUME_SPEC_BW.json` records the exact remaining OFF5 rows 8–15, row7 repeat, retained package identities and original BE proof gates. Archive access is currently unavailable under the environment's host restrictions; no workaround is authorized or attempted. The metadata-only alternative-source scout found no complete eligible new ON/OFF cadence. Next queued fresh targets remain HIP58684/65193 and HIP59280/65205.
