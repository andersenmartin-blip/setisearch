# Milestone 16 header-screen URL correction

Status: **FIXED BEFORE THE CORRECTED CADENCE ROUTES ARE OPENED**.

Attempt 1 established that the discovery API's filter-decorated cadence URLs
return empty record lists. The corrected run changes only URL serialization:

- `-grades:fine;-76697` becomes `--76697`;
- the same transformation is applied to IDs 63424, 65393, 66869, 67073,
  67169, 82035, 73890, 74424, and 70291.

The five hosts, planet templates, cadence IDs, ranking, geometry checks,
frequency-coverage requirement, and nearest-qualifying-host selection rule are
unchanged. The corrected run remains header-only and may not read an HDF5
spectral dataset value.
