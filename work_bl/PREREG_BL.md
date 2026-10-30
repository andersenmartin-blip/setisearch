# BL: fixed descriptive native170 search, 30 October 2026

Before any BL power decoding or scores, fix q1–q32 as four sequential batches
of eight carrier cores. Target HIP98505 / HD189733, historical six-scan visit
2017-04-28, native170 origin 178257920, first channel 2304.78515625 MHz.
No native171 replay or native172 search is authorized by this scope.

Each batch uses unchanged full-native AC normalization before cropping,
4096-channel cores and halo, widths 1/3/9/33, strides 1/1/2/8,
839 drift rates over ±4 Hz/s, local ESS threshold 10, three-ON requirement
and OFF neighborhood veto at 5. The executable plans contain exact six-scan
headers, input hashes, source hashes and runtime pins. Endpoint/DC cores
q0/q128/q255 remain outside carrier admission.

Expected scope: 192 scan/core searches and 1,732,018,176 correlated track
combinations; 131,072 carrier channels, 366,210.9375 Hz technical width.
These are correlated computational combinations, not independent trials.

After each closed search, run the separate finite saved-result audit:
1,728 selected independent math.fsum sums and 576 shared-kernel calibration
replays per batch. This does not independently qualify the codec, normalization
model, every search trajectory or astronomical detection sensitivity.

The campaign stops at any failure, changed hash, incomplete result, or passing
descriptive ON/OFF flag. No automatic retry, overwrite or background continuation.
The final stdout log is published atomically only after the child is reaped.
All actual exits, logs, artifacts, failures and partial results are retained.
Each search has a 600-second internal / 620-second external limit; audit 60 s.

Local ESS is not calibrated sigma, SNR or FAP. This is expanded-method
reanalysis of previously exposed historical data; some native170 bands were
searched under the older full-native ESS method. No fresh/blind-data claim,
new observation, unique archive ID or BA coverage credit is added.
Historical A/B, B06/native172/q81 failures and no-retry states remain unchanged.
Protected 2016/2019 data and HIP44295 remain outside this execution. 0 DKK,
0 new telescope-archive requests. Use the exact published commit as the
campaign preregistration argument and verify its source/plan bytes first.
