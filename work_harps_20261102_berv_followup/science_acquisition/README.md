# Two fixed archival spectra for the HD122640 frame comparison

The [prospective plan](PLAN.json) selects the minimum and maximum recorded BERV from the two independently checked seasonal headers. The exact May 2017 and January 2018 identities, raw progenitors and prior selection are fixed before downloading either spectrum. These are additional archival follow-up inputs; the original 300-exposure survey and 669 V2 dispositions remain unchanged.

The [direct-file contract](DIRECT_FILE_CONTRACT.json) distinguishes the downloadable FITS file from the ObsCore DataLink metadata URL. Two anonymous HTTPS requests are allowed, one per fixed product, with a 60-second and 16 MiB bound each, no redirects and no retries. A failure preserves its response and leaves later slots explicitly unattempted. No automatic substitution is permitted.

`download_inputs.py` requires a SHA-bound `ROOT_RELEASE.json` after exact public readback of the [freeze](PREFLIGHT_FREEZE.json). It records exact payload bytes and hashes without interpreting any spectral array. The separate comparison runner verifies primary and table headers, including identity, BERV, resolving power, fiber mode, barycentric air wavelength units and flux units, before accessing any new array. Failed compatibility gates remain blocked slots.

The unchanged event-specific method is documented in [the comparison plan](../prospective_comparison/PLAN.json). The six HD122640 events can receive two new epoch comparisons. The four HD135204 events have no newly selected exposure under this bounded search. All ten remain provisionally unresolved; profile comparisons alone cannot establish photon origin, a laser candidate or calibrated sensitivity.

Downloaded products are an ignored local working cache. Exact original FITS bytes will be retained in checksum-bound compressed archive parts and a restore script after acquisition. This prospective README does not assert that acquisition or comparison has completed; consult the acquisition manifest and subsequent result report.
