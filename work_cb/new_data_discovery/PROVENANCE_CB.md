# Newly acquired HIP35136 radio powers

The source is the official UCBerkeleySETI/breakthrough repository, current
commit `9fbb457da1c1404495927c2527542b25d788a616`. The complete 71,565,694-byte
file `GBT/filterbank_tutorial/blc04_guppi_57563_69862_HIP35136_0011.gpuspec.0002.fil`
was acquired by an ordinary request to the repository's raw GitHub URL.
Git blob `6fd2b196909eb35099eb07b7ba6d551bbf445725` and the complete file SHA-256
were verified. No Berkeley archive host, proxy or replacement-host route was
requested. This is an independent author-published repository copy, not a
network workaround.

The original addition commit is `7e1852ad6c05351990cfea9b7a9aadda9a17b967`,
dated 2016-10-05, with the message “Add Filterbank Tutorial Jupyter Notebook
and supporting materials”. The same file/blob is present in that historical
tree. The current and original trees have no accompanying high-resolution
`.0000` file or ON/OFF sequence. The current tree also contains one small
selected HIP42814 ML NumPy file; it was not acquired or analyzed here.

## Meaning of the data

The official `Filterbank Tutorial (public).ipynb` explicitly opens the exact
filename. Its text defines filterbank files as time series of received power
spectra from the GBT and explicitly identifies the target as the Hipparcos
star HIP35136. It explains that evenly spaced spectral spikes are band-pass
filter artifacts and identifies the broad feature near 1420 MHz as hydrogen
21-cm emission. These are prior source descriptions, not discoveries from CB.

The original notebook bytes are retained as `Filterbank_Tutorial_original.ipynb`
with verified Git blob `7206492497d5102a14197179b2aa47f15d2d443d`.
`HIP35136_TUTORIAL_PROVENANCE.json` is an extracted source-cell aid, not a
substitute for the original file. `TUTORIAL_SOURCE_IDENTITY.json` binds the
original notebook bytes. Header and geometric metadata are separate JSON files.

The SIGPROC header names source HIP35136 and original raw file
`guppi_57563_69862_HIP35136_0011.0000.raw`, with telescope ID 6. The payload is
273 complete rows of 65,536 channels, one IF, 32-bit samples; there are no
partial trailing rows. The discovery process parsed only the header and
validated file/blob bytes. It did not inspect numeric power values.

## Scope limitations

This is one complete deposited **mid-resolution frequency subband**, not the
entire telescope observation or a complete cadence. Its channel width is
2861.02294921875 Hz and its nominal frequency-edge span is 187.5 MHz. Ordinary
few-Hz/s drift moves a signal less than one native channel over the observation;
this input cannot support a claim of a normal fine-resolution drift search.

No paired OFF scan is supplied. Any spectral or temporal feature found in CB
requires further discrimination and is not, on that basis, a SETI candidate.
No calibrated flux density, radiometric sensitivity or global false-alarm
probability follows from a descriptive normalized-power analysis.

The newly acquired bytes are historical observation data. Whether this exact
file was already exposed elsewhere in this project's earlier archive is being
checked separately; “newly acquired” alone does not establish new search coverage.

## Other bounded source check

PetchMa/DeepSeti master at `636768e9bbb97052295f69b4c1045dfd3ad49405` was
inspected through an untruncated recursive tree. It contained two named encoder
model HDF5 files and the same small selected HIP42814 NumPy artifact also present
in the official repository. No complete unselected observation or ON/OFF cadence
was established, and no payload was acquired from this repository. Searches
also returned other leads, but uninspected results are not counted as checked
or acquired datasets. No repeated request was made for the already exhausted
TOP8 data source or any prior blocked original archive.
