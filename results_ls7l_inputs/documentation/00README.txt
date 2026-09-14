This repository contains TESS pixel response function (PRF) models and
data products.  The models are updated based on the improved pointing
performance starting in Sector 4, and are strictly valid only for
Sector 4 data and beyond.

A keword 'VERSION' was added to these fits files with value
'UPDATED_2.0' in order to distinguish these PRF models from the old
PRF models constructed for Sectors 1-3.  If additional versions of
the PRF are ever delivered, the number in this keyword will be
incremented.

The models were fit by SPOC to micro-dithered data taken during PRF
commissioning exercises.  See the Instrument Handbook for details on the data
collection.  These data were collected in 2018 July, and represent the
TESS pointing profile for science data taken after sector 4.

Files with PRF data are provided in .mat (proprietary MATLAB) format.
One file per TESS CCD exits.  The fundamental description of the PRF
is a two dimensional surface defined by the coefficients of a high
order polynomial.  The coefficients are stored hierarchically.  Each
file contains PRF models defined at gridpoints on the CCD spaced by
~2.4 degrees.  At each grid point, there is a different polynomial
surface for 121 sub-pixel locations.  Bilinear interpolation is used
to evaluated the PRF surfaces at sub-interval locations (both at the
sub-pixel and CCD grid levels).

Super-sampled images of the PRF at each 5x5 CCD gridpoint were also
created from the PRF model and exported as .mat files by the SPOC.
The POC converted these data into .fits files.  For each CCD
gridpoint, there is an associated .fits file.  The reference
row/column of the grid points are provided in the image file names and
.fits headers.  These reference locations define the center of the PRF
image in the TESS CCD coordinate system.  The images have 9x9
intra-pixel samples per physical TESS CCD pixel, and span 13x13
physical TESS CCD pixels.  The 'PHYSICAL' WCS solutions can be used to
convert the PRF image coordinates to the corresponding locations on
the TESS CCDs.  Each .fits file contains two extensions---the primary
header contains the PRF image data itself, and the 2nd extension
contains the uncertainties.

The TESS CCD coordinate systems are defined so that row,col = 1,1 is
the center of the lower left pixel of each CCD.  Note that the PRF
locations do not always map to "real" TESS pixels---in the adopted
coordinate system, there may be negative TESS pixels, or pixels larger
than the total number in the CCD imaging arrays (> 2048).  These
locations are well defined in the instrument's focal plane even though
no light-sensitive pixels are present.  Bilinear interpolation on the
images between the grid points can be used to estimate the PRF at
arbitrary locations and is accurate to 1--5\%.  This coordinate system
is offset from the FFIs/TPF coordinate system by 44 columns, owing to
the presence of collateral pixels in the science data products
(overscan regions).


This repository also includes the original scripts that convert the
.mat data to .fits files (export_mat2fits.m).

Directory contents:
cam1_ccd1/		| Camera/CCD directory.
cam1_ccd2/		| Camera/CCD directory.
cam1_ccd3/		| Camera/CCD directory.
cam1_ccd4/		| Camera/CCD directory.
cam2_ccd1/		| Camera/CCD directory.
cam2_ccd2/		| Camera/CCD directory.
cam2_ccd3/		| Camera/CCD directory.
cam2_ccd4/		| Camera/CCD directory.
cam3_ccd1/		| Camera/CCD directory.
cam3_ccd2/		| Camera/CCD directory.
cam3_ccd3/		| Camera/CCD directory.
cam3_ccd4/		| Camera/CCD directory.
cam4_ccd1/		| Camera/CCD directory.
cam4_ccd2/		| Camera/CCD directory.
cam4_ccd3/		| Camera/CCD directory.
cam4_ccd4/		| Camera/CCD directory.
export_mat2fits.m	| Matlab export script.
README.txt		| This README file.
tess_prf_camera_1.tgz	| Tar bundle containing all PRF FITS files from Camera 1.
tess_prf_camera_2.tgz	| Tar bundle containing all PRF FITS files from Camera 2.
tess_prf_camera_3.tgz	| Tar bundle containing all PRF FITS files from Camera 3.
tess_prf_camera_4.tgz	| Tar bundle containing all PRF FITS files from Camera 4.

Camera/CCD directory contents:
*-characterized-prf.mat	| Matlab PRF data file.
*-row????-col????.fits	| Super-sampled PRF at 5x5 grid point in FITS format.
*_spocprf.mat		| Super-sampled PRF at 5x5 grid point in Matlab format.
