# LS7K: mission response provenance

Assessed 14 September 2026. File measurements are in
[the input inventory](results_ls7k_inputs/inventory.json); this document records
what the primary literature establishes and what it leaves unresolved.

| Input or relationship | Established description | Remaining requirement |
|---|---|---|
| Processed target pixels | FLUX contains calibrated, cosmic-ray-cleaned, background-subtracted pixels. LC PDC metadata do not identify the processing of this pixel array. [SDPDD, tables 8 and 13](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf) | A shifted image proxy is not automatically the response of these processed pixels. |
| POS_CORR1/2 | Local motion in detector column/row, in pixels, with pointing, differential velocity aberration and thermal contributions. [SDPDD, tables 8 and 13](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf) | The inspected documentation does not identify the exact 2020 fast-cadence estimator, temporal kernel, reference realization, covariance or target exclusion. |
| Centroids | MOM_CENTR and PSF_CENTR are target photometry/PSF-derived quantities. [SDPDD, table 13](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf) | LS7J found all PSF values missing. MOM values cannot simply be declared independent of an injected source pulse. |
| Time | TIME minus TIMECORR removes the barycentric light-travel correction; TIME refers to cadence midpoint. [SDPDD, target-pixel timing and headers](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf) | Inspect the engineering file's own time system before joining. LS7J's cadence-ID join does not establish a timing error. |
| PRF calibration | Commissioning-derived UPDATED_2.0 models apply from sector 4 onward. Each CCD has a 5-by-5 location grid; each FITS model samples a 13-by-13-pixel footprint at 9-by-9 subpixel phases and includes an uncertainty image. [Mission model README](https://archive.stsci.edu/missions/tess/models/prf_fitsfiles/start_s0004/00README.txt) | File availability and nominal applicability do not establish accuracy for these particular processed frames. |
| PRF coordinate convention | The model documentation warns of a 44-column offset related to collateral pixels, and quotes roughly 1–5% interpolation accuracy. [Mission model README](https://archive.stsci.edu/missions/tess/models/prf_fitsfiles/start_s0004/00README.txt) | Determine the actual header-to-header mapping before applying an offset. Image interpolation accuracy is not a calibrated uncertainty on a small-motion derivative or pulse distortion. |
| Engineering source | MAST documents quaternion and engineering FITS products under the mission engineering archive. [Official data-products page](https://archive.stsci.edu/missions-and-data/tess/data-products) | A listed file is not yet a verified time series. LS7K inventories matching sector links without downloading or aligning their values. |

The pipeline design describes PSF fits to bright stars to estimate pointing and
focus. This is design-level evidence for an ensemble-derived motion product,
not a specification of the POS_CORR implementation in the two restored
20-second releases. In particular, it does not establish whether TIC 307210830
contributes to that estimate.
[Jenkins et al. 2016, The TESS Science Processing Operations Center, SPIE 99133E](https://heasarc.gsfc.nasa.gov/docs/tess/docs/jenkinsSPIE2016-copyright.pdf),
DOI 10.1117/12.2233418.

## Match the original releases

The restored sector-29 light curve is DR43, camera 4/CCD 3. Its release notes
state that camera 4 alone supplied guiding in both orbits 65 and 66.
[Sector 29 DR43, section 1.2](https://archive.stsci.edu/missions/tess/doc/tess_drn/tess_sector_29_drn43_v02.pdf).

The restored sector-32 product is DR48, camera 4/CCD 4. Camera 4 guided in orbit
71; cameras 1 and 4 guided in orbit 72. The reported star-tracker issue delayed
observations before their start; the notes report no other scientific effect.
[Sector 32 DR48, section 1.2](https://archive.stsci.edu/missions/tess/doc/tess_drn/tess_sector_32_drn48_v02.pdf).

Both release notes show detrended quaternion plots binned over one minute and
one hour; these plots are not the cadence-level engineering input.
[DR43](https://archive.stsci.edu/missions/tess/doc/tess_drn/tess_sector_29_drn43_v02.pdf),
[DR48](https://archive.stsci.edu/missions/tess/doc/tess_drn/tess_sector_32_drn48_v02.pdf).
Sharing the guiding camera does not prove that this target was a guide star.
Guide membership and estimator weights remain unverified. Neither the guide
configuration nor the pre-observation anomaly is an identified cause of
LS7J's negative result.

## Consequences for the next model

The mission offers a physical response family worth inspecting: the PRF
location/phase grid and its uncertainties. This supports a coordinate and
response benchmark after the actual files are checked. It does not justify
fitting a gain, sign, lag or profile to repair LS7J.

A later specification must distinguish rigid pointing from local DVA/thermal
motion; map absolute detector coordinates and subpixel phase explicitly;
account for finite stamp boundaries, the target's flux normalization and
processed-pixel background handling; and propagate the limits of the
calibration. Commissioning PRF uncertainty does not automatically include
sector-specific focus, jitter, color dependence or pipeline residuals.

Upstream signal protection is unresolved: digital additions to saved pixels
leave saved motion estimates fixed. Passing that digital protection test does
not show that the original estimator would ignore the same physical pulse.
Either establish target exclusion and estimator provenance, bound that
coupling, or declare it an explicit limitation of any subsequent benchmark.

There is no adopted detector, new candidate, added observing coverage or
unused-sector evaluation in this input assessment.
