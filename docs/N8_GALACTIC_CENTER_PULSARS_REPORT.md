# Spor N8 — Galaktisk Centrum (*Sgr A**) & Mælkevejens Pulsar- & Gammastråle-Fyrtårns-Søgning (`2.501` Pulsarer + `222` *Fermi* Bulge)

**Kampagne-ID:** `SPOR_N8_GALACTIC_CENTER_BEACON_AND_PULSAR_SURVEY` · **Dato:** 27. november 2026  
**Status:** **AFSLUTTET (`0` verificerede Mælkevejs-ETI · `N8_GALACTIC_CENTER_AUDIT: 12/12 PASSED` · `external_contacts == 0`)**

---

## 1. Resumé

Spor N8 udvider den rene Mælkevejs-kampagne til **Mælkevejens indre kerne (`Sgr A*` / Den Galaktiske Bulge)** og **hele vores galakses kendte pulsar-population (`ATNF B/psr/psr`, med `LMC`/`SMC`-pulsarer strengt udelukket)** forenet med *Fermi*-LAT `4FGL-DR3` gammastrålekilder, *NVSS* `1,4 GHz` radio og *Chandra* `CSC 2.0` røntgen:

- **Analysepopulation (Streng Mælkevej):**
  - **`2.501`** rene Mælkevejs-pulsarer i `ATNF` (heraf **`104`** i Den Galaktiske Kernes indre felt $|l| \le 5^\circ, |b| \le 2^\circ$).
  - **`222`** gammastrålekilder i Den Galaktiske Bulge (`|l| <= 10 deg, |b| <= 5 deg` i `4FGL-DR3`), heraf **`168`** uassocierede.
  - **`1.780`** *NVSS* `1,4 GHz` radiokilder (inden for `2,5°` omkring `Sgr A*`) og **`7.457`** *Chandra* `CSC 2.0` røntgenkilder (inden for `0,5°` omkring `Sgr A*`).
- **Prospektiv blind låsning:** `METHOD_LOCK.json` + `n8_galactic_center_analyzer.py` (`3bc4e2d794ce3e6a36499fcadff9cc2515f7ef479a3e4d4105bdb08c937b2d6b`) låst kl. **`2026-11-27T19:07:48.702545+00:00`** før Stage 1-download (`19:07:55.168224+00:00` for Stage 2).
- **Stage 2 → Stage 3 Veto (`4 -> 0 ETI`):**
  - Tværs over alle **`222`** *Fermi*-LAT Bulge-kilder findes **`0`** uassocierede hårde/kurvede (`PLGam < 1,85`, `SigCurv >= 5`, `Sig >= 10`) eller ekstremt variable (`VarInd >= 100`) gamma-fyrtårne.
  - Tværs over alle **`2.501`** Mælkevejs-pulsarer udløses præcis **`4`** triggere (`3` `N8_PSR_SPINUP_ANOMALY` $\dot{P} < -10^{-17}$ + `1` `N8_PSR_DEATHLINE_VIOLATION` $\log_{10}(B/P^2) < 10{,}6$, `0` ultra-lange/kunstigt harmoniske perioder):
    1. **`PSR J2129+1210A`** (`GC:M15`, $P_0 = 0{,}1107\text{ s}$, $\dot{P} = -2{,}103\times 10^{-17}$): Kuglehobs-gravitationsacceleration i `M15`.
    2. **`PSR J2129+1210D`** (`GC:M15`, $P_0 = 4{,}803\text{ ms}$, $\dot{P} = -1{,}075\times 10^{-17}$): Kuglehobs-gravitationsacceleration i `M15`.
    3. **`PSR J1144-6146`** ($P_0 = 0{,}9878\text{ s}$, $\dot{P} = (-3{,}8 \pm 8{,}9)\times 10^{-17}$, Parkes `mlc+01`): Kun **$0{,}43\sigma$** fra nul — ikkesignifikant timing-støj i tidlig opdagelsesfit.
    4. **`PSR J2144-3933`** ($P_0 = 8{,}5098\text{ s}$, $\dot{P} = 4{,}96\times 10^{-16}$, $B = 2{,}08\times 10^{12}\text{ G}$, $\log_{10}(B/P^2) = 10{,}458$): Den klassiske langsomme nærliggende (`160 pc`) radiopulsar (Young et al. 1999) med krum-rumtids parproduktion.
  - **Verificerede galaktiske ETI-kandidater: `0`.**
- **1.200 Injektioner & Bayesianske Nullgrænser (`0` ETI):**
  - Pulsar-injektioner giver `100,0 %` (stærk spin-up) og `92,67 %` (under dødsstregen) $\rightarrow$ **`96,33 %`** samlet ($N_{\mathrm{eff}} = 2.409{,}21$); *Fermi* Bulge `Sig >= 20` giver **`100,0 %`**.
  - **Alle Mælkevejs-pulsarer (`2.501` raw / `2.409,2` eff.):** **Jeffreys $f_{95} = 0{,}0768\,\%$ (`raw`) / $0{,}0797\,\%$ (`eff`)** · Uniform `0,1197 %` / `0,1242 %`.
  - **Galaktisk Kerne-pulsarer (`n = 104`):** Jeffreys **`1,8255 %`** · **`Fermi` Bulge (`n = 222`):** **`0,8605 %`** (`1,1351 %` for `168` uassocierede).

---

## 2. Stage 3 Forensisk Veto-Tabel (`4 -> 0 ETI`)

| Pulsar | `l, b` (deg) | `P0` (s) | `P1` (s/s) / `e_P1` | Port | Klassifikation & Bevis | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `J2129+1210A` | `65,01, -27,31` | `0,11066` | `-2,10e-17` / `2,0e-22` | `N8_PSR_SPINUP_ANOMALY` | `GLOBULAR_CLUSTER_GRAVITATIONAL_ACCEL` (`GC:M15`, `SIMBAD Psr`) | `VETOED_ASTROPHYSICAL_OR_NOISE` |
| `J2129+1210D` | `65,01, -27,31` | `0,00480` | `-1,08e-17` / `1,2e-19` | `N8_PSR_SPINUP_ANOMALY` | `GLOBULAR_CLUSTER_GRAVITATIONAL_ACCEL` (`GC:M15`, `SIMBAD Psr`) | `VETOED_ASTROPHYSICAL_OR_NOISE` |
| `J1144-6146` | `295,12, +0,07` | `0,98778` | `-3,80e-17` / `8,9e-17` | `N8_PSR_SPINUP_ANOMALY` | `TIMING_NOISE_UNSIGNIFICANT_P1` (`0,43 sigma` fra 0, `mlc+01`) | `VETOED_ASTROPHYSICAL_OR_NOISE` |
| `J2144-3933` | `2,79, -49,47` | `8,50983` | `+4,96e-16` / `5,0e-18` | `N8_PSR_DEATHLINE_VIOLATION` | `CURVED_SPACETIME_SLOW_RADIO_PULSAR` (Young+1999, `160 pc`, `log(B/P^2)=10,46`) | `VETOED_ASTROPHYSICAL_OR_NOISE` |

---

## 3. Figurer, Audit & Reproducerbarhed

- **Visuelt verificerede 300-DPI PNGs (`figN8_01`–`figN8_06`, godkendt i `VISUAL_REVIEW_N8.json`):** Galaktisk pulsar/bulge-kort, $P-\dot{P}$-diagram med dødsstreg, *Fermi* Bulge $\Gamma$-vs-kurvatur & $1^\circ$ `Sgr A*` *Chandra*/*NVSS*-felt, variabilitet + veto-tragt, `1.200` injektioner & $f_{95}$ samt Mælkevejs-syntese.
- **Ren-stdlib Audit (`/usr/bin/python3 -S scripts/audit_n8_galactic_center.py`):** **`N8_GALACTIC_CENTER_AUDIT: 12/12 PASSED`** (`external_contacts == 0`).
- **Lokal arkivpakke:** `archives_n8/SETI_N8_GALACTIC_CENTER_AND_PULSARS_2026-11-27.zip`.
