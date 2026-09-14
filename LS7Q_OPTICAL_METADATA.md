# LS7Q: HiPERCAM metadata assessment

14 September 2026. **Assessment complete; a native pilot is not ready.**

The public XO-2b run below has promising header-derived time sampling for a
30–100-second optical study. Its raw-file transfer, calibration mapping and
per-frame quality contract remain unestablished. No science pixels were read,
no event was screened and no observing coverage or candidate is added.

This follows the optical-product reassessment in the two-week plan. It is an
exploratory metadata study, not a prospective detector experiment. The earlier
LS7P numerical result cannot currently be verified in the public branch;
[the reconciliation record](LS7P_PUBLICATION_RECONCILIATION.md) keeps that gap
separate from the observations established here.

## Inventory and selected input

The [GTC search form](https://gtc.sdc.cab.inta-csic.es/gtc/jsp/searchform.jsp)
was queried for HiPERCAM imaging between 16 March 2009 and 13 September 2025,
with 100 results per page and the archive's observing-date order. The interface
reported **1,035 matching products on 11 pages**. Only the first **100 rows**
were inspected and saved. This is not a census of all public observing runs:
the rows also include acquisitions and calibrations.

XO-2b was selected from the visible object names, before reading any science
flux. Three associated run headers and three calibration-related headers were
retrieved, together with the calibration listing and the observatory QC log.
Header and QC product identities agree.

| Product | Original run | Header type | Stored frame count |
|---|---|---|---:|
| 5070352 | run0013.fits | data | 11,152 |
| 5070347 | run0012.fits | acquisition | 120 |
| 5070345 | run0011.fits | acquisition | 136 |
| 5070341 | run0007.fits | flat | 256 |
| 5070335 | run0001.fits | bias | 101 |
| 5070343 | run0009.fits | data, named flux standard | 49 |

The science identity is **GTC70-24B / 0004A / 5070352**, beginning
27 February 2025 at 20:46:41.1959 UTC according to its header. Its primary
array dimensions imply **116,937,596,992 uncompressed data bytes**, excluding
FITS padding. The compressed transport size is unknown. This makes a full
download inappropriate as a first diagnostic; it does not prevent a correctly
documented subset transfer.

## Timing established from metadata

The recorded mode is OneWindow, without CCD clearing, with 1×1 binning.
The frame-transfer interval is 0.007818 seconds and the base cycle is
0.6520134 seconds. Channel skip counters differ, so a single EXPTIME value
cannot describe all five channels.

| CCD / header filter label | Skip count | Regular exposure (s) | Repeat interval (s) | Nominal real frames, including first |
|---|---:|---:|---:|---:|
| 1 / us | 19 | 13.0324500 | 13.0402680 | 557 |
| 2 / gs | 0 | 0.6441954 | 0.6520134 | 11,152 |
| 3 / NaI | 1 | 1.2962088 | 1.3040268 | 5,576 |
| 4 / is | 0 | 0.6441954 | 0.6520134 | 11,152 |
| 5 / zs | 0 | 0.6441954 | 0.6520134 | 11,152 |

These are nominal calculations, not measured usable-frame counts. The first
real exposure in each channel has a different duration; dummy frames and
individual GPS/timing flags must be handled explicitly. The saved summary
includes the first-exposure and timestamp-offset values. The calculation uses
the instrument's [timing specification](https://cygnus.astro.warwick.ac.uk/phsaap/hipercam/docs/html/timing/timing.html)
and is checked against the [official reader at a fixed source commit](https://github.com/HiPERCAM/hipercam/blob/6a0b9a9d9053b831517a0aa4f8935e8878c3fc13/hipercam/hcam.py).

The archive row displays exposure zero and an end time one day after its
start. In contrast, the header's frame count times nominal cycle is
7,271.2534368 seconds, while sequence start to file creation spans
7,272.9619 seconds, about 121.2 minutes. Neither quantity establishes exact
observing coverage. Actual per-frame timestamps remain unread. Even the
generic header EXPTIME differs from the timing-derived fast-channel exposure
by 15.4 microseconds.

## Calibration and access obstacles

The [QC log](https://gtc.sdc.cab.inta-csic.es/gtc/servlet/FetchProd?prog_id=GTC70-24B&obl_id=0004A&log_filename=GTC70-24B_0004a_qc.txt)
records that high humidity ended the observation before the requested block
was complete. It lists a bias and standards in addition to the flat shown by
the [calibration page](https://gtc.sdc.cab.inta-csic.es/gtc/jsp/viewprod.jsp?prod_id=GTC70-24B..0004A..5070352&modtype=CAL).
Therefore absence from that page alone would have missed relevant inputs.

The retrieved flat has the same window geometry and binning, but its third
filter label is **rs**, while the science label is **NaI**. Science read-speed
code is **1**; the listed bias, flat and inspected standard use **0**. The
bias is full-frame. These differences require a documented calibration
mapping; they do not by themselves prove the data unusable. The standard
does share the science filter labels. No compatible fast-bias correction,
NaI response, defect map or calibrated noise model has been established.
The generic GAIN=1 and RON=0 cards are not adopted as measured noise parameters.
The [instrument reduction guide](https://cygnus.astro.warwick.ac.uk/phsaap/hipercam/docs/html/reduction.html)
provides the relevant bias, flat, defect and aperture procedures.

A HEAD request to the actual science download returned HTTP 200 with
Content-Length **−28,101,029**, an invalid transport length. A browser GET
and one bounded `Range: bytes=0-0` request returned Bad Gateway. No raw body
bytes were obtained. These results establish a failure of the inspected
access path in this session, not permanent unavailability of HiPERCAM data.
The negative number is not a file-size estimate. No archive contact was sent.

## Verification and decision

The standard-library reproduction script parses the six saved HTML headers,
checks the 100 unique catalogue IDs, preserves input-type distinctions and
derives timing with decimal arithmetic. A separate path executes only the
inspected timing block and method from the checksum-pinned official source.
All **66 boundary/regular timing tuples** agree, including valid/dummy flags;
maximum absolute difference is **3.56×10⁻¹⁵ seconds**. This verifies the
arithmetic, not physical timing accuracy or native calibration.

**Decision: NOT_READY for science acquisition and qualification.** First
establish a bounded raw-data delivery with file identity and valid lengths,
the matching calibration set and the per-channel scene/timing contract. A
new protocol must specify any retained channels before science inspection;
do not silently substitute an r flat for NaI or impose an identical pulse
requirement in all filters. The signal hypothesis must distinguish a
broadband glint from a wavelength-specific emission search.

CHEOPS remains the secondary metadata-assessment route if a usable HiPERCAM
input package cannot be established. Its actual exposure/stacking and pixel
products must be checked before selection; it was not evaluated in LS7Q.
Unused TESS sectors and M43 panels remain closed.

[Reproduction, source identities and saved evidence](results_ls7q_metadata/README.md).
[Concrete continuation](LS7Q_CONTINUATION.md).

Based on data from the GTC Archive at CAB (CSIC-INTA). The GTC Archive is part
of the Spanish Virtual Observatory project funded by MCIN/AEI/10.13039/501100011033
through grant PID2023-146210NB-I00.
