# Arkitektur- og mappeoversigt for `setisearch`

Dette dokument forklarer opbygningen af repositoriet på tværs af dets fire historiske og aktive forskningsspor, så både forskere og reproducerbarheds-tjek hurtigt kan orientere sig.

---

## 1. Overblik over mapper og filer på `main`

| Sti / mønster | Spor | Rolle og status |
| --- | --- | --- |
| [`README.md`](../README.md) | Alle | Kortfattet hovedindgang, aktuel status på tværs af alle spor og reproduktionsvejledning. |
| [`CONTINUE_SETI.md`](../CONTINUE_SETI.md) | `V6.8` Optical/NIR Spectropolarimetry (`D110`) | Autoritativ teknisk overdragelse, faglige guardrails og videre `D111+`-perspektiver (Spor 3–5) efter afslutningen af `D079–D110` (`1.012` analyserede systemer / `267` `< 10 pc` [`61/61` host drift closure] / `179` science-broer [`2.635` celler] / `67` spektrografer [`97` arme, inkl. `TBL_NARVAL`] / `60,845` EM-oktaver + `0,1 TeV–10 PeV` $\nu_\mu$ + `2–8 keV` *IXPE* pol. + opt./NIR pol. / `23/23` lukning). |
| [`paper/`](../paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf) | All-Sky & Rum Pankromatisk + Penta-Regime + Polarimetri (`D079–D110`) | Færdigkompileret to-spaltet `97`-siders publikations-PDF (`ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf`, `65.185.477` B, SHA-256 `6a932c888943112ba266f60bd8f8e54233494519d04183ba0255a4c647e7d3fd`), Markdown-manuskript (`ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.md`), LaTeX-kilde (`main.tex`) og publikationsfigurer (`paper/figures/`, inkl. `fig151–fig156`). |
| [`docs/OPTICAL_V3_SURVEY_INDEX.md`](OPTICAL_V3_SURVEY_INDEX.md) | All-Sky & Rum Pankromatisk + Penta-Regime + Polarimetri (`D079–D110`) | Indeks over det prospektivt kalibrerede `V3.0–V6.8` + `POL_V68` + `DRIFT_V67`-survey (`1.012` unikke systemer, `4.150` eksponeringer på `67` spektrografer/arrays / `97` arme over `4,132807e-15–8.556,41831 µm` + `0,1 TeV–10 PeV` IceCube + `2–8 keV` *IXPE* + opt./NIR pol.). |
| [`docs/OPTICAL_HD43629_INDEX.md`](OPTICAL_HD43629_INDEX.md) | Optisk (`D001`–`D078`) | Samlet indeks over `D001`/`D002` og alle danske delrapporter gennem den afsluttede `HD 43629`-syntese (`D078`). |
| [`docs/history/`](history/README_LOG_ARCHIVE_THROUGH_2026-11-14.md) | Historisk arkiv | Ubeskåret arkiv af tidligere omvendt-kronologisk `README.md`, `CONTINUE_SETI.md` samt gren-oprydningskvittering. |
| [`progress/`](../progress/2026-11-26-v6-8-optical-nir-spectropolarimetry-d110/RESULTS_REPORT.md) | `V6.8` & Alle Pankromatiske Faser (`D075–D110`) | Maskinlæsbare offentlige leverancer (`METHOD_LOCK.json`, `IMPLEMENTATION_LOCK.json`, `RESULTS_MANIFEST_SHA256.json`, `SUMMARY.json`, `SOURCES.json`, `VISUAL_REVIEW.json`, CSV-tabeller og `RESULTS_REPORT.md` / [`D110_RESULTS_REPORT.md`](reports_d035_d077/D110_RESULTS_REPORT.md)) fra `D075` til `D110`. |
| [`work_seti_20261105_d001_delivery/`](../work_seti_20261105_d001_delivery/README.md) | Optisk (`HARPS`) | Konsolideret audit af de 300 oprindelige HARPS-eksponeringer (20 stjerner) + udvælgelse af 54 friske eksponeringer (`D001`). |
| `work_harps_20261101_*` .. [`work_harps_20261105_c037_context/`](../work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md) | Optisk (`HARPS`) | Forseglede kontekst- og BERV/topocentriske analyser (`C001`–`C037`) for den lukkede `90`-rækkers kø (`6.320` filer). |
| `work_rubin_20261102/` | Optisk fotometri | Lukket Rubin/Fink-feasibility-forstudie (`STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET`). |
| `src/seti_repeater/`, `tests/`, `scripts/`, `config/` | Radio (`M5`–`M41`) | Python/C-pakke (`seti-repeater`) til multi-epoke smalbånds-de-Doppler-søgning; testes automatisk af [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). |
| `results_m10/` .. `results_m36/`, `DATA_MANIFEST_M*.sha256`, `RESULTS_MANIFEST_M*.sha256`, `validation_m*.json` | Radio (`M10`–`M41`) | **Forseglede rod-artefakter.** Kontrolleres direkte af CI-testsuiten og må efter [`CONTRIBUTING.md`](../CONTRIBUTING.md) ikke flyttes eller omskrives. |

---

## 2. Historiske specialgrene (bevaret urørt)

Under oprydningen den 14. november 2026 blev **16 fuldt indmergede midlertidige arbejdsgrene** (dokumenteret i [`MERGED_BRANCH_CLEANUP_2026-11-14.json`](history/MERGED_BRANCH_CLEANUP_2026-11-14.json)) fjernet fra remote-listen, mens samtlige ikke-mergede forskningsgrene (`m43-support-qualification`, `ls1`..`ls6`, `radio-bp-paired-controls-20261031`, `codex/seti-d002-fresh-20261105`) bevares urørt.

---

## 3. Kompakte numeriske kompagnonarkiver A–Z, AA–AJ (Optical/NIR Spectropolarimetry, `16 Cyg B` Penta-Regime & `1.012`-Star Synthesis, `V6.8`)

Større mellemliggende arrays, `bounded_inputs`-bundter og figurfiler for `D069`–`D110` opbevares i kompakte, SHA-256-låste kompagnonarkiver (verificeres med `restore_d110_workspace.py --destination /tmp/d110_verify` og `--recompute`):

| Kode | Arkiv | Størrelse (bytes) | SHA-256 |
| :---: | --- | ---: | --- |
| **A** | `SETI_D069_D074_FEROS_VELOCITY_CONTEXT_RESULTS_2026-11-13.zip` | `45.920.303` | `b9bd142de7bdbf98b88d87dd5889cee3b1f1b43d93c17c4e711e6ed8a2e11820` |
| ↳ | indlejret `SETI_D069_D071_FEROS_EXTRACTION_AND_ORDERS_RESULTS_2026-11-13.zip` | `35.469.693` | `4bdc74a115f087fcbc04b88d2be35b4bbefa1df1c52d5258b6a88f0d388f024e` |
| **B** | `SETI_D075_D076_FEROS_ORDERS_AND_DIRECTION_RESULTS_2026-11-13.zip` | `28.329.072` | `2b7c5b48ee2f3b62ec7c3b6b65c150af4fed80b1930355d4d6b212b0d262fa31` |
| **C** | `SETI_D077_FEROS_WLC_METADATA_GATE_RESULTS_2026-11-14.zip` | `659.654` | `828466e2c8ede7897be98d38d247fb18def0e5acdb40754656c8d2517c27c818` |
| **D** | `SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_RESULTS_2026-11-14.zip` | `11.427.944` | `83132e0a43903a26ba6808b8bcca34f39850088d0aee05f0bdfb93b5d5ea6069` |
| **E** | `SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_RESULTS_2026-11-14.zip` | `5.770.342` | `ae7ec48fc51522c823c06940c60b661725430f632ba6f048402d9cf66ce07af3` |
| **F** | `SETI_D080_V3_1_EXOPLANET_AND_HARPS_ESPRESSO_RESULTS_2026-11-14.zip` | `7.736.372` | `0c663b2b65e340deedf629cea069cee5092230a954ad56b6c39bf79684f00133` |
| **G** | `SETI_D081_V3_2_TRANSIT_KINEMATICS_AND_10PC_RESULTS_2026-11-15.zip` | `8.045.722` | `12b951d77993cae116b8b7e8968866c13a374a23bd06ac1e96610ac63ee713a9` |
| **H** | `SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_RESULTS_2026-11-15.zip` | `29.473.205` | `d5f73f0c93e6e6381441896e0457ea18d3baa05fadd7a8c569b60361f88a2457` |
| **I** | `SETI_D083_V3_4_CRIRES_KBAND_AND_100STAR_RESULTS_2026-11-15.zip` | `5.549.428` | `f60cf9d63b457c5246dcb14c5b4064376ef709118b5b325360d0d6c1686adf19` |
| **J** | `SETI_D084_V3_5_NORTHERN_10PC_AND_125STAR_RESULTS_2026-11-16.zip` | `10.117.107` | `d13c6f409047d9b8a16c74f26098c44d4808d9f6a96a2e79dba34395f99d77cc` |
| **K** | `SETI_D085_V3_6_SPIROU_YJHK_AND_COMB_V4_RESULTS_2026-11-17.zip` | `17.448.033` | `2d27e24d9b943af3ff8d4796155ab0bbf97e87540b265f7cef5df56dba0685cb` |
| **L** | `SETI_D086_V3_7_UVES_NUV_PANCHROM_AND_COMB_V4_1_RESULTS_2026-11-17.zip` | `22.587.203` | `b37d27ac6269e6671fb341b98514b27edad5b2dbbc392bec75eaeaa63073aea1` |
| **M** | `SETI_D087_V3_8_SPACE_UV_STIS_FARRED_AND_200STAR_RESULTS_2026-11-18.zip` | `19.262.628` | `95b35e2a8b93b536c07b3c47c6c70f2ab1712455613059d66c7a00fe9591671c` |
| **N** | `SETI_D088_V3_9_NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_RESULTS_2026-11-18.zip` | `9.492.762` | `c0210250b925df3bebb1710c2bf7333a64ed767ebdc1f38a496d6a9454f7d45d` |
| **O** | `SETI_D089_V4_0_SPACE_LYMAN_FUV_NUV_RESULTS_2026-11-19.zip` | `4.262.551` | `4864dd3b5c0e958e428e1af815e1a378a37824d6bc87a89de9c223d89bccd723` |
| **P** | `SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip` | `8.610.790` | `2940839e8613b0d388c9b922743ba8244852806411f28586696e59eb8d73841a` |
| **Q** | `SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip` | `22.923.782` | `9da4739bdb413d675b9bc1f17dc9d60d5abc7944622714017cf1889a097b51d0` |
| **R** | `SETI_D092_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF_RESULTS_2026-11-20.zip` | `27.934.528` | `845f0186a6a793ece2b62f9a2e7caaca5181a9b5a12f8db39326376a58a1d8dd` |
| **S** | `SETI_D093_V5_1_DEDOPPLER_DRIFT_ELLIPSOID_GRACES_CORALIE_CARMENES_RESULTS_2026-11-21.zip` | `25.934.814` | `2588057cbd611686d50ced7f4432dce623b16609bc62de01d6460c91c504979a` |
| **T** | `SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip` | `16.641.712` | `fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc` |
| **U** | `SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip` | `16.898.458` | `24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d` |
| **V** | `SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip` | `15.941.580` | `a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158` |
| **W** | `SETI_D097_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_OPTICAL_JERK_RESULTS_2026-11-22.zip` | `11.687.103` | `aa296f9c72faefcacbd4f4fedb73c7c3f2b1377823fad3e308fd6a9844f6fed8` |
| **X** | `SETI_D098_V5_6_SOFIA_GREAT_ISO_SWS_FORCAST_OPTICAL_JERK_RESULTS_2026-11-22.zip` | `22.898.406` | `f57f48355df2b92257f39d76e83f2d850ae6d9164ea10ef1539bede1ca8fb838` |
| **Y** | `SETI_D099_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT_RESULTS_2026-11-22.zip` | `15.546.915` | `77b187f3509a704978096c14b97f83a13d3eebb6b2fc9d53a8c3b296b362df0b` |
| **Z** | `SETI_D100_V5_8_JCMT_3MM_SOFIA_FIFILS_IUE_ECCENTRIC_KEPLERIAN_RESULTS_2026-11-22.zip` | `13.186.766` | `f8900c1aee6db352b6317c1dd6bf308d286bab2c0c0b367e8863383438446bd2` |
| **AA** | `SETI_D101_V5_9_ALMA_MM_BAND1_GAP_CLOSURE_DRIFTING_COMB_RESULTS_2026-11-23.zip` | `18.094.897` | `848a2ade7fdb46ed4e4f067e729ccf796a5181501f6e0ed18f573ff871fa8b20` |
| **AB** | `SETI_D102_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_ALMA_UNBROKEN_MM_RESULTS_2026-11-23.zip` | `22.236.761` | `684d6828063cf17b8adcd666932633c07196e8764038dbbdd3a48bdd5433ca2c` |
| **AC** | `SETI_D103_V6_1_HARD_XRAY_NUSTAR_XMM_RGS_ALMA_B9B10_700STAR_RESULTS_2026-11-23.zip` | `20.006.424` | `d0155c0b3c98625c0e8f9cff5f55ccb89d7477e6ada6b3fd18a0ba8cc6615de4` |
| **AD** | `SETI_D104_V6_2_SOFT_GAMMA_SUZAKU_GSO_XRISM_NICER_200STAR_10PC_RESULTS_2026-11-24.zip` | `18.980.731` | `08169d98eb4313ea15610b8c4367f85a717cacdc10263ebd0a21e2a503cfad06` |
| **AE** | `SETI_D105_V6_3_MEV_GEV_GAMMA_OSSE_COMPTEL_FERMI_LAT_800STAR_RESULTS_2026-11-24.zip` | `21.288.611` | `74ee4b760a0b585ba6b6d7a2e0edbfe623258aa170a507fe577189247749778a` |
| **AF** | `SETI_D106_V6_4_VHE_TEV_GAMMA_HESS_MAGIC_VERITAS_HAWC_60OCTAVE_RESULTS_2026-11-24.zip` | `22.232.278` | `5a5a04924333472d1775f5d6fd843e4712e1d39da824f2a8c6555741a09e0553` |
| **AG** | `SETI_D107_V6_5_ICECUBE_NEUTRINO_SWIFT_BAT_XRT_900STAR_RESULTS_2026-11-25.zip` | `21.105.677` | `125c4db22ff7d8fcdaabe50b929df44f9a6a3f5384738fe77c5ce4e28c201272` |
| **AH** | `SETI_D108_V6_6_IXPE_POLARIMETRY_EROSITA_DR1_RXTE_1000STAR_RESULTS_2026-11-25.zip` | `18.673.537` | `b66922487b86763fce56def95b360aa8b1dae0c7e05e1a4553d77000a3d133bf` |
| **AI** | `SETI_D109_V6_7_10PC_DRIFT_CLOSURE_BAYESIAN_FTX_CWTFM_RESULTS_2026-11-25.zip` | `37.047.683` | `7f681525dc74be7c2f80a464b47f947960f8c0206e31fce2cdbe0a69ed76215c` |
| **AJ** | `SETI_D110_V6_8_OPTICAL_NIR_SPECTROPOLARIMETRY_RESULTS_2026-11-26.zip` | `42.385.734` | `11b2ba8cdb2a8b7aeaa97687fc75bf5d30ab82d7b92a880c5d29509f96e621dd` |
