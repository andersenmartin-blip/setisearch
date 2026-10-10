# Decimal HDF coordinates and a nominal GBT metadata gate

This separate V3 family preserves the old core, wrapper, fixtures and actual
ineligible result. The prior packed SIGPROC conversion does not apply to these
HDF5 attribute conventions. The exact pinned primary evidence is
PRIMARY_COORDINATE_AND_BEAM_EVIDENCE.json, SHA256
d8f05ea08d0f665039910069666b5303603cdf39344b02c502fa163f6af40df0,
1325 bytes. Blimpy H5Reader.read_header interprets src_raj as decimal hours and
src_dej as decimal degrees. The new core therefore multiplies finite RA in
[0,24) hours by 15 and preserves finite DEC in [-90,90] degrees.

The prospective consistency gate uses nominal FWHM radians =
1.18*(299792458/fmax_Hz)/100, from the primary GBT beam source. The highest
actual channel-center frequency in the common six-source grid supplies fmax;
no prior visit geometry is substituted. Every ON pair must be separated by
at most half that FWHM. Each control must be separated from every ON by at
least one FWHM. The three actual control names must remain distinct. This
approximate beam model is a metadata consistency rule. It does not certify
measured telescope response, blank sky, independent noise or a detection.

All original extraction bounds, typed attribute preservation, shape/datatype/
filter checks, exact six identities and grids, time cadence, native midpoint,
cache-only reader and layout-pointer evidence remain in force. No amplitude,
search kernel, frequency-frame selection or hypothesis rule changes here.
Source values and independent validation remain BLOCKED within qualification.

Scope schema is SETI_VISIT2019_SIX_HDF_HEADER_CACHE_QUALIFICATION_SCOPE_V3.
It carries the exact primary_coordinate_and_beam_evidence_pin and the core's
literal QUALIFICATION_RULES dictionary. Other pinned cache/planner/manifest
fields follow the generic qualification API. Its output_directory is a new
child of results/radio_visit2019_hdf_coordinates_v3_20261010; old attempted
directories cannot be reused. Limits remain 20 CPU seconds, 300 wall seconds,
512 MiB address space, 4 MiB output and 12 GiB shared workspace.

Result/source/execution schemas and downstream fields remain V1. Eligible
result status remains PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY and execution
status COMPLETE_CACHE_ONLY_METADATA_QUALIFICATION_NO_VALUES_ADMISSION.
New source metadata records identify the decimal HDF coordinate convention;
the aggregate includes actual nominal beam frequency/width and exact evidence
pin. The root separately verifies full child close and actual resource caps.

PURE_COORDINATE_BEAM_FIXTURE.py contains 15 entirely synthetic cases for decimal
units, RA wrap/bounds, signed DEC/poles, nonfinite rejection, angular separation,
known nominal beam value/inverse frequency, six-source eligibility, ON/OFF
beam boundaries and same-pointing rejection. Root alone executes it after
independent source review. The older 12-case packed fixture remains historical
and does not validate the HDF coordinate convention.

Production invocation after exact source/scope freeze and root GO:

```text
PYTHONPATH=/workspace/scratch/a8d1e29996d0/seti_fullpower_work/deps PYTHONDONTWRITEBYTECODE=1 PRIMARYPY ABS_qualify_once.py --scope ABS_NEW_SCOPE --expected-scope-sha256 EXACT_SHA --public-freeze-commit EXACT_40_HEX --root-go-metadata-only
```

The sole h5py import follows exact source/provenance admission and resource
limit installation. There is no HTTP, dataset-value read, chunk-index traversal
or signal-codec invocation. Unknown cache reads fail closed without filling gaps.
