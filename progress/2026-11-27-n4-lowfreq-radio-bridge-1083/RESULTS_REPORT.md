# Spor N4 Resultatrapport: All-Sky Low-Frequency Radio Bridge (54 MHz – 3.0 GHz + CHIME/FRB Catalog 1) over alle 1.083 Master-Stjerner

**Kampagne-ID:** `SPOR_N4_LOWFREQ_RADIO_BRIDGE_1083`  
**Prospektivt låst:** `2026-11-27T11:25:35.601774+00:00` (`METHOD_LOCK.json` + `IMPLEMENTATION_LOCK.json`)  
**Stage 2 & Stage 3 afsluttet:** `2026-11-27T12:00:02+00:00` (`0` verificerede teknosignaturer, `external_contacts == 0`)  
**Låst ren-stdlib analysator SHA-256 (`n4_radio_analyzer.py`):** `8ad201a645d02d30327755bdfdabc5c3995da39c79dfce57e6bfd9c058ef1a77`  
**`METHOD_LOCK.json` SHA-256:** `92ca9cf77eead96ddc2a8e3063e5fd4df03769024584a3287aa394e4d22ea2c0`  
**`IMPLEMENTATION_LOCK.json` SHA-256:** `0c2055e70414bbefe6ec2c46916e72f3e0089a67fa0e77018c7e92aca01f99b5`  

---

## 1. Hovedkonklusion

Spor N4 forbinder **alle `1.083` stjerner** i hovedkataloget (`table1_master_catalog_1083stars.csv`: `787` Science-mål + `296` astronomiske/extragalaktiske kontrolmål; heraf `267` `< 10 pc`) til **9 levende kontinuerlige radioundersøgelser** fra `54 MHz` til `1,4 GHz` (`ASTRON LoLSS/LoTSS DR3/TGSS`, `CSIRO RACS-low/mid`, `NASA HEASARC NVSS/FIRST/SUMSS/VLSSr`) plus **`CHIME/FRB Catalog 1` (`400–800 MHz`)** og direkte **`VLASS 1.2` (`3,0 GHz`) FITS-billedfotometri**.

- **100,0 % all-sky dækning (`1.083 / 1.083` stjerner):** Hver eneste stjerne i kataloget dækkes af **mindst `3`** og **median `5`** uafhængige radioundersøgelser.
- **Pankromatisk spændvidde udvidet til `71,9233` EM-oktaver:** Fra **`54,0 MHz`** (*LOFAR LoLSS*) til **`1,000 PeV`** (*1LHAASO*) — en nettotilvækst på **`+9,3413` oktaver** ud over `V7.0`'s `62,582` oktaver svarende til et energiforhold på **$4{,}4778 \times 10^{21}$** på tværs af alle 1.083 systemer (sammen med `0,1 TeV–10 PeV` *IceCube*-neutrinoer samt optisk/NIR og X-ray spektropolarimetri).
- **Stage 2 → Stage 3 Veto (`489` match-rækker / `172` stjerner → `0` ETI):**
  - **`104` Kontrolbenchmarks** (`3C 84` @ `0,00"`, `BL Lac` @ `0,07"`, `OJ 287` @ `0,106"`, `Mrk 501` @ `0,135"`, `NGC 4736`, `NGC 7009`, `PKS 2155-304` m.fl.) genfindes med `100 %` positiv præcision.
  - **`68` radiomatchede Science-stjerner → `0` ETI:** **`37`** kendte aktive koronale / flare / RS CVn-stjerner (`V374 Peg` @ `0,088"` / `VLASS SNR 7,25`, `AR Lac` @ `0,137"` / `SNR 46,6`, `CW UMa` @ `0,224"` / `SNR 7,12`, `HR 1099` @ `0,782"` / `SNR 29,96`, `GJ 1151`, `DG CVn`, `YZ CMi`, `AT Mic`, `EQ Peg`, `AB Dor`, `AP Col`, `AD Leo` m.fl.), **`16`** kendte YSO / protostjerne-jets / symbiotiske & udviklede stjerner (`T Tauri` @ `0,078"` / `SNR 17,64`, `L1551 IRS 5`, `IRAS 16293-2422`, `NGC 2071 IR`, `DG Tau`, `W3(OH)`, `CH Cyg`, `Antares` m.fl.), og **`15`** baggrunds-extragalaktiske radiokilder (`Hephaistos Object D` @ `2,369"` i `LoTSS DR3` `1,77 mJy` med `VLASS SNR 1,71`, `61 Vir / HD 115617` @ `19,423"` med synkrotronindeks $\alpha = -0{,}674$, plus `13` feltforskudte kilder ved `8,74"–17,19"` alle uden `3 GHz`-modpart i `VLASS`).
- **Direkte `VLASS 1.2` (`3,0 GHz`) FITS-fotometri (`74/75` gyldige FITS-utsnit):** Median RMS = **`0,1412 mJy/beam`**, ned til `2,9681e5 W Hz⁻¹` (`2,9681e14 W` per GHz) $5\sigma$ smalbands-EIRP på nærmeste stjerner, og **`0/22` detektioner (`>= 4σ`)** på nære `< 10 pc` umatched'e kontrolstjerner.
- **`CHIME/FRB Catalog 1` (`26/26` overlap afvist → `0` stjerne-FRB'er):** Mindste observerede DM = **`176,3 pc cm⁻³`**, svarende til **`32,39×` til `4.078,54×`** overskud (*Procyon*) over konservativ galaktisk forgrundssøjle ($0{,}05\,d_{\text{pc}}$).
- **`1.200` syntetiske injektioner & Bayesianske nulgrænser ($k=0$):** **`100,0 %`** genfinding for $S_\nu \ge 2{,}0\text{ mJy}$ (`67,0 %` samlet over `0,3–15,0 mJy`). Eksakt Jeffreys $\mathrm{Beta}(0,5, N+0,5)$ $95\,\%$ øvre grænse når **`0,1772 %`** (`0,2760 %` Uniform) for alle `1.083` stjerner, **`0,2437 %`** (`0,3794 %` Uniform) for `787` Science-stjerner, og **`0,7161 %`** for `267` `< 10 pc`-stjerner.

---

## 2. Live Radioundersøgelser & Dækning på 1.083 Stjerner

| Survey | Frekvens | Dækning (stjerner) | Rå-matches (Stage 1) | Matchradius (låst) | $5\sigma$ Reference (mJy) | Arkivkilde |
| --- | --- | --- | --- | --- | --- | --- |
| **LoLSS** | `54,0 MHz` | `12` (empirisk footprint) | `4` (`< 180"`) | `30"` | `20,0` | ASTRON TAP (`lolss.source_catalog`) |
| **VLSSr** | `74,0 MHz` | `774` (`Dec >= -30°`) | `48` | `45"` | `500,0` | NASA HEASARC TAP (`vlssr`) |
| **LoTSS DR3** | `144,0 MHz` | `533` (empirisk `mosaics`) | `471` (`< 72"`) | `15"` | `0,50` | ASTRON TAP (`lotss_dr3.main_sources`) |
| **TGSS ADR1** | `150,0 MHz` | `956` (`Dec >= -53°`) | `121` (`< 108"`) | `25"` | `17,5` | ASTRON TAP (`tgssadr.main`) |
| **SUMSS** | `843,0 MHz` | `309` (`Dec <= -30°`) | `19` | `25"` | `6,0` | NASA HEASARC TAP (`sumss`) |
| **RACS-low** | `888,0 MHz` | `978` (`Dec <= +49°`) | `509` (`< 54"`) | `15"` | `1,50` | CSIRO CASDA TAP (`AS110.racs_low2_v02`) |
| **RACS-mid** | `1367,5 MHz` | `978` (`Dec <= +49°`) | `124` (`< 54"`) | `15"` | `1,00` | CSIRO CASDA TAP (`racs_mid_25arcsec`) |
| **NVSS** | `1400,0 MHz` | `866` (`Dec >= -40°`) | `141` | `25"` | `2,25` | NASA HEASARC TAP (`nvss`) |
| **FIRST** | `1400,0 MHz` | `242` (empirisk footprint) | `65` | `10"` | `0,75` | NASA HEASARC TAP (`first`) |
| **CHIME/FRB Cat 1** | `400–800 MHz` | `605` (`Dec >= -11°`) | `26` ($3\sigma$-ellipse) | $3\sigma$ (min `0,5°`) | Transient (Jy ms) | VizieR (`J/ApJS/257/59/table2`) |
| **VLASS 1.2** | `3000,0 MHz` | `74/75` cutouts | Direkte FITS-fotometri | `3"x3"` boks (`0,6"/px`) | Median `0,71` (`0,141` RMS) | Legacy Survey Viewer FITS |

---

## 3. Kalibrerede Injektionsforsøg & Bayesianske $f_{95}$ Øvre Grænser ($k=0$ ETI)

| Fluxbin $S_\nu$ (`mJy`) | Forsøg | Genfundet | Komplethed | | Kohort ($k=0$ ETI) | $N_{\text{eff}}$ | Jeffreys $f_{95}$ | Uniform $f_{95}$ | Clopper-Pearson $f_{95}$ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0,3` | `200` | `2` | `1,0 %` | | **All Master Stars ($S \ge 2\text{ mJy}$)** | `1.083,0` | **`0,1772 %`** | `0,2760 %` | `0,2762 %` |
| `0,5` | `200` | `53` | `26,5 %` | | **Science Stars ($S \ge 2\text{ mJy}$)** | `787,0` | **`0,2437 %`** | `0,3794 %` | `0,3799 %` |
| `1,0` | `200` | `149` | `74,5 %` | | **Solar Neighborhood (`< 10 pc`)** | `267,0` | **`0,7161 %`** | `1,1116 %` | `1,1157 %` |
| `2,0` | `200` | `200` | **`100,0 %`** | | **LoTSS DR3 (`144 MHz`, `0,5 mJy`)** | `533,0` | **`0,3595 %`** | `0,5594 %` | `0,5605 %` |
| `5,0` | `200` | `200` | **`100,0 %`** | | **RACS (`888/1367,5 MHz`)** | `978,0` | **`0,1962 %`** | `0,3055 %` | `0,3058 %` |
| `15,0` | `200` | `200` | **`100,0 %`** | | **CHIME/FRB (`400–800 MHz`)** | `605,0` | **`0,3168 %`** | `0,4931 %` | `0,4939 %` |

---

## 4. Figurer & Reproducerbarhed

Alle 6 figurer (300 DPI PNG) er inspiceret og verificeret i `results/VISUAL_REVIEW_N4.json`:
1. `figures/figN4_01_panchromatic_em_ladder_72oct.png` — `71,9233`-oktavers pankromatisk EM-stige (`54 MHz` til `1,000 PeV`).
2. `figures/figN4_02_allsky_radio_coverage_1083.png` — All-sky Aitoff-dækning af `1.083` stjerner (`3–9` surveys).
3. `figures/figN4_03_eirp_sensitivity_vs_distance.png` — `5σ` EIRP-grænser mod afstand & Kardashev-skalaer (`+ VLASS FITS`).
4. `figures/figN4_04_vlass_cutouts_and_vetting_funnel.png` — `6` direkte `VLASS 1.2` `3,0 GHz` FITS-utsnit & Stage 3 veto-tragt (`0` ETI).
5. `figures/figN4_05_injection_completeness_and_bayesian_f95.png` — `1.200`-forsøgs injektionskurve & Bayesianske $f_{95}$-grænser.
6. `figures/figN4_06_spectral_index_and_chime_dm_veto.png` — Radiospektralindeks $\alpha$ (`N=112`) & `CHIME/FRB` DM-eksklusion (`32×–4.079×`).

Lokalt rå- & beregningsarkiv (inkl. `74` `VLASS` FITS-utsnit): `archives_n4/SETI_N4_LOWFREQ_RADIO_BRIDGE_1083_2026-11-27.zip`.  
Ingen eksterne tidsskriftsuploads er foretaget (`external_contacts == 0`).
