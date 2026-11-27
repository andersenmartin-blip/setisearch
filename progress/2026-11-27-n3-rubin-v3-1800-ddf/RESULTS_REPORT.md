# Spor N3 — Vera Rubin Observatory V3 Skaleret DDF-Kampagne (`1.800` Nul-Overlap Gaia-Stjerner + Opgraderet Krydsstrøm-Detektor)

**Status:** **FULDENDT & VERIFICERET (`N3_RUBIN_V3_AUDIT: 12/12 PASSED` + `N2_RUBIN_ISO_TRAILS_AUDIT: 12/12 PASSED` + `N1_DYSON_VASCO_AUDIT: 12/12 PASSED` + `RUBIN_V2_AUDIT: 12/12 PASSED` + `SPOR5_PUBLICATION_AUDIT: 12/12 PASSED` under `/usr/bin/python3 -S`, `0` verificerede teknosignaturer, `0` eksterne uploads, `0` ændringer til forseglede `A–AL`, Rubin V2, `N1` eller `N2`-arkiver)**

---

## 1. Nul-Overlap `1.800`-Stjerners Kohorte & Prospektiv Lås (`N3_COHORT_1800_FROZEN.csv`)

- Vi ekskluderede prospektivt samtlige **`530` tidligere anvendte Rubin-identiteter** (`210` fra `work_rubin_20261102` + `300` fra Spor R1 + `20` fra Spor R1-kontroller) på både `diaObjectId` og `gaia_source_id`.
- Ud fra Gaia DR3-isolerede punktstjerner (`sep <= 1,0"`, ingen Gaia-nabo `<= 3,0"`, `16,0 <= G <= 21,0`, `ruwe < 1,4`, `max_band_ndata >= 8`) fastlåste vi præcis **`1.800` helt nye DDF-stjerner** (`COSMOS`: **`737`**, `EDFS_B`: **`1.063`**) og forseglede `rubin_v3_detector.py` + kohorte i [`METHOD_LOCK.json`](results/METHOD_LOCK.json) & [`IMPLEMENTATION_LOCK.json`](results/IMPLEMENTATION_LOCK.json) før al Stage 2-fotometrihentning.
- Live Fink Vera Rubin LSST-hentning over tvungen IPv4 (`72` sekventielle batches $\times 25$):
  - **`/api/v1/sources`:** **`105.040` rækker** (`74,27 MB`) på **`1.800/1.800`** stjerner (`29.812` rene; **`572` LONO-evaluérbare stjerner** / `8.340` LONO-epoker, vs. `85` i R1).
  - **`/api/v1/fp` (forced photometry):** **`392.451` rækker** (`89,53 MB`) på **`1.793/1.800`** stjerner (**`1.555` LONO-evaluérbare stjerner** / `277.314` LONO-epoker, vs. `254` i R1).

---

## 2. V3 Krydsstrøm- & Astrometrisk Detektor (`152 -> 6 -> 2 -> 0 ETI`)

Den opgraderede V3-detektor demonstrerer markant falsk-positiv-reduktion over R1/V2 på de samme fysiske tærskler (Dim $\ge 0{,}30\,\mathrm{mag}, Z \ge 5{,}0$; Flash $\ge 0{,}50\,\mathrm{mag}, Z \ge 6{,}0$):

1. **Rå V2-style `/sources`-triggere:** **`152` epoker** (`143` Dim + `9` Flash over `103` objekter).
2. **V3 Gate 1 (astrometrisk stabilitet `<= 0,40"` & `reliability >= 0,50`):** Bortfiltrerer direkte **`146/152` (`96,1 %`)** DIA-artefakter/centroidehop (typisk `0,5–0,9"` offset og `rel ~ 0,10–0,15`). Kun **`6` epoker** passerer Gate 1.
3. **V3 Gate 2 (`/sources` $\leftrightarrow$ `/fp` krydsstrøm-bekræftelse inden for `±0,05 d` i samme bånd):** Bortfiltrerer yderligere **`4/6`** ubekræftede DIA-udslag (`veto_unconfirmed_in_fp`).
4. **Eneste V3 Sam-Bekræftede Kandidat (`1` stjerne / `2` epoker):**
   - **`diaObjectId = 313980945231249489`** (`Gaia DR3 4830879128919529216`, `EDFS_B`, $G = 19{,}68$, **`BP - RP = 2{,}6322`** = kold M-dværg).
   - Klassisk **blå `g`-bånds M-dværg-flare**: `1,8263×` i `/sources` (`Z_flash = +11,407`, `reliability = 0,9463`, **`0,0115"` astrometrisk stabilitet**) og næsten identisk **`1,8141×` i `/fp`**, bekræftet som centreret punkt-PSF uden dipol i ægte Rubin FITS-cutouts (`DiffSNR = 5,62–12,66`, `neg/pos = 0,009–0,118`, `42/42` FITS valideret). Disposition: **`ASTROPHYSICAL_FLARE_MDWARF_BLUE`** $\rightarrow$ **`0` verificerede ETI**.
5. **Root-cause audit af top-30 rå `/fp`-afvigere:** `12` DIA dårlig/sub-tærskel, `10` ingen tilsvarende `/sources`-alert, `8` rå `/sources`-dipoler — alle forklaret af manglende pixel-maskering i `/fp`.

---

## 3. Injektion-Genfinding (`9.600` Forsøg) & Forenede Bayesianske `2.100`-Stjerners Grænser (`f_95`)

Over **`4.800` seedede syntetiske forsøg pr. datastrøm (`2.400` Dim + `2.400` Flash på `400` stjerner $\times 6$ amplituder = `9.600` forsøg i alt)**:
- **Komplethed (`/fp`):** **`94,33 %`** Dim (`95,75 %` for $\ge 0{,}50\,\mathrm{mag}$) og **`95,00 %`** Flash (`96,15 %` for $\ge 0{,}75\,\mathrm{mag}$).
- **Komplethed (`/sources`):** **`56,92 %`** Dim og **`63,71 %`** Flash.

| Kampagne & Strøm | Evaluérbare Stjerner (`N_eff`) | `Jeffreys f_95` (`k=0`) | `Uniform f_95` | `Clopper–Pearson` |
|---|---:|---:|---:|---:|
| **Rubin V3 N3 `/sources` (Dim / Flash)** | `572` (`325,6 / 364,4`) | **`0,5877 % / 0,5253 %`** | `0,9131 % / 0,8165 %` | `0,9159 % / 0,8187 %` |
| **Rubin V3 N3 `/fp` (Dim / Flash)** | `1.555` (`1.466,8 / 1.477,3`) | **`0,1308 % / 0,1299 %`** | `0,2039 % / 0,2024 %` | `0,2040 % / 0,2026 %` |
| **Forenet Rubin V2 + V3 `/sources` (`2.100` stj.)** | `657` (`369,1 / 420,0`) | **`0,5187 % / 0,4560 %`** | `0,8062 % / 0,7090 %` | `0,8084 % / 0,7107 %` |
| **Forenet Rubin V2 + V3 `/fp` (`2.100` stj.)** | **`1.809`** (`1.669,4 / 1.693,8`) | **`0,1150 % / 0,1133 %`** | **`0,1792 % / 0,1766 %`** | `0,1793 % / 0,1767 %` |

Den forenede Vera Rubin V2 + V3-grænse på **`0,1133–0,1150 %` Jeffreys (`0,1766–0,1792 %` Uniform)** trykker den optiske transient-grænse næsten **`3×` under** hele den `1.083`-stjerners spektroskopiske `ALL_SCIENCE_EM`-hovedgrænse (`0,3243 %` Jeffreys).

---

## 4. Figurer, Arkiv & Revisioner (`12/12 PASSED`)

- **6 Visuelt Godkendte 300-DPI Figurer (`figN3_01–figN3_06`):** [`VISUAL_REVIEW_N3.json`](results/VISUAL_REVIEW_N3.json).
- **Ren-Stdlib Revision (`/usr/bin/python3 -S`):** [`audit_n3_rubin_v3.py`](scripts/audit_n3_rubin_v3.py) $\rightarrow$ **`N3_RUBIN_V3_AUDIT: 12/12 PASSED`**, samt samtidig bekræftelse af **`N2_RUBIN_ISO_TRAILS_AUDIT: 12/12 PASSED`**, **`N1_DYSON_VASCO_AUDIT: 12/12 PASSED`**, **`RUBIN_V2_AUDIT: 12/12 PASSED`** og **`SPOR5_PUBLICATION_AUDIT: 12/12 PASSED`**.
- **Fuld Arkivpakke (`archives_n3/`):** `SETI_N3_RUBIN_V3_1800STARS_2026-11-27.zip` (`26,429,735 B`, SHA-256 `ef51060974d26eccc86eaf0eaf58d3f7404c29021dd4bb4614307994d881af39`).
