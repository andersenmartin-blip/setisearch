# Spor 5 — Peer-Review Journal Synthesis Article, Machine-Readable Catalogs (.mrt/.fits/.csv), arXiv Bundle & Zenodo Package (`D079–D112`, `V7.0`)

**Status:** **FULDENDT & VERIFICERET (`SPOR5_PUBLICATION_AUDIT: 12/12 PASSED` under `/usr/bin/python3 -S`, `38/38` Companion Archives `A–AL` intakte, `CLEAN_ROOM_ARXIV_COMPILE_PASS`, `0` modificerede arkiver)**

---

## 1. Hovedleverancer i Spor 5

1. **Peer-Review Synteseartikel (19 sider, to-spaltet AJ/ApJ-format):**
   - **PDF (`3.561.993 B`, `19` sider, SHA-256 `551bef372a6fab18fbe9648d5ce3fa591e2548aba9c40a273214d119fc5dd6c9`):** Bit-identisk synkroniseret på:
     1. `/home/martin/SETI_Fortsaettelse_2026-11-14/setisearch/paper_journal/ANDERSEN_2026_AJ_PANCHROMATIC_SETI_SYNTHESIS.pdf` (`andersen2026_aj_synthesis.pdf`)
     2. `/home/martin/SETI_Fortsaettelse_2026-11-14/reports/ANDERSEN_2026_AJ_PANCHROMATIC_SETI_SYNTHESIS.pdf`
     3. `/home/martin/SETI_Fortsaettelse_2026-11-14/seti_spor5_publication_deliverables/ANDERSEN_2026_AJ_PANCHROMATIC_SETI_SYNTHESIS.pdf`
   - **LaTeX & arXiv-kildepakke (`3.390.685 B = 3,23 MiB`, SHA-256 `b7ede94370e5938c6ba986538770d0399efaaf8cf7d1879bda97755d60d95831`):** `paper_journal/andersen2026_aj_synthesis.tex`, `00README.XXX` og `arxiv_submission_andersen2026_seti_v7_0.tar.gz` — testet via clean-room udpakning og `tectonic`-kompilering (`19` sider, `3.561.993 B`).
   - **9 Visuelt Verificerede 300-DPI Syntesefigurer (`figJ01–figJ09`):** Dokumenteret og godkendt i `paper_journal/VISUAL_REVIEW_JOURNAL.json` sammen med visuel inspektion af de renderede PDF-sider.
   - **Supplerende Teknisk Monografi (`105` sider):** `setisearch/paper/ANDERSEN_2026_PANCHROMATIC_ECHELLE_SETI_SURVEY.pdf` (`70.184.768 B`, SHA-256 `f7368a7901f99abdcb8328f643dece57da3ba5053eb90c247ebb0abea090d334`) bevaret 100% uændret.

2. **7 AAS / VizieR Machine-Readable Table Sæt (`.mrt` + binær `.fits` + `.csv`):**
   - `table1_master_catalog_1083stars` (`1.083` rækker: `787` Science / `296` Controls; streng 3-skala adskillelse med `777` beamed, `352` HE-isotrope, `54` *IceCube*, `33` rene *IceCube*-mål).
   - `table2_solar_neighborhood_10pc_267stars` (`267` rækker: `212` Science [`61/61` planetværter lukket / `121` planeter] + `55` Controls; `0,78810 kW` median).
   - `table3_spectrograph_atlas_72inst_104arms` (`104` arme / `72` primære spektrografer & observatorier fra `1.000 PeV` til `35 GHz` inkl. `10/10` ALMA `B1–B10`).
   - `table4_panchromatic_bridge_matrix_2695cells` (`2.695` celler på `197` Science-broer / `262` multi-fase mål; `126/126` tomme EM *IceCube*-celler strengt bevaret).
   - `table5_bayesian_ftx_and_cwtfm` (`136` rækker) + `table5b_cwtfm_benchmark` (`7` rækker) — rapporterer eksakt Uniform $f_{95}$ (`0,5048 %` for `ALL_SCIENCE_EM`), eksakt analytisk $\mathrm{Beta}(0,5, N_{\mathrm{eff}}+0,5)$ Jeffreys (`0,3243 %` for `ALL_SCIENCE_EM`), og Clopper–Pearson (`0,5056 %`).
   - `table6_companion_archives_38manifest` (`38` rækker `A–AL`, `689.427.242 B = 657,49 MiB`, live SHA-256 verificeret).
   - Fuldt dokumenteret i `zenodo_package/VizieR_ReadMe.txt` med nul fast-bredde trunkering (`truncs=[]`).

3. **Zenodo & Citeringsmetadata + Ren-Stdlib Audit (`12/12 PASSED`):**
   - `.zenodo.json`, `codemeta.json`, `CITATION.cff` (`v7.0.0`), `zenodo_package/DATA_AVAILABILITY_AND_REPRODUCIBILITY.md`, `zenodo_package/ZENODO_DEPOSIT_MANIFEST_SHA256.json` (`28` publikations-/tabel-artefakter + `38` Companion Archives `A–AL`), samt `/usr/bin/python3 -S zenodo_package/verify_publication_package.py` -> **`12/12 PASSED`**.
