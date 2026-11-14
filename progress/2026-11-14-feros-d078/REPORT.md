# D078 — Empirisk stellar hvileramme, inter-ordens bølgelængde-/blaze-diagnose og samlet kryds-instrument syntese for HD 43629

**Dato:** 2026-11-14  
**Fase:** `work_feros_20261114_d078_stellar_restframe_and_hd43629_synthesis` (`D078`)  
**Status:** Gennemført, uafhængigt stdlib-revideret (`python -S audit.py` = `PASS`) og videnskabeligt afsluttet for `HD 43629` (`0` kvalificerede laserkandidater).

---

## 1. Formål og prospektiv metodisk låsning

Efter metadata- og proveniens-gaten i `D077` stod tre sammenhængende astrofysiske spørgsmål tilbage for at kunne lukke hele `HD 43629`-undersøgelsen (`TOI-880` / `TIC 34077285`, K-dværg med transiterende exoplaneter) rent og samlet:

1. **Empirisk stellar hvileramme i FEROS (november 2019):** Hvad er `HD 43629`'s faktiske barycentriske radialhastighed i de fem FEROS-epoker (`F1`–`F5`), målt direkte på isolerede fotosfæriske absorptionslinjer i de eksisterende `D071`-profiler uden ny arkivhentning og uden dobbelt `BARYCORR`, og stemmer den med Gaia DR3 (`+33.84 ± 0.45 km/s`)?
2. **Fysisk forklaring på `D075`–`D076`'s `1.45 km/s` ordensafvigelse ved `D002-0061`:** Skyldtes forskellen mellem `HDU 29`, `HDU 30` og det sammenlagte spektrum `HDU 0` i enkelt-sidebåndsmaskerne (`BLUE` vs. `RED`) en reel bølgelængde-fejlregistrering mellem echelle-ordenerne, eller skyldtes den kombinationen af `HD 43629`'s systemhastighed (`~+33.8 km/s`), atmosfæriske telluriske $\mathrm{H_2O}$-linjer og echelle-blaze-hældning nær ordensranden af `HDU 30`?
3. **5-epoke stellar hvileramme-coadd og samlet syntese (HARPS 2021 + FEROS 2019):** Viser det 5-epoke-middelvægtede FEROS-spektrum — justeret til `HD 43629`'s empiriske stellare hvileramme — nogen vedvarende smal emissionskomponent ved hvilebølgelængderne for `D002-0061`, `D002-0063` og `D002-0071`?

Før en eneste `.npz`-fluxprofil blev åbnet til linjefitning, låste `freeze_method.py` `METHOD_LOCK.json` (`d8c3e3c7ac8834224f2fdde55d08219f64c32486215e0a97b27733e4f3df7bd0`, `267` input-hashes) med 10 autoritative laboratoriebølgelængder i tør luft (NIST ASD / VALD / Sousa-Neves HARPS FGK-linjeliste / HITRAN $\mathrm{H_2O}$), eksakt speciel-relativistisk rapiditet ($\eta = \operatorname{atanh}(v/c)$), fast lokalt vindue $\pm 0.33\,\mathrm{\AA}$ og 401-punkts hastighedsgrid ($\pm 8.0\,\mathrm{km/s}$ i trin på $0.04\,\mathrm{km/s}$ med lukket 5-punkts parabolsk forfining).

---

## 2. Hovedresultater

### 2.1 Del 1 & 3A — Empirisk stellar radialhastighed for HD 43629 (`F1`–`F5`)

Samtlige `810` profil-ankermålinger over de `240` `D071`-profiler (`324.810` lineære mindste-kvadraters fits) konvergerede til indre absorptionsminima (`693 STRONG_CLEAN_ABSORPTION`, `117 WEAK_OR_SHALLOW_ABSORPTION`, **`0` grænse-hits eller ikke-absorptioner**). Alle 5 primære rene fotosfæriske ankre (`Fe I 6546.238 Å`, `Ni I 4829.023 Å`, `V I 5727.048 Å`, `Fe I 5731.762 Å`, `Fe I 5732.296 Å`) opnåede `STRONG_CLEAN_ABSORPTION` i hver eneste epoke:

| Epoke | UTC start (`DATE-OBS`) | Nominel `BARYCORR` (`km/s`) | Empirisk stellar $v_{\mathrm{bary}}$ (`km/s`) | Linje-til-linje SD / SEM (`km/s`) | Afvigelse fra Gaia DR3 (`km/s`) | Tellurisk $\mathrm{H_2O}$ $v_{\mathrm{topo}}$ (`km/s`) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `F1` | `2019-11-04T07:39:37.309` | `+19.0142` | **`+33.4865`** | `0.2015 / 0.0901` | `-0.3535` | `-0.5329` |
| `F2` | `2019-11-07T07:46:17.029` | `+18.2126` | **`+34.0390`** | `0.1913 / 0.0856` | `+0.1990` | `+0.4117` |
| `F3` | `2019-11-08T06:31:09.737` | `+18.0792` | **`+33.9691`** | `0.2706 / 0.1210` | `+0.1291` | `+0.2255` |
| `F4` | `2019-11-10T05:01:01.524` | `+17.6692` | **`+33.7507`** | `0.1651 / 0.0738` | `-0.0893` | `-0.4876` |
| `F5` | `2019-11-14T06:29:26.536` | `+16.3340` | **`+33.8529`** | `0.1877 / 0.0839` | `+0.0129` | `+0.1708` |
| **Middel (`F1`–`F5`)** | — | — | **`+33.8196`** | **Inter-epoke SD `0.2164`** (`ptp 0.5526`) | **`-0.0204`** (`-20.4 m/s`) | — |

- Den empiriske 5-epoke middelværdi **`+33.820 km/s`** stemmer med Gaia DR3 (`+33.84 ± 0.45 km/s`) inden for **`-0.020 km/s` (`0.045 σ`)** — uden nogen fri efterjustering og uden dobbelt anvendelse af `BARYCORR`.
- Epoke-til-epoke spredningen på `0.216 km/s` (`peak-to-peak = 0.553 km/s`) kvantificerer direkte den faktiske bølgelængde-/hastighedsnøjagtighed i ESO's uovervågede `fern/1.0` Phase-3 reduktion (daglig `ThAr+Ne` WLC uden simultan natlig kalibreringslampe + lavpræcisions `BARYCORR`).

### 2.2 Del 2 — Løsning af `D075`–`D076`'s `1.45 km/s` sidebåndsafvigelse og inter-ordens konsistens

Direkte sammenligning af identiske fotosfæriske ankre i overlappende echelle-ordener (`INTER_ORDER_ANCHOR_PAIRS300.csv` og `ORDER_BLAZE_RATIOS60.csv`) løser `D075`–`D076`-gåden fuldstændigt:

1. **Ingen stor bølgelængde-fejlregistrering mellem overlappende ordener:**
   - Ved `D002-0061` (`Fe I 6546.238 Å`, dybde `70–74 %`) er den absolutte hastighedsforskel $|v(\mathrm{HDU\ 30}) - v(\mathrm{HDU\ 29})|$ kun **`0.170 km/s` i middel** (`3.7 mÅ` = `0.12` sample; maks. `0.288 km/s` over alle 30 epoke/mode/flat-kombinationer; i primær `mode=1, flat=True` er middelværdien `+0.099 km/s`).
   - Ved `D002-0071` (`Fe I 5731.762 Å` i primær `mode=1, flat=True`) er forskellen `v(HDU 25) - v(HDU 24)` kun **`-0.003 km/s` i middel** (maks. `0.071 km/s` = `1.4 mÅ`)! Over alle 90 `D002-0071`-par inkl. den svagere nabolinje `5732.296 Å` i `F1` er middel $|\Delta v| = 0.178\,\mathrm{km/s}$.
   - Ved `D002-0063` (`HDU 17` vs. `HDU 0` kontrol) er forskellen eksakt **`0.000 km/s`**.
2. **Hvorfor `D075` viste op til `1.45 km/s` ordensforskel i `RED`-masken ved `D002-0061`:**
   - Ved `HD 43629`'s systemhastighed (`+33.82 km/s`, dvs. `+0.74 Å` rødforskydning ved `6550 Å`) flyttes den stærke fotosfæriske linje `Ti I 6554.23 Å` til `6554.97 Å` — **uden for** `D074`–`D076`'s faste `1–4 Å` `RED`-maske `[6551.10, 6554.10] Å`.
   - Dermed styres `BLUE`-masken `[6546.10, 6549.10] Å` af den dybe fotosfæriske linje `Fe I 6546.238 Å` (ved `6546.98 Å`, maks. skift `0.50–0.65 km/s`, lav korrelation med $\Delta\mathrm{BARYCORR}$: $r = -0.18..-0.22$), mens `RED`-masken `[6551.10, 6554.10] Å` kun rummer den svage stellare `Fe I 6551.680 Å` (`~15 %` dybde) i direkte konkurrence med atmosfærisk vanddamp **`H2O 6552.629 Å`** (ved `6552.99–6553.04 Å`).
   - Melllem `F1` og `F5` driver $\Delta\mathrm{BARYCORR} = -2.6802\,\mathrm{km/s}$ vanddamplinjen blåværts i barycentriske koordinater, samtidig med at linjens optiske dybde næsten tredobles på nat `F5` (`2019-11-14`) pga. højere luftfugtighed over La Silla. I `HDU 30` ligger `6550 Å` desuden kun `18.5 Å` fra ordenens blå start (`6531.63 Å`), hvor rå fotonflux i uflatfieldede spektre kun er **`50.1 %`** af `HDU 29` med en stejl blaze-hældning på **`+3.96 %/Å`** og forhøjet ekstraktions-ripple (mens `HDU 0` vægter `~66.1 % HDU 29 + ~33.9 % HDU 30`). Derfor korrelerer `(RED - BLUE)`-skiftet i `HDU 30` tydeligt med $\Delta\mathrm{BARYCORR}$ ($r = -0.56$, hældning `-0.48 km/s` pr. `km/s` $\Delta\mathrm{BARYCORR}$, maks. `RED`-skift `1.80 km/s`).

### 2.3 Del 3B & 4 — 5-epoke stellar hvileramme-coadd og samlet syntese for de tre HARPS-kandidater

Når de tre kandidatpositioner transformeres fra barycentriske luftbølgelængder til `HD 43629`'s empiriske stellare hvileramme ($v_{\mathrm{bary}} = +33.8196\,\mathrm{km/s}$), og alle 5 FEROS-epoker coaddes både uændret og RV-justeret hen over alle 6 `D068`-baggrundsmodeller (`36` cases i `CANDIDATE_RESTFRAME_COADD36.csv`), fås:

| Kandidat | HARPS-dato | Barycentrisk $\lambda_{\mathrm{air}}$ (`Å`) | Stellar hvileramme $\lambda_{\mathrm{rest,air}}$ (`Å`) | FEROS 5-epoke coadd primær kontrast (`1–2 Å aff`) | FEROS 5-epoke coadd spænd (alle 6 baggrunde) | Fortegnsskift over baggrunde? | Samlet kryds-instrument status (`HD43629_SYNTHESIS3.csv`) |
| :--- | :--- | ---: | ---: | ---: | ---: | :---: | :--- |
| `D002-0061` | `2021-03-05` | `6550.0950` | **`6549.3561`** | `+2.14 %` | `-1.52 %` til `+5.02 %` | **Ja** | Dumpet oprindelig HARPS rå/nativ $\rho = 0.7807 < 0.8$ (`D018`); fraværende i marts-kontroller; ingen vedvarende emission i FEROS 2019. |
| `D002-0063` | `2021-03-09` | `4826.6475` | **`4826.1030`** | `+16.90 %` | `-12.22 %` til `+37.26 %` | **Ja** | Enkelt-epoke hændelse fraværende i 4 marts-kontroller; domineret i ydre CCD-rækker af enkelt nabopixel `k2573` (`~5.380 ADU` vinduesskift i `D063`, typisk kosmisk stråle / lokal ladningsdeponering); blå COMB uvalideret; FEROS hvilebølgelængde ligger på almindelig K-dværg kontinuumtop mellem dybe metallinjer. |
| `D002-0071` | `2021-09-09` | `5730.7150` | **`5730.0686`** | `+10.97 %` | `-1.44 %` til `+19.51 %` | **Ja** | Enkelt-epoke hændelse fraværende i 6. og 18. sept.-kontroller; uforenelig med valideret 2D fiber-PSF (`60.9–65.3 ADU` række-RMS = `4.9–5.6×` kontrolmedian i `D055`–`D056`); FEROS `HDU 24/25` bekræfter bølgelængdeskalaen til `<0.08 km/s` og viser almindeligt absorptionsstruktureret kontinuum med fortegnsskift. |

Figur 3 illustrerer direkte, hvorfor smalle polynomiske baggrundsringe i en kølig K-dværg kan give tilsyneladende positive procentkontraster (`+11 %` til `+37 %`) uden nogen emissionslinje: ved både `4826.103 Å` og `5730.069 Å` falder kandidatpositionen på en smal lokal kontinuumryg flankeret af dybe neutrale metal-absorptionslinjer (`Mn I`, `Cr II`, `V I`, `Fe I`), som trækker den lineære/kvadratiske baggrundsmodel ned under det sande stellare kontinuum, mens en bredere `2.0–3.0 Å` kvadratisk model vender fortegnet negativt (`-12.22 %` og `-1.44 %`).

---

## 3. Uafhængig numerisk revision og tabel-normalisering

- **`audit.py` (100 % ren Python stdlib, afviklet med `python -S` uden adgang til NumPy/SciPy):**
  - Læste alle `240` `.npz`-profiler samt `ANCHOR_GRIDS810.npz` og `COADD_PROFILES3.npz` direkte via `zipfile` + `struct` og verificerede samtlige `267` låste input-hashes.
  - Rekonstruerede alle `810 × 401 = 324.810` lineære mindste-kvadraters fits via dobbelt-ortogonaliseret Gram-Schmidt QR med `math.fsum`: maksimal afvigelse `1.84 × 10⁻¹²` i SSE, `1.13 × 10⁻¹²` i koefficienter og `3.47 × 10⁻¹⁰ km/s` i parabolsk hastighed.
  - Verificerede alle `300` inter-ordens par, `60` blaze-kvotienter, `30` sidebånds-korrelationer, `5` epoke-hvilerammer, `36` coadd-baggrundskontraster (maks. afvigelse `1.08 × 10⁻¹³` procentpoint) og `3` synteserækker.
- **Normaliseret tabelpolitik (`STATE_PRESERVATION_AUDIT.json` = `PASS`):**
  - De historiske oversigtstabeller i `D077` (`ALL37_INTERPRETATION.csv` og `FULL_SAMPLE_STATE141.csv`, `107.105` celler) bevares byte-for-byte uændrede uden at påklistre tomme FEROS-kolonner på de 104 uvedkommende stjerner; alle `D078`-resultater leveres som selvstændige, normaliserede CSV/JSON-tabeller.

---

## 4. Begrænsninger og videnskabelig status ved lukning af HD 43629

1. **Nul kvalificerede laserkandidater (`qualified_lasers = 0`):** Hverken HARPS (2021) eller FEROS (2019) indeholder en valideret, astrofysisk eller teknosignatur-kvalificeret laserlinje i `HD 43629`.
2. **Eksakt mikrofysisk årsag ikke overfortolket:** Mens både en vedvarende stellar emissionslinje og en gentagen teknosignatur er udelukket i alle kontrol- og 2019-epoker, og `D002-0063`/`D002-0071` opfører sig som lokale enkelt-eksponerings 2D-detektorhændelser (f.eks. skrå kosmiske stråler / lokalt CCD-ladningsindfald), hævdes intet definitivt partikelfysisk bevis ud over de målte 2D-residualer (`physical_origin_definitively_proven = false`).
3. **FEROS Phase-3 begrænsninger respekteret:** Manglende `TIMESYS`, udokumenterede `WLC QC`-enheder, `~77–91″` `RA/DEC`-headerafvigelse mod Gaia ICRS og fravær af rå natlige `OBJECT,WAVE`-billeder er bevaret uændret fra `D073`–`D077`.

---

## 5. Næste hovedfase — Trin 2 (`V3` kalibreret optisk detektor på ny arkivkohorte)

Med `HD 43629`-opfølgningen (`D002`–`D078`) og den oprindelige `D001`/`D002`-kø på 50 eksponeringer / 141 rå triggers fuldt afsluttet, er det naturlige **Trin 2** for det optiske spor at opbygge en prospektivt kalibreret **2D + ordens-konsistent detektor (`V3`)** før åbning af en ny kohorte af arkivstjerner:

1. **2D tværdispersions fiber-PSF gate ved selve detektionen** (eliminerer kosmiske stråler og lokale pixelhændelser som `D002-0063` og `D002-0071` straks på rå 2D-rammer).
2. **Ordens-overlap & rå fotonvarians-konsistens** i overlappende echelle-ordener fremfor blind tillid til sammenlagte 1D-spektre.
3. **Eksplicit stellar RV-forankring + tellurisk/K-dværg kontinuummaskering** baseret på erfaringerne fra `D074`–`D078`.
4. **Syntetisk laser-injektion/recovery (`FAP`-kalibrering)** på reelle kontrolrammer før ublindet kørsel på nye arkivmål.
