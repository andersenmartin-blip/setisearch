# SETI Fase D079 (Trin 2) — Prospektivt Kalibreret `HARPS_ECELLE_V3` Optisk Lasersøgning på 10 Friske Sol-Analoge Stjerner

**Dato:** 14. november 2026  
**Fase:** `D079` (`work_harps_20261114_d079_v3_calibrated_search`)  
**Prospektiv metodelås (`METHOD_LOCK.json`):** `17f9324ce81e680877e57e8a5776e37df1d6502f43f7419f3ca495da488cde56` (frosset `2026-11-14T16:11:39.478783+00:00`, strengt før første science-download)  
**Dokumenteret implementerings- og forensisk tillæg (`IMPLEMENTATION_LOCK.json`):** `24156b91050531cca85fa46e5505b7c749d86e3dc8d399d422a8d4c2791d3f5d`  
**Uafhængig ren-stdlib numerisk audit (`/usr/bin/python3 -S audit.py`):** `PASS` (`6,072` uafhængige kontroller, `0` fejl, maks. afvigelse `< 5 × 10⁻⁹`)  
**Hovedkonklusion:** **`0` verificerede ETI-lasersignaler** på tværs af `50` friske HARPS-eksponeringer af `10` nære sol-analoge stjerner (`15,2–46,3 pc`, `13.799,8 s` science-integration, `15.320.849` gennemsøgte 1D-bins i Kanal T + `10` 5-epoke coadds i Kanal P) og `10` prospektive kontroleksponeringer på `2` kontrolstjerner (`HD 1461`, `HD 4308`). De `8σ` kalibrerede øvre grænser for en diffraktionsbegrænset `10 m`-lasersender spænder fra **`17,30 kW` til `201,41 kW`** (median **`46,99 kW`**, ækvivalentbredde median **`3,81 mÅ`** over hele `3800–6900 Å`, inkl. det nyåbnede blå interval `3800–4000 Å`).

---

## 1. Baggrund og formål med Trin 2 (`D079`)

Efter den fulde arkivmæssige og tvær-instrumentelle lukning af `HD 43629` i `D078` (`D002–D078`, `107.105` bevarede historiske statustabelceller) var næste hovedskridt i projektets køreplan (**Trin 2**) at konstruere, syntetisk kalibrere og prospektivt låse en 3. generations optisk echelle-laserdetektor (**`HARPS_ECELLE_V3`**) *før* åbning af en helt frisk arkivkohorte i ESO HARPS-arkivet ($R \approx 115\,000$, `3782–6912 Å`).

De tidligere detektorversioner (`V1`/`V2` i `C001–D002`) led under fire veldokumenterede svagheder, som udløste `141` falske alarmer på `50` eksponeringer i `D002`:
1. Fravær af empirisk stellar hvileramme-forankring (hvilket skabte `P`-cyigni-lignende subtraktionsartefakter på stejle fotosfæriske absorptionsflanker under varierende barycentrisk hastighed).
2. Udelukkende brug af sammenlagte 1D-spektre (`S1D`) ved selve detektionen uden simultan kontrol af individuelle echelle-ordener (`_e2ds_A`), kalibrerings-/sky-fiber (`_e2ds_B`) og rå `4096 × 4096` CCD-pixelrammer.
3. Blind maskering af det blå interval `< 4000 Å` samt fravær af en fler-epoke hvileramme-kanal for vedvarende svage lasere.
4. Fravær af prospektive kontrolstjerner og end-to-end syntetisk laser-injektion/genfinding til empirisk fastlæggelse af detektionsfuldstændighed og falsk-alarm-adfærd.

`D079` løser disse fire punkter i én samlet, deterministisk og uafhængigt revideret leverance til `0 DKK`.

---

## 2. Prospektiv metodelås, nul-overlap-bevis og kohorte (`60` HARPS-eksponeringer)

### 2.1 Streng nul-overlap-verifikation mod alle tidligere faser
Før udvælgelsen af `FROZEN_COHORT60.csv` udtog og krydstjekkede vi samtlige `40` tidligere stjernenavne og `363` tidligere ESO `ADP.*`-identifikatorer fra `C001–C037`, `D001`, `D002–D034` og `D035–D078` (`PRIOR_EXCLUSION_VERIFICATION.json`, SHA-256 `45f97de1a75407ce...`):
- **Overlap i stjernenavne:** **`0`** (mod alle `40` tidligere mål).
- **Overlap i ESO `dp_id`:** **`0`** (mod alle `363` tidligere `ADP.*`-filer).

### 2.2 Kohortestruktur og tidslig metodelås
Kohorten (`FROZEN_COHORT60.csv`, SHA-256 `05d20ea6d02f17c5...`) består af præcis **`60` offentlige ESO HARPS-eksponeringer** (`16.439,76 s` samlet integration, `SNR = 95,4–333,7`, median `178`), opdelt på forhånd i:
- **`2` dedikerede prospektive kontrolstjerner (`10` eksponeringer, `5` distinkte nætter pr. stjerne):** `HD 1461` (`G3V`, `23,40 pc`, $[\mathrm{M/H}] = +0,02$) og `HD 4308` (`G6V`, `22,05 pc`, metal-fattig skive/tyk-skive-analog med $[\mathrm{M/H}] = -0,59$, $\mathrm{RV} = +95,58\,\mathrm{km/s}$).
- **`10` friske nære sol-analoge science-stjerner (`50` eksponeringer, `5` distinkte nætter pr. stjerne):** `HD 4915`, `HD 38858`, `HD 43162`, `HD 45184`, `HD 50499`, `HD 52265`, `HD 59967`, `HD 65907`, `HD 70642` og `HD 76151` (`15,21–46,30 pc`, $5525 \le T_{\mathrm{eff}} \le 5982\,\mathrm{K}$, Gaia `RUWE < 1,25`).

Metodelåsen (`METHOD_LOCK.json`, SHA-256 `17f9324ce81e6808...`) blev forseglet ved `2026-11-14T16:11:39.478783+00:00` *før* nogen science-FITS- eller TAR-fil blev hentet (`FIRST_SCIENCE_DOWNLOAD_RECEIPT.json`).

### 2.3 Bevaret teknisk kørselsfejl og dokumenteret implementeringstillæg (`IMPLEMENTATION_LOCK.json`)
I fuld overensstemmelse med projektets gennemsigtighedsregler bevares både den oprindelige kode (`FROZEN_PRE_INGESTION/{analyze_v0.py, audit_v0.py, plot_figures_v0.py}`) og de to dokumenterede tillæg i `IMPLEMENTATION_LOCK.json`:
1. **`AMEND_1_FIBER_B_71_VS_72_ORDERS` (før nogen resultatfil blev dannet):** Ved første kørsel på de downloadede HARPS `.tar`-pakker stoppede `analyze_v0.py` med `IndexError: index 71 is out of bounds for axis 0 with size 71` i `build_order_patches_for_wave`. Årsagen er en reel instrumentel egenskab ved HARPS DRS: `_e2ds_A.fits` (stjernefiber A) indeholder `72` echelle-ordener (`0..71`), mens `_e2ds_B.fits` (kalibrerings-/skyfiber B) kun indeholder `71` ordener (`0..70`), fordi orden $m = 115$ (Fiber A indeks `45` omkring `5277,2 Å`) falder i mellemrummet mellem den blå og røde CCD for Fiber B. Direkte indeksopslag `e2ds_b[o]` fejlede derfor ved `o = 71` og forskød Fiber B med `+1` orden på hele den røde detektor (`o = 46..70`). Fejlen blev løst fysisk ved at udlæse Fiber B's egne bølgelængdepolynomier (`ESO DRS CAL TH COEFF LL`) fra `_e2ds_B.fits` og parre hver Fiber A-orden med den fysiske Fiber B-orden inden for `< 0,01 Å` (`None` på hul-ordenen `45`), uden at ændre én eneste detektortærskel eller parameter i `v3_detector.py`.
2. **`AMEND_2_POST_UNBLINDING_FORENSIC_VETTING_F1_F2` (efter ublindet kørsel af de låste Gates G1–G5):** De låste `G1–G5`-tærskler og samtlige `321` rækker i `V3_CANDIDATE_LEDGER.csv` bevares `100 %` uændrede, men da de to prospektive kontrolstjerner umiddelbart viste statistisk paritet med science-stjernerne (`2,80` mod `2,96` nominelle G1–G5-passager pr. eksponering), tilføjede vi en deterministisk, ren-stdlib-revideret forensisk klassifikation (`FORENSIC_VETTING_176.csv`, Tests `F1` og `F2`), så hverken `SUMMARY.json` eller `FIG2` fremsætter falske påstande om ETI-detektioner.

---

## 3. Arkitektur for `HARPS_ECELLE_V3` og kalibreringsresultater

### 3.1 Stellar hvileramme-verifikation (`720` NIST-ankerfits på tværs af `12` stjerner)
På hver af de `60` eksponeringer tilpassede vi `12` isolerede fotosfæriske NIST-absorptionslinjer (`Fe I`, `Ca I`, `Ti II`, `Cr I`, `Ni I` fra `4005,2 Å` til `6750,2 Å`) på et `321`-punkts hastighedsgitter (`±16 km/s` omkring Gaia DR3 i skridt af `0,10 km/s` med parabolsk sub-grid-forfining):
- **`672 / 720` (`93,3 %`)** rene absorptionsfits og **`0` randtræf (`boundary_hits = 0`)**.
- Epoke-til-epoke reproducerbarhed pr. stjerne over de `5` observationsnætter ligger på **`12,0–44,2 m/s` RMS**!
- Middelafvigelsen mod Gaia DR3 ligger samlet mellem **`+0,227` og `+0,664 km/s`** (median **`+0,431 km/s`**), hvilket svarer præcist til det kendte nulpunktsskift (konvektiv blåforskydning og gravitationsrødforskydning mellem optiske `Fe I`-linjer ved $R=115\,000$ og Gaia RVS `Ca II`-tripletten).

### 3.2 Syntetisk end-to-end kalibrering (`816` forsøg inkl. `3800–4000 Å` blåt bånd)
På de to kontrolstjerner (`HD 1461` og `HD 4308`) gennemførtes **`816` syntetiske injektions- og 2D-kalibreringsforsøg** over `8` bølgelængdebånd fra **`3825,40 Å` til `6815,50 Å`**:
1. **Kanal T (1-epoke transiente lasersignaler, `480` forsøg ved `4, 6, 8, 12, 20σ` og sub-bin-faser `-0,35, 0,0, +0,35`):**
   - Samlet end-to-end genfindingsgrad (gennem `G1 + G2 + G3 + G4`) ved **`>= 8σ`: `85,07 %`** (`245 / 288`), stigende til **`100,0 %` i samtlige 8 bånd ved `20σ`**.
   - I det nyåbnede blå interval **`3800–4000 Å`** (`3825,4 Å` og `3945,2 Å`) opnås **`83,33 %` genfinding ved `>= 8σ`** (`100 %` ved `3825,4 Å` fra `8σ` og op; `50 %` ved `8–12σ` og `100 %` ved `20σ` tæt ved `Ca II H&K`-flanken ved `3945,2 Å`).
2. **Kanal P (5-epoke vedvarende lasersignaler i stellar hvileramme mod Beer-Lambert-skaleret 11-stjerne-atlas, `240` forsøg ved `5, 7, 9, 12, 20σ`):**
   - Samlet end-to-end genfindingsgrad ved **`>= 9σ`: `83,33 %`** (`120 / 144`), herunder **`100,0 %` i begge blå bånd (`3825,4 Å` og `3945,2 Å`) fra `9σ` og op**.
3. **Gate G5 & Forensisk Test F2 på ægte rå `4096 × 4096` HARPS CCD-udsnit (`96` rumlige forsøg):**
   - Rå CCD-orientering verificeret mod `_e2ds_A` på alle `39` rå `.fits.Z`-rammer med median tværkorrelation **`0,9958–0,9993`** og median top-forskydning **`0,0 px`**.
   - `Gate G5` (1-rækkes tværdispersions-PSF): **`90,63 %`** (`29 / 32`) pass-rate for ægte fiber-fødede lasere og **`79,69 %`** (`51 / 64`) afvisning af forskudte 1-pixel kosmiske stråler og skrå spor.
   - `Test F2` (fuld 2D separabel `5 × 11` fiber-LSF cosinus $\ge 0,85$, 3-rækkers centroid-stationaritet $\le 0,85\,\mathrm{px}$ og dispersionsvinge-henfald $\le 0,55$): bevarer **`84,38 %`** (`27 / 32`) af de syntetiske fiberlasere og afviser **`100 %`** af samtlige skrå kosmiske myonspor i de uinjicerede data.

---

## 4. Ublindede søgeresultater, kontrol-paritet og forensisk lukning (`0` ETI-lasere)

### 4.1 Samlet overblik pr. stjerne (`12` stjerner, `60` eksponeringer)

| Stjerne | Rolle | Afstand (pc) | $G$ (mag) | $T_{\mathrm{eff}}$ (K) | $[\mathrm{M/H}]$ | HARPS $\overline{\mathrm{RV}}$ (km/s) | Epoke-RMS (m/s) | $\Delta\mathrm{RV}_{\mathrm{HARPS-Gaia}}$ (km/s) | V2 træf | V3 Ch.T G1 | V3 Ch.T G1–G5 | V3 Ch.P G1–G5 | Verif. ETI | Median $P_{10\,\mathrm{m},8\sigma}$ (kW) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `HD1461` | `CONTROL` | 23,40 | 6,31 | 5641 | +0,02 | -9,710 | 26,3 | +0,412 | 6 | 7 | 2 | 14 | **0** | — |
| `HD4308` | `CONTROL` | 22,05 | 6,39 | 5591 | -0,59 | +95,583 | 14,9 | +0,358 | 8 | 7 | 3 | 9 | **0** | — |
| `HD4915` | `SCIENCE` | 22,43 | 6,81 | 5652 | -0,36 | -3,284 | 38,9 | +0,543 | 6 | 0 | 0 | 4 | **0** | 41,84 |
| `HD38858` | `SCIENCE` | 15,21 | 5,81 | 5647 | -0,53 | +31,969 | 20,4 | +0,550 | 3 | 3 | 1 | 15 | **0** | 32,26 |
| `HD43162` | `SCIENCE` | 16,70 | 6,19 | 5525 | -0,05 | +22,356 | 39,8 | +0,664 | 1 | 5 | 1 | 0 | **0** | 29,11 |
| `HD45184` | `SCIENCE` | 21,89 | 6,22 | 5740 | -0,31 | -3,424 | 18,2 | +0,422 | 3 | 2 | 1 | 3 | **0** | 50,83 |
| `HD50499` | `SCIENCE` | 46,30 | 7,07 | 5891 | -0,04 | +37,279 | 26,2 | +0,365 | 2 | 4 | 1 | 0 | **0** | 136,65 |
| `HD52265` | `SCIENCE` | 29,92 | 6,16 | 5982 | -0,14 | +54,216 | 44,2 | +0,227 | 3 | 3 | 0 | 0 | **0** | 96,45 |
| `HD59967` | `SCIENCE` | 21,75 | 6,50 | 5670 | -0,53 | +9,756 | 32,8 | +0,576 | 4 | 5 | 0 | 0 | **0** | 39,08 |
| `HD65907` | `SCIENCE` | 16,17 | 5,44 | 5886 | -0,42 | +15,355 | 12,0 | +0,342 | 3 | 5 | 0 | 3 | **0** | 31,10 |
| `HD70642` | `SCIENCE` | 29,28 | 7,01 | 5580 | -0,00 | +49,834 | 39,6 | +0,521 | 6 | 3 | 0 | 18 | **0** | 54,46 |
| `HD76151` | `SCIENCE` | 16,85 | 5,85 | 5656 | -0,11 | +32,431 | 25,7 | +0,439 | 3 | 5 | 1 | 100 | **0** | 36,14 |

### 4.2 Hvorfor de to prospektive kontrolstjerner var afgørende
På de `60` uinjicerede eksponeringer gav den historiske ukalibrerede `V2`-algoritme **`48` falske alarmer** (`14` i kontrol [`1,40/eksp`] og `34` i science [`0,68/eksp`]). Den prospektivt låste `HARPS_ECELLE_V3` (`Gates G1–G5`) scannede `18.385.165` 1D-bins og fandt `321` Gate G1-kandidater (`49` i Kanal T + `272` i Kanal P):
- `Gate G2` (tellurisk airglow): `321 → 320`
- `Gate G3` (nativ `_e2ds_A` LSF-symmetri og enkeltpixel-fraktion): `320 → 235`
- `Gate G4` (naboordens-overlap og Fiber B lampe/sky-veto): `235 → 229`
- `Gate G5` (1-rækkes rå `4096 × 4096` tværdispersions-PSF): `229 → 176` nominelle passager.

Opdeles disse `176` nominelle `G1–G5`-passager efter den prospektive blindingsnøgle (`CONTROL` mod `SCIENCE`), ses øjeblikkeligt:
- **Kontrolstjerner (`10` eksponeringer):** **`28` nominelle passager = `2,80 pr. eksponering`** (`5` i Kanal T = **`0,50/eksp`**; `23` i Kanal P = `2,30/eksp`).
- **Science-stjerner (`50` eksponeringer):** **`148` nominelle passager = `2,96 pr. eksponering`** (`5` i Kanal T = **`0,10/eksp`**; `143` i Kanal P = `2,86/eksp`).

Der er **nul statistisk overskud på science-stjernerne** (`2,96/eksp` mod `2,80/eksp` i kontrol, og i Kanal T har kontrolstjernerne endda `5×` højere rate pr. eksponering end science-stjernerne: `0,50/eksp` mod `0,10/eksp`!). Uden dedikerede kontrolstjerner i det låste forsøgsdesign kunne en naiv pipeline have fejlfortolket de `148` nominelle passager; med kontrolstjernerne afsløres de straks som instrumentelle/astrofysiske baggrundseffekter.

### 4.3 Eksakt fysisk identifikation af alle `176` nominelle passager (`FORENSIC_VETTING_176.csv`)

#### A. Kanal P (`166 / 166` afvist af Test F1: Sub-kontinuum fotosfærisk absorptions-mismatch)
I Kanal P dannes residualspektret som $y_P(\lambda) = C_s(\lambda) - M_{-s}(\lambda)$, hvor $M_{-s}$ er et Beer-Lambert-dybdeskaleret 11-stjerne-medianatlas. Når en stjerne (f.eks. `HD 76151` med $[\mathrm{M/H}] = +0,07$ eller `HD 1461` med $[\mathrm{M/H}] = +0,02$ eller `HD 4308` med $[\mathrm{M/H}] = -0,59$) har svage umættede metal-absorptionslinjer (`Fe I`, `Ni I`, `Cr I`, `Mn I`) med en lidt anden linjedybde eller $[\mathrm{X/Fe}]$-sammensætning end 11-stjerne-medianen, opstår en smal positiv differens-top $C_s - M_{-s} > 0$ *nede i bunden af en stellar absorptionslinje*. Da disse fotoner er ægte stjernelys i Fiber A, består de naturligt `G2`, `G3`, `G4` og `G5`!
- **Test F1 (`fn_pk3 >= 1,02` på nativ `_e2ds_A` normaliseret til lokal sidebånds-`Q80`):** På tværs af **samtlige `166` nominelle Kanal P-passager** (`23` kontrol + `143` science) ligger `fn_pk3` mellem **`0,5809` og `0,9787`** (median **`0,8810`**). **Nul ud af `166` (`0,0 %`) når over det lokale stellare kontinuum (`1,00`)!** Samtlige `166` er `100 %` entydigt sub-kontinuum fotosfæriske absorptionslinjer.

#### B. Kanal T (`10 / 10` afvist af Test F2: Skrå 2D kosmiske myonspor og kontinuum-pedestal)
I Kanal T reducerede `Gates G1–G5` allerede antallet af science-træf fra `34` (`V2`, `0,68/eksp`) til blot **`5` på `50` science-eksponeringer (`0,10/eksp`, og `0` på halvdelen af alle science-stjerner)**. Pixel-for-pixel inspektion af de gemte `21 × 25` rå CCD-udsnit forklarer præcis, hvorfor disse `10` enkelt-epoke træf (`5` kontrol + `5` science, alle uden naboordens-dækning `overlap_tested = False`) slap igennem 1-rækkes `Gate G5`: når et skråt kosmisk stråle-/myonspor krydser fiberens spor under en vinkel, eksisterer der altid **én enkelt dispersionsrække `r_pk`**, hvor sporet passerer tæt forbi fibercenteret (`cols 11–13`), mens centroiden vandrer skråt ud i fibervingerne (`cols 7–9` og `cols 14–17`) på naborækkerne `r_pk - 1` og `r_pk + 1`!

| Kandidat-ID | Rolle | Stjerne | ESO `dp_id` | $\lambda_{\mathrm{bary}}$ (Å) | $\mathrm{SNR}_{\mathrm{mid}}$ | `fn_pk3` | `cos_2d_5x11` | `max_3row_dx` (px) | `tilt_2row` (px) | `far_wing_34` | Forensisk klassifikation |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `V3-T-0004` | `CONTROL` | `HD1461` | `ADP.2021-08-02T01:02:00.847` | 3912,193 | 13,86 | 1,348 | 0,684 | 0,97 | 1,22 | -0,009 | `REJECTED_F2_DIAGONAL_2D_COSMIC_RAY_MUON_TRACK` |
| `V3-T-0005` | `CONTROL` | `HD1461` | `ADP.2021-08-02T01:02:00.847` | 6705,085 | 6,71 | 1,021 | 0,905 | 0,46 | 0,03 | 0,632 | `REJECTED_F2_BROAD_CONTINUUM_PEDESTAL_ARTIFACT` |
| `V3-T-0009` | `CONTROL` | `HD4308` | `ADP.2020-11-20T01:24:25.616` | 6249,705 | 9,67 | 1,045 | 0,772 | 0,43 | 0,60 | 0,578 | `REJECTED_F2_DIAGONAL_2D_COSMIC_RAY_MUON_TRACK` |
| `V3-T-0010` | `CONTROL` | `HD4308` | `ADP.2021-07-15T01:06:19.107` | 5603,805 | 9,26 | 1,135 | 0,540 | 1,92 | 1,84 | 0,025 | `REJECTED_F2_DIAGONAL_2D_COSMIC_RAY_MUON_TRACK` |
| `V3-T-0012` | `CONTROL` | `HD4308` | `ADP.2021-08-02T01:02:00.853` | 5978,002 | 10,18 | 1,071 | 0,453 | 1,75 | 3,23 | 0,037 | `REJECTED_F2_DIAGONAL_2D_COSMIC_RAY_MUON_TRACK` |
| `V3-T-0017` | `SCIENCE` | `HD38858` | `ADP.2021-09-14T01:01:55.994` | 6860,335 | 13,64 | 1,136 | 0,506 | 3,15 | 5,58 | -0,114 | `REJECTED_F2_DIAGONAL_2D_COSMIC_RAY_MUON_TRACK` |
| `V3-T-0020` | `SCIENCE` | `HD43162` | `ADP.2020-12-14T01:15:37.715` | 4717,515 | 13,65 | 1,037 | 0,653 | 1,23 | 2,20 | 0,091 | `REJECTED_F2_DIAGONAL_2D_COSMIC_RAY_MUON_TRACK` |
| `V3-T-0024` | `SCIENCE` | `HD45184` | `ADP.2021-09-16T01:08:37.209` | 4826,005 | 14,58 | 1,185 | 0,549 | 2,10 | 2,55 | -0,016 | `REJECTED_F2_DIAGONAL_2D_COSMIC_RAY_MUON_TRACK` |
| `V3-T-0028` | `SCIENCE` | `HD50499` | `ADP.2021-03-18T01:09:29.768` | 5377,618 | 10,74 | 1,089 | 0,753 | 1,09 | 0,84 | 0,147 | `REJECTED_F2_DIAGONAL_2D_COSMIC_RAY_MUON_TRACK` |
| `V3-T-0049` | `SCIENCE` | `HD76151` | `ADP.2021-06-07T01:10:54.243` | 6090,690 | 15,38 | 1,050 | 0,727 | 1,29 | 2,55 | 0,247 | `REJECTED_F2_DIAGONAL_2D_COSMIC_RAY_MUON_TRACK` |

- **Alle `5` science-kandidater (`V3-T-0017`, `0020`, `0024`, `0028`, `0049`) og `4 / 5` kontrol-kandidater** har `cos_2d_5x11 = 0,453–0,773 < 0,85` og en tværdispersions-hældning `tilt_2row` på op til **`5,58 CCD-pixels`** hen over blot 2 dispersionsrækker — klassiske skrå kosmiske myonspor på CCD'en.
- Den sidste kontrol-kandidat (`V3-T-0005` på `HD 1461` ved `6705,085 Å`, kun `6,71σ`) har en flad `21`-rækkers kontinuum-pedestal (`far_wing_34 = 0,632 > 0,55`, mod `0,059` for en optisk Gaussisk LSF) kombineret med et skråt randtræf i kolonne `14–15`.
- **Samlet resultat efter `F1 + F2`:** **`0` kontrol-kandidater og `0` science-kandidater (`0` verificerede ETI-lasersignaler).**

---

## 5. Astrofysiske `8σ` øvre grænser for optiske ETI-lasersendere (`10` stjerner, `3800–6900 Å`)

Ud fra den empirisk målte residualstøj i hvert af de `8` kalibrerede bølgelængdebånd (`3825,4–6815,5 Å`), Gaia DR3 $G$-magnituder, $T_{\mathrm{eff}}$ og parallakseafstande ($15,21–46,30\,\mathrm{pc}$) fastsætter `STAR_UPPER_LIMITS_80.csv` fysiske `8σ` øvre grænser for monokromatiske optiske sendere rettet mod Solsystemet (for en diffraktionsbegrænset senderåbning $D_{\mathrm{tx}} = 10\,\mathrm{m}$ med forstærkning $G_{\mathrm{tx}} = (\pi D_{\mathrm{tx}} / \lambda)^2$):
- **Spektral ækvivalentbredde $\mathrm{EW}_{8\sigma}$:** **`1,68 mÅ` til `23,39 mÅ`** (median **`3,81 mÅ`**; skarpest på den klare `G0V`-stjerne `HD 65907` ved `16,17 pc` med `1,68 mÅ` ved `5178,4 Å`).
- **Indfaldende linjeflux $F_{\mathrm{lim},8\sigma}$:** **`1,43 × 10⁻¹⁴` til `1,06 × 10⁻¹³ erg cm⁻² s⁻¹`**.
- **Nødvendig udstrålet lasereffekt $P_{10\,\mathrm{m},8\sigma}$:** **`17,30 kW` til `201,41 kW`** (median på tværs af alle `80` stjerne-bånd-celler: **`46,99 kW`**; bedst ved `4233,2 Å` på `HD 43162` [`16,70 pc`] med **`17,30 kW`** og `HD 65907` [`16,17 pc`] med **`19,20 kW`**).

---

## 6. Dokumenterede begrænsninger og konkret opgradering til `HARPS_ECELLE_V3.1` (Trin 3)

1. **Pligtfaktor (duty cycle) og strålebredde:** De fastlagte `17,3–201,4 kW`-grænser gælder kontinuerlige eller højrepetitive optiske lasere, der er aktive under de konkrete `5` observationsvinduer pr. stjerne (`2020–2021`) og rettet mod Jorden inden for diffraktionskeglen $\theta \approx \lambda / D_{\mathrm{tx}} \approx 0,01''$. Sjældne kortpuls-fyr med lav pligtfaktor udelukkes ikke af arkivspektroskopi med `5` epoker.
2. **Direkte opgradering til `HARPS_ECELLE_V3.1` før skalering i Trin 3 (`D080`):**
   - **Indbyg `Test F1` + 2D $(T_{\mathrm{eff}}, [\mathrm{M/H}])$-interpoleret stjerneatlas direkte i Kanal P's Gate G1:** Ved at kræve `fn_pk3 >= 1,02` (eller modellere differentiel metallinje-dybde som funktion af både $T_{\mathrm{eff}}$ og $[\mathrm{M/H}]$) elimineres alle `166` sub-kontinuum absorptions-mismatches allerede i 1D-screeningen.
   - **Opgradér `Gate G5` fra `1 × 11` til fuld `5 × 11` separabel 2D fiber-LSF + 3-rækkers centroid-stationaritet (`Test F2`):** Eliminerer samtlige skrå kosmiske myonspor ved selve den automatiske råbilled-gate, mens `~85 %` følsomhed for ægte fiber-lasere bevares ned til `3825 Å`.
   - **Trin 3 (`D080`):** Anvend den opgraderede `HARPS_ECELLE_V3.1`-pipeline på en større volumenbegrænset kohorte (`50–100` nære FGKM- og kendte exoplanet-værtsstjerner i ESO `HARPS` + VLT `ESPRESSO` ved $R \approx 140\,000$), hvor `8,2 m` VLT-opsamlingsarealet vil presse sendereffekt-grænsen ned mod få kilowatt.
