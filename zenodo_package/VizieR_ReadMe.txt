Title: The SETIsearch 62.58-Octave, 1,083-Star Panchromatic & Multi-Messenger
       Technosignature Survey (Phases D079-D112): Machine-Readable Catalogs
Author: Andersen, M. (University of Copenhagen)
Date: 2026-11-26
Repository: https://github.com/andersenmartin-blip/setisearch
================================================================================
Overview:
  This VizieR/AAS ReadMe documents the six machine-readable table sets
  (.mrt fixed-width ASCII CDS/AAS format, .fits binary FITS tables, and .csv)
  accompanying the D079-D112 (V7.0) 1,083-star panchromatic + multi-messenger
  technosignature survey (62.582 EM octaves 1.239842e-15 - 8,556.41831 um,
  10/10 ALMA receiver bands, 1.000 PeV 1LHAASO, INTEGRAL 511 keV, IXPE &
  optical/NIR Stokes spectropolarimetry, and IceCube 10-yr muon neutrinos).
  Total verified ETI technosignature detections: 0.
--------------------------------------------------------------------------------
File Summary:
  table1_master_catalog_1083stars.mrt           1083 rows    341186 B  Master 1,083-Star Panchromatic & Multi-Messenger SETI Synthesis Catalog (D079-D112)
  table2_solar_neighborhood_10pc_267stars.mrt    267 rows     90004 B  Solar Neighborhood (<10 pc) Volume-Limited Panchromatic & Multi-Messenger Catalog (267 Stars)
  table3_spectrograph_atlas_72inst_104arms.mrt   104 rows     20686 B  72-Spectrograph / 104-Spectral-Arm Panchromatic & Multi-Messenger Instrument Atlas (D079-D112)
  table4_panchromatic_bridge_matrix_2695cells.mrt  2695 rows    622038 B  Panchromatic Multi-Phase Science & Control Bridge Matrix (2,695 Cells, 197 Science Bridges)
  table5_bayesian_ftx_and_cwtfm.mrt              136 rows     22061 B  Bayesian 95% Transmitter Occurrence Limits across Regimes, Power Thresholds, and Duty Cycles (D112)
  table5b_cwtfm_benchmark.mrt                      7 rows      3183 B  Cosmic Haystack / CWTFM Survey Benchmark Comparison (D112 vs. Literature)
  table6_companion_archives_38manifest.mrt        38 rows     10414 B  Cryptographic Manifest of All 38 Prospectively Locked Companion Archives (A-AL)
================================================================================

Byte-by-byte Description of file: table1_master_catalog_1083stars.mrt (1083 rows)
Title: Master 1,083-Star Panchromatic & Multi-Messenger SETI Synthesis Catalog (D079-D112)
--------------------------------------------------------------------------------
 Bytes   Format  Units          Label                    Explanations
--------------------------------------------------------------------------------
   1- 16 A16     ---            star                     Canonical star or system identifier
  18- 45 A28     ---            common_name              Common astronomical designation
  47- 53 A7      ---            role                     Survey role (SCIENCE or CONTROL)
  55- 74 A20     ---            subrole                  Target subcohort classification
  76- 85 F10.6   deg            ra_deg                   ICRS Right Ascension (J2000/Gaia DR3)
  87- 96 F10.6   deg            dec_deg                  ICRS Declination (J2000/Gaia DR3)
  98-107 F10.4   pc             dist_pc                  Distance in parsecs
     109 I1      ---            within_10pc              1 if within 10 pc Solar Neighborhood else 0
 111-112 I2      ---            n_exoplanets             Confirmed exoplanets hosted
 114-116 I3      ---            n_nights                 Distinct observation nights across all phases
 118-177 A60     ---            phases                   Plus-delimited phase IDs covering target
 179-180 I2      ---            n_instruments            Distinct spectrograph/array count
     182 I1      ---            has_beamed               1 if diffraction-beamed UV-mm covered else 0
 184-203 A20     ---            best_beamed_inst         Instrument yielding deepest 10m beamed EIRP
 205-216 E12.5   kW             min_beamed_10m_kw        Minimum 10m beamed transmitter EIRP limit (UV-mm)
 218-229 E12.5   kW             min_opt_ir_10m_kw        Minimum 10m beamed EIRP limit (Opt-IR only)
     231 I1      ---            has_he_em                1 if HE isotropic EM (EUV-PeV) covered else 0
 233-252 A20     ---            best_he_inst             Instrument yielding deepest HE isotropic limit
 254-265 E12.5   erg/cm2/s      min_he_flux_cgs          Minimum HE isotropic narrowband flux limit
 267-278 E12.5   MW             min_he_l_iso_mw          Minimum HE isotropic luminosity limit
     280 I1      ---            has_neutrino             1 if IceCube 10-yr neutrino covered else 0
 282-293 E12.5   MW             min_nu_l_iso_mw          Minimum IceCube neutrino isotropic luminosity
     295 I1      ---            etz_qualified            1 if inside Earth Transit Zone else 0
     297 I1      ---            ellipsoid_180d           1 if within 180d SETI Ellipsoid crossing else 0
     299 I1      ---            verified_eti             Verified ETI technosignature detections (0)
--------------------------------------------------------------------------------

Byte-by-byte Description of file: table2_solar_neighborhood_10pc_267stars.mrt (267 rows)
Title: Solar Neighborhood (<10 pc) Volume-Limited Panchromatic & Multi-Messenger Catalog (267 Stars)
--------------------------------------------------------------------------------
 Bytes   Format  Units          Label                    Explanations
--------------------------------------------------------------------------------
   1- 16 A16     ---            star                     Canonical star or system identifier
  18- 45 A28     ---            common_name              Common astronomical designation
  47- 53 A7      ---            role                     Survey role (SCIENCE or CONTROL)
  55- 74 A20     ---            subrole                  Target subcohort classification
  76- 85 F10.6   deg            ra_deg                   ICRS Right Ascension (J2000/Gaia DR3)
  87- 96 F10.6   deg            dec_deg                  ICRS Declination (J2000/Gaia DR3)
  98-107 F10.4   pc             dist_pc                  Distance in parsecs
     109 I1      ---            within_10pc              1 if within 10 pc Solar Neighborhood else 0
 111-112 I2      ---            n_exoplanets             Confirmed exoplanets hosted
 114-116 I3      ---            n_nights                 Distinct observation nights across all phases
 118-177 A60     ---            phases                   Plus-delimited phase IDs covering target
 179-180 I2      ---            n_instruments            Distinct spectrograph/array count
 182-188 F7.1    K              teff_k                   Effective photospheric temperature
     190 I1      ---            has_beamed               1 if diffraction-beamed UV-mm covered else 0
 192-211 A20     ---            best_beamed_inst         Instrument yielding deepest 10m beamed EIRP
 213-224 E12.5   kW             min_beamed_10m_kw        Minimum 10m beamed transmitter EIRP limit (UV-mm)
 226-237 E12.5   kW             min_opt_ir_10m_kw        Minimum 10m beamed EIRP limit (Opt-IR only)
     239 I1      ---            has_he_em                1 if HE isotropic EM (EUV-PeV) covered else 0
 241-260 A20     ---            best_he_inst             Instrument yielding deepest HE isotropic limit
 262-273 E12.5   erg/cm2/s      min_he_flux_cgs          Minimum HE isotropic narrowband flux limit
 275-286 E12.5   MW             min_he_l_iso_mw          Minimum HE isotropic luminosity limit
     288 I1      ---            has_neutrino             1 if IceCube 10-yr neutrino covered else 0
 290-301 E12.5   MW             min_nu_l_iso_mw          Minimum IceCube neutrino isotropic luminosity
     303 I1      ---            etz_qualified            1 if inside Earth Transit Zone else 0
     305 I1      ---            ellipsoid_180d           1 if within 180d SETI Ellipsoid crossing else 0
     307 I1      ---            drift_v67_closed         1 if multi-epoch Keplerian drift closed in D109
     309 I1      ---            verified_eti             Verified ETI detections (0)
--------------------------------------------------------------------------------

Byte-by-byte Description of file: table3_spectrograph_atlas_72inst_104arms.mrt (104 rows)
Title: 72-Spectrograph / 104-Spectral-Arm Panchromatic & Multi-Messenger Instrument Atlas (D079-D112)
--------------------------------------------------------------------------------
 Bytes   Format  Units          Label                    Explanations
--------------------------------------------------------------------------------
   1-  3 I3      ---            arm_index                Spectral arm sequence index (1-104)
   5- 24 A20     ---            instrument_id            Canonical facility/instrument identifier
  26- 53 A28     ---            facility                 Observatory / space mission / array
  55- 74 A20     ---            arm_id                   Specific grating, receiver band, or detector arm
  76- 91 A16     ---            regime                   Spectral or multi-messenger regime
  93-103 E11.4   um             wave_min_um              Minimum rest/obs wavelength in micrometers
 105-115 E11.4   um             wave_max_um              Maximum rest/obs wavelength in micrometers
 117-127 E11.4   eV             e_min_ev                 Minimum photon or neutrino energy in eV
 129-139 E11.4   eV             e_max_ev                 Maximum photon or neutrino energy in eV
 141-155 A15     ---            res_power                Nominal resolving power R = lambda/dlambda
 157-161 A5      ---            first_phase              Survey phase where arm first entered
 163-175 A13     ---            scale_regime             Physical coupling scale (BEAMED_10M/HE_ISOTROPIC/NU)
     177 I1      ---            is_primary_spec          1 if primary unit in cumulative tally
--------------------------------------------------------------------------------

Byte-by-byte Description of file: table4_panchromatic_bridge_matrix_2695cells.mrt (2695 rows)
Title: Panchromatic Multi-Phase Science & Control Bridge Matrix (2,695 Cells, 197 Science Bridges)
--------------------------------------------------------------------------------
 Bytes   Format  Units          Label                    Explanations
--------------------------------------------------------------------------------
   1- 16 A16     ---            star                     Multi-phase bridge star identifier
  18- 43 A26     ---            common_name              Common stellar designation
  45- 49 A5      ---            phase_id                 Survey phase identifier (D079-D112)
  51- 72 A22     ---            instrument               Instrument identifier
  74-111 A38     ---            spectral_regime          Regime string for cell
 113-140 A28     ---            band_id                  Representative calibration/search band ID
 142-151 F10.4   pc             dist_pc                  Target distance in parsecs
 153-163 E11.4   um             wave_um                  Representative wavelength in micrometers
 165-175 E11.4   mA             ew_lim_mA                Equivalent width upper limit (milli-Angstrom)
 177-188 E12.5   erg/cm2/s      flux_lim_cgs             Narrowband flux upper limit
 190-201 E12.5   MW             l_iso_mw                 Isotropic luminosity upper limit (EM or nu)
 203-214 E12.5   kW             p_beam_10m_kw            10m diffraction-beamed EIRP (blank for HE/IceCube)
 216-227 E12.5   W              p_beam_10m_w             10m diffraction-beamed EIRP in Watts
     229 I1      ---            verified_eti             Verified ETI detections (0)
--------------------------------------------------------------------------------

Byte-by-byte Description of file: table5_bayesian_ftx_and_cwtfm.mrt (136 rows)
Title: Bayesian 95% Transmitter Occurrence Limits across Regimes, Power Thresholds, and Duty Cycles (D112)
--------------------------------------------------------------------------------
 Bytes   Format  Units          Label                    Explanations
--------------------------------------------------------------------------------
   1- 22 A22     ---            regime                   Physical scaling regime
  24- 51 A28     ---            cohort                   Target cohort name
  53- 56 I4      ---            n_cohort_total           Total stars in cohort
  58- 71 A14     ---            threshold_unit           Transmitter threshold unit
  73- 90 A18     ---            power_threshold          Power threshold or ANY_CALIBRATED
  92- 96 F5.2    ---            duty_cycle_eta           Assumed transmitter duty cycle eta
  98-103 F6.4    ---            c_cal                    Calibration recovery completeness
 105-108 I4      ---            n_sensitive              Stars reaching threshold sensitivity
 110-117 F8.3    ---            n_eff                    Effective completeness-weighted sample size
 119-126 F8.4    %              f95_uniform_pct          95% upper bound f_tx under Uniform(0,1) prior
 128-135 F8.4    %              f95_jeffreys_exact_pct   Exact 95% Beta(0.5, N_eff+0.5) Jeffreys upper bound
 137-144 F8.4    %              f95_clopper_pct          95% frequentist Clopper-Pearson upper bound
     146 I1      ---            verified_eti             Verified ETI detections (0)
--------------------------------------------------------------------------------

Byte-by-byte Description of file: table5b_cwtfm_benchmark.mrt (7 rows)
Title: Cosmic Haystack / CWTFM Survey Benchmark Comparison (D112 vs. Literature)
--------------------------------------------------------------------------------
 Bytes   Format  Units          Label                    Explanations
--------------------------------------------------------------------------------
   1- 32 A32     ---            survey_or_cohort         Survey or benchmark cohort identifier
  34- 63 A30     ---            reference                Bibliographic reference
      65 I1      ---            is_this_work             1 if this work else literature comparison
  67-112 A46     ---            regime_and_band          Wavelength/energy span description
 114-118 I5      ---            n_stars                  Number of stars/targets surveyed
 120-126 F7.3    oct            spectral_octaves         Spectral octave span covered
 128-135 F8.4    ---            nu_rel_cwtfm             Relative frequency span factor for CWTFM
 137-150 A14     kW             median_p10m_kw           Median 10m beamed power limit
 152-162 E11.4   W              median_eirp_w            Median isotropic equivalent EIRP (Watts)
 164-174 E11.4   ---            cwtfm_eirp_score         Continuous Waveform Transmitter Figure of Merit
 176-185 A10     %              f95_uniform_pct          95% steady occurrence rate limit (%)
--------------------------------------------------------------------------------

Byte-by-byte Description of file: table6_companion_archives_38manifest.mrt (38 rows)
Title: Cryptographic Manifest of All 38 Prospectively Locked Companion Archives (A-AL)
--------------------------------------------------------------------------------
 Bytes   Format  Units          Label                    Explanations
--------------------------------------------------------------------------------
   1-  4 A4      ---            archive_code             Companion Archive letter code (A-AL)
   6- 15 A10     ---            phase_span               Phases sealed in archive
  17- 88 A72     ---            filename                 Canonical archive zip filename
  90- 99 I10     B              bytes                    Exact compressed archive size in bytes
 101-108 F8.4    MiB            mib                      Archive size in MiB
 110-173 A64     ---            sha256                   SHA-256 cryptographic digest
 175-234 A60     ---            milestone_summary        Cumulative milestone summary
--------------------------------------------------------------------------------
