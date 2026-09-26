# Fixed HD 1461 official-metadata completion

HD 1461 was selected by the published original catalogue ordering before the
current archive checks. While its exact six-source identity check completes,
perform one fixed official NASA Exoplanet Archive `pscomppars` query for
`pl_name='HD 1461 b'`. The 18 selected fields are listed in
`scripts/radio_hd1461_metadata.py`: target aliases, ICRS position, proper motion,
parallax/distance, systemic radial velocity and composite orbit parameters.

Use only `https://exoplanetarchive.ipac.caltech.edu/TAP/sync`, with the exact
query encoded by the script. Maximum 1 MiB per response, 25 seconds per attempt,
at most two attempts and only a transient-network/server retry. Refuse redirects,
multiple records, changed schema or a target/HD/HIP identity mismatch. Preserve
the raw response, request, times, headers and hash. Missing numeric fields are
reported as missing rather than silently imputed; this is not permission to
invent an orbit or a source phase.

The script and this protocol must match a published freeze before execution.
Results go to a separate, non-overwritable `astrometry` subdirectory. No telescope
product, spectral value, amplitude, search score or new target is accessed by
this query. A complete metadata record only permits preparation of the new
target-specific geometry and control protocol. It cannot adopt M43AI, transfer
old calibration or authorize an unregistered spectral pilot.
