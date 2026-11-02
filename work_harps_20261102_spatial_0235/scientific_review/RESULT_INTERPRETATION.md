V2E2-0235 has a larger, more concentrated mismatch to the fixed local trace model than the eight held-out controls. The mismatch is predominantly **near the trace**, within the declared ±3-pixel band. It does not establish a remote off-trace deposit or resolve the photon/charge ambiguity. Retain **U**.

The released run completed all 232 training rows and 27 template/window slots using exactly 8,275 native pixels. No controls or templates were replaced.

| Pooled-template diagnostic | Target | Eight controls |
|---|---:|---:|
| Residual L1, ADU | 8,633.12 | 2,249.83–4,024.91 |
| Largest pixel / residual L1 | 6.52% | 2.08–2.72% |
| Residual L1 outside ±3 pixels | 15.70% | 29.09–38.81% |
| Mean absolute residual inside ±3 pixels, ADU/pixel | 110.27 | 20.86–42.85 |
| Mean absolute residual outside ±3 pixels, ADU/pixel | 12.32 | 7.41–11.25 |

The target result persists under both separately trained flank templates: residual L1 is 8,445–8,903 ADU and the off-band share is 15.55–15.99%. The pooled positive residual maximum is +562.98 ADU at relative raw row −3 and cross-dispersion offset −0.799 pixel; the negative minimum is −319.08 ADU at row −1 and +1.220 pixels. Their locations and amplitudes change little across the three templates. This alternating, localized residual pattern supports model inadequacy around the trace; it is not a clean trace-template match.

The background estimator has a systematic side asymmetry. The median rowwise positive-minus-negative outer-band difference is 24 ADU at the target and 22–37 ADU across controls. It is therefore not peculiar to the target. The nearest fiber-B calibration trace is +16.354 pixels from fiber A; its wings remain a possible contribution to the positive background band. These data do not identify the cause of the asymmetry.

The target is also brighter: its summed fitted amplitude is 50,361 ADU, compared with 33,339–46,533 ADU for controls. Residual magnitude divided by that amplitude is 0.171 for the target versus 0.060–0.091 for controls, but this is only a descriptive scaling, not a photon fraction or calibrated noise statistic. Every control shares the same exposure and order. No gain/read-noise/covariance calibration or independent replication converts the empirical ordering into a probability.

Trace-aligned contamination can be absorbed into the free amplitude, while profile variation, interpolation and background errors can leave compact residuals. A photon/charge mixture remains possible. The May-quality comparison's lack of a comparable 0235 central spike is additional temporal context, not an origin label. The original extraction, earlier results and U adjudication remain unchanged.

Sources: released `analysis/results/SUMMARY.json`, `WINDOW_METRICS.json`, `ROW_METRICS.csv`, `EMPIRICAL_CONTEXT.json` and `SPATIAL_ARRAYS.npz`. Method commit: `8193e79cefabc32ec4a08230b2f77468905a5eee`; analysis SHA: `17e1f666896fc504105689675611261bbe376ddb325e342ae21101cf33b1d12b`. This reading opened saved outputs only and made no requests.
