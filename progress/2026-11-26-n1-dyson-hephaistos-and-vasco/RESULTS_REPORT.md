# Spor N1 — Dyson-sfærer (*Project Hephaistos II* + Blind DDF-søgning) & Multi-Årti "Forsvindende Stjerner" (VASCO)

**Status:** **FULDENDT & VERIFICERET (`N1_DYSON_VASCO_AUDIT: 12/12 PASSED` + `RUBIN_V2_AUDIT: 12/12 PASSED` + `SPOR5_PUBLICATION_AUDIT: 12/12 PASSED` under `/usr/bin/python3 -S`, `0` verificerede teknosignaturer, `0` eksterne uploads, `0` ændringer til forseglede `A–AL` eller Rubin-arkiver)**

---

## 1. Søjle N1A — Uafhængig Efterprøvning af Alle `7` *Project Hephaistos II*-Kandidater (`A–G`)

Vi hentede og forbandt uafhængigt `Gaia DR3`, `2MASS`, `AllWISE`, `NERSC DESI Legacy DR10` direkte `Tractor`-kataloger, `DSS2 Red`, `unWISE-neo7`, `VLASS 1.2` (3 GHz radio), `Fink Vera Rubin LSST` (`0` alerts) og `SIMBAD` for alle 7 M-dværgkandidater (`A–G`, Suazo et al. 2024, arXiv:2405.02927) og tilpassede fysiske to-komponent sorte-legeme-SED'er (`photosphere + T_DS`):

| Kandidat | Gaia DR3 ID | Afstand (pc) | $W1-W3$ / $W1-W4$ | $\Delta\chi^2$ / $\gamma$ | DR10-naboer $\le 8''$ (Udv. galakser) | VLASS 3 GHz SNR | Samlet Disposition |
|---|---|---|---|---|---|---|---|
| **A** | `3496509309189181184` | `144,22` | `1,97 / 5,18` | `272,0 / 0,105` | `0 (0)` | `2,56σ` (`0,51 mJy` @ `3,16"`) | **`UNBLENDED_IN_DR10_NEEDS_JWST_OR_ALMA`** |
| **B** | `4843191593270342656` | `213,62` | `2,88 / 4,99` | `113,7 / 0,090` | `4 (3)` | Syd for VLASS (`-40,5°`) | **`EXTENDED_BACKGROUND_GALAXY_IN_WISE_PSF`** |
| **C** | `4649396037451459712` | `220,11` | `3,17 / 5,98` | `94,7 / 0,202` | `1 (0)` | Syd for VLASS (`-74,2°`) | **`NEARBY_FAINT_NEIGHBOR_IN_WISE_PSF`** |
| **D** | `2660349163149053824` | `212,96` | `3,14 / 5,98` | `92,6 / 0,194` | `4 (3)` | `2,24σ` (`0,28 mJy`) | **`EXTENDED_BACKGROUND_GALAXY_IN_WISE_PSF`** |
| **E** | `3190232820489766656` | `275,99` | `2,54 / 5,03` | `73,2 / 0,081` | `1 (1)` | `2,41σ` (`0,33 mJy`) | **`EXTENDED_BACKGROUND_GALAXY_IN_WISE_PSF`** |
| **F** | `2956570141274256512` | `268,27` | `1,02 / 4,25` | `23,1 / 0,044` | `8 (5)` | `2,77σ` (`0,40 mJy`) | **`EXTENDED_BACKGROUND_GALAXY_IN_WISE_PSF`** |
| **G** | `2644370304260053376` | `251,98` | `1,45 / 4,68` | `19,8 / 0,060` | `8 (6)` | **`127,12σ` (`21,53 mJy` @ `7,0"`)** | **`RADIO_AGN_AND_GALAXY_BLEND_IN_WISE_PSF`** |

- **`6/7` (`B, C, D, E, F, G`)** har direkte optiske/udvidede galakse- eller nabokilder inden for `8"` (`WISE W3`-strålen) i Legacy DR10, og vores VLASS FITS-analyse genfinder præcist **`127,12σ` radio-AGN-kilden ved Kandidat G** (`7,0"` offset, svarende til Ren et al. 2024/2025).
- **`Kandidat A`** er optisk ublandet i Legacy DR10 (`0` naboer $\le 8''$, `2,56σ` i VLASS) og kræver sub-buesekund JWST/ALMA-opfølgning; **ingen ETI kan konkluderes (`0` verificerede ETI)**.

---

## 2. Søjle N1B — Blind Dyson-sfære-søgning (`260` Parallakse-Rene Stjerner i `3` DDF'er)

- Tværs over `COSMOS` (`72`), `EDFS_B` (`147`) og `ELAIS_S1` (`41`) bestod **`260` parallakse-verificerede stjerner** ($d \le 1.000\,\mathrm{pc}$, `SNR_plx >= 5`, `RUWE < 1,4`, ublandet Gaia-nabo $\le 6''$, rene `AllWISE` flag; `156` med `W3 SNR >= 5`).
- **`1.200` syntetiske Dyson-sfære SED-injektionsforsøg** ($\gamma \in \{0{,}01, 0{,}05, 0{,}15, 0{,}30\} \times T_{\mathrm{DS}} \in \{150, 300, 500\}\,\mathrm{K}$): **`99,00 %`** (`891/900`) genfinding for $\gamma \ge 0{,}05$ (`85,67 %` samlet over hele griddet inkl. $\gamma = 0{,}01$).
- Kun **`3` blinde triggere** udløste ($W1-W3 \ge 1{,}0$, $\gamma \ge 0{,}02$, $\Delta\chi^2 \ge 25$):
  - **`3/3` (`100,0 %`)** blev opklaret af Legacy DR10 `Tractor`-deblending & FITS-cutouts som **baggrundsgalakser i `WISE`-strålen (`EXTENDED_BACKGROUND_GALAXY_IN_WISE_PSF`)**:
    - `EDFS_B 4830932519656396288` (`718,8 pc`): `3` udvidede DR10-galakser inden for `10"`.
    - `EDFS_B 4830898091199210240` (`908,9 pc`): `3` udvidede DR10-galakser inden for `10"`, `22,3×` stærkere `W3`-nabo.
    - `COSMOS 3836044169202480640` (`812,5 pc`, $G=14{,}50$ sol-lignende stjerne): en Sersic-galakse `8,08"` syd for stjernen har **`28,15×`** stærkere `W3`-flux (`989,4` mod `35,1` nanomaggies), tydelig i både `figN04` Legacy DR10 og aflang `unWISE`!
- **Bayesiansk $f_{95}$ ($\gamma \ge 0{,}05$, $N_{\mathrm{eff}} = 257{,}4$, `0` ETI):** **Jeffreys `0,7427 %`** (`1,1526 %` Uniform / `1,1571 %` Clopper–Pearson).

---

## 3. Søjle N1C — Multi-Årti "Forsvindende Stjerner" (VASCO, `1990s DSS2 / 2012 PS1 / 2016 Gaia -> 2020 DR10`)

- **`1.197` rene Gaia DR3-stjerner** (`16,0 <= G <= 20,5`, egenbevægelses-propageret til `2020.0`, strengt inde i `8` NERSC Legacy DR10-bricks på tværs af `COSMOS`, `EDFS_B`, `ELAIS_S1`): **`1.197/1.197` (`100,00 %`) genfundet i Legacy DR10** $\rightarrow$ **`0` forsvundne stjerner** (Jeffreys $f_{95} = \mathbf{0{,}1603\,\%}$, Uniform `0,2497 %`).
- **`372` Pan-STARRS1 DR2 (`~2012`) punktformede `COSMOS`-kilder (`nDetections >= 5`):** `345` matchet direkte i Tractor + `27` flagget for visuel FITS-kontrol (`figN05`):
  - **`2/27`** var ægte klare stjerner (`ls_dr10_center_snr = 237,1σ` & `4066,3σ` + `DSS2 47,5σ` & `48,2σ`), som blot lå deblendede/uden for brick-match (`347/347` ægte kilder `100 %` genfundet $\rightarrow$ Jeffreys $f_{95} = \mathbf{0{,}5516\,\%}$).
  - **`25/27`** viste sig alle at være **`r`-enkelte PS1-spøgelsesartefakter med sentinelværdi `iMeanPSFMag = -999,0` & `zMeanPSFMag = -999,0`** (falsk `|iPSF-iKron|=0`) og fuldstændigt fravær i både `1990'er DSS2` (`1,3–3,1σ`) og `Legacy DR10` (`1,1–3,6σ`)!
- **Samlet VASCO-udbytte: `0` forsvundne eller permanent slukkede stjerner (`0` ETI).**

---

## 4. Figurer, Arkiv & Revisioner (`12/12 PASSED`)

- **6 Visuelt Godkendte 300-DPI Figurer (`figN01–figN06`):** [`VISUAL_REVIEW_N1.json`](results/VISUAL_REVIEW_N1.json).
- **Ren-Stdlib Revision (`/usr/bin/python3 -S`):** [`audit_n1_dyson_vasco.py`](scripts/audit_n1_dyson_vasco.py) $\rightarrow$ **`N1_DYSON_VASCO_AUDIT: 12/12 PASSED`**, samt samtidig bekræftelse af **`RUBIN_V2_AUDIT: 12/12 PASSED`** og **`SPOR5_PUBLICATION_AUDIT: 12/12 PASSED`**.
- **Fuld Arkivpakke (`archives_n1/`):** `SETI_N1_DYSON_HEPHAISTOS_VASCO_2026-11-26.zip` (`40,915,313 B`, SHA-256 `2783591a93686fb2e48266e17b071c1207b923c7afed28399d335ad5833662df`).
