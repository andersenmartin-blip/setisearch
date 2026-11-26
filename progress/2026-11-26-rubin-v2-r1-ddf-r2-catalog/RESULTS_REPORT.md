# Vera C. Rubin Observatory (LSST) V2 — Spor R1 (DDF Gaia-stjerner) & Spor R2 (538 Sydlige Katalogstjerner)

**Status:** **FULDENDT & VERIFICERET (`RUBIN_V2_AUDIT: 12/12 PASSED` + `SPOR5_PUBLICATION_AUDIT: 12/12 PASSED` under `/usr/bin/python3 -S`, `0` verificerede teknosignaturer, `0` overlappende IDs med `work_rubin_20261102`, `0` eksterne tidsskriftsuploads)**

---

## 1. Hvorfor Rubin V2 lykkedes — Løsning af 2. november-flaskehalsen

I den tidligere afgrænsede oktober-pilot (`work_rubin_20261102`, 2. november 2026) indeholdt Finks offentlige LSST-API kun `2` oktober-nætter, hvilket kun gav **`2/190` evaluerbare stjerner i `/sources`** og **`4/190` i `/fp`** — langt under minimumskravet på `50` stjerner.

Ved vores live API-genoptagelse den **26. november 2026** via anonym offentlig adgang (`https://api.lsst.fink-portal.org`, `0 DKK`, uden krav om Rubin Data Rights) rummer Finks LSST-katalog nu **`87` nætter og `16.252.979` alerts** (`5.543` visits) fra februar til og med **`11` nye november-nætter (`2026-11-05` til `2026-11-15`: `765.131` alerts i `u, g, r, i, z`)**.

Ved at målrette tre høj-kadence Rubin Deep Drilling Fields (**`COSMOS`**, **`EDFS-b`**, **`ELAIS-S1`**) og prospektivt krydsmatche mod **Gaia DR3** (vi Hentede kataloget via Heidelberg ARI TAP spejlet `https://gaia.ari.uni-heidelberg.de/tap/sync` efter egenbevægelses-propagation til `2026.85`) blev flaskehalsen fuldstændig brudt:
- **`2.638`** rene, isolerede Gaia-stjerner ($16 \le G \le 21$, `RUWE < 1,4`, ingen Gaia-nabo inden for `3,0"`) opfyldte `max_band_ndata >= 8` *før* åbning af lyskurverne.
- Herfra blev **`300` prospektivt låste Gaia-stjerner** (`COSMOS`: `182`, `EDFS_B`: `100`, `ELAIS_S1`: `18`) + **`20` uafhængige kontroller** (`10` `mdwarf_flare` + `10` `in_tns`) låst i `METHOD_LOCK.json` (`2026-11-26T19:24:10.589719+00:00`) med `0` overlap mod de `210` tidligere IDs i `work_rubin_20261102`.

---

## 2. Spor R1 — DDF Dæmpnings- (`Channel A`) & Optisk Flash- (`Channel B`) Søgning

Alle målestrømme holdes **strengt adskilt** (`/sources` mod `/fp` forced photometry), og alle 64-bit ID'er bevares som strenge (`parse_int=str`).

| Målestrøm (Spor R1) | Udvalgte stjerner | Rå rækker | Rene rækker efter flag | LONO evaluerbare stjerner (`>= 50`?) | Kausale (`-180d`) stjerner | Dim-triggere (`<=0,759`, $Z \ge 5$) | Flash-triggere (`>=1,585`, $Z \ge 6$) | Verificerede ETI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`/sources`** (direkte alerts + pixel-flag) | `300` | `30.617` (`33.045` inkl. ctrl) | `5.631` | **`85` (`JA`, `2.926` rækker)** | `78` (`1.490` rækker) | `30` rækker / **`16` obj** | `3` rækker / **`1` obj** | **`0`** |
| **`/fp`** (forced phot. uden pixel-flag) | `300` | `91.990` (`100.123` inkl. ctrl) | `91.990` *(forced flags utilg.)* | **`254` (`JA`, `75.332` rækker)** | `250` (`40.128` rækker) | `826` rækker / `184` obj | `13` rækker / `8` obj | **`0`** |

*(Bemærk: `timeWithdrawnMjdTai` var `null` på alle rækker (`0` non-null). Fraværet af pixel- og mætningsflag på `/fp`-strømmen giver forventet høj artefaktrate i rå `/fp`-fluktuationer, hvorfor `/fp` fungerer som værdifuld krydsvalideringsstrøm mod flag-renset `/sources`.)*

### Fuld triage & FITS cutout-validering af alle `17` triggede R1-objekter

Stage 3 hentede **`39` officielle FITS-cutouts (`Science`, `Template`, `Difference`)** fra Fink (`/api/v1/cutouts`) over `13` objekter, kørte Lomb–Scargle periodogrammer (`astropy.timeseries.LombScargle`), SIMBAD TAP-opslag (`3,2"` radius) og epoke-synkron `/sources` vs. `/fp` + astrometrisk centroidekontrol:

1. **`4` bekræftede periodiske variable stjerner (`ASTROPHYSICAL_VARIABLE_PERIODIC_LS`):**
   - `313893023224168464` (`EDFS_B`, Gaia `VARIABLE`): $P = 0{,}112356\,\mathrm{d}$ (`FAP = 1,79e-34`), bekræftet samtidig i `/fp` (`fp_ratio = 0,782`).
   - `313730297654411302` (`ELAIS_S1`): $P = 0{,}21524\,\mathrm{d}$ (`ls_power = 0,9657`, `FAP = 5,03e-9`).
   - `313980948723007593` (`COSMOS`): $P = 4{,}99338\,\mathrm{d}$ (`FAP = 1,12e-10`), bekræftet i `/fp` (`fp_ratio = 0,619`, `Diff SNR = 148,1`).
   - `313963405124304897` (`COSMOS`, Gaia `VARIABLE`): $P = 0{,}23384\,\mathrm{d}$ (`FAP = 7,79e-4`).
2. **`1` bekræftet astrofysisk M-dværg flare (`ASTROPHYSICAL_FLARE_MDWARF_CANDIDATE`):**
   - `313972182854139942` (`COSMOS`, $G=19{,}24$, $BP-RP = 2{,}62$): eneste R1 flash-trigger (`r`-bånd `1,964×`, $Z=+11{,}93$; `g`-bånd `1,702×`, $Z=+7{,}09$). Bekræftet samtidig i `/fp` (`fp_ratio = 1,453`) med ren punktformet FITS `Difference`-kilde (`SNR = 27,66`, `dipole = 0,0`, centroide-offset `0,264 px`).
3. **`1` FITS-cutout dipol-afvisning (`INSTRUMENTAL_ARTIFACT_CUTOUT_VETO`):**
   - `313774269504422076` (`EDFS_B` `g`): stærk S/N-dipol i `Difference`-billedet (`dipole_lobe_ratio = 0,8886`) og stabil `/fp` på samme eksponering (`fp_same_epoch_ratio = 0,9988`).
4. **`10` tidlige `diaSource`-centroide / PSF-underestimeringer (`INSTRUMENTAL_DIA_CENTROID_PSF_BIAS`):**
   - Inkl. flerbånds-kandidaten `313871014203228340` (`COSMOS i+z`): hvor fast-positions forced photometry (`/fp`) på *præcis* samme eksponering måler fuld stjernelysstyrke (`fp_same_epoch_ratio = 0,9838` til `1,0323`; specifikt `1,0028` for `313871014203228340`), eller hvor difference-fluxen (`r:psfFlux`) var positiv på februars SV-nætter (`MJD 61032/61033/61090/61091/61095`).
5. **`1` lav-pålideligheds centroide-hop (`INSTRUMENTAL_CENTROID_HOP_LOW_REL`):**
   - `313980948857749506` (`COSMOS r`, `61095.12760–61095.12853`): astrometrisk centroide sprang `1,00"` (`~5 px`) væk fra stjernen med lav `reliability = 0,254` og lavt cutout-SNR (`3,62`).

### Injektionskalibrering & Bayesianske Øvre Grænser ($0$ Verificerede ETI)

Fra **`4 × 1.200 = 4.800`** syntetiske injektionsforsøg pr. målestrøm på de reelle tidsstempler og fluxfejl:
- **`/sources` betinget på samplet epoke:** $\eta_{\mathrm{dim}} = \mathbf{51{,}17\,\%}$ ($614/1.200$), $\eta_{\mathrm{flash}} = \mathbf{65{,}42\,\%}$ ($785/1.200$, og `81%` ved `2.0 mag / 30 s`). Fuld survey-duty-cycle er $\eta_{\mathrm{dim,duty}} = 7{,}83\,\%$ pga. åbne observationsgab mellem blokkene.
- **`/sources` Bayesiansk $f_{95}$ (`85` evaluerbare stjerner, `0` ETI):**
  - Optisk Flash (betinget, $N_{\mathrm{eff}} = 55{,}61$): **`3,3801 %` Jeffreys** (`5,1546 %` Uniform / `5,2448 %` Clopper–Pearson).
  - Dæmpning (betinget, $N_{\mathrm{eff}} = 43{,}50$): **`4,2956 %` Jeffreys** (`6,5112 %` Uniform / `6,6558 %` Clopper–Pearson; duty-cycle `24,2500 %` Jeffreys).
- **`/fp` betinget ($254$ evaluerbare stjerner, $\eta_{\mathrm{dim}} = 79{,}75\,\%$, $\eta_{\mathrm{flash}} = 85{,}25\,\%$):** **`0,8821 %` Flash Jeffreys** (`1,3677 %` Uniform) og **`0,9426 %` Dimming Jeffreys** (`1,4609 %` Uniform).

---

## 3. Spor R2 — Systematisk Krydstjek af Alle `538` Sydlige SETI-Katalogstjerner

Alle **`538` Science-stjerner** fra det endelige `1.083`-stjerners katalog med `Dec <= +15°` (inkl. `136` stjerner inden for `< 10 pc`) blev spurgt mod Fink LSST `/api/v1/conesearch` (`radius = 10"`):
- **Status:** **`538/538` HTTP 200** (`100 %` dækning af forespørgsler).
- **Resultat:** **`537/538` har `0` Fink LSST-alerts** (forventet, fordi nære lyse katalogstjerner mætter Rubins 8,4 m detektor under $r \lesssim 16\,\mathrm{mag}$ eller ligger uden for hidtidige difference-image alerts).
- **Eneste træf (`1/538`):** **`GJ 27.1`** (`23,6062 pc`, `HARPS Orbit #188` eksoplanetvært nær `ELAIS-S1`) har ét matchende objekt `diaObjectId = 313699505148526678` i **`9,5898"` afstand** (`NEARBY_COMPANION_OR_FIELD_2_10ARCSEC`, `1` ren `g`-båndsrække uden mætningsflag, `0` `/fp`-rækker). FITS `Template`-cutouttet (`figR05`, nederste række) viser direkte `GJ 27.1`'s lyse rand til venstre og en svag baggrundskilde ved trådkorset `9,59"` væk — dvs. **`0` direkte værtsstjerne-træf (`<= 2,0"`)** og **`0` verificerede ETI**.

---

## 4. Verifikation, Figurer & Arkiv

- **6 Visuelt Godkendte 300-DPI Figurer (`figR01–figR06`):** `figures/` og `progress/2026-11-26-rubin-v2-r1-ddf-r2-catalog/figures/` (`VISUAL_REVIEW_RUBIN_V2.json`).
- **Ren-Stdlib Audit (`12/12 PASSED`):** `/usr/bin/python3 -S .../scripts/audit_rubin_v2.py` verificerer `R1–R12` inkl. uafhængig stdlib-genberegning af alle `33` triggede rækker (`max diff < 1e-10`) samt at Spor 5-auditten fortsat består **`SPOR5_PUBLICATION_AUDIT: 12/12 PASSED`**.
- **Fuld Arkivpakke (`12.815.386 B`, SHA-256 `bd5cdf6f5bb0c158e271080acbed53872bfddd91b204bedaca329d9367fc4719`):** `/home/martin/SETI_Fortsaettelse_2026-11-14/archives_rubin_v2/SETI_RUBIN_V2_R1_R2_RESULTS_2026-11-26.zip` (helt adskilt fra de `38` forseglede arkiver `A–AL` i `archives/`).
