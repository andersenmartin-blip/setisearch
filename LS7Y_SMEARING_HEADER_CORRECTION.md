# LS7Y smearing-header shape correction — 19 September 2026

The second LS7Y execution completed the fixed bounded transfers but stopped
before computing the image diagnostics because the implementation required the
`SCI_COR_SmearingRow` IMAGE extension to have exactly the two dimensions
`200 x 432`.

The already fixed scientific contract only requires 200 smearing values per
subarray cadence and 432 cadences. FITS may encode singleton/intermediate axes
without changing the flattened image payload. The extension data size is
691,200 bytes = 200 x 432 x 8 bytes.

Before rerunning, the structural check is corrected to require:

- BITPIX = -64;
- NAXIS1 = 200, so one contiguous row contains 200 float64 values;
- the product of every remaining NAXIS dimension = 432;
- total payload = 691,200 bytes.

The selected byte offsets remain `SMEAR_DATA_START + cadence*200*8` and the
same two 31-cadence contexts are read. No candidate score, image metric or
classification from LS7Y was produced before this correction. No scientific
threshold, aperture, context, missing-pixel rule or interpretation gate is
changed.
