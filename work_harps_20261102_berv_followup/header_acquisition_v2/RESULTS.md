Both prospective header requests completed and passed the frozen identity, single-exposure, provenance, mode, and recorded-BERV checks. The endpoint returned FITS header cards inside HTML PRE. The successful version made **two requests and received 455,347 response bytes**; including the preserved serialization failure, the complete target-header history is **three requests and 457,986 bytes**. No spectra were downloaded by this header stage.

The unchanged selector proposed two HD122640 exposures, in the frozen minimum-then-maximum BERV order:

| Role | ADP identifier | Observation UTC | Recorded BERV (km/s) |
| --- | --- | --- | ---: |
| Minimum | ADP.2017-05-23T01:01:52.459 | 2017-05-22T05:20:05.415 | -11.0816664353436 |
| Maximum | ADP.2018-01-21T01:01:37.761 | 2018-01-20T08:50:34.270 | 29.2818122856138 |

The new and combined HD122640 BERV span is **40.3634787209574 km/s**, compared with the existing 14-exposure span of 2.2379098704629 km/s. The increase is 38.1255688504945 km/s. The combined span is 15.483378347396924 times the nominal c/R scale at R=115,000, exceeding the predeclared 2.6068909391304347 km/s readiness threshold. This is a descriptive planning displacement, not a detection significance, sensitivity estimate, or physical-origin classification.

HD135204 has no new header or payload proposal because the bounded metadata search produced no eligible candidate. Its existing 15-exposure span remains 1.714121120020998 km/s (0.6575346495288243 nominal resolution elements), below the same gate. This does not establish the absence of other archive epochs.

Both returned products have exact matching ADP and sole raw-progenitor identities, NCOMBINE=1, INSTRUME=HARPS, SPECSYS=BARYCENT, SPEC_RES=115000, HEFS ST=false, actual INS MODE=HARPS, and PROCSOFT/DRS version HARPS_3.8. Original card comments and response bytes are retained. These are 2017/2018 archival epochs, separated by years from the existing 2023 sample; instrument and reduction-history compatibility still needs to be considered. Spectral table units, air-wavelength convention, and payload-header consistency remain mandatory checks before any array access. The header parser intentionally used only the primary HDU.

`EXTREME_SELECTION.json` binds the two proposed products to the exact header-result indices, bodies, receipts, metadata, and plan. It remains a proposal pending a separate payload release. `OUTPUT_MANIFEST.json` hashes the outputs. Frozen code and both the original failed and successful plans remain unchanged. No additional month, target, header, or catalogue query was introduced. Cost remains 0 DKK, and this additional archival follow-up is kept outside the original 300-spectrum survey.
