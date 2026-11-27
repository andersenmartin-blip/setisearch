# Spor N9 — Ren Mælkevej: *Gaia DR3 NSS*, *Brandt HGCA* & *Kervella PMa* Astrometrisk Søgning Efter Mørke Ledsagere (`996` Stjerner)

**Kampagne-ID:** `SPOR_N9_MILKY_WAY_GAIA_DR3_DARK_COMPANION_AND_ASTROMETRY` · **Dato:** 27. november 2026  
**Status:** **AFSLUTTET (`0` verificerede Mælkevejs-ETI · `N9_GAIA_DARK_COMPANIONS_AUDIT: 12/12 PASSED` · `external_contacts == 0`)**

---

## 1. Resumé

**Spor N9** forener hele **Gaia DR3 Non-Single-Star (`I/357/tbooc`, `tbosb1`, `acc7`, `acc9`)** med to uafhængige 25-årige **Hipparcos–Gaia** egenbevægelses-accelerationskataloger (**Brandt HGCA `J/ApJS/254/42`** og **Kervella `J/A+A/657/A7/tablea1`**) på alle **`996` rene Mælkevejs-masterstjerner** ($d \le 50\text{ kpc}$ fra `table1_master_catalog_1083stars.csv`, med alle `87` ekstragalaktiske kilder udeladt) plus de tre galaktiske sorte-huls-benchmarks **`Gaia BH1`**, **`Gaia BH2`** og **`Gaia BH3`**:

- **Astrometrisk dækning (Ren Mælkevej):** **`968/996`** matchede i `Gaia DR3`, **`529`** med fuld **25-årig Hipparcos–Gaia dynamisk basislinje** (`509` `HGCA` + `524` `Kervella`), og **`6`** med fulde `DR3 NSS` to-legeme-/accelerationsløsninger.
- **Prospektiv blind låsning:** `METHOD_LOCK.json` + `n9_gaia_dark_companion_analyzer.py` (`f3824e4d4413452e221adb6deb8ea2ff4f6eb189d15bb6676eddc02d1f628025`) låst kl. **`2026-11-27T19:13:49.643707+00:00`** før Stage 1 (`19:15:26.457346+00:00` for Stage 2).
- **Positiv Sort-Huls-Benchmark (`Gaia BH1`):** Blindt genfundet i Port D1 (`N9_DARK_MASS_ORBIT`: $P = 185{,}766\text{ d}$, $M_{2,\mathrm{proxy}} = 11{,}09\,M_\odot$), mens **`0/996`** af de rene Mælkevejsstjerner overskrider Chandrasekhar-/mørk-kompakt-objekt-porten D1 ($M_2 \ge 1{,}4\,M_\odot$ eller $f(M) \ge 0{,}5\,M_\odot$).
- **Stage 2 → Stage 3 Veto (`127` Science PMa/RUWE-triggere $\rightarrow$ `0` Mørke ETI):**
  - `35` opløste/`NSS`/multi-peak stjernebinære · `31` bekræftede exoplaneter & brune dværge (`GJ 229 B+Ca/b`, `AF Lep`, `HD 13724`, `HD 206893`, `GJ 676 A`, `14 Her`, `tau Boo`) · `25` kalibreringskontroller (`AM Her`, `GK Per`, `R Aqr`, `CH Cyg`, `HM Sge`) · `23` lysende hovedseriedobbelte (`61 Cyg B`, `mu Cas`, `mu Her`, `xi Boo A`, `41 Ara`) · `12` unge skiver / AGB fotocenter-jitter (`T Tau`, `RY Tau`, `GW Ori`, `VY CMa`, `IK Tau`, `R Cas`) · `1` kendt perspektiv-/høj-PM-kalibrator (`van Maanen 2 / VMA2`, `M2_10au = 0,8 M_Jup`, `Kervella SNR = 2,07`) $\rightarrow$ **`0` verificerede mørke ETI-ledsagere**.
- **1.200 Injektioner & Bayesianske Nullgrænser (`0` ETI):**
  - `1.200` astrometriske injektioner giver **`80,33 %`** (`D1` $M_2 \ge 0{,}5\,M_\odot$), **`100,0 %`** (`D2` `SNR >= 25`) og **`82,67 %`** (`D3` `RUWE >= 2,5`), samlet **`87,67 %`** ($N_{\mathrm{eff}} = 873{,}19$).
  - **Rene Mælkevejsstjerner (`996` raw / `873,19` eff.):** **Jeffreys $f_{95} = 0{,}1926\,\%$ (`raw`) / $0{,}2197\,\%$ (`eff`)** · Uniform `0,3000 %` / `0,3421 %`.
  - **25-års `HGCA/Kervella`-kohorte (`n=529`):** Jeffreys **`0,3623 %`** · **Exoplanet-værter (`n=327`):** **`0,5852 %`** · **`< 10 pc` (`n=267`):** **`0,7161 %`**.

---

## 2. Forensisk Veto-Oversigt (`128 -> 1 Benchmark + 0 Mørke ETI`)

| Forensisk Klasse | Antal | Fysisk Forklaring | Status |
| --- | --- | --- | --- |
| `RESOLVED_OR_NSS_LUMINOUS_BINARY` | `35` | `ipd_frac_multi_peak >= 2`, `non_single_star > 0` eller `Gaia acc7/9 / SB1` | `VETOED_ASTROPHYSICAL_COMPANION_OR_INSTRUMENTAL` |
| `KNOWN_EXOPLANET_OR_BROWN_DWARF_PULL` | `31` | Eksisterende `pscomppars`-exoplaneter eller brune dværge | `VETOED_ASTROPHYSICAL_COMPANION_OR_INSTRUMENTAL` |
| `CALIBRATION_CONTROL_BINARY_OR_EVOLVED` | `25` | `CONTROL`-kontroller (`CV`, symbiotiske, binære) | `VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL` -> `VETOED_ASTROPHYSICAL_COMPANION_OR_INSTRUMENTAL` |
| `KNOWN_LUMINOUS_STELLAR_BINARY_OR_SATURATION` | `23` | Kendte dobbeltstjerner / lysstærke `G < 6,5` | `VETOED_ASTROPHYSICAL_COMPANION_OR_INSTRUMENTAL` |
| `YSO_DISK_OR_AGB_PHOTOCENTER_JITTER` | `12` | Konvektive AGB-skaller (`VY CMa`, `IK Tau`) & unge YSO-skiver | `VETOED_ASTROPHYSICAL_COMPANION_OR_INSTRUMENTAL` |
| `HIGH_PMA_LOW_MASS_COMPANION_CANDIDATE` | `1` | `VMA2` (`van Maanen 2`: `3,0"/år` perspektivisk høj-PM, `0,8 M_Jup`, `SNR=2,07`) | `VETOED_ASTROPHYSICAL_COMPANION_OR_INSTRUMENTAL` |
| `POSITIVE_BH_BENCHMARK_RECOVERED` | `1` | `Gaia BH1` (`185,8 d`, `11,09 M_sun` proxy) | `BENCHMARK_RECOVERED` |
| **Verificerede Mørke ETI-Ledsagere** | **`0`** | `0/996` Mælkevejs-science i `Gate D1` ($\ge 1{,}4\,M_\odot$) | **`0` ETI** |

---

## 3. Figurer, Audit & Reproducerbarhed

- **Visuelt verificerede 300-DPI PNGs (`figN9_01`–`figN9_06`):** `Gaia DR3` CMD & `25`-års `M2(10 AU)`, `HGCA chi2` vs `Kervella SNR` & `RUWE`, `Gaia NSS` mørk-masse-diagram (`Gaia BH1` vs Mælkevej), veto-tragt, `1.200` injektioner & $f_{95}$ samt komplet Mælkevejs-syntese (`N1–N5 + N7–N9`).
- **Ren-stdlib Audit (`/usr/bin/python3 -S scripts/audit_n9_gaia_dark_companions.py`):** **`N9_GAIA_DARK_COMPANIONS_AUDIT: 12/12 PASSED`** (`external_contacts == 0`).
- **Lokal arkivpakke:** `archives_n9/SETI_N9_GAIA_DR3_DARK_COMPANIONS_2026-11-27.zip`.
