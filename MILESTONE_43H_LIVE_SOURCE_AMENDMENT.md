# M43H amendment: HDF5 integration qualified; enable the fixed live anchors

The initial protocol recorded the installation tool's cancelled network-approval
response. During its full-size fixture run, both dependencies became available.
That run still kept the HDF5 integration gate closed, correctly making no remote
request. Preserve its result as `fixture_qualification.json` and its original
configuration as `config/m43h_widened_source_fixture.json`. The original package
limitation is historical; it is not the current reason to stop.

Actual local HDF5 integration now passes using h5py 3.16.0, HDF5 2.0.0,
hdf5plugin 7.1.0 and NumPy 2.3.5. Both gzip and Bitshuffle/LZ4 files were decoded
through the bounded sparse file interface using explicitly simulated HTTP replies.
The tests interrupted after one row, resumed the other two, compared exact raw
hyperslabs and sorted normalization, rejected a changed header and completed a
restart with zero new HTTP requests. The six local HDF5 rows are additional to
the 32 full-size dataset-facade rows; neither is telescope evidence.

The integration receipt pins the implementation hashes and runtime. Publish it,
the original fixture receipts, this amendment, the current code and updated config
before enabling a live invocation. No bank, window, scan or numerical selection
changes. The only new code adds request counters and qualified-runtime/filter
provenance to the prospective live branch; integration was repeated against that
exact implementation before this freeze.

Run only epoch1_on and epoch1_off at m37_1412p5, all sixteen integrations each,
with the original frozen M43F interval [163032021, 164164291). Compare each complete
source's normalization against the sorted reference. Publish source receipts and
range-plan/checkpoint ancestry, plus separate counts of attempted/completed HEAD
and range requests and accepted bytes. An attempt may fail; preserve its exact
error and any committed partial-row count and do not count it as an attested source.

Source/checkpoint payloads remain intermediate working inputs. Publish derived
receipts and reproduction code, not raw telescope arrays. No spectral filter,
track score, recovery measurement, candidate ranking or calibration is part of
this source-only gate. A pass supplies the sources needed for the next separately
qualified real-data cache/score anchor. A failed transport/identity/normalization
check remains a failed or incomplete live gate, regardless of passed local tests.

The earlier authorization includes these downloads/reads and publication. No new
owner permission is requested by this amendment. Network/tool enforcement still
applies; do not work around a rejected route.
