# Spor N11A — Fin-Opløsning Vandhuls-SETI (`2,794–2,836 Hz`): Gajjar Plasma-Udtværing & Frekvenskamme via Live HTTP-Range Utsnit (`0,76 TiB` -> `2,80 GiB`)

**Kampagne-ID:** `SPOR_N11A_FINE_WATERHOLE_GAJJAR_PLASMA` · **Dato:** 28. november 2026  
**Status:** **AFSLUTTET (`0` verificerede Mælkevejs-ETI · `N11A_WATERHOLE_GAJJAR_AUDIT: 12/12 PASSED` · `external_contacts == 0`)**

---

## 1. Resumé & Metodisk Gennembrud

Hvor **Spor N10** gennemsøgte fuld-bånds L-båndsprodukter (`.0002.h5`, `2,86 kHz` opløsning) over hele `1,08–1,92 GHz`, angriber **Spor N11A** direkte den fineste **Breakthrough Listen GBT `.0000.h5` rå-kanal-opløsning (`2,794–2,836 Hz`)** inde i **Vandhullet (`1422,36–1426,77 MHz`, `2,93–2,97 MHz` ren båndbredde pr. stjerne)**. I stedet for at downloade hele arkivet på `835,08 GB` (`0,76 TiB`), skar vi præcis det prospektivt låste `1.048.576`-kanalers Vandhuls-vindue ud af samtlige **`54` eksterne `.0000.h5` skanninger** over persistent HTTP Range (`KeepAliveRangeFile`, **`2,80 GiB` overført = `278,18×` båndbredde-reduktion**, **`40×` dybere følsomhed end N10**):

- **Analysepopulation (Streng Mælkevej `<= 6,0 pc`):** **`9`** nærliggende M-dværge i komplet **`ABACAD`-kadence** (`54` skanninger, **`576` rene `16.384`-kanalers blokke**, **`26,4936 MHz`** samlet ren båndbredde, median **`>5σ` RFI-belægning = `0,0083 %`**): **`GJ 411`**, **`GJ 65A`**, **`GJ 866`**, **`GJ 54.1`**, **`GJ 273`**, **`GJ 687`**, **`GJ 1245AC`**, **`GJ 1002`** og **`HIP 1242`**.
  - *Bemærkning om frekvensbånd:* `6` stjerner (`GJ 65A`, `GJ 866`, `GJ 54.1`, `GJ 687`, `GJ 1245AC`, `HIP 1242`) ligger ved `df = 2,7940 Hz` (`1422,363–1425,293 MHz`, `tsamp = 18,2536 s`), mens `3` stjerner (`GJ 411`, `GJ 273`, `GJ 1002`) fra et tilstødende BLC-bånd har `df = 2,8355 Hz` (`1423,7918–1426,7651 MHz`, `tsamp = 17,9862 s`).
- **Prospektiv blind låsning:** `METHOD_LOCK.json` og `IMPLEMENTATION_LOCK.json` forseglet præ-datahentning kl. `2026-11-28T06:58:12.123450+00:00` med eksakt analysator-hash **`a460ca9a6553082aabac2cd96a26a20d33f5f755f2e07a7c24ac3582a74ab5e7`** (`pre_acquisition_blind_lock == True`).
- **1.200-Forsøgs Hoved-Mod-Hoved Benchmark på Rigtig `2,8 Hz` GBT Vandhuls-Støj (`N11A` vs. Klassisk `turboSETI` `1`-bin lineær baseline):**
  1. **Primært Gajjar Stjernevinds Plasma-Udtværet Regime (`GAJJAR_PLASMA_10_350HZ`, $\sigma_f = 17\text{–}126\,\text{Hz}$ / FWHM $\approx 40\text{–}300\,\text{Hz}$):** Spor N11A (`G1`) opnår **`370/400` (`92,50 %`)** mod **`0/400` (`0,00 %`)** for klassisk `1`-bin `turboSETI`-analog.
  2. **Fint Harmonisk Frekvenskam (`FINE_HARMONIC_COMB`, 10 tænder @ `224–727 Hz`):** Spor N11A (`G3` + `G1`) opnår **`253/400` (`63,25 %`)** mod **`0/400` (`0,00 %`)**.
  3. **Fint Krumt Orbital-Drift (`FINE_CURVED_ORBITAL`):** Spor N11A (`G2`) opnår **`39/400` (`9,75 %`)** mod **`0/400` (`0,00 %`)** — en ærlig diagnosticeret gitterbegrænsning, idet `G2`'s grove lineære drift-trin (`Δd1 = 16` bins) undersampler `W = 1–4` bins krumme spor ved `2,8 Hz`-opløsning. Samlet 3-morfologi middelværdi er derfor **`55,17 %`** (`662/1.200`) mod **`0,00 %`** klassisk.
- **Zero-ETI Resultat (`0` Stage 2-triggere tværs over `576` blokke):**
  - Det ultra-stille Vandhul (`0,0082–0,0096 %` RFI) gav **`0` `ABACAD` Stage 2-triggere** (`G1 = 0`, `G2 = 0`, `G3 = 0`). Stage 3 bekræftede, at de få terrestriske kam-mønstre med høj `ON`-autokorrelation (op til **`comb_on2 = 226,981`** ved `1426,60 MHz` på `GJ 411`) alle blev afvist af stærk `OFF`-kam (`comb_off_max = 126,262`) i samme kadence $\rightarrow$ **`0` verificerede radio-ETI**.
- **Fysiske EIRP-grænser & Bayesianske $f_{95}$ (`40×` dybere end Spor N10):**
  - GBT `10σ` EIRP (`SEFD = 10 Jy`): **`5,44–29,79 GW`** (median **`12,038 GW`**) for `W = 1`, **`48,153 GW`** for `W = 16` (`45 Hz` Gajjar plasma-kerne), og **`96,306 GW`** for `W = 64` (`179 Hz` bredt plasma).
  - **Konservativ 3-morfologi kombineret grænse (`n_eff = 4,965` stjerner / `317,76` blokke):** Stjerner raw (`N = 9`) Jeffreys $f_{95} = \mathbf{18{,}7366\,\%}$ (`25,8866 %` Uniform); effektiv stjernegrænse **`30,7435 %`** (`39,4813 %` Uniform); **`16.384`-ch blok × stjerne (`N_eff = 317,76`)**: Jeffreys $f_{95} = \mathbf{0{,}6022\,\%}$ (`0,9354 %` Uniform). (På det primære Gajjar-plasma-regime alene, `92,50 %`, er blok-grænsen `0,360 %` / stjerne-eff `20,05 %`.)

---

## 2. Kadenceoversigt (`9` `< 6 pc` M-Dværge · `54` HTTP-Range Utsnit · `576` Blokke)

| Stjerne | Kadence | Afstand (`pc`) | Exoplaneter | `df` (`Hz`) | Ren BW (`MHz`) | EIRP `W=1` (`GW`) | EIRP `W=16` (`45 Hz`, `GW`) | `>5σ` RFI (`%`) | Triggere (`G1/G2/G3`) / ETI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GJ 411` | `--72283` | `2,5461` | `2` | `2,8355` | `2,9728` | `5,4443` | `21,7772` | `0,00932` | `0 / 0 / 0` $\rightarrow$ **`0 ETI`** |
| `GJ 65A` | `--73638` | `2,6749` | `0` | `2,7940` | `2,9292` | `5,9209` | `23,6838` | `0,00868` | `0 / 0 / 0` $\rightarrow$ **`0 ETI`** |
| `GJ 866` | `--73872` | `3,4100` | `0` | `2,7940` | `2,9292` | `9,6223` | `38,4894` | `0,00844` | `0 / 0 / 0` $\rightarrow$ **`0 ETI`** |
| `GJ 54.1` | `--73620` | `3,7167` | `3` | `2,7940` | `2,9292` | `11,4310` | `45,7238` | `0,00832` | `0 / 0 / 0` $\rightarrow$ **`0 ETI`** |
| `GJ 273` | `--517180` | `3,7861` | `2` | `2,8355` | `2,9728` | `12,0383` | `48,1532` | `0,00958` | `0 / 0 / 0` $\rightarrow$ **`0 ETI`** |
| `GJ 687` | `--75045` | `4,5498` | `2` | `2,7940` | `2,9292` | `17,1300` | `68,5199` | `0,00823` | `0 / 0 / 0` $\rightarrow$ **`0 ETI`** |
| `GJ 1245AC` | `--517935` | `4,6600` | `0` | `2,7940` | `2,9292` | `17,9698` | `71,8793` | `0,00845` | `0 / 0 / 0` $\rightarrow$ **`0 ETI`** |
| `GJ 1002` | `--72885` | `4,8461` | `2` | `2,8355` | `2,9728` | `19,7230` | `78,8918` | `0,00897` | `0 / 0 / 0` $\rightarrow$ **`0 ETI`** |
| `HIP 1242` | `--73656` | `6,0000` | `0` | `2,7940` | `2,9292` | `29,7903` | `119,1612` | `0,00839` | `0 / 0 / 0` $\rightarrow$ **`0 ETI`** |

---

## 3. Figurer, Verifikation & Arkiv

- **6 visuelt kontrollerede 300-DPI PNG-figurer (`figN11A_01`–`figN11A_06`, forseglet i `VISUAL_REVIEW_N11A.json`):** Vandhullets `>5σ` RFI-profil og `5,4–29,8 GW` EIRP; `1.200`-forsøgs Gajjar-benchmark; reelle `2,8 Hz` `ABACAD` injektionsvandfald; log-log `G3`-kamdiagnostik (`ON=OFF=227` RFI afvist af `OFF`); Bayesiansk $f_{95}$ & følsomhed; samt ærlig syntese med Spor N10.
- **Ren-stdlib Audit (`/usr/bin/python3 -S scripts/audit_n11a_waterhole_gajjar.py`):** **`N11A_WATERHOLE_GAJJAR_AUDIT: 12/12 PASSED`** (`external_contacts == 0`, regressionskæde bestået mod `N10`, `N8`, `N3` og `Spor 5`).
- **Lokal arkivpakke:** `archives_n11a/SETI_N11A_FINE_WATERHOLE_GAJJAR_PLASMA_2026-11-28.zip`.
