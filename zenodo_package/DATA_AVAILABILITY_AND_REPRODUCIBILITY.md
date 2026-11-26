# SETIsearch `D079–D112` (`V7.0`) Archival Release & Clean-Room Reproducibility Guide

**Author:** Martin Andersen (MSc Astrophysics, University of Copenhagen)  
**Version:** `7.0.0` (Survey Phases `D079–D112` + Supporting Phases `D069–D078`, Companion Archives `A–AL`)  
**Total Verified ETI Technosignature Detections:** `0` across **`1,083` unique targets** (`787` Science [`327` exoplanet hosts / `576` planets] + `296` Controls), **`72` spectrographs / `104` spectral arms**, **`62.582` EM octaves (`1.239842e-15 – 8,556.41831 µm`)**, **`4,383` exposures (`736,410.27 h`)**, and **`113,967` calibration trials**.

---

## 1. Contents of `zenodo_package/`

- **`tables/table1_master_catalog_1083stars.{mrt,fits,csv}`**: Unified `1,083`-star catalog preserving strict three-regime scale separation (`777` diffraction-beamed UV–mm @ `10 m`, `352` HE isotropic `EUV–1 PeV`, `54` *IceCube* 10-yr $\nu_\mu$ including `33` strictly *IceCube*-only zero-EM stars).
- **`tables/table2_solar_neighborhood_10pc_267stars.{mrt,fits,csv}`**: Volume-limited `< 10 pc` sample (`267` stars = `212` Science [`61` hosts / `121` planets] + `55` Control; `100.0%` host Keplerian drift closure; median `0.78810 kW` beamed UV–mm).
- **`tables/table3_spectrograph_atlas_72inst_104arms.{mrt,fits,csv}`**: Complete `104`-arm / `72`-facility instrument atlas across `10/10` ALMA bands (`B1–B10`), *1LHAASO*, *INTEGRAL*, *IXPE*, *eROSITA*, *IceCube*, *JWST*, *HST*, *FUSE*, *Herschel*, *SOFIA*, *VLT*, *CFHT*, *TBL*, *Gemini*, and *CAHA*.
- **`tables/table4_panchromatic_bridge_matrix_2695cells.{mrt,fits,csv}`**: `2,695` cell-level upper limits across `197` Science bridges (`262` multi-phase targets), explicitly keeping `126/126` empty EM power cells for *IceCube* neutrinos.
- **`tables/table5_bayesian_ftx_and_cwtfm.{mrt,fits,csv}`** & **`tables/table5b_cwtfm_benchmark.{mrt,fits,csv}`**: Numerical Bayesian 95% occurrence-rate bounds ($f_{95}$ under Uniform, exact analytical $\mathrm{Beta}(0.5, N_{\mathrm{eff}}+0.5)$ Jeffreys, and frequentist Clopper–Pearson) plus CWTFM Cosmic Haystack comparison.
- **`tables/table6_companion_archives_38manifest.{mrt,fits,csv}`**: Exact byte sizes (`689,427,242 B = 657.49 MiB`) and SHA-256 digests of all `38` Companion Archives `A–AL`.
- **`VizieR_ReadMe.txt`**: Full AAS/CDS byte-by-byte format specification.
- **`verify_publication_package.py`**: Standalone pure-Python (`/usr/bin/python3 -S`) 12-check verification suite.

---

## 2. Clean-Room Multi-Archive Verification (`38/38 PASS`)

To verify every intermediate phase (`D069–D112`) and reproduce all final tables from bounded IEEE-754 inputs with **`0` CSV/JSON diffs**:

```bash
python3 -u restore_d112_workspace.py --archives-dir /path/to/archives --recompute
/usr/bin/python3 -S zenodo_package/verify_publication_package.py --archives-dir /path/to/archives
```
