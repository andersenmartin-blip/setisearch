# CHEOPS calibration clarification — prepared, unsent

15 September 2026. Operational follow-up to LS7V; no new experiment or
scientific milestone. This is a complete message draft. No email, contact
form submission or mailbox draft has been created.

**To:** Dr Andrea Fortier <andrea.fortier@unibe.ch>  
**Subject:** CHEOPS OBSID 1015522: DRP 14.0.1 calibration and reference inputs

Dear Dr Fortier,

I am developing an independent method for short optical transients in the
public SETIsearch project. Before extracting target flux from CHEOPS visit
`CH_PR300024_TG000301_V0300` (55 Cnc, OBSID 1015522, 9 March 2020), I would
like to resolve three calibration questions. The retained products were
reprocessed on 15 March 2023 with overall DRP 14.1.2; the calibration log
identifies `main_calibration.py 14.0.1`.

Could you point me to the relevant documentation or SOC/DRP specialist?

1. **Gain and output units.** For GainCorrection V0109, which housekeeping
   quantity and temperature-offset sign apply in this reduction? The reference
   has `TEMP_OFF=-40` degrees C. The public CHEOPSim implementation subtracts
   that signed offset; the common_sw gain schema describes addition. A pinned
   PIPE reader also uses `VOLT_FEE_CCD` in its temperature term, whereas the
   visit contains a distinct `TEMP_FEE_CCD` field. We have not selected a
   convention from these comparisons. Also, what are the numerical units of
   the delivered CAL/COR image pixels? Their `BUNIT` cards say `ADU`, while
   the log reports a gain correction in electrons/ADU.

2. **Stacking and offline nonlinearity.** What exact operator does `gcoadd`
   represent for these raw imagettes (`NEXP=2`), and how does it differ from
   the raw subarray's `coadd` (`NEXP=14`)? Both have `ROUNDING=0` and
   `NLIN_COR=false`. We need the sum/mean/weighting and any clipping or
   rounding convention, plus the order and normalization of bias, gain and
   offline LUT100 correction for stacked exposures. The individual-exposure
   records are metadata, so we cannot assume individual image samples are
   recoverable. The recorded subarray readout is bright mode, 230 kHz, main
   channel, script 6.

3. **Exact reference contents and applicability.** Is there supported public
   delivery for the four files below, with their original validity headers
   and selection/interpolation rules? The dark correction was applied in
   MAP mode. The archive lists 17 March 2020 as the dark/bad-map “Obs Start”,
   after this 9 March observation; we do not know whether that archive column
   represents the applicable validity interval. We need the actual
   `V_STRT_U`/`V_STOP_U` values and the rule used by this reduction.

| Required input | Exact file named by the retained evidence |
|---|---|
| Offline nonlinearity | `CH_TU2018-01-01T00-00-00_REF_APP_CCDLinearisationLUT100_V0104.fits` |
| Point-source flat | `CH_TU2020-01-29T00-00-00_REF_APP_FlatFieldTeff-PointSource_V0104.fits` |
| Applied dark map | `CH_TU2020-03-17T12-29-01_REF_APP_DarkFrame_V0201.fits` |
| Bad-pixel map | `CH_TU2020-03-17T12-29-01_REF_APP_BadPixelMap_V0201.fits` |

The flat is listed as 1168.0200 archive MB. If an official subset is available,
our literal subarray header cards are `T_EFF=5196`, `X_WINOFF=715`,
`Y_WINOFF=181`, `NAXIS1=NAXIS2=200`. The relevant temperature planes/region,
documented coordinate convention and interpolation rule, with original-file
provenance, could avoid transferring the full cube. We have not assumed the
offsets' index base. WhitePSF V0106 would be an additional input if the final
method uses that reference; its exact filename is in the linked manifest.

We already have verified GainCorrection V0109 contents. The original log also
resolves the default bias and noise as 563.43 and 7.13 ADU/frame and says the
spatial bias-frame correction was skipped; those are not outstanding questions.

The [gain evidence](https://github.com/andersenmartin-blip/setisearch/blob/cacdbe22bd238b7b98afb4dc13709874d9a2fd77/LS7T_CALIBRATION_CONTRACT.md)
links the exact public source revisions. The
[log reconciliation](https://github.com/andersenmartin-blip/setisearch/blob/cacdbe22bd238b7b98afb4dc13709874d9a2fd77/LS7V_CALIBRATION_RECONCILIATION.md)
and [input manifest](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/CHEOPS_REQUIRED_INPUTS.json)
provide the remaining provenance. This request concerns calibration before
target-image analysis; we have no candidate or instrument-fault claim.

Thank you for any documentation or routing you can provide.

Best regards,  
Martin Andersen  
[SETIsearch](https://github.com/andersenmartin-blip/setisearch)

---

## Contact resolution and delivery state

The official [CHEOPS contact page](https://cheops.space.unibe.ch/about-us/contact),
checked on 15 September 2026, directs technical questions to the project
manager and lists Dr Andrea Fortier with the address above. Its separate
mission-PI and general-office contacts are not additional recipients. No
institutional affiliation has been inferred for the sender.

The standing project authorization covers public GitHub files and README
updates. It does not authorize person-directed contact. This draft is
**unsent**; no response has been requested or is pending. The owner can send
this text through their chosen channel. Before an assistant sends it, obtain
explicit authorization and use an available supported communication tool.

The two additional repository leads checked in this follow-up, `CHEOPS DRT`
and `CHEOPS IASW`, returned no repositories. This bounded search does not
establish that no documentation exists. It did not resolve an operator or
deliver a reference. Reuse LS7V as the scientific state; proceed when relevant
mission documentation or the exact input package becomes available.
