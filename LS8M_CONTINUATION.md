# Continue after LS8M

LS8M is complete at result commit
`f881bbf61b8bdfcaf94cc44eaa2bdba4baf2c2c8`, following prospective method freeze
`f56c1b8e842396a4d7d5c6715e9a1a9869701326`. Its scientific status is
**COMPLETE_AUDITED_DESCRIPTIVE_ONLY**. This ends the bounded WASP-189
retained-data follow-up; it does not resolve a unique physical cause.

## What the integrated study established

For the smaller positive TG000201_P0, the residual left by the combined
brightness/displacement model is **spatially concentrated and comparable in
total weighted energy to local sideband variability**. It does not require a
new stellar-signal interpretation on the evidence of this diagnostic.

- In COR, the combined fit explains 28.280–28.428% of weighted event-map
  energy. The remaining weighted energy is **1.10127–1.10616 times** the
  sideband-derived reference in C0/C1. **8/24 and 7/24** held-sideband controls,
  respectively, are at least as large. These are overlapping descriptive
  controls, not false-alarm probabilities.
- The ten most energetic residual pixels contain **48.393–48.514%** of its
  weighted residual energy. The largest pixel, native **(x=105,y=106)** in
  both center conventions, accounts for **18.805–18.891%**. This identifies a
  compact feature that the smooth brightness/gradient model does not capture;
  it does not establish that the pixel is defective or identify its cause.
- Unweighted residual energy is only **0.58736–0.58761 times** its unweighted
  sideband reference. The raw and weighted comparisons answer different
  questions. The original LS8L combined unweighted fit of about 54.2% is
  retained and is not replaced by a differently weighted percentage.
- Sideband whole-aperture flux variability is **34,141–41,408 ADU**, while a
  diagonal-only calculation gives about **368,290 ADU**. The strong cancellation
  between pixels matters. Pixel-wise standardization cannot be interpreted as
  an independent-pixel source significance.
- Under the same COR projector, CAL residual energy is 1.87875–1.92267 times
  COR in weighted coordinates; the DELTA term is 0.83840–0.88149 and the cross
  term is -1.71714 to -1.80416. Delivered correction therefore reduces this
  weighted residual through cancellation. The corresponding raw DELTA/COR
  residual-energy term is only 0.00485–0.00505. None of these energy budgets is
  the historical signed aperture-flux correction gate or a unique cause label.

The full native excursion is **not proved to be ordinary noise** by this
residual study. For example, its fitted combined brightness coefficient is
positive (0.00244–0.00251) with empirical sideband coefficient variability
0.00059–0.00060. Those values are not Gaussian significances: the event was
selected earlier, pixel variability is correlated, and only 24 local side
images support the reference. The unresolved historical classification stays.

## Signed comparison cases and protection tests

| Representative | COR weighted residual / sideband reference, C0–C1 | Held-side controls >= event | Unchanged LS8L label |
|---|---:|---:|---|
| TG000201_P0 | 1.10127–1.10616 | 8/24; 7/24 | UNRESOLVED_WITHIN_FIXED_SCOPE |
| TG000202_P0 | 1.80071–1.89187 | 1/24; 1/24 | SPATIALLY_STRUCTURED |
| TG000202_N0 | 10.86307–10.88848 | 0/24; 0/24 | CORRECTION_LINKED |

The negative control retains a substantial structured residual. Its historical
correction-linked label concerns signed aperture flux, so it does not imply
that all residual image energy is removed by the delivered correction.

Eight pre-analysis tests pass. All **72 signed known-template cases**, **120
signed compact cases**, and **192 additive linearity checks** pass the frozen
numerical audit. A hypothetical displacement-plus-constant subtraction would
retain only **80.729–81.305% of weighted energy and 91.750–92.117% of signed
flux** for the smaller event's injected COR brightness pulse. That measurable
signal loss is retained explicitly; no subtraction, veto or new classifier
is adopted.

The independent audit passes **790,128 numerical comparisons and 911,228
exact checks**, with zero disagreements. It reconstructs all 12 native
product/convention cases, 288 leave-one-sideband cases, signed injections,
spatial cells, concentration measures and paired correction budgets from the
retained bytes. The maximum discrepancy is 0.00202 of the frozen numerical
tolerance. All three published figures were visually reviewed.

No new native source bytes, pixels, visits or apertures were acquired. No
qualified candidate, detector or observing coverage is added. LS8L's original
80%/20%-advantage and 50%-correction rules remain unchanged.

## Next action: separately freeze independent GJ 1132 transfer

Move away from these closed WASP-189 contexts. Use **rank 2, GJ 1132**, from
the unchanged LS8J 107-cohort ledger and its complete-inventory reconciliation.
The two visits already selected by its chronological rule are:

| Exact file key | Archive start MJD | Metadata exposure / coadds |
|---|---:|---:|
| CH_PR100041_TG000401_V0300 | 58934.9948654389 | 60 s / 1 |
| CH_PR100041_TG000403_V0300 | 58943.1171305167 | 60 s / 1 |

1. Freeze a new metadata-first transfer protocol identifying those two exact
   visits, DEFAULT L2 product, retained census/reconciliation identities and
   failure/stop rules before retrieving new source ranges. Do not repeat the
   population census or choose a target using signal values.
2. Verify exact DEFAULT L2 headers and source identities. Freeze byte scope
   before opening light-curve values; if the schema or identities differ,
   preserve the failure and resolve it before any science-table acquisition.
3. Transfer the unchanged stable LS8K screen: both signs, durations 1/2/3,
   sidebands 12+12, guards 2, fixed +/-8.5 endpoints, status/cadence rules,
   overlapping/adjacent signed clustering and unchanged independent audit.
   LS8M supplies no new screening weights, veto, thresholds or selection cut.
4. Keep both visits and all outcomes. If there are signed representatives,
   establish their exposure joins and separately freeze one bounded CAL/COR
   image follow-up retaining every representative. If none, publish the null
   result and close the pair under the same stopping rule.

Do not acquire those GJ 1132 science values as an automatic continuation of
LS8M. The next study needs the separate freeze above, not fresh user permission
for already authorized routine research/publication. Do not widen WASP-189,
reclassify it with weighted gates, reopen old hosts or release reserved TESS
sectors/M43 held-out panels. The raw-imagette calibration gate remains
NOT_READY; its technical request is unsent and no reply is pending.

[Complete numerical report and figures](results_ls8m_residuals/REPORT.md) ·
[Protocol](LS8M_RESIDUAL_NOISE_PROTOCOL.md) ·
[Independent audit](results_ls8m_residuals/audit.json) ·
[Publication identities](PUBLICATION_2026-09-20_LS8M.md).
