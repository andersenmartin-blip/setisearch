# Milestone 17 selected-metadata attempt 1

Status: **TECHNICAL FAIL-CLOSED STOP; NO SPECTRAL CONTACT**.

GitHub Actions run `32571508763` verified the frozen GJ 849 selection, the two
reserved cadence identities, all prior provenance hashes, and the exact NASA
Exoplanet Archive query. The query returned the unique GJ 849 b composite
record, but the script then stopped because `hd_name` was null.

An HD catalogue alias is not needed for the orbital projection or target
identity. The required HIP identity, sky position, distance, parallax, proper
motion, radial velocity, and orbital fields remain mandatory. The corrected
query script therefore changes only the completeness assertion: `hd_name`
remains requested and preserved but may be null.

No telescope product was opened and no spectral dataset value was read. This
attempt produced no metadata artifact and no search configuration.
