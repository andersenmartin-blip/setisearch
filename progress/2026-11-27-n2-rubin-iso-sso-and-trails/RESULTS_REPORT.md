# Spor N2 — Vera Rubin Interstellare Objekter (ISO), Solsystemets Anomalier (`SSOFT`) & Hurtige Optiske Spor (`faint_trails`)

**Status:** **FULDENDT & VERIFICERET (`N2_RUBIN_ISO_TRAILS_AUDIT: 12/12 PASSED` + `N1_DYSON_VASCO_AUDIT: 12/12 PASSED` + `RUBIN_V2_AUDIT: 12/12 PASSED` + `SPOR5_PUBLICATION_AUDIT: 12/12 PASSED` under `/usr/bin/python3 -S`, `0` verificerede teknosignaturer, `0` eksterne uploads, `0` ændringer til forseglede `A–AL`, Rubin eller `N1`-arkiver)**

---

## 1. Søjle N2A — Hyperbolske Baner ($e > 1{,}0$) & Ikke-Gravitationel Fysik (`JPL SBDB`)

Vi hentede hele **NASA/JPL Small-Body Database (SBDB)** for samtlige **`526` hyperbolske objekter ($e > 1{,}0$)** og samtlige **`625` asteroider med ikke-gravitationel acceleration ($A_1, A_2, A_3$)** og krydstjekkede alle **`33`** interstellare / stærkt ikke-gravitationelle kandidater ($\max|A_1, A_2, A_3| \ge 10^{-12}\,\mathrm{AU/d^2}$ eller $v_\infty \ge 10\,\mathrm{km/s}$) samt detaljerede JPL-profiler (`34` profiler):

- **Interstellare objekter ($v_\infty \ge 10{,}0\,\mathrm{km/s}$, `5/526`):**
  1. **`3I/ATLAS` (`C/2025 N1`)**: $e = 6{,}1235$, $v_\infty = 57{,}9794\,\mathrm{km/s}$, $a_{\mathrm{rad}}(1\,\mathrm{AU}) = 9{,}218\times 10^{-7}\,\mathrm{m/s^2}$ — aktiv hyperbolsk komet (`ACTIVE_HYPERBOLIC_COMET_ISO_3I`).
  2. **`2I/Borisov` (`C/2019 Q4`)**: $e = 3{,}3565$, $v_\infty = 32{,}2776\,\mathrm{km/s}$ — aktiv hyperbolsk komet (`ACTIVE_HYPERBOLIC_COMET_ISO_2I`).
  3. **`1I/'Oumuamua` (`A/2017 U1`)**: $e = 1{,}2011$, $v_\infty = 26{,}4089\,\mathrm{km/s}$, $(A/m)_{\mathrm{SRP}} = 1{,}2305\,\mathrm{m^2/kg}$ — historisk 2017 ikke-gentagende ISO/udgasning (`HISTORICAL_2017_ISO_OUTGASSING_DARK_COMET_1I`).
  4. **`C/2023 F2 (SOHO)`** & **`C/1999 U2 (SOHO)`**: 1-dags lysbue SOHO-solstrygere ($q = 0{,}034$–$0{,}049\,\mathrm{AU}$) med kunstig kortbue-$e > 1$ (`SHORT_ARC_SOHO_SUNGRAZER_SPURIOUS_E`).
  - Øvrige **`521/526`** hyperbolske objekter ($v_\infty < 10\,\mathrm{km/s}$) er planet-perturberede Oort-sky-kometer.
- **Ikke-gravitationelle asteroider (`625` objekter):**
  - **`596`** følger klassisk termisk Yarkovsky-drift ($< 10^{-12}\,\mathrm{AU/d^2}$), herunder **`2` direkte observeret i Vera Rubin `SSOFT`** (`(2015 NJ24)` med $(A/m)_{\mathrm{SRP}} = 5{,}71\times 10^{-7}\,\mathrm{m^2/kg}$ og `467336 (2002 LT38)` med $1{,}05\times 10^{-7}\,\mathrm{m^2/kg}$).
  - **`13`** meter-skala NEO'er / midlertidige minimåner (`2020 CD3`, `2006 RH120`, `2026 QQ8`, `2015 TC25`, `2020 GE`, `2021 VH2` osv.) drevet af klassisk solstrålingstryk (SRP).
  - **`1`** aktiv hovedbæltekomet (`457175 / 362P (2008 GO98)`).
  - **`14`** kendte "mørke kometer" med $\mathrm{H_2O/CO_2}$-udgasning (`2016 NJ33`, `2005 VL1`, `2013 BA74`, `2013 XY20`, `1998 KY26`, `523599 (2003 RM)` osv.).
- **Bayesiansk $f_{95}$ (`k = 0` ny ETI):** Hyperbolske ($N=526$) **Jeffreys `0,3643 %`** (`0,5668 %` Uniform); Ikke-grav. asteroider ($N=625$) **Jeffreys `0,3067 %`** (`0,4774 %` Uniform).

---

## 2. Søjle N2B — Vera Rubin `SSOFT` (`18.782` SSO'er, `1.368` med `n_obs >= 10`)

- **Modeldiagnostik:** `90,32 %` (`1.269/1.405` med finit `R`; `90,20 %` blandt `n_obs >= 10`) af `SHG1G2`-fit lander på nedre optimizer-grænse `R = 0,30`, hvilket dokumenteres som modelforhold snarere end fysisk elongation.
- **`1.200` syntetiske injektionsforsøg** (`100` reelle `SSOFT`-objekter $\times$ `12` amplituder):
  - **Fotometriske glint/puls-afvigelser ($\Delta m \ge 1{,}0\,\mathrm{mag}$):** **`86,25 %`** genfinding ($N_{\mathrm{eff}} = 1.179{,}9$).
  - **Astrometrisk ikke-gravitationel drift ($\delta_{\mathrm{ast}} \ge 0{,}20''$):** **`100,00 %`** genfinding ($N_{\mathrm{eff}} = 1.368{,}0$).
- **Fuld Stage 3-vetting af samtlige `77/77` udløste afvigere** (`2.156` reelle Rubin-detektioner hentet via `/api/v1/sso` + JPL `SBDB` + `18` FITS-cutouts på top `6`):
  - **`47/47`** astrometriske triggere (`2013 RM72`, `2004 VL137`, `2017 BS269`, `2023 SO29` osv.): **`KNOWN_SSO_EPHEMERIS_OR_ORBIT_ARC_RESIDUAL`** (kort observationsbue / kendt baneusikkerhed i efemeriden).
  - **`18/77`** fotometriske triggere (`1998 FG32`, `2003 AN29`, `2004 VN111` osv.): **`MULTIBAND_OUTLIER_OR_EDGE_BADPIX_IN_SHG1G2`** (bl.a. farvetrin i `u`-båndet på ~21 mag vs. `g/r/i/z` ~18–19,5 mag).
  - **`12/77`** fotometriske triggere: **`ROTATING_ELONGATED_ASTEROID_LIGHTCURVE_MODULATION`**.
- **Bayesiansk $f_{95}$ (`k = 0` ETI):** Fotometrisk **Jeffreys `0,1626 %`** (`0,2534 %` Uniform); Astrometrisk **Jeffreys `0,1403 %`** (`0,2186 %` Uniform).

---

## 3. Søjle N2C — Vera Rubin `faint_trails` (`113` Spor + `IMCCE SkyBoT` + `60` FITS-Cutouts)

- Samtlige **`113/113`** `faint_trails` i Fink LSST bevæger sig mellem **`1,2853` og `6,6954 deg/dag`** (median **`3,1836 deg/dag`**, `0` `glint_trail = True`), dvs. rent solsystem/NEO-regime (`50×–10.000×` langsommere end `GEO` ved `360 deg/dag` og `LEO > 40.000 deg/dag` $\rightarrow$ **`0` kunstige LEO/GEO-satellitter**).
- **Stage 3-vetting af alle `113/113` spor (`60` N2C + `18` N2B = `78` ægte Rubin FITS-cutouts analyseret 2D-morfologisk):**
  - **`12`** linkede Rubin `ssObjectId`-kontrolspor (median `a/b = 2,163`).
  - **`6`** hidtil ulinkede `faint_trails` blev via **IMCCE `SkyBoT`** (observatorium `X05`) direkte identificeret som kendte asteroider: bl.a. **`2021 VJ108`** (`2` spor ved `5,62` & `5,52 deg/d`), **`447084 (2004 TX43)` / `188548 (2004 SW39)`**, **`2019 SL27`**, **`86225 (1999 TV97)`** og **`2015 TF415` / `2012 DN31`**.
  - **`12`** rene, skarpe enkeltoptagelses-spor i tomme `Template`-cutouts (`diffSNR = 6,3–24,3σ`, `tmplSNR <= 2,7σ`, median `a/b = 3,838` op til `6,475`) + **`77`** øvrige rene enkeltoptagelsesspor (`rel >= 0,70`) + **`6`** lav-pålidelighedsfiltrerede spor (`< 0,70`).
- **Bayesiansk $f_{95}$ (`k = 0` ETI):** **Jeffreys `1,6817 %`** (`2,5936 %` Uniform, `2,6163 %` Clopper–Pearson).

---

## 4. Figurer, Arkiv & Revisioner (`12/12 PASSED`)

- **6 Visuelt Godkendte 300-DPI Figurer (`figN2_01–figN2_06`):** [`VISUAL_REVIEW_N2.json`](results/VISUAL_REVIEW_N2.json).
- **Ren-Stdlib Revision (`/usr/bin/python3 -S`):** [`audit_n2_rubin_iso_trails.py`](scripts/audit_n2_rubin_iso_trails.py) $\rightarrow$ **`N2_RUBIN_ISO_TRAILS_AUDIT: 12/12 PASSED`**, samt samtidig bekræftelse af **`N1_DYSON_VASCO_AUDIT: 12/12 PASSED`**, **`RUBIN_V2_AUDIT: 12/12 PASSED`** og **`SPOR5_PUBLICATION_AUDIT: 12/12 PASSED`**.
- **Fuld Arkivpakke (`archives_n2/`):** `SETI_N2_RUBIN_ISO_SSO_TRAILS_2026-11-27.zip` (`10,363,471 B`, SHA-256 `8a65f6758761c926b9ddcedc10c0cc176c6eb13153adf4b75253956dfa6418d3`).
